"""
Run the full LightIN reproduction: prints a consolidated results table, writes
results.json, and saves verification figures into figures/.

--quick runs the same pipeline with the seed sweeps and bootstraps cut down, and
writes results_quick.json and figures_quick/ so a quick run never overwrites the
full one. Its numbers are noisier and are not the ones the report quotes.
"""

import argparse
import json
import os
import platform
import time
import sys
from importlib.metadata import version
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from lightin import (unitary, nonunitary, nn_iris, ppuf, mrm, switching, throughput,
                     coupler, expressivity, recirculating, ppuf_recirc)
from lightin.metrics import enob, propagation_latency

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fit_fig4                       # noqa: E402  (sibling script)
import fit_fig4e                      # noqa: E402  (sibling script)

# Several modules print Greek letters. The Windows console codepage is usually cp1252,
# which cannot encode them, so the run dies partway through unless stdout is UTF-8.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FIGDIR = os.path.join(os.path.dirname(__file__), "..", "figures")
QUICK_FIGDIR = os.path.join(os.path.dirname(__file__), "..", "figures_quick")
_figdir = FIGDIR      # directory the current run writes figures to; main() sets it

QUICK_SEEDS = range(2)      # Iris seed sweep and both controls
QUICK_N_BOOT = 50           # every Fig 4d and Fig 4e bootstrap
FULL_SEEDS = range(10)
FULL_N_BOOT = 500

# Recirculating PUF. One solve of the 40-cell mesh costs about 2 ms against a fraction
# of a microsecond for the feed-forward matrix product, so the die and challenge counts
# are chosen to keep this block near five minutes. The headline evaluation uses the
# paper's own 100-die simulation size; the spread sweep, six more evaluations, is cut to
# 20 dies x 32 challenges and that reduction is recorded in the block.
RECIRC_DIES, RECIRC_CHALLENGES = 100, 128
RECIRC_SWEEP_DIES, RECIRC_SWEEP_CHALLENGES = 20, 32
QUICK_RECIRC_DIES, QUICK_RECIRC_CHALLENGES = 10, 16
QUICK_RECIRC_SIGMAS = (0.001, 1.05)
FULL_RECIRC_SIGMAS = (0.001, 0.01, 0.1, 0.5, 1.05, 3.0)
RECIRC_TOPOLOGY = ("4x4 square recirculating mesh, 40 cells, stated wiring "
                   "(not the paper's), rotational challenge grouping per preprint")
WIRING_AGREEMENT_TOL = 0.05

# Population sweeps. A PUF metric computed on a finite die sample has a sampling
# spread; ten independent populations measure it. 40 dies x 64 challenges x 10 seeds
# is about thirteen minutes across the three models, which is most of this script's
# runtime.
POP_SEEDS = range(10)
POP_DIES, POP_CHALLENGES = 40, 64
QUICK_POP_SEEDS = range(3)
QUICK_POP_DIES, QUICK_POP_CHALLENGES = 10, 16
NOISE_SIGMAS = (0.002, 0.005, 0.01, 0.02, 0.05)
QUICK_NOISE_SIGMAS = (0.01, 0.05)
PAPER_PUF_UNIQUENESS = 0.4997      # paper's 100-die simulated uniqueness


_SECTIONS = []      # [label, start, end] per numbered block, for the runtime summary


def section(label):
    """Print a numbered block's heading and time it.

    The block runtime is a number the report quotes and a budget the campaign is held to,
    so it is measured here rather than estimated afterwards from a stopwatch on the whole
    script. Each call closes the previous block, so the timings partition the run.
    """
    now = time.perf_counter()
    if _SECTIONS:
        _SECTIONS[-1][2] = now
    _SECTIONS.append([label, now, None])
    print(f"\n--- {label} ---")


def close_sections():
    """Stop the last block and return (label, seconds) sorted slowest first."""
    if _SECTIONS and _SECTIONS[-1][2] is None:
        _SECTIONS[-1][2] = time.perf_counter()
    return sorted(((lab, end - start) for lab, start, end in _SECTIONS),
                  key=lambda t: -t[1])


def figpath(name):
    """Path of a figure inside the directory this run writes to."""
    return os.path.join(_figdir, name)


NULL_SCAN_NM = (1540.0, 1600.0, 0.1)   # diagnostic grid for the T20 null


def mesh_fit_derived(f4_mesh, f4_proxy, design_nm=coupler.LAMBDA0):
    """Values §3, §5 and §6 quote that are arithmetic on the mesh fit, stored so each
    one has a path of its own.

    The T20 null is where the mesh routes least power to port 2. It is displaced from
    the wavelength at which the couplers are 50:50, because the path crosses four
    stages, and the size of that displacement is the argument for fitting the mesh
    rather than the single-coupler proxy. It is a grid scan, not arithmetic, so it is
    computed here rather than derived from the values above; the floor is pushed far
    down so that it cannot fill the null in.

    The rest measure the two bootstrap intervals against each other and against the
    design wavelength, which is where §6.1 argues the parametric interval is the more
    honest of the two.
    """
    lo, hi, step = NULL_SCAN_NM
    lam = np.arange(lo, hi + step / 2, step)
    depth = fit_fig4.mesh_t20_model(lam, f4_mesh["lambda0_nm"], f4_mesh["slope"], -300.0)
    null_nm = float(lam[int(np.argmin(depth))])

    pairs_width = f4_mesh["lambda0_pairs_p95_nm"] - f4_mesh["lambda0_pairs_p05_nm"]
    param_width = f4_mesh["lambda0_param_p95_nm"] - f4_mesh["lambda0_param_p05_nm"]
    pairs_gap = f4_mesh["lambda0_pairs_p05_nm"] - design_nm
    param_gap = f4_mesh["lambda0_param_p05_nm"] - design_nm
    return {
        "t20_null_nm": null_nm,
        "t20_null_displacement_nm": float(f4_mesh["lambda0_nm"] - null_nm),
        "null_scan_grid_nm": [lo, hi, step],
        "lambda0_pairs_width_nm": float(pairs_width),
        "lambda0_param_width_nm": float(param_width),
        "param_over_pairs_width": float(param_width / pairs_width),
        "design_wavelength_nm": float(design_nm),
        "pairs_p05_over_design_nm": float(pairs_gap),
        "param_p05_over_design_nm": float(param_gap),
        "pairs_p05_over_design_in_widths": float(pairs_gap / pairs_width),
        "param_p05_over_design_in_widths": float(param_gap / param_width),
    }


