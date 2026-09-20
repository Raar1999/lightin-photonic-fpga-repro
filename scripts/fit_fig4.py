"""
Fit the coupler dispersion to the digitized LightIN Fig 4d (all-cross) T20 crosstalk
curve, and overlay the fitted model. Run: python scripts/fit_fig4.py

The digitized data (data/fig4d_T20_digitized.csv) was extracted from the published
figure by colour segmentation, with the dB scale anchored to figure-read endpoints
(~+/-2 dB). Cross-state crosstalk has a floor (the ~-25 dB minimum from fabrication /
measurement), so the model is  10*log10[(1-2*kappa)^2 + floor],  with
kappa(lambda) = sin^2(arcsin(sqrt(0.5)) + slope*(lambda - lambda0)).

The 25 digitized points carry a stated ~+/-2 dB reading uncertainty, so the point fit
alone says nothing about how well lambda0 is determined. A pairs bootstrap -- resample
the (lambda, dB) pairs with replacement and refit -- turns that scatter into an interval
on lambda0 and on the dispersion slope.
"""
import os
import sys

# Python puts scripts/ on sys.path when this file is run as a script, not the repository
# root, so `lightin` resolves only when the package itself has been installed. Adding the
# root keeps `pip install -r requirements.txt` -- which installs the dependencies and not
# this package -- a working alternative to `pip install -e .`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from scipy.optimize import curve_fit
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from lightin import switching

HERE = os.path.dirname(__file__)
CSV = os.path.join(HERE, "..", "data", "fig4d_T20_digitized.csv")
FIG = os.path.join(HERE, "..", "figures", "fig4_digitized.png")

FIT_RANGE_NM = [1549, 1587]     # wavelength span of the digitized points
P0 = (1568.0, 0.0045, -25.0)      # proxy: lambda0 (nm), slope (rad/nm), floor (dB)
MESH_P0 = (1571.0, 0.0029, -25.0)  # mesh: same three parameters
DIGITIZATION_SD_DB = 2.0           # CSV header's "~+/-2 dB", taken as one sigma


def crosstalk_model(lam, lam0, slope, floor_db):
    a0 = np.arcsin(np.sqrt(0.5))
    k = np.sin(a0 + slope * (lam - lam0)) ** 2
    return 10 * np.log10((1 - 2 * k) ** 2 + 10 ** (floor_db / 10))


def mesh_t20_model(lam, lam0, slope, floor_db):
    """T20 crosstalk of the full 4x4 mesh, normalised to the total output power.

    crosstalk_model above is a single-coupler proxy: its lambda0 is a parameter of that
    formula, not of the mesh. The mesh routes input 0 through four stages, so its T20
    null is displaced from the couplers' own 3-dB point. This model evaluates the mesh
    that lightin/switching.py actually uses, so the fitted lambda0 and slope are the
    couplers' parameters and the comparison with the data is like for like.

    Normalising by the total output power removes the insertion loss, which the
    digitized figure does not carry. floor_db is the phenomenological crosstalk floor
    the measured curve shows and the mesh model has no term for.
    """
    lam = np.atleast_1d(np.asarray(lam, float))
    Tdb, _ = switching.transmission_spectra("cross", lam, lam0=lam0, slope=slope)
    T = 10.0 ** (Tdb / 10.0)
    ratio = T[2, 0] / T[:, 0].sum(axis=0)
    return 10 * np.log10(ratio + 10 ** (floor_db / 10.0))


def load_points(path=CSV):
    """Read the digitized (wavelength_nm, crosstalk_dB) pairs."""
    lam, db = [], []
    with open(path) as f:
        for line in f:
            if line.startswith("#") or line.startswith("wavelength"):
                continue
            a, b = line.strip().split(",")
            lam.append(float(a)); db.append(float(b))
    return np.array(lam), np.array(db)


def fit(lam, db, p0=P0):
    """Least-squares fit of crosstalk_model; raises RuntimeError if it does not converge."""
    popt, _ = curve_fit(crosstalk_model, lam, db, p0=list(p0), maxfev=40000)
    return popt


