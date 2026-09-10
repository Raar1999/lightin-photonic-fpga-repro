"""
Run the full LightIN reproduction: prints a consolidated results table, writes
results.json, and saves verification figures into figures/.
"""

import json
import os
import platform
import sys
from importlib.metadata import version
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from lightin import (unitary, nonunitary, nn_iris, ppuf, mrm, switching, throughput,
                     coupler, expressivity, recirculating)
from lightin.metrics import enob, propagation_latency

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fit_fig4                       # noqa: E402  (sibling script)

# Several modules print Greek letters. The Windows console codepage is usually cp1252,
# which cannot encode them, so the run dies partway through unless stdout is UTF-8.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FIGDIR = os.path.join(os.path.dirname(__file__), "..", "figures")
FIG4D_KEYS = ("model", "lambda0_median_nm", "lambda0_p05_nm", "lambda0_p95_nm",
              "slope_median", "slope_p05", "slope_p95",
              "n_boot", "n_failed", "fit_range_nm", "rms_db")
XTALK_FIT_RANGE_NM = [1549, 1565]           # inside the digitized Fig 4d wavelengths
XTALK_EXTRAP_RANGE_NM = [1530, 1549]        # below the data; model only
FLOOR_NOTE = ("phenomenological floor fitted to Fig 4d; the mesh model has no floor "
              "term, so modelled crosstalk below this level is not reached on the chip")
ENV_PACKAGES = ("numpy", "scipy", "scikit-learn", "matplotlib")
os.makedirs(FIGDIR, exist_ok=True)


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
    fig.tight_layout(); fig.savefig(os.path.join(FIGDIR, "unitary.png"), dpi=140)
    plt.close(fig)


def fig_nonunitary(nu):
    fig, ax = plt.subplots(1, 2, figsize=(8, 3.6))
    _heat(ax[0], nu["target_scaled"], "|M| target (3x3 non-unitary)")
    _heat(ax[1], nu["realised"], f"|M| realised (SVD/diamond)\ncorr = {nu['modulus_corr']:.5f}")
    fig.suptitle("Non-unitary matrix multiplication (Fig. 2l,n)", fontsize=11)
    fig.tight_layout(); fig.savefig(os.path.join(FIGDIR, "nonunitary.png"), dpi=140)
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
    fig.tight_layout(); fig.savefig(os.path.join(FIGDIR, "iris_confusion.png"), dpi=140)
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
    fig.tight_layout(); fig.savefig(os.path.join(FIGDIR, "ppuf.png"), dpi=140)
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
    fig.tight_layout(); fig.savefig(os.path.join(FIGDIR, "mrm.png"), dpi=140)
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
    fig.tight_layout(); fig.savefig(os.path.join(FIGDIR, "switching.png"), dpi=140)
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
    fig.tight_layout(); fig.savefig(os.path.join(FIGDIR, "expressivity.png"), dpi=140)
    plt.close(fig)


def fig_coupler():
    lams = np.linspace(1500, 1600, 200)
    kpow = coupler.dc_power_coupling(lams)
    ext = np.array([coupler.extinction_ratio_db(l) for l in np.linspace(1530, 1565, 36)])
    lam_e = np.linspace(1530, 1565, 36)
    lam_d, kdata = coupler._demo_measured_dataset()
    k0, slope, rms = coupler.fit_dc_dispersion(lam_d, kdata)
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
    fig.tight_layout(); fig.savefig(os.path.join(FIGDIR, "coupler.png"), dpi=140)
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
    fig.tight_layout(); fig.savefig(os.path.join(FIGDIR, "recirculating.png"), dpi=140)
    plt.close(fig)


def main():
    print("=" * 72)
    print("LightIN reproduction — running all modules")
    print("=" * 72)

    print("\n--- 1. Unitary matrix multiplication ---")
    u = unitary.run()
    print("\n--- 2. Non-unitary matrix multiplication ---")
    nu = nonunitary.run()
    print("\n--- 3. Iris unitary neural network ---")
    ir = nn_iris.run()
    print("\n--- 4. MRM wavelength locking (differentiator) ---")
    mr = mrm.run()
    print("\n--- 5. Optical switching crosstalk ---")
    sw = switching.run()
    print("\n--- 6. Photonic PUF ---")
    pp = ppuf.run(n_dies=100)
    print("\n--- 7. Throughput & energy ---")
    te = throughput.reproduce()
    print("\n--- 8. CMT directional coupler (physical model) ---")
    cp = coupler.run()
    print("\n--- 9. Single-theta PUC expressivity ---")
    ex = expressivity.run()
    print("\n--- 10. Recirculating mesh with feedback loops ---")
    rc = recirculating.run()
    print("\n--- 11. Fig 4d coupler dispersion fit (bootstrapped) ---")
    f4_all = fit_fig4.main()
    f4 = {k: v for k, v in f4_all.items() if k in FIG4D_KEYS}
    f4_mesh = f4_all["mesh"]

    print("\n--- Generating figures ---")
    fig_unitary(u); fig_nonunitary(nu); fig_iris(ir); fig_ppuf(pp)
    fig_mrm(mr); fig_switching(sw); fig_coupler(); fig_expressivity(ex)
    fig_recirculating()
    figs = sorted(os.listdir(FIGDIR))
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
                 "logistic_baseline": ir["logistic_baseline"]},
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
        },
        "ppuf": {"uniqueness": pp["uniqueness"], "uniformity": pp["uniformity"],
                 "reliability_intra_die_HD": pp["reliability_intra_die_HD"],
                 "tie_fraction": pp["tie_fraction"],
                 "sensitivity_sweep": pp["sensitivity_sweep"]},
        "throughput_energy": te,
        "coupler": dict(
            {k: cp[k] for k in ("extinction_at_3db_db", "extinction_at_1560_db",
                                "extinction_at_1520_db", "link_budget_db")},
            demo_fit_kappa0=cp["fit_kappa0"],
            demo_fit_slope=cp["fit_slope"],
            demo_true_kappa0=cp["demo_true_kappa0"],
            demo_true_slope=cp["demo_true_slope"],
            demo_fit_lam0_nm=cp["demo_fit_lam0_nm"],
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
        "fig4d_mesh_fit": f4_mesh,
        "recirculating": rc,
        "latency_on_chip_ps": propagation_latency(4.5e-3) * 1e12,
        "environment": environment(),
    }
    out = os.path.join(os.path.dirname(__file__), "..", "results.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote {os.path.abspath(out)}")
    return results


if __name__ == "__main__":
    main()