def cross_check(f4_mesh, f4e):
    """Each fitted model measured against the panel it was not fitted to.

    The cross state was fitted from Fig 4d and the bar state from Fig 4e, with the coupler
    constants DC_LAMBDA_3DB and DC_SLOPE held at their Fig 4d values throughout, so the
    two fits are independent and each can now be tested against the other's data. Nothing
    is refitted here.

    The Fig 4d model runs through switching.power_spectra, so it carries SIGMA_SPLIT and
    SIGMA_PHASE: adopting a Fig 4e spread would move the Fig 4d prediction whether or not
    anything else changed. The shipped spread is the assumed 0.02, so the "shipped" and
    "assumed" legs below are the same evaluation and agree by construction. What makes the
    block discriminate is the third leg: the same model at the Fig 4e fitted spread, which
    was not adopted. The difference between that and the shipped value is what adopting
    the fit would have cost, and it is the number behind calling the panel a consistency
    check rather than a fit.
    """
    lam, db = fit_fig4.load_points()
    shipped = (coupler.DC_LAMBDA_3DB, coupler.DC_SLOPE, switching.FIG4D_FLOOR_DB)
    fitted = f4e["sigma_split_fit"]["value"]
    after = fit_fig4.rms_db(fit_fig4.mesh_t20_model, lam, db, *shipped)
    before = _fig4d_rms_at_spreads(lam, db, shipped, fit_fig4e.SIGMA_ASSUMED,
                                   fit_fig4e.SIGMA_ASSUMED)
    at_fitted = _fig4d_rms_at_spreads(lam, db, shipped, fitted, switching.SIGMA_PHASE)
    lam_e, db_e = fit_fig4e.load_points()
    rms_e = fit_fig4e.rms_db(lam_e, db_e, switching.SIGMA_SPLIT, switching.SIGMA_PHASE)
    rms_e_before = fit_fig4e.rms_db(lam_e, db_e, fit_fig4e.SIGMA_ASSUMED,
                                    fit_fig4e.SIGMA_ASSUMED)
    rms_e_fitted = fit_fig4e.rms_db(lam_e, db_e, fitted, switching.SIGMA_PHASE)
    print(f"[cross-check] Fig 4d mesh model on its own 25 points, no refit: "
          f"{after:.2f} dB at the shipped spreads "
          f"(sigma_split={switching.SIGMA_SPLIT:.4f}, "
          f"sigma_phase={switching.SIGMA_PHASE:.4f}); "
          f"{before:.2f} dB at the 0.02 both spreads carried before the Fig 4e fit; "
          f"{f4_mesh['rms_db']:.2f} dB recorded in fig4d_mesh_fit, which refits "
          f"lambda0, slope and floor")
    print(f"[cross-check] Fig 4e bar model on its own {lam_e.size} points: "
          f"{rms_e:.2f} dB at the shipped spreads, {rms_e_before:.2f} dB at the 0.02 both "
          f"carried before the fit")
    print(f"[cross-check] at the Fig 4e fitted spread of {fitted:.4f}, which was NOT "
          f"adopted: Fig 4d {at_fitted:.2f} dB (shipped {after:.2f} dB), "
          f"Fig 4e {rms_e_fitted:.2f} dB (shipped {rms_e:.2f} dB)")
    return {"fig4d_rms_after_fig4e_fit_db": float(after),
            "fig4d_rms_at_fit_db": float(f4_mesh["rms_db"]),
            "fig4d_rms_at_assumed_spreads_db": float(before),
            "fig4e_rms_db": float(rms_e),
            "fig4e_rms_at_assumed_spreads_db": float(rms_e_before),
            "fig4d_rms_at_fitted_spread_db": float(at_fitted),
            "fig4e_rms_at_fitted_spread_db": float(rms_e_fitted),
            # What adopting the Fig 4e fitted spread would have bought on its own panel
            # and cost on the other: differences of the four RMS values above, stored so
            # that each one has a path of its own.
            "fig4e_rms_improvement_at_fitted_spread_db": float(rms_e_before - rms_e_fitted),
            "fig4d_rms_penalty_at_fitted_spread_db": float(at_fitted - before),
            "fitted_spread_not_adopted": float(fitted),
            "sigma_split": float(switching.SIGMA_SPLIT),
            "sigma_phase": float(switching.SIGMA_PHASE),
            "note": ("no parameter is refitted here; the Fig 4d numbers are the same "
                     "model on the same 25 points, evaluated at the shipped spreads, at "
                     "the 0.02 they also carry, and at the Fig 4e fitted spread that was "
                     "not adopted")}


def _fig4d_rms_at_spreads(lam, db, coupler_params, sigma_split, sigma_phase):
    """Fig 4d mesh RMS with the module's fabrication spreads temporarily overridden."""
    keep = (switching.SIGMA_SPLIT, switching.SIGMA_PHASE)
    switching.SIGMA_SPLIT, switching.SIGMA_PHASE = sigma_split, sigma_phase
    try:
        return fit_fig4.rms_db(fit_fig4.mesh_t20_model, lam, db, *coupler_params)
    finally:
        switching.SIGMA_SPLIT, switching.SIGMA_PHASE = keep


FIG4D_KEYS = ("model", "lambda0_nm", "slope_rad_nm", "floor_db",
              "lambda0_median_nm", "lambda0_p05_nm", "lambda0_p95_nm",
              "slope_median", "slope_p05", "slope_p95",
              "n_boot", "n_failed", "fit_range_nm", "rms_db")
XTALK_FIT_RANGE_NM = [1549, 1565]           # inside the digitized Fig 4d wavelengths
XTALK_EXTRAP_RANGE_NM = [1530, 1549]        # below the data; model only
FLOOR_NOTE = ("phenomenological floor fitted to Fig 4d; the mesh model has no floor "
              "term, so modelled crosstalk below this level is not reached on the chip")