def _curve_fit_mesh(lam, db, p0=MESH_P0):
    """Least-squares fit of mesh_t20_model; returns (popt, standard errors)."""
    popt, pcov = curve_fit(mesh_t20_model, lam, db, p0=list(p0), maxfev=40000)
    return popt, np.sqrt(np.diag(pcov))


def rms_db(model, lam, db, *params):
    """Root-mean-square difference in dB between a model and the digitized points."""
    return float(np.sqrt(np.mean((db - model(lam, *params)) ** 2)))


def fit_proxy(lam=None, db=None, p0=P0):
    """Single fit of the single-coupler proxy model to the digitized Fig 4d points.

    Returns lambda0 (nm), slope (rad/nm), floor_db and rms_db. Loads the CSV when lam
    and db are not given. This is the fit on its own, without the bootstrap: one fit
    costs milliseconds where 500 resampled refits cost minutes, so a caller that only
    needs the fitted parameters -- the test suite in particular -- calls this.
    """
    if lam is None or db is None:
        lam, db = load_points()
    popt = fit(lam, db, p0)
    return {"lambda0": float(popt[0]), "slope": float(popt[1]),
            "floor_db": float(popt[2]),
            "rms_db": rms_db(crosstalk_model, lam, db, *popt)}


def fit_mesh(lam=None, db=None, p0=MESH_P0):
    """Single fit of the 4x4 mesh T20 model to the same points.

    Same four keys as fit_proxy, plus the curve_fit standard errors and the point
    count. These lambda0 and slope are the couplers' own parameters, which is why
    DC_LAMBDA_3DB and DC_SLOPE are taken from here and not from the proxy.
    """
    if lam is None or db is None:
        lam, db = load_points()
    popt, se = _curve_fit_mesh(lam, db, p0)
    return {"lambda0": float(popt[0]), "slope": float(popt[1]),
            "floor_db": float(popt[2]),
            "rms_db": rms_db(mesh_t20_model, lam, db, *popt),
            "lambda0_se_nm": float(se[0]), "slope_se": float(se[1]),
            "floor_se_db": float(se[2]), "n_points": int(lam.size)}


def _mesh_fit_samples(samples):
    """Fit the mesh model to each (lam, db) resample; return lam0s, slopes, n_failed.

    A resample whose fit does not converge, or which returns a non-finite parameter, is
    discarded and counted rather than retried with a different seed, so the reported
    interval is over the fits that actually succeeded.
    """
    lam0s, slopes, n_failed = [], [], 0
    for lam_i, db_i in samples:
        try:
            popt, _ = _curve_fit_mesh(lam_i, db_i)
        except (RuntimeError, ValueError, TypeError):
            n_failed += 1
            continue
        if not np.all(np.isfinite(popt[:2])):
            n_failed += 1
            continue
        lam0s.append(float(popt[0]))
        slopes.append(float(popt[1]))
    return np.array(lam0s), np.array(slopes), n_failed


def bootstrap_mesh(lam, db, n_boot=500, seed=0, param_seed=1,
                   noise_sd_db=DIGITIZATION_SD_DB):
    """Pairs and parametric bootstrap of the mesh T20 fit.

    The pairs bootstrap resamples the (lambda, dB) points with replacement, so its
    interval reflects only the scatter of the digitized points about the model. The
    parametric bootstrap keeps all 25 wavelengths and perturbs each dB value by
    N(0, noise_sd_db), so its interval also carries the digitization uncertainty the
    CSV header states. The second is the wider and the more honest of the two.
    """
    n = lam.size
    rng_pairs = np.random.default_rng(seed)
    pairs = []
    for _ in range(n_boot):
        idx = rng_pairs.integers(0, n, size=n)
        pairs.append((lam[idx], db[idx]))
    l_pairs, s_pairs, f_pairs = _mesh_fit_samples(pairs)

    rng_param = np.random.default_rng(param_seed)
    param = [(lam, db + rng_param.normal(0.0, noise_sd_db, size=n))
             for _ in range(n_boot)]
    l_param, s_param, f_param = _mesh_fit_samples(param)

    return {
        "lambda0_pairs_p05_nm": float(np.percentile(l_pairs, 5)),
        "lambda0_pairs_p95_nm": float(np.percentile(l_pairs, 95)),
        "slope_pairs_p05": float(np.percentile(s_pairs, 5)),
        "slope_pairs_p95": float(np.percentile(s_pairs, 95)),
        "lambda0_param_p05_nm": float(np.percentile(l_param, 5)),
        "lambda0_param_p95_nm": float(np.percentile(l_param, 95)),
        "slope_param_p05": float(np.percentile(s_param, 5)),
        "slope_param_p95": float(np.percentile(s_param, 95)),
        "n_pairs_failed": int(f_pairs),
        "n_param_failed": int(f_param),
    }