ENV_PACKAGES = ("numpy", "scipy", "scikit-learn", "matplotlib")


def environment():
    """Interpreter and package versions that produced this results.json.

    The Iris accuracies move slightly with the scipy and scikit-learn versions, so the
    numbers below are only reproducible against the versions recorded here.
    """
    env = {"python_version": platform.python_version(), "platform": platform.platform()}
    env.update({pkg: version(pkg) for pkg in ENV_PACKAGES})
    return env


def _heat(ax, M, title):
    im = ax.imshow(np.abs(M), cmap="viridis", vmin=0, vmax=np.abs(M).max())
    ax.set_title(title, fontsize=10)
    ax.set_xticks(range(M.shape[1])); ax.set_yticks(range(M.shape[0]))
    for (i, j), v in np.ndenumerate(np.abs(M)):
        ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                color="w" if v < 0.6 * np.abs(M).max() else "k", fontsize=8)
    return im


def fig_unitary(u):
    U = u["random"]["random_1"]["target"]
    Ur = u["random"]["random_1"]["realised"]
    fid = u["random"]["random_1"]["fidelity"]
    fig, ax = plt.subplots(1, 2, figsize=(8, 3.6))
    _heat(ax[0], U, "|U| target (4x4 unitary)")
    _heat(ax[1], Ur, f"|U| realised on mesh\nfidelity = {fid:.5f}")
    fig.suptitle("Unitary matrix multiplication (Fig. 2h,i)", fontsize=11)
    fig.tight_layout(); fig.savefig(figpath("unitary.png"), dpi=140)
    plt.close(fig)


def fig_nonunitary(nu):
    fig, ax = plt.subplots(1, 2, figsize=(8, 3.6))
    _heat(ax[0], nu["target_scaled"], "|M| target (3x3 non-unitary)")
    _heat(ax[1], nu["realised"], f"|M| realised (SVD/diamond)\ncorr = {nu['modulus_corr']:.5f}")
    fig.suptitle("Non-unitary matrix multiplication (Fig. 2l,n)", fontsize=11)
    fig.tight_layout(); fig.savefig(figpath("nonunitary.png"), dpi=140)
    plt.close(fig)


def fig_iris(ir):
    cm = ir["confusion_percent"]
    names = [n[:3].upper() for n in ir["class_names"]]
    fig, ax = plt.subplots(figsize=(4.6, 4.2))
    im = ax.imshow(cm, cmap="Blues", vmin=0, vmax=100)
    ax.set_xticks(range(3)); ax.set_yticks(range(3))
    ax.set_xticklabels(names); ax.set_yticklabels(names)
    ax.set_xlabel("True class"); ax.set_ylabel("Predicted class")
    for (i, j), v in np.ndenumerate(cm):
        ax.text(j, i, f"{v:.0f}", ha="center", va="center",
                color="w" if v > 50 else "k", fontsize=11)
    ax.set_title(f"Iris unitary NN (Fig. 2o)\noffline acc = {100*ir['full_acc']:.2f}% "
                 f"(paper 94.67%)", fontsize=10)
    fig.colorbar(im, fraction=0.046, pad=0.04, label="% of true class")
    fig.tight_layout(); fig.savefig(figpath("iris_confusion.png"), dpi=140)
    plt.close(fig)


def fig_ppuf(pp):
    fig, ax = plt.subplots(figsize=(6, 3.8))
    ax.hist(pp["prop1_per_die"], bins=20, color="#4C72B0", edgecolor="k", alpha=0.85)
    ax.axvline(0.5, color="r", ls="--", label="ideal 0.5")
    ax.set_xlabel("Proportion of '1's per die (uniformity)")
    ax.set_ylabel("Number of dies")
    ax.set_title(f"PPUF over {pp['n_dies']} dies (Fig. 5)\n"
                 f"uniqueness = {100*pp['uniqueness']:.2f}% (paper 49.97%), "
                 f"uniformity = {100*pp['uniformity']:.2f}% (paper 50.15%)", fontsize=9.5)
    ax.legend()
    fig.tight_layout(); fig.savefig(figpath("ppuf.png"), dpi=140)
    plt.close(fig)


def fig_mrm(sw):
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    ax0 = ax[0]
    ax0.plot(sw["bias"], sw["monitoring"] / sw["monitoring"].max(),
             color="#C44E52", label="monitoring (norm.)")
    ax0b = ax0.twinx()
    ax0b.plot(sw["bias"], sw["er_db"], color="#4C72B0", label="ER (dB)")
    ax0.axvline(sw["lock_bias"], color="k", ls="--", lw=1, label="lock point")
    ax0.set_xlabel("Heater bias (a.u.)"); ax0.set_ylabel("Monitoring signal", color="#C44E52")
    ax0b.set_ylabel("Extinction ratio (dB)", color="#4C72B0")
    ax0.set_title("Differentiator monitoring & ER vs bias (Fig. 3c)", fontsize=10)

    # eye diagrams: locked vs unlocked
    t_l, eye_l = mrm.eye_data(sw["lock_bias"])
    t_u, eye_u = mrm.eye_data(0.0)
    for tr in eye_u[:200]:
        ax[1].plot(t_u, tr, color="#999999", lw=0.4, alpha=0.5)
    for tr in eye_l[:200]:
        ax[1].plot(t_l, tr, color="#55A868", lw=0.4, alpha=0.6)
    ax[1].set_title("Eye diagram: locked (green) vs unlocked (grey)\n(model only; SNR/Q are hardware)",
                    fontsize=9.5)
    ax[1].set_xlabel("Time (bit periods)"); ax[1].set_ylabel("Detected power (a.u.)")
    fig.tight_layout(); fig.savefig(figpath("mrm.png"), dpi=140)
    plt.close(fig)


def fig_switching(sw):
    cross = sw["cross"]
    lams = cross["lambdas"]; Tdb = cross["spectra_db"]; intended = cross["intended"]
    j = 0
    i_int = intended[j]
    fig, ax = plt.subplots(figsize=(6.4, 3.9))
    ax.plot(lams, Tdb[i_int, j], color="#55A868", lw=2,
            label=f"intended path (in{j}->out{i_int})")
    for i in range(Tdb.shape[0]):
        if i != i_int:
            ax.plot(lams, Tdb[i, j], lw=1, alpha=0.8, label=f"crosstalk -> out{i}")
    ax.axhline(-20, color="r", ls=":", lw=1, label="-20 dB")
    ax.set_xlabel("Wavelength (nm)"); ax.set_ylabel("Transmission (dB)")
    ax.set_ylim(-60, 2)
    ax.set_title("Switch transmission spectra, all-cross (Fig. 4d)\n(model; measured spectra are hardware)",
                 fontsize=9.5)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout(); fig.savefig(figpath("switching.png"), dpi=140)
    plt.close(fig)


def fig_expressivity(ex):
    rng = np.random.default_rng(0)
    gap = ex["haar_gap"]; dof = ex["dof"]
    rungs = [("single_theta", dof["single_theta"], "single-θ\n(Eq. 1 chip)"),
             ("single_theta+output_phases", dof["single_theta+output_phases"],
              "single-θ\n+ output φ"),
             ("two_dof_universal", dof["two_dof_universal"], "2-DOF MZI\n(universal)")]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for i, (key, d, label) in enumerate(rungs):
        vals = gap[key]
        ax.scatter(np.full_like(vals, i, dtype=float) + rng.uniform(-0.06, 0.06, len(vals)),
                   vals, s=28, alpha=0.7, color="#4C72B0", zorder=3)
        ax.scatter([i], [vals.mean()], marker="_", s=2200, color="#C44E52", zorder=4)
        ax.text(i, 0.36, f"{d} DOF", ha="center", fontsize=9, color="#333")
    ax.axhline(1.0, color="green", ls="--", lw=1, label="fidelity = 1 (universal)")
    ax.set_xticks(range(3)); ax.set_xticklabels([r[2] for r in rungs])
    ax.set_ylabel("Best-fit fidelity to Haar-random U(4)")
    ax.set_ylim(0.33, 1.03)
    ax.set_title("Single-θ PUC expressivity limit (paper Discussion)\n"
                 "dim U(4) = 16; universality needs the full 2-DOF mesh", fontsize=10)
    ax.legend(loc="center right")
    fig.tight_layout(); fig.savefig(figpath("expressivity.png"), dpi=140)
    plt.close(fig)


def fig_coupler():
    lams = np.linspace(1500, 1600, 200)
    kpow = coupler.dc_power_coupling(lams)
    ext = np.array([coupler.extinction_ratio_db(l) for l in np.linspace(1530, 1565, 36)])
    lam_e = np.linspace(1530, 1565, 36)
    lam_d, kdata = coupler._demo_measured_dataset()
    k0, slope, rms = coupler.fit_dc_dispersion(lam_d, kdata, lam0=coupler.DEMO_LAMBDA0)
    kfit = coupler.dc_power_coupling(lams, kappa0=k0, slope=slope)

    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
    ax[0].plot(lams, kpow, color="#4C72B0")
    ax[0].axhline(0.5, color="grey", ls=":")
    ax[0].set_title(f"Directional-coupler dispersion\n"
                    f"(3-dB at {coupler.DC_LAMBDA_3DB:.0f} nm only; design is 1560 nm)",
                    fontsize=9.5)
    ax[0].set_xlabel("Wavelength (nm)"); ax[0].set_ylabel("Power coupling κ")

    ax[1].plot(lam_e, ext, color="#55A868")
    ax[1].set_title("Single-θ MZI extinction ratio\n(coupler-imbalance limited)", fontsize=9.5)
    ax[1].set_xlabel("Wavelength (nm)"); ax[1].set_ylabel("Extinction ratio (dB)")

    ax[2].scatter(lam_d, kdata, s=20, color="#C44E52", label="demo 'measured'", zorder=3)
    ax[2].plot(lams, kfit, color="#4C72B0",
               label=f"CMT fit\nκ0={k0:.3f}, slope={slope:.4f}\nRMS={rms:.4f}")
    ax[2].set_xlim(1515, 1585)
    ax[2].set_title("CMT dispersion fit to data", fontsize=9.5)
    ax[2].set_xlabel("Wavelength (nm)"); ax[2].set_ylabel("Power coupling κ")
    ax[2].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(figpath("coupler.png"), dpi=140)
    plt.close(fig)


def fig_recirculating():
    import numpy as _np
    fig, ax = plt.subplots(2, 2, figsize=(11, 7))

    # (a) all-pass ring: SMN vs analytic
    lams, p_smn, p_ana, rms = recirculating.validate_ring(verbose=False)
    ax[0, 0].plot(lams, p_ana, color="#999", lw=3, label="analytic")
    ax[0, 0].plot(lams, p_smn, color="#C44E52", lw=1, ls="--", label="SMN solver")
    ax[0, 0].set_title(f"All-pass ring: feedback solver vs analytic\nRMS = {rms:.1e}",
                       fontsize=10)
    ax[0, 0].set_xlabel("Wavelength (nm)"); ax[0, 0].set_ylabel("Through transmission")
    ax[0, 0].legend(fontsize=8)

    # (b) add-drop ring: SMN vs analytic
    lams2, p_drop, p_ana2, rms2 = recirculating.validate_add_drop(verbose=False)
    ax[0, 1].plot(lams2, p_ana2, color="#999", lw=3, label="analytic")
    ax[0, 1].plot(lams2, p_drop, color="#4C72B0", lw=1, ls="--", label="SMN solver")
    ax[0, 1].set_title(f"Add-drop ring: drop port\nRMS = {rms2:.1e}", fontsize=10)
    ax[0, 1].set_xlabel("Wavelength (nm)"); ax[0, 1].set_ylabel("Drop transmission")
    ax[0, 1].legend(fontsize=8)

    # (c) FIR vs IIR
    lams3, p_ff, p_ring = recirculating.fir_vs_iir(verbose=False)
    ax[1, 0].plot(lams3, p_ff, color="#55A868", label="feedforward MZI (FIR)")
    ax[1, 0].plot(lams3, p_ring, color="#C44E52", label="recirculating ring (IIR)")
    ax[1, 0].set_title("Feedback adds poles: FIR vs IIR\n(same PUCs, larger function class)",
                       fontsize=10)
    ax[1, 0].set_xlabel("Wavelength (nm)"); ax[1, 0].set_ylabel("Transmission")
    ax[1, 0].legend(fontsize=8)

    # (d) engineered multi-resonance comb (6 rings on a bus)
    comb = recirculating.multi_ring_bus(6, base_um=600.0, detune=0.01)
    lams4 = _np.linspace(1548, 1552, 1500)
    p_comb = _np.array([abs(comb.transfer(l, (0, "L", 0), (5, "R", 0))) ** 2
                        for l in lams4])
    ax[1, 1].plot(lams4, 10 * _np.log10(p_comb + 1e-6), color="#8172B3")
    ax[1, 1].set_title("6-ring recirculating bus (6 PUCs)\nengineered multi-notch response",
                       fontsize=10)
    ax[1, 1].set_xlabel("Wavelength (nm)"); ax[1, 1].set_ylabel("Through (dB)")

    fig.suptitle("Recirculating mesh with feedback loops (paper: 4×4 square recirculating mesh)",
                 fontsize=11)
    fig.tight_layout(); fig.savefig(figpath("recirculating.png"), dpi=140)
    plt.close(fig)