def bootstrap(lam, db, n_boot=500, seed=0):
    """Pairs bootstrap: resample the points with replacement, refit, tabulate.

    A resample whose fit does not converge, or which returns a non-finite parameter, is
    discarded and counted in "n_failed" rather than being retried with a different seed,
    so the reported interval is over the fits that actually succeeded.
    """
    rng = np.random.default_rng(seed)
    n = lam.size
    lam0s, slopes, n_failed = [], [], 0
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        try:
            p = fit(lam[idx], db[idx])
        except (RuntimeError, ValueError, TypeError):
            n_failed += 1
            continue
        if not np.all(np.isfinite(p[:2])):
            n_failed += 1
            continue
        lam0s.append(float(p[0])); slopes.append(float(p[1]))
    lam0s = np.array(lam0s); slopes = np.array(slopes)
    return {
        "lambda0_median_nm": float(np.median(lam0s)),
        "lambda0_p05_nm": float(np.percentile(lam0s, 5)),
        "lambda0_p95_nm": float(np.percentile(lam0s, 95)),
        "slope_median": float(np.median(slopes)),
        "slope_p05": float(np.percentile(slopes, 5)),
        "slope_p95": float(np.percentile(slopes, 95)),
        "n_boot": int(n_boot),
        "n_failed": int(n_failed),
        "fit_range_nm": list(FIT_RANGE_NM),
    }