def paired_logistic_minus_photonic(seed_sweep, logistic_baseline):
    """Per-seed logistic-minus-photonic accuracy difference, on the shared seeds.

    Both sweeps run the same seeds in the same order, and the seed fixes the split, so
    element k of one list and element k of the other describe the same train/test
    partition. Differencing them seed by seed removes the split-to-split variation that
    dominates the two separate means, and nothing is retrained here.

    Reports the mean and standard deviation of the difference plus how many seeds fall
    each way, so a difference smaller than the seed-to-seed spread is visible as such.
    """
    out = {}
    for key, prefix in (("full_acc_per_seed", "full"), ("test_acc_per_seed", "test")):
        d = np.array(logistic_baseline[key]) - np.array(seed_sweep[key])
        out[f"{prefix}_mean"] = float(d.mean())
        out[f"{prefix}_std"] = float(d.std(ddof=1)) if d.size > 1 else 0.0
        out[f"{prefix}_n_logistic_higher"] = int((d > 0).sum())
        out[f"{prefix}_n_equal"] = int((d == 0).sum())
        out[f"{prefix}_n_photonic_higher"] = int((d < 0).sum())
    return out


PUF_RECIRC_HEADING = "6b. Photonic PUF on the recirculating mesh"


def print_population_sweep(label, sweep):
    """One line per metric: mean, sample standard deviation and the per-seed range."""
    print(f"[PUF population/{label}] {sweep['n_seeds']} seeds x {sweep['n_dies']} dies "
          f"x {sweep['n_challenges']} challenges")
    for key in ("uniqueness", "uniformity", "reliability"):
        vals = sweep[f"{key}_per_seed"]
        print(f"[PUF population/{label}]   {key:<12} "
              f"{100*sweep[key + '_mean']:6.2f}% +/- {100*sweep[key + '_std']:.2f}%  "
              f"(min {100*min(vals):.2f}%, max {100*max(vals):.2f}%)")


def print_noise_sweep(label, rows):
    print(f"[PUF noise/{label}] metrics vs the assumed per-cell measurement noise")
    print(f"[PUF noise/{label}]   {'sigma':>7} {'uniqueness':>11} {'uniformity':>11} "
          f"{'reliability':>12} {'ties':>8}")
    for r in rows:
        print(f"[PUF noise/{label}]   {r['meas_noise_sigma']:>7.3f} "
              f"{r['uniqueness']:>11.4f} {r['uniformity']:>11.4f} "
              f"{r['reliability']:>12.4f} {r['tie_fraction']:>8.4f}")


def paired_uniqueness(ff_sweep, rc_sweep, paper=PAPER_PUF_UNIQUENESS):
    """Per-seed uniqueness difference, recirculating minus feed-forward.

    Matched by population seed rather than by die: the two models have different cell
    counts, so one seed gives corresponding draws, not identical dies. The verdict follows
    the rule used for the Iris comparison -- within the seed-to-seed spread when the
    absolute paired mean is smaller than the paired standard deviation, a consistent
    difference otherwise.
    """
    ff = np.asarray(ff_sweep["uniqueness_per_seed"], dtype=float)
    rc = np.asarray(rc_sweep["uniqueness_per_seed"], dtype=float)
    d = rc - ff
    std = float(d.std(ddof=1)) if d.size > 1 else 0.0
    out = {
        "difference_per_seed": [float(x) for x in d],
        "mean": float(d.mean()),
        "std": std,
        "paper_uniqueness": paper,
        "n_seeds_recirc_closer": int((np.abs(rc - paper) < np.abs(ff - paper)).sum()),
        "n_seeds_feedforward_closer": int((np.abs(ff - paper) < np.abs(rc - paper)).sum()),
        "n_seeds_equal": int((np.abs(rc - paper) == np.abs(ff - paper)).sum()),
        "within_seed_spread": bool(abs(float(d.mean())) < std),
        "note": ("recirculating C4_FREE_1 minus feed-forward, matched by population seed; "
                 "the two models have different cell counts, so a seed gives corresponding "
                 "draws rather than identical dies"),
    }
    verdict = ("within the seed-to-seed spread" if out["within_seed_spread"]
               else "a consistent difference")
    print(f"[PUF paired] recirculating minus feed-forward uniqueness: "
          f"{100*out['mean']:+.2f}% +/- {100*out['std']:.2f}% over "
          f"{len(d)} seeds -> {verdict}")
    print(f"[PUF paired] closer to the paper's {100*paper:.2f}%: "
          f"recirculating on {out['n_seeds_recirc_closer']} seeds, "
          f"feed-forward on {out['n_seeds_feedforward_closer']}, "
          f"tied on {out['n_seeds_equal']}")
    return out


def recirc_puf_block(quick=False, feedforward=None):
    """The ppuf_recirc results block: both wirings, their comparison, the robustness check.

    The vertex wiring is a stated choice, not the paper's, so every number here is
    reported for both selected wirings and the two are required to agree on uniqueness.
    """
    n_dies = QUICK_RECIRC_DIES if quick else RECIRC_DIES
    n_ch = QUICK_RECIRC_CHALLENGES if quick else RECIRC_CHALLENGES
    sw_dies = QUICK_RECIRC_DIES if quick else RECIRC_SWEEP_DIES
    sw_ch = QUICK_RECIRC_CHALLENGES if quick else RECIRC_SWEEP_CHALLENGES
    sigmas = QUICK_RECIRC_SIGMAS if quick else FULL_RECIRC_SIGMAS
    pop_seeds = QUICK_POP_SEEDS if quick else POP_SEEDS
    pop_dies = QUICK_POP_DIES if quick else POP_DIES
    pop_ch = QUICK_POP_CHALLENGES if quick else POP_CHALLENGES
    noise_sigmas = QUICK_NOISE_SIGMAS if quick else NOISE_SIGMAS

    per_wiring = {}
    for name, rule in ppuf_recirc.wirings():
        res = ppuf_recirc.evaluate(n_dies=n_dies, n_challenges=n_ch, wiring=rule)
        sweep = ppuf_recirc.sensitivity_sweep(sigmas=sigmas, n_dies=sw_dies,
                                              n_challenges=sw_ch, wiring=rule)
        pop = ppuf_recirc.population_sweep(seeds=pop_seeds, n_dies=pop_dies,
                                           n_challenges=pop_ch, wiring=rule)
        per_wiring[name] = {
            "population_sweep": pop,
            "uniqueness": res["uniqueness"],
            "uniformity": res["uniformity"],
            "reliability_intra_die_HD": res["reliability_intra_die_HD"],
            "tie_fraction": res["tie_fraction"],
            "tie_tol": ppuf.TIE_TOL,
            "measurement_noise_sigma": ppuf.MEAS_NOISE_SIGMA,
            "measurement_noise_source": ppuf.MEAS_NOISE_SOURCE,
            "sensitivity_sweep": sweep,
            "challenge_bits": res["challenge_bits"],
            "response_bits": res["response_bits"],
            "live_pairs": res["live_pairs"],
            "n_meas": ppuf_recirc.N_MEAS_DEFAULT,
        }
        print(f"[PPUF-recirc/{name}] {n_dies} dies x {n_ch} challenges: "
              f"uniqueness {100*res['uniqueness']:.2f}%, "
              f"uniformity {100*res['uniformity']:.2f}%, "
              f"reliability {100*res['reliability']:.2f}%, "
              f"ties {100*res['tie_fraction']:.2f}%  "
              f"({res['challenge_bits']}-bit challenge, "
              f"{res['response_bits']}-bit response, {res['live_pairs']} live pairs)")
        print_population_sweep(f"recirculating {name}", pop)

    first = list(per_wiring)[0]
    per_wiring[first]["noise_sweep"] = ppuf_recirc.noise_sweep(
        sigmas=noise_sigmas, n_dies=pop_dies, n_challenges=pop_ch,
        wiring=dict(ppuf_recirc.wirings())[first])
    print_noise_sweep(first, per_wiring[first]["noise_sweep"])

    names = list(per_wiring)
    primary = per_wiring[names[0]]
    block = dict(primary)
    block.update({
        "n_dies": n_dies, "n_challenges": n_ch,
        "sweep_n_dies": sw_dies, "sweep_n_challenges": sw_ch,
        "noise_sweep_n_dies": pop_dies, "noise_sweep_n_challenges": pop_ch,
        "topology": RECIRC_TOPOLOGY,
        "primary_wiring": names[0],
        "wiring_names": names,
        "wiring_note": ("the vertex wiring is a stated choice, not the paper's; both "
                        "selected wirings are reported and required to agree"),
    })
    block.update(per_wiring)
    d_uq = abs(per_wiring[names[0]]["uniqueness"] - per_wiring[names[1]]["uniqueness"])
    block["wiring_robustness"] = {
        "uniqueness_difference": float(d_uq),
        "tolerance": WIRING_AGREEMENT_TOL,
        "wirings_agree": bool(d_uq < WIRING_AGREEMENT_TOL),
    }
    # The headline runs agree to d_uq above; the population sweeps average the sampling
    # spread out of that comparison, and their gap is the number the report quotes. It is
    # a difference of two values this block already holds, stored so that one path carries
    # it rather than the report doing the subtraction.
    pop_means = [per_wiring[name]["population_sweep"]["uniqueness_mean"]
                 for name in names]
    block["wiring_uniqueness_gap"] = float(abs(pop_means[1] - pop_means[0]))
    print(f"[PPUF-recirc] the two wirings agree on uniqueness to {d_uq:.4f} "
          f"(tolerance {WIRING_AGREEMENT_TOL}); their population means differ by "
          f"{100 * block['wiring_uniqueness_gap']:.3f} points")
    if feedforward is not None:
        block["vs_feedforward"] = {
            "uniqueness": float(primary["uniqueness"] - feedforward["uniqueness"]),
            "uniformity": float(primary["uniformity"] - feedforward["uniformity"]),
            "reliability_intra_die_HD": float(primary["reliability_intra_die_HD"]
                                              - feedforward["reliability_intra_die_HD"]),
            "note": ("recirculating minus feed-forward, both at the arm-length-derived "
                     "spread N(-0.08 um, 0.11 um)"),
            "paired_uniqueness": paired_uniqueness(
                feedforward["population_sweep"], per_wiring[names[0]]["population_sweep"]),
        }
        hdr = f"{'metric':<28}{'feed-forward':>14}{'recirculating':>15}{'difference':>13}"
        print("[PPUF compare] " + hdr)
        for key, lab in (("uniqueness", "uniqueness"),
                         ("uniformity", "uniformity"),
                         ("reliability_intra_die_HD", "reliability (intra-die HD)")):
            print(f"[PPUF compare] {lab:<28}{100*feedforward[key]:>13.2f}%"
                  f"{100*primary[key]:>14.2f}%{100*block['vs_feedforward'][key]:>12.2f}%")
    return block