def main(verbose=True, n_boot=500, seed=0, fig_path=FIG):
    lam, db = load_points()
    pf = fit_proxy(lam, db)
    mf = fit_mesh(lam, db)
    lam0, slope, floor, rms = pf["lambda0"], pf["slope"], pf["floor_db"], pf["rms_db"]
    popt = (lam0, slope, floor)
    mopt = (mf["lambda0"], mf["slope"], mf["floor_db"])
    mse = (mf["lambda0_se_nm"], mf["slope_se"], mf["floor_se_db"])
    mrms = mf["rms_db"]

    boot = bootstrap(lam, db, n_boot=n_boot, seed=seed)
    mboot = bootstrap_mesh(lam, db, n_boot=n_boot, seed=seed)

    if verbose:
        print("Fit to digitized Fig 4d T20 crosstalk:")
        print(f"  coupler 3-dB wavelength lambda0 = {lam0:.1f} nm")
        print(f"  dispersion slope                = {slope:.4f} rad/nm  "
              f"(literature/default was 0.004)")
        print(f"  crosstalk floor                 = {floor:.1f} dB")
        print(f"  fit RMS                         = {rms:.2f} dB")
        print(f"  fitted wavelength range         = {FIT_RANGE_NM[0]}-{FIT_RANGE_NM[1]} nm"
              f" ({lam.size} points)")
        print(f"  pairs bootstrap, {boot['n_boot']} resamples "
              f"({boot['n_failed']} failed fits discarded):")
        print(f"    lambda0 median = {boot['lambda0_median_nm']:.1f} nm  "
              f"[5%, 95%] = [{boot['lambda0_p05_nm']:.1f}, {boot['lambda0_p95_nm']:.1f}] nm")
        print(f"    slope   median = {boot['slope_median']:.4f} rad/nm  "
              f"[5%, 95%] = [{boot['slope_p05']:.4f}, {boot['slope_p95']:.4f}] rad/nm")
        print("Fit of the 4x4 mesh T20 model (normalised to total output) to the same points:")
        print(f"  coupler 3-dB wavelength lambda0 = {mopt[0]:.1f} +/- {mse[0]:.1f} nm")
        print(f"  dispersion slope                = {mopt[1]:.4f} +/- {mse[1]:.4f} rad/nm")
        print(f"  crosstalk floor                 = {mopt[2]:.1f} +/- {mse[2]:.1f} dB")
        print(f"  fit RMS                         = {mrms:.2f} dB "
              f"(single-coupler proxy: {rms:.2f} dB)")
        print(f"  pairs bootstrap ({mboot['n_pairs_failed']} failed): "
              f"lambda0 [{mboot['lambda0_pairs_p05_nm']:.1f}, "
              f"{mboot['lambda0_pairs_p95_nm']:.1f}] nm, "
              f"slope [{mboot['slope_pairs_p05']:.4f}, {mboot['slope_pairs_p95']:.4f}]")
        print(f"  parametric bootstrap, +/-{DIGITIZATION_SD_DB:.0f} dB "
              f"({mboot['n_param_failed']} failed): "
              f"lambda0 [{mboot['lambda0_param_p05_nm']:.1f}, "
              f"{mboot['lambda0_param_p95_nm']:.1f}] nm, "
              f"slope [{mboot['slope_param_p05']:.4f}, {mboot['slope_param_p95']:.4f}]")

    lf = np.linspace(lam.min(), lam.max(), 400)
    fig, ax = plt.subplots(figsize=(7, 4.4))
    ax.scatter(lam, db, s=26, color="#C44E52", zorder=3,
               label="digitized Fig 4d $T_{20}$ (±2 dB)")
    ax.plot(lf, crosstalk_model(lf, *popt), color="#4C72B0", lw=2, ls="--",
            label=(f"single-coupler proxy\n$\\lambda_0$={lam0:.1f} nm, "
                   f"slope={slope:.4f} rad/nm\nRMS={rms:.2f} dB"))
    ax.plot(lf, mesh_t20_model(lf, *mopt), color="#55A868", lw=2,
            label=(f"4x4 mesh $T_{{20}}$ fit\n$\\lambda_0$={mopt[0]:.1f} nm, "
                   f"slope={mopt[1]:.4f} rad/nm\nRMS={mrms:.2f} dB"))
    ax.axvspan(boot["lambda0_p05_nm"], boot["lambda0_p95_nm"], color="#4C72B0",
               alpha=0.12, zorder=0,
               label=(f"$\\lambda_0$ bootstrap 5–95%\n"
                      f"[{boot['lambda0_p05_nm']:.1f}, {boot['lambda0_p95_nm']:.1f}] nm"))
    ax.axhline(-15, color="grey", ls=":", lw=1)
    ax.set_xlabel("Wavelength (nm)"); ax.set_ylabel("Crosstalk (dB)")
    ax.set_title("Coupler dispersion fitted to the chip's measured crosstalk\n"
                 "(LightIN Fig 4d, all-cross $T_{20}$; digitized)", fontsize=10)
    ax.legend(fontsize=8); ax.set_ylim(-27, -10)
    fig.tight_layout(); fig.savefig(fig_path, dpi=140)
    plt.close(fig)
    if verbose:
        print(f"  wrote {os.path.abspath(fig_path)}")

    out = dict(boot)
    out.update({"model": "single-coupler proxy",
                "lambda0_nm": float(lam0), "slope_rad_nm": float(slope),
                "floor_db": float(floor), "rms_db": rms})
    out["mesh"] = {
        "model": "4x4 mesh T20 normalised to total output",
        "lambda0_nm": mf["lambda0"], "slope": mf["slope"],
        "floor_db": mf["floor_db"],
        "lambda0_se_nm": mf["lambda0_se_nm"], "slope_se": mf["slope_se"],
        "floor_se_db": mf["floor_se_db"],
        "rms_db": mrms, "n_points": mf["n_points"],
        **mboot,
    }
    return out


if __name__ == "__main__":
    main()