def main(quick=False):
    """Run every module, write the results file, save the figures.

    quick=True cuts the Iris seed sweep to QUICK_SEEDS and both Fig 4d bootstraps to
    QUICK_N_BOOT, and redirects the outputs to results_quick.json and figures_quick/.
    Everything else, including the single fits, is identical to a full run.
    """
    global _figdir
    seeds = QUICK_SEEDS if quick else FULL_SEEDS
    n_boot = QUICK_N_BOOT if quick else FULL_N_BOOT
    _figdir = QUICK_FIGDIR if quick else FIGDIR
    results_name = "results_quick.json" if quick else "results.json"
    os.makedirs(_figdir, exist_ok=True)

    print("=" * 72)
    print("LightIN reproduction — running all modules"
          + ("  [quick mode]" if quick else ""))
    print("=" * 72)

    section("1. Unitary matrix multiplication")
    u = unitary.run()
    section("2. Non-unitary matrix multiplication")
    nu = nonunitary.run()
    section("3. Iris unitary neural network")
    ir = nn_iris.run(seeds=seeds)
    section("4. MRM wavelength locking (differentiator)")
    mr = mrm.run()
    section("5. Optical switching crosstalk")
    sw = switching.run()
    onchip_il = switching.onchip_insertion_loss()
    leak_mechanism = switching.leak_mechanism_check()
    paper_lo, paper_hi = switching.ONCHIP_IL_PAPER_RANGE_DB
    print(f"[switching] modelled on-chip insertion loss over 8 intended paths: "
          f"{onchip_il['min_db']:.2f} to {onchip_il['max_db']:.2f} dB; "
          f"paper measured {paper_lo:.2f} to {paper_hi:.2f} dB")
    section("6. Photonic PUF")
    pp = ppuf.run(n_dies=100)
    pop_seeds = QUICK_POP_SEEDS if quick else POP_SEEDS
    pop_dies = QUICK_POP_DIES if quick else POP_DIES
    pop_ch = QUICK_POP_CHALLENGES if quick else POP_CHALLENGES
    pp["population_sweep"] = ppuf.population_sweep(seeds=pop_seeds, n_dies=pop_dies,
                                                   n_challenges=pop_ch)
    print_population_sweep("feed-forward", pp["population_sweep"])
    section(PUF_RECIRC_HEADING)
    pr = recirc_puf_block(quick=quick, feedforward=pp)
    section("7. Throughput & energy")
    te = throughput.reproduce()
    section("8. CMT directional coupler (physical model)")
    cp = coupler.run()
    section("9. Single-theta PUC expressivity")
    ex = expressivity.run()
    section("10. Recirculating mesh with feedback loops")
    rc = recirculating.run()
    section("11. Fig 4d coupler dispersion fit (bootstrapped)")
    f4_all = fit_fig4.main(n_boot=n_boot,
                           fig_path=figpath("fig4_digitized.png"))
    f4 = {k: v for k, v in f4_all.items() if k in FIG4D_KEYS}
    f4_mesh = f4_all["mesh"]

    section("12. Fig 4e bar-state fabrication-spread fit (bootstrapped)")
    # Fig 4e sets its own resample count rather than sharing the Fig 4d one: its bootstrap
    # costs a fit per resample where Fig 4d's costs milliseconds, and the interval is
    # quoted only to be shown far narrower than the percentile dependence beside it.
    f4e = fit_fig4e.main(n_boot=n_boot if quick else fit_fig4e.ADOPTED_BOOT_N,
                         fig_path=figpath("fig4e_digitized.png"))
    xc = cross_check(f4_mesh, f4e)

    section("12a. Fig 4e diagonals vs the paper's on-chip insertion loss")
    f4e_diag = fit_fig4e.diagonal_summary()
    bar_il = fit_fig4e.bar_il_vs_digitized()

    paired = paired_logistic_minus_photonic(ir["seed_sweep"], ir["logistic_baseline"])
    print("\n--- Paired Iris comparison (logistic - photonic, same seeds) ---")
    for pfx, label in (("full", "full-set"), ("test", "held-out")):
        print(f"[Iris paired {label}] mean {100*paired[pfx + '_mean']:+.2f}% "
              f"+/- {100*paired[pfx + '_std']:.2f}%  "
              f"(logistic higher on {paired[pfx + '_n_logistic_higher']}, "
              f"equal on {paired[pfx + '_n_equal']}, "
              f"photonic higher on {paired[pfx + '_n_photonic_higher']} seeds)")

    print("\n--- Generating figures ---")
    fig_unitary(u); fig_nonunitary(nu); fig_iris(ir); fig_ppuf(pp)
    fig_mrm(mr); fig_switching(sw); fig_coupler(); fig_expressivity(ex)
    fig_recirculating()
    figs = sorted(os.listdir(_figdir))
    print("Saved:", ", ".join(figs))

    results = {
        "unitary": {
            "perm_routing_fidelity": [u["perm_1"]["routing_fidelity"],
                                      u["perm_2"]["routing_fidelity"]],
            "random_mean_fidelity": u["random_mean_fidelity"],
            "random_mean_modulus_corr": u["random_mean_modulus_corr"],
            "enob_at_sigma_0.0269": enob(0.0269),
        },
        "nonunitary": {
            "modulus_corr": nu["modulus_corr"], "max_abs_err": nu["max_abs_err"],
            "enob_at_sigma_0.0453": enob(0.0453),
        },
        "iris": {"offline_train_acc": ir["train_acc"], "test_acc": ir["test_acc"],
                 "full_acc": ir["full_acc"],
                 "seed_sweep": ir["seed_sweep"],
                 "identity_control": ir["identity_control"],
                 "logistic_baseline": ir["logistic_baseline"],
                 "paired_logistic_minus_photonic": paired,
                 # The identity control runs the same seeds on the same splits, so the
                 # difference of the two full-set means is what the unitary contributes.
                 "unitary_minus_identity_full_acc": float(
                     ir["seed_sweep"]["full_acc_mean"]
                     - ir["identity_control"]["full_acc_mean"])},
        "mrm": {"lock_bias": mr["lock_bias"], "max_er_db": float(mr["er_db"].max())},
        "switching": {
            "cross_xtalk_center_db": sw["cross"]["xtalk_center_db"],
            "bar_xtalk_center_db": sw["bar"]["xtalk_center_db"],
            "cross_worst_xtalk_cband_db": sw["cross"]["worst_xtalk_over_cband_db"],
            "bar_worst_xtalk_cband_db": sw["bar"]["worst_xtalk_over_cband_db"],
            "cross_structural_zeros": sw["cross"]["structural_zeros"],
            "bar_structural_zeros": sw["bar"]["structural_zeros"],
            "cross_worst_xtalk_fitrange_db": switching.worst_cross_xtalk_db(
                np.linspace(1549, 1565, 65)),
            "cross_worst_xtalk_extrapolated_db": switching.worst_cross_xtalk_db(
                np.linspace(1530, 1549, 77)),
            "fit_range_nm": XTALK_FIT_RANGE_NM,
            "extrapolated_range_nm": XTALK_EXTRAP_RANGE_NM,
            "chip_crosstalk_floor_db": switching.FIG4D_FLOOR_DB,
            "floor_note": FLOOR_NOTE,
            "fibre_to_fibre_loss_db": switching.insertion_loss_budget(),
            "onchip_il_min_db": onchip_il["min_db"],
            "onchip_il_max_db": onchip_il["max_db"],
            "onchip_il_paths": onchip_il["paths"],
            "onchip_il_paper_range_db": switching.ONCHIP_IL_PAPER_RANGE_DB,
            # Modelled minus measured, positive where the model is the less lossy of the
            # two. The nearest gap separates the two ranges; the other two compare the
            # ends. All three are differences of the four values above.
            "onchip_il_gap_nearest_db": float(onchip_il["min_db"] - paper_hi),
            "onchip_il_gap_least_lossy_db": float(onchip_il["max_db"] - paper_hi),
            "onchip_il_gap_most_lossy_db": float(onchip_il["min_db"] - paper_lo),
            "leak_mechanism_check": dict(
                leak_mechanism,
                # Forcing both couplers to an exact 50:50 split, in dB.
                cross_ideal_coupler_improvement_db=float(
                    leak_mechanism["cross_cell_leak_db_model"]
                    - leak_mechanism["cross_cell_leak_db_ideal_coupler"])),
            "bar_il_vs_fig4e": bar_il,
        },
        "ppuf": {"uniqueness": pp["uniqueness"], "uniformity": pp["uniformity"],
                 "population_sweep": pp["population_sweep"],
                 "reliability_intra_die_HD": pp["reliability_intra_die_HD"],
                 "tie_fraction": pp["tie_fraction"],
                 "tie_tol": ppuf.TIE_TOL,
                 "measurement_noise_sigma": pp["measurement_noise_sigma"],
                 "measurement_noise_source": pp["measurement_noise_source"],
                 # The factor by which the two metrics separate at the paper's spread.
                 "uniqueness_over_reliability": float(
                     pp["uniqueness"] / pp["reliability_intra_die_HD"]),
                 "sensitivity_sweep": pp["sensitivity_sweep"]},
        "ppuf_recirc": pr,
        "throughput_energy": te,
        "coupler": dict(
            {k: cp[k] for k in ("extinction_at_3db_db", "extinction_at_1560_db",
                                "extinction_at_1520_db", "link_budget_db")},
            demo_fit_kappa0=cp["fit_kappa0"],
            demo_fit_slope=cp["fit_slope"],
            demo_true_kappa0=cp["demo_true_kappa0"],
            demo_true_slope=cp["demo_true_slope"],
            demo_fit_lam0_nm=cp["demo_fit_lam0_nm"],
            power_coupling_at_1560=float(coupler.dc_power_coupling(1560.0)),
            # Recovered against generated, for the two demo parameters: kappa0 as a
            # magnitude and the slope as a fraction of the generator's value.
            demo_kappa0_abs_error=float(abs(cp["fit_kappa0"] - cp["demo_true_kappa0"])),
            demo_slope_offset_frac=float((cp["fit_slope"] - cp["demo_true_slope"])
                                         / cp["demo_true_slope"]),
            demo_fit_note=("recovered from the synthetic _demo_measured_dataset, "
                           "not from chip data"),
            extinction_note=("ideal null: model contains no loss or coupler imbalance, "
                             "so the extinction is unbounded"),
        ),
        "expressivity": {
            "dof": ex["dof"],
            "haar_fidelity_mean": {k: float(v.mean()) for k, v in ex["haar_gap"].items()},
            "realizable_unitary_fidelity": ex["realizable"],
            "coupler_ceiling_min_fidelity": float(ex["coupler_ceiling_fidelity"].min()),
            "coupler_ceiling_range_nm": [float(ex["coupler_ceiling_lambdas"].min()),
                                         float(ex["coupler_ceiling_lambdas"].max())],
            "coupler_ceiling_fidelity_at_1560": ex["coupler_ceiling_at_1560"],
        },
        "fig4d_fit": f4,
        "fig4d_mesh_fit": dict(f4_mesh,
                               digitization_sd_db=fit_fig4.DIGITIZATION_SD_DB,
                               # Mesh minus proxy: the model-form uncertainty on the
                               # coupler's 3-dB wavelength, from the two fits above.
                               lambda0_minus_proxy_nm=float(f4_mesh["lambda0_nm"]
                                                            - f4["lambda0_nm"]),
                               **mesh_fit_derived(f4_mesh, f4)),
        "fig4e_fit": f4e,
        "fig4e_diagonals": f4e_diag,
        "cross_check": xc,
        "recirculating": rc,
        "latency_on_chip_ps": propagation_latency(4.5e-3) * 1e12,
        "environment": environment(),
    }
    timings = close_sections()
    total = sum(t for _, t in timings)
    print(f"\n--- Block runtimes (total {total / 60:.1f} min) ---")
    for lab, t in timings:
        print(f"  {t / 60:6.2f} min  {t / total * 100:5.1f}%  {lab}")

    out = os.path.join(os.path.dirname(__file__), "..", results_name)
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote {os.path.abspath(out)}")
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true",
                    help="reduced seed sweep and bootstraps; writes results_quick.json "
                         "and figures_quick/")
    main(quick=ap.parse_args().quick)
