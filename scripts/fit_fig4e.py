"""
Fit the bar-state fabrication spread to the digitized LightIN Fig 4e T32 curve, and
overlay the fitted model. Run: python scripts/fit_fig4e.py

The digitized data (data/fig4e_bar_digitized.csv) is the UPPER ENVELOPE of the T32 band
in the bottom-left sub-panel of Fig 4e, because that band's lower edge is cut off by the
panel's -25 dB axis limit at every wavelength and its centre therefore cannot be read.
Each point is therefore a peak-hold over the fast wavelength ripple, and bar_model returns
the matching statistic -- the PCT-th quantile of the fabrication ensemble, not its mean.
Fitting the mean to these points instead inflates the spread by the 7.4 dB that separates
the two, which is what quantile_sensitivity() measures.

The bar state nulls exactly when the couplers split 50:50 and the arms are balanced, so
its leakage is set jointly by the coupler-split spread sigma_split and the arm-phase
spread sigma_phase. Both are assumed to be 0.02. Whether one curve can separate them is
the question identifiability() answers; it cannot, so fit_one() fits one at a time with
the other held.

The fitted value is NOT adopted, and switching.SIGMA_SPLIT keeps its assumed 0.02. What
this module produces is a consistency check on that assumption rather than a measurement
replacing it, for two reasons it reports itself: shape_check() finds the model no better
on these 27 points than a best-fit constant, and sensitivity() finds the fitted spread
running from 0.0152 to 0.0707 with the choice of ensemble percentile, at an RMS that does
not move. 0.02 lies inside that range. Every fit below is still run and still recorded,
because what the panel rules out is worth having; nothing downstream reads its value.
"""
import os
import warnings
import numpy as np
from scipy.optimize import curve_fit, OptimizeWarning
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from lightin import switching
from lightin.coupler import DC_LAMBDA_3DB, DC_SLOPE

HERE = os.path.dirname(__file__)
CSV = os.path.join(HERE, "..", "data", "fig4e_bar_digitized.csv")
FIG = os.path.join(HERE, "..", "figures", "fig4e_digitized.png")

FIT_RANGE_NM = [1550, 1589]        # wavelength span of the digitized points
DIGITIZATION_SD_DB = 0.3           # CSV header's "~+/-0.3 dB", taken as one sigma
N_REAL = 3200                      # fabrication realisations per ensemble. The fitted
# statistic is a tail quantile, which needs more realisations than a mean to settle: the
# 99th percentile scatters across ensemble seeds by 0.35 dB at 1600, 0.16 dB at 3200 and
# 0.15 dB at 6400, against the 0.2 dB the model needs to be steadier than. 3200 is the
# first count that clears it, and 6400 costs twice as much for 0.01 dB.
PCT = 99.0                         # ensemble quantile the model reports, and the one
# quantity in this file that is a modelling choice rather than a measurement. The digitized
# points are a peak-hold over the fast wavelength ripple inside each digitization window,
# so their model counterpart is a high quantile of the leakage distribution, not its mean.
# 99 corresponds to the largest of about a hundred independent ripple samples per window.
# quantile_sensitivity() reports the fit at 90, 99 and 99.9 so the dependence is visible.
FLOOR_DB = -60.0                   # additive crosstalk floor, held fixed at a level 40 dB
# below the data so it contributes nothing. lightin/switching.py deliberately does not add
# the Fig 4d floor to any crosstalk it reports, and there is no independent bar-state floor
# measurement, so the whole measured leakage is attributed to the fabrication spreads --
# which is another reason the fitted spreads are upper bounds.
SIGMA_ASSUMED = 0.02               # the value both spreads carried before this fit
EPSFCN = 1e-6                      # curve_fit finite-difference control. leastsq's default
# step is sqrt(macheps)*sigma ~ 3e-10, over which the ensemble quantile changes by ~1e-7 dB
# and the difference underflows, so the Jacobian comes back singular and no covariance can
# be estimated. sqrt(1e-6)*sigma ~ 2e-5 is small enough that the derivative is unchanged
# -- 452.9 dB per unit sigma at 1e-8, 1e-6 and 1e-5 alike -- and large enough to resolve.

IN_PORT, OUT_PORT = 2, 3           # T32: input 2, output 3 (bottom-left sub-panel)


EXCESS_LOSS_DB = 0.1          # per directional coupler, as switching.power_spectra uses
PROP_DB_PER_STAGE = 0.25      # per mesh layer, likewise


def _cell(ka, kb, ph, dl):
    """2x2 field transfer of one MZI, for every realisation and wavelength.

    ka, kb, ph have shape (n_real,) and dl = DC_SLOPE*(lam - lam0) shape (n_lam,); the
    result is (n_real, n_lam, 2, 2). This is mzi_single_theta written out over the whole
    ensemble at once -- asserted equal to it, cell by cell, in the test suite -- because
    the bootstrap calls the model tens of thousands of times and the per-cell Python loop
    it replaces costs hours. One cell is built at a time so peak memory stays at one
    (n_real, n_lam, 2, 2) block rather than six.
    """
    kA = np.sin(np.arcsin(np.sqrt(ka))[:, None] + dl) ** 2          # (R, L)
    kB = np.sin(np.arcsin(np.sqrt(kb))[:, None] + dl) ** 2
    amp = 10 ** (-EXCESS_LOSS_DB / 20.0)
    e = np.exp(1j * (switching.THETA_BAR + ph))[:, None]            # (R, 1)

    tA, cA = np.sqrt(1 - kA), np.sqrt(kA)
    tB, cB = np.sqrt(1 - kB), np.sqrt(kB)
    # M = DCb . diag(e, 1) . DCa, written out so the whole ensemble is one expression
    M = np.empty(kA.shape + (2, 2), dtype=complex)
    M[..., 0, 0] = tB * e * tA + (1j * cB) * (1j * cA)
    M[..., 0, 1] = tB * e * (1j * cA) + (1j * cB) * tA
    M[..., 1, 0] = (1j * cB) * e * tA + tB * (1j * cA)
    M[..., 1, 1] = (1j * cB) * e * (1j * cA) + tB * tA
    M *= amp ** 2
    return M


def _bar_ensemble(lam, sigma_split, sigma_phase, n_real, seed, N=4, chunk=4000):
    """T32 / (total output from input 2) for every realisation: shape (n_real, n_lam).

    One realisation is one draw of the 2*n_mzi coupler splits and n_mzi arm phase errors,
    in the same order and from the same Generator call pattern switching.power_spectra
    uses, but at the spreads passed in rather than at the module constants.

    All n_real realisations come from one Generator seeded once, so the same seed gives
    the same ensemble at every (sigma_split, sigma_phase) and any statistic of it moves
    smoothly with both, which is what curve_fit needs. The whole ensemble is drawn in one
    go -- three (n_real, n_mzi) arrays, kilobytes -- and only the propagation is chunked,
    so the result does not depend on chunk. What chunking bounds is the one big array,
    the (chunk, n_lam, 2, 2) cell block.
    """
    lam = np.atleast_1d(np.asarray(lam, float))
    n_mzi = N * (N - 1) // 2
    dl = DC_SLOPE * (lam - DC_LAMBDA_3DB)
    amp = 10 ** (-PROP_DB_PER_STAGE / 20.0)
    rng = np.random.default_rng(seed)
    ka = np.clip(rng.normal(0.5, sigma_split, size=(n_real, n_mzi)), 0.3, 0.7)
    kb = np.clip(rng.normal(0.5, sigma_split, size=(n_real, n_mzi)), 0.3, 0.7)
    ph = rng.normal(0.0, sigma_phase, size=(n_real, n_mzi))

    out = []
    for lo in range(0, n_real, chunk):
        hi = min(lo + chunk, n_real)
        # Only the IN_PORT column of the fabric matrix is needed, so one input vector is
        # swept through the four layers instead of a full NxN product. Within a layer the
        # pairs are disjoint, so each cell acts on two components independently.
        v = np.zeros((hi - lo, lam.size, N), dtype=complex)
        v[:, :, IN_PORT] = 1.0
        k = 0
        for layer in range(N):
            for (m, n) in switching._layer_pairs(N, layer):
                c = _cell(ka[lo:hi, k], kb[lo:hi, k], ph[lo:hi, k], dl)   # (r, L, 2, 2)
                vm, vn = v[:, :, m].copy(), v[:, :, n]
                v[:, :, m] = c[..., 0, 0] * vm + c[..., 0, 1] * vn
                v[:, :, n] = c[..., 1, 0] * vm + c[..., 1, 1] * vn
                k += 1
            v *= amp
        T = np.abs(v) ** 2
        out.append(T[:, :, OUT_PORT] / T.sum(axis=2))
    return np.concatenate(out, axis=0)


def bar_model(lam, sigma_split, sigma_phase, floor_db, n_real=N_REAL, seed=0, pct=PCT):
    """Bar-state T32 crosstalk in dB: the pct-th quantile of the fabrication ensemble.

    Normalising by the total output from input 2 removes the insertion loss, which the
    digitized figure does not carry, exactly as fit_fig4.mesh_t20_model does for the cross
    state. floor_db is the same phenomenological additive floor: the mesh has no term for
    one, so it is carried as a parameter here and held fixed during the fits.

    pct, not the ensemble mean, is what makes the comparison like for like. The digitized
    Fig 4e points are the upper envelope of a band whose lower edge the panel's -25 dB axis
    cuts off, so each one is a peak-hold over the fast wavelength ripple inside the
    digitization window, not a level. Against the ensemble mean the same data returns
    sigma_split = 0.048, which is the +7.4 dB by which this model's own 99th percentile
    sits above its own mean being absorbed into the fitted spread; it wrecks the Fig 4d
    agreement, and quantile_sensitivity() below reports how the fit moves with pct.
    """
    r = _bar_ensemble(lam, abs(sigma_split), abs(sigma_phase), n_real, seed)
    return 10 * np.log10(np.percentile(r, pct, axis=0) + 10 ** (floor_db / 10.0))


def bar_model_mean(lam, sigma_split, sigma_phase, floor_db, n_real=N_REAL, seed=0):
    """Ensemble-MEAN bar-state T32 crosstalk in dB. Diagnostic, not the fitted model.

    Kept because it is the quantity lightin/switching.py's crosstalk_summary reports for a
    single realisation, and because quantile_sensitivity() quotes the offset between it and
    bar_model.
    """
    r = _bar_ensemble(lam, abs(sigma_split), abs(sigma_phase), n_real, seed)
    return 10 * np.log10(r.mean(axis=0) + 10 ** (floor_db / 10.0))


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


def rms_db(lam, db, sigma_split, sigma_phase, floor_db=FLOOR_DB, n_real=N_REAL,
           pct=PCT):
    """Root-mean-square difference in dB between bar_model and the digitized points."""
    return float(np.sqrt(np.mean(
        (db - bar_model(lam, sigma_split, sigma_phase, floor_db, n_real, pct=pct)) ** 2)))


# --------------------------------------------------------------------------- diagonals

DIAG_CSV = os.path.join(HERE, "..", "data", "fig4e_diagonal_digitized.csv")
DIAG_NAMES = ("T00", "T11", "T22", "T33")
DIAG_CONTINUOUS_MAX_NM = 1574.0    # last wavelength before each sub-panel's legend box
# hides the trace. The grid resumes at 1589.0 nm, inside the roll-off at the end of the
# scan, so every summary below is reported over both the full tabulated band and this
# continuous segment; which one is used changes the comparison with the paper by more
# than a decibel.


def load_diagonals(path=DIAG_CSV):
    """Read data/fig4e_diagonal_digitized.csv as (wavelengths, {name: dB array})."""
    lam, cols = [], {n: [] for n in DIAG_NAMES}
    with open(path) as f:
        for line in f:
            if line.startswith("#") or line.startswith("wavelength"):
                continue
            parts = line.strip().split(",")
            if len(parts) != 1 + len(DIAG_NAMES):
                raise ValueError(f"expected {1 + len(DIAG_NAMES)} columns, got {line!r}")
            lam.append(float(parts[0]))
            for n, v in zip(DIAG_NAMES, parts[1:]):
                cols[n].append(float(v))
    return np.array(lam), {n: np.array(v) for n, v in cols.items()}


def diagonal_summary(paper_range_db=None, verbose=True):
    """Compare the digitized all-bar through paths with the paper's insertion-loss range.

    The question this answers is whether the gap between the two is a calibration offset
    on the digitized dB scale, which would move every fitted spread, or a difference in
    which paths the paper quoted, which would not. A constant offset shifts both ends of
    the range by the same amount; anything else does not, so the two end differences are
    the diagnostic and are reported separately.

    offset_db, used by sensitivity() as a what-if, is the digitized mean minus the
    midpoint of the paper's range. It is a single number standing in for a disagreement
    that is not a single number, which is why the sensitivity test it feeds is labelled a
    sensitivity test rather than a correction.
    """
    if paper_range_db is None:
        paper_range_db = list(switching.ONCHIP_IL_PAPER_RANGE_DB)
    lo_paper, hi_paper = min(paper_range_db), max(paper_range_db)
    lam, cols = load_diagonals()
    cont = lam <= DIAG_CONTINUOUS_MAX_NM

    def block(mask):
        per = {n: {"min_db": float(v[mask].min()), "max_db": float(v[mask].max()),
                   "mean_db": float(v[mask].mean()), "n_points": int(mask.sum())}
               for n, v in cols.items()}
        allv = np.concatenate([v[mask] for v in cols.values()])
        return per, {
            "range_db": [float(allv.min()), float(allv.max())],
            "mean_db": float(allv.mean()),
            "most_lossy_end_minus_paper_db": float(allv.min() - lo_paper),
            "least_lossy_end_minus_paper_db": float(allv.max() - hi_paper),
            "end_difference_db": float(abs((allv.min() - lo_paper)
                                           - (allv.max() - hi_paper))),
            "mean_minus_paper_midpoint_db": float(allv.mean()
                                                  - 0.5 * (lo_paper + hi_paper)),
        }

    per_full, comb_full = block(np.ones_like(lam, bool))
    per_cont, comb_cont = block(cont)
    out = {
        "n_points": int(lam.size),
        "band_nm": [float(lam.min()), float(lam.max())],
        "continuous_band_nm": [float(lam.min()), float(DIAG_CONTINUOUS_MAX_NM)],
        "paper_range_db": [lo_paper, hi_paper],
        "paper_n_paths": 8,
        "panel_n_paths": 4,
        "per_diagonal": per_full,
        "per_diagonal_continuous": per_cont,
        "combined": comb_full,
        "combined_continuous": comb_cont,
        "offset_db": round(comb_full["mean_minus_paper_midpoint_db"], 2),
        "note": ("Fig 4e is the all-bar state, so its four diagonals are four of the "
                 "eight intended paths the paper's range covers; the other four are the "
                 "all-cross paths, which this panel does not draw"),
    }
    if verbose:
        print("Digitized Fig 4e diagonals (all-bar through paths) vs the paper's "
              "on-chip insertion loss:")
        print(f"  {lam.size} wavelengths, {lam.min():.1f}-{lam.max():.1f} nm "
              f"({int(cont.sum())} of them over the continuous "
              f"{lam.min():.1f}-{DIAG_CONTINUOUS_MAX_NM:.1f} nm segment)")
        print(f"  {'':5s} {'full band 1550-1589 nm':>28s}   "
              f"{'continuous 1550-1574 nm':>28s}")
        for n in DIAG_NAMES:
            a, b = per_full[n], per_cont[n]
            print(f"  {n:5s} min {a['min_db']:+6.2f}  max {a['max_db']:+6.2f}  "
                  f"mean {a['mean_db']:+6.2f}   "
                  f"min {b['min_db']:+6.2f}  max {b['max_db']:+6.2f}  "
                  f"mean {b['mean_db']:+6.2f}")
        for lbl, c in (("full band      ", comb_full),
                       ("continuous only", comb_cont)):
            print(f"  all four, {lbl}: {c['range_db'][0]:+.2f} to "
                  f"{c['range_db'][1]:+.2f} dB, mean {c['mean_db']:+.2f} dB")
            print(f"    against the paper's {lo_paper:+.2f} to {hi_paper:+.2f} dB: "
                  f"most-lossy end {c['most_lossy_end_minus_paper_db']:+.2f} dB, "
                  f"least-lossy end {c['least_lossy_end_minus_paper_db']:+.2f} dB")
            print(f"    the two ends differ by "
                  f"{c['end_difference_db']:.2f} dB, so the disagreement is "
                  f"{'not ' if c['end_difference_db'] > 0.3 else ''}a constant offset")
        print(f"  the paper's range covers {out['paper_n_paths']} intended paths; this "
              f"panel is the all-bar state and draws {out['panel_n_paths']} of them")
        print(f"  what-if offset used by sensitivity(): {out['offset_db']:+.2f} dB "
              f"(digitized mean minus the paper's range midpoint)")
    return out


# --------------------------------------------------------------------------- Step 2

def identifiability(lam=1560.0, grid=(0.005, 0.08), n=6, floor_db=FLOOR_DB,
                    n_real=N_REAL, verbose=True):
    """Model value at one wavelength over a (sigma_split, sigma_phase) grid.

    If the contours of constant crosstalk run along a line in this plane, the two spreads
    trade off and only their combination is constrained by one curve.
    """
    s = np.linspace(*grid, n)
    Z = np.array([[float(bar_model(lam, ss, sp, floor_db, n_real)[0]) for sp in s]
                  for ss in s])
    if verbose:
        print(f"  bar_model at {lam:.0f} nm, floor held at {floor_db:.0f} dB, "
              f"n_real={n_real} (dB)")
        print("    sigma_split \\ sigma_phase " + "".join(f"{v:9.3f}" for v in s))
        for i, ss in enumerate(s):
            print(f"    {ss:24.3f} " + "".join(f"{Z[i, j]:9.2f}" for j in range(n)))
    return s, Z


def n_real_scatter(sigma_split=SIGMA_ASSUMED, sigma_phase=SIGMA_ASSUMED, lam=1560.0,
                   counts=(50, 200, 800), floor_db=FLOOR_DB, n_seeds=12, verbose=True):
    """Model value at one parameter setting for several realisation counts.

    The single-seed value at each count is what a fit at that count would use; the spread
    across n_seeds independent ensembles is the scatter that value carries, and is the
    number N_REAL is chosen against.
    """
    vals, spread = {}, {}
    for n in counts:
        v = np.array([float(bar_model(lam, sigma_split, sigma_phase, floor_db, n,
                                      seed=s)[0]) for s in range(n_seeds)])
        vals[n] = float(v[0])
        spread[n] = float(v.std(ddof=1))
        if verbose:
            print(f"    n_real={n:5d}:  {v[0]:8.3f} dB   "
                  f"scatter over {n_seeds} ensemble seeds: {spread[n]:.3f} dB")
    if verbose:
        lo, hi = min(vals.values()), max(vals.values())
        print(f"    spread over these counts at seed 0: {hi - lo:.3f} dB")
    return {"value": vals, "seed_scatter_db": spread}


def quantile_sensitivity(lam=None, db=None, pcts=(90.0, 99.0, 99.9), floor_db=FLOOR_DB,
                         n_real=N_REAL, verbose=True):
    """How the fitted sigma_split moves with the quantile the model reports.

    PCT is the one modelling choice in this file that the figure does not fix, so its
    effect is reported rather than buried. The ensemble mean is included as the pct that
    would be wrong, to show the size of the error it causes.
    """
    if lam is None or db is None:
        lam, db = load_points()
    out = {}
    for p in pcts:
        r = fit_one("split", lam, db, floor_db=floor_db, n_real=n_real, pct=p)
        out[f"p{p:g}"] = {"sigma_split": r["value"], "se": r["se"],
                          "rms_db": r["rms_db"]}
        if verbose:
            print(f"    pct={p:5.1f}:  sigma_split = {r['value']:.4f} +/- {r['se']:.4f}"
                  f"   RMS = {r['rms_db']:.2f} dB")
    mean_fit = _fit_against(bar_model_mean, "split", lam, db, floor_db, n_real)
    out["ensemble_mean"] = mean_fit
    if verbose:
        print(f"    ensemble mean (the wrong statistic for this data): "
              f"sigma_split = {mean_fit['sigma_split']:.4f}, "
              f"RMS = {mean_fit['rms_db']:.2f} dB")
    return out


def _fit_against(model, which, lam, db, floor_db, n_real, held=SIGMA_ASSUMED):
    """Single-parameter fit of an arbitrary model function; used by quantile_sensitivity."""
    def f(x, s):
        args = (s, held) if which == "split" else (held, s)
        return model(x, *args, floor_db, n_real)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", OptimizeWarning)
        popt, _ = curve_fit(f, lam, db, p0=[0.02], maxfev=4000, epsfcn=EPSFCN)
    val = float(abs(popt[0]))
    args = (val, held) if which == "split" else (held, val)
    rms = float(np.sqrt(np.mean((db - model(lam, *args, floor_db, n_real)) ** 2)))
    return {f"sigma_{which}": val, "rms_db": rms}


# --------------------------------------------------------------------------- Step 3

def fit_one(which, lam=None, db=None, held=SIGMA_ASSUMED, floor_db=FLOOR_DB,
            n_real=N_REAL, p0=0.02, pct=PCT):
    """Fit one spread with the other held fixed.

    which is "split" or "phase". The two are not separately identifiable from one curve
    (identifiability() above), so a joint fit would return an arbitrary point on a ridge
    with a confident-looking covariance. Each single fit instead answers a well-posed
    question: what spread of this kind alone would produce the measured leakage.
    """
    if lam is None or db is None:
        lam, db = load_points()

    if which == "split":
        def f(x, s):
            return bar_model(x, s, held, floor_db, n_real, pct=pct)
    elif which == "phase":
        def f(x, s):
            return bar_model(x, held, s, floor_db, n_real, pct=pct)
    else:
        raise ValueError(f"which must be 'split' or 'phase', got {which!r}")

    with warnings.catch_warnings():
        # A fit that runs to sigma = 0 leaves a singular Jacobian and curve_fit warns that
        # it cannot estimate a covariance. That is the diagnosis, not a problem to silence:
        # it is caught here and reported as at_bound rather than printed once per resample.
        warnings.simplefilter("ignore", OptimizeWarning)
        popt, pcov = curve_fit(f, lam, db, p0=[p0], maxfev=4000, epsfcn=EPSFCN)
    val = float(abs(popt[0]))
    se = float(np.sqrt(pcov[0, 0]))
    at_bound = bool(val < 1e-5 or not np.isfinite(se))
    args = (val, held) if which == "split" else (held, val)
    return {"fitted": which, "value": val, "se": None if at_bound else se,
            "at_bound": at_bound,
            "held": which_other(which), "held_value": float(held),
            "rms_db": rms_db(lam, db, *args, floor_db, n_real, pct),
            "n_points": int(lam.size), "floor_db": float(floor_db),
            "n_real": int(n_real), "pct": float(pct),
            "fit_range_nm": list(FIT_RANGE_NM)}


def which_other(which):
    return "phase" if which == "split" else "split"


def fit_joint(lam=None, db=None, floor_db=FLOOR_DB, n_real=N_REAL, p0=(0.02, 0.02),
              pct=PCT):
    """Fit both spreads at once. Diagnostic only: this is the fit NOT adopted.

    It is run to produce the 2x2 parameter correlation matrix, which is the direct
    evidence that the two spreads are not separately identifiable from one curve. Nothing
    downstream uses its parameter values.
    """
    if lam is None or db is None:
        lam, db = load_points()

    def f(x, ss, sp):
        return bar_model(x, ss, sp, floor_db, n_real, pct=pct)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", OptimizeWarning)
        popt, pcov = curve_fit(f, lam, db, p0=list(p0), maxfev=8000, epsfcn=EPSFCN)
    se = np.sqrt(np.diag(pcov))
    corr = pcov / np.outer(se, se)
    return {"sigma_split": float(abs(popt[0])), "sigma_phase": float(abs(popt[1])),
            "sigma_split_se": float(se[0]), "sigma_phase_se": float(se[1]),
            "correlation": [[float(v) for v in row] for row in corr],
            "rms_db": rms_db(lam, db, abs(popt[0]), abs(popt[1]), floor_db, n_real)}


def _fit_samples(which, samples, held=SIGMA_ASSUMED, floor_db=FLOOR_DB, n_real=N_REAL,
                 p0=0.02, pct=PCT):
    """Fit each (lam, db) resample; return the values and the number of failed fits.

    p0 is the point estimate from the unresampled data. Starting every resample there
    rather than at 0.02 is a warm start: it roughly halves the number of model
    evaluations curve_fit needs, and the model is monotonic in the fitted spread, so it
    cannot change which optimum is found.

    A resample whose fit does not converge, or which returns a non-finite parameter, is
    discarded and counted rather than retried with a different seed, so the reported
    interval is over the fits that actually succeeded -- the same rule as fit_fig4.
    """
    vals, n_failed = [], 0
    for lam_i, db_i in samples:
        try:
            r = fit_one(which, lam_i, db_i, held=held, floor_db=floor_db, n_real=n_real,
                        p0=p0, pct=pct)
        except (RuntimeError, ValueError, TypeError):
            n_failed += 1
            continue
        if not np.isfinite(r["value"]):
            n_failed += 1
            continue
        vals.append(r["value"])
    return np.array(vals), n_failed


ADOPTED_BOOT_N = 250       # resamples for the one bootstrap this module still runs. Each
# resample is a fresh fit costing about a second, so this is the whole cost of the Fig 4e
# block; 250 places the 5th and 95th percentiles to about a part in a thousand of sigma,
# which is three orders of magnitude finer than the percentile dependence the interval is
# quoted against, and nothing downstream reads it more precisely than that.

BOOTSTRAP_NOTE = ("the interval is reported only to show that it is far narrower than the "
                  "percentile dependence; the fit itself was not adopted")


def bootstrap_one(which, lam, db, n_boot=ADOPTED_BOOT_N, param_seed=1,
                  noise_sd_db=DIGITIZATION_SD_DB, held=SIGMA_ASSUMED,
                  floor_db=FLOOR_DB, n_real=N_REAL, p0=0.02, pct=PCT):
    """Parametric bootstrap of one single-parameter fit.

    All wavelengths are kept and each dB value is perturbed by N(0, noise_sd_db), so the
    interval carries the digitization uncertainty the CSV header states as well as the
    scatter of the points about the model.

    A pairs bootstrap, resampling the (lambda, dB) points with replacement, used to be run
    alongside this one and is not any more. It answered a narrower question -- scatter
    about the model, without the reading error -- and returned a narrower interval, and
    since the fitted value is not adopted, nothing rests on either. Running both doubled
    the cost of the whole script for a second version of a number quoted once.
    """
    n = lam.size
    rng_param = np.random.default_rng(param_seed)
    param = [(lam, db + rng_param.normal(0.0, noise_sd_db, size=n))
             for _ in range(n_boot)]
    v_param, f_param = _fit_samples(which, param, held, floor_db, n_real, p0, pct)

    return {
        "param_p05": float(np.percentile(v_param, 5)),
        "param_p95": float(np.percentile(v_param, 95)),
        "param_median": float(np.median(v_param)),
        "n_boot": int(n_boot),
        "n_param_failed": int(f_param),
        "noise_sd_db": float(noise_sd_db),
    }



def bar_il_vs_digitized(max_nm=DIAG_CONTINUOUS_MAX_NM, path=DIAG_CSV, verbose=True):
    """Modelled bar-state intended-path loss against the four digitized Fig 4e diagonals.

    The paper quotes one insertion-loss range over eight paths and does not say which
    path or which switch state each end of it belongs to. The digitized diagonals are
    four measured bar-state values, one per intended path, so they support a per-path
    comparison the quoted range cannot: not just whether the modelled loss is in the
    right place, but whether it varies across the four ports the way the chip does.

    Restricted to wavelengths at or below max_nm because each sub-panel's legend box
    hides roughly 1574.5-1588.3 nm and the grid resumes at 1589.0 nm inside the roll-off
    at the end of the scan, where the drawn trace is half again as thick as it is across
    the rest of the band. Including that one point moves the digitized side of this
    comparison by more than a decibel, so it is left out and the restriction is recorded.

    The model here is switching.fabric_matrix, which uses nominal 50:50 couplers: the
    intended-path loss is set by the propagation and coupler excess-loss constants, not
    by the fabrication spreads, so nothing in this comparison depends on SIGMA_SPLIT.
    """
    lam, cols = load_diagonals(path)
    sel = lam <= max_nm
    lam_s = lam[sel]
    if lam_s.size == 0:
        raise ValueError(f"no digitized points at or below {max_nm} nm")

    per_port, diffs_all = [], []
    for j, name in enumerate(DIAG_NAMES):
        model_db, out_ports = [], set()
        for x in lam_s:
            T = np.abs(switching.fabric_matrix("bar", float(x))) ** 2
            i = int(np.argmax(T[:, j]))
            out_ports.add(i)
            model_db.append(10 * np.log10(T[i, j]))
        model_db = np.array(model_db)
        if out_ports != {j}:
            # the all-bar state must route input j to output j; if it does not, this
            # comparison is pairing the digitized diagonal with the wrong modelled path
            raise ValueError(f"bar state routes input {j} to {sorted(out_ports)}, not {j}")
        dig_db = cols[name][sel]
        d = model_db - dig_db
        diffs_all.append(d)
        per_port.append({
            "trace": name, "in_port": j, "out_port": j,
            "model_db": float(model_db.mean()),
            "digitized_db": float(dig_db.mean()),
            "difference_db": float(d.mean()),
            "model_min_db": float(model_db.min()), "model_max_db": float(model_db.max()),
            "digitized_min_db": float(dig_db.min()),
            "digitized_max_db": float(dig_db.max()),
            "n_points": int(lam_s.size),
        })

    diffs_all = np.concatenate(diffs_all)

    # The modelled fabric is symmetric under port reversal, so it gives two distinct
    # losses across four ports and ties 0 with 3 and 1 with 2. Sorting would hide that
    # behind whatever the sort does with equal keys, and the verdict would then be an
    # artifact of tie-breaking rather than a statement about the model. Every pair is
    # compared instead, and a tie is recorded as the model declining to order that pair.
    TIE_DB = 1e-9
    agree = disagree = tied = 0
    for a in range(len(per_port)):
        for b in range(a + 1, len(per_port)):
            dm = per_port[a]["model_db"] - per_port[b]["model_db"]
            dd = per_port[a]["digitized_db"] - per_port[b]["digitized_db"]
            if abs(dm) <= TIE_DB:
                tied += 1
            elif (dm > 0) == (dd > 0):
                agree += 1
            else:
                disagree += 1

    def ranking(key):
        ordered = sorted(per_port, key=lambda p: -p[key])
        parts = [ordered[0]["trace"]]
        for prev, cur in zip(ordered, ordered[1:]):
            parts.append(" = " if abs(prev[key] - cur[key]) <= TIE_DB else " < ")
            parts.append(cur["trace"])
        return "".join(parts)

    out = {
        "band_nm": [float(lam_s.min()), float(lam_s.max())],
        "n_wavelengths": int(lam_s.size),
        "per_port": per_port,
        "mean_abs_diff_db": float(np.abs(diffs_all).mean()),
        "mean_signed_diff_db": float(diffs_all.mean()),
        "model_order_least_to_most_lossy": ranking("model_db"),
        "digitized_order_least_to_most_lossy": ranking("digitized_db"),
        "pairs_ordered_correctly": agree,
        "pairs_ordered_wrongly": disagree,
        "pairs_tied_in_the_model": tied,
        "order_reproduced": disagree == 0 and tied == 0,
        "note": ("model minus digitized, so a positive signed mean means the model "
                 "predicts less loss than the chip shows; the model uses nominal 50:50 "
                 "couplers, so no fabrication spread enters it"),
    }
    if verbose:
        print("Modelled bar-state intended-path loss vs the digitized Fig 4e diagonals, "
              f"{lam_s.min():.1f}-{lam_s.max():.1f} nm ({lam_s.size} wavelengths):")
        print("    port  trace   model      digitized   difference")
        for p in per_port:
            print(f"    {p['in_port']}->{p['out_port']}   {p['trace']}  "
                  f"{p['model_db']:+8.2f} dB  {p['digitized_db']:+8.2f} dB  "
                  f"{p['difference_db']:+8.2f} dB")
        print(f"    mean absolute difference {out['mean_abs_diff_db']:.2f} dB, "
              f"signed mean {out['mean_signed_diff_db']:+.2f} dB "
              f"({'optimistic' if out['mean_signed_diff_db'] > 0 else 'pessimistic'}: "
              f"the model predicts "
              f"{'less' if out['mean_signed_diff_db'] > 0 else 'more'} loss than measured)")
        print(f"    least to most lossy, model:     "
              f"{out['model_order_least_to_most_lossy']}")
        print(f"    least to most lossy, digitized: "
              f"{out['digitized_order_least_to_most_lossy']}")
        print(f"    ordering reproduced: {out['order_reproduced']} "
              f"({agree} of the 6 port pairs ordered correctly, {disagree} wrongly, "
              f"{tied} tied in the model, which is symmetric under port reversal)")
    return out



# --------------------------------------------------------------------------- Step 2b

SCAN_PCTS = (50.0, 75.0, 90.0, 95.0, 99.0, 99.9)
# The scan reports point estimates and RMS only. It used to bootstrap every percentile,
# and those intervals were not worth their cost: each one came out two orders of magnitude
# narrower than the spread across percentiles it sits inside, so they answered a question
# nobody was asking while accounting for most of this script's runtime. One full-strength
# bootstrap is still run, at the adopted percentile, in main(); it is passed in here as
# adopted_boot and it is the only interval the comparison below uses.


def sensitivity(lam=None, db=None, pcts=SCAN_PCTS,
                floor_db=FLOOR_DB, n_real=N_REAL, adopted_pct=PCT, adopted_boot=None,
                offset_db=None, verbose=True):
    """How far sigma_split moves under the two choices the digitized curve cannot settle.

    The first is PCT. The digitized points are the upper envelope of a truncated band, so
    their model counterpart is a high quantile of the fabrication ensemble, but which
    quantile is a judgement about how many independent ripple samples fall inside one
    digitization window, not something the figure fixes. Fitting at each of pcts shows
    what that judgement is worth.

    The second is the dB calibration of the digitized scale. diagonal_summary() finds that
    the digitized through paths and the paper's insertion-loss range do not differ by a
    constant, so there is no offset to correct; offset_db is nonetheless applied to every
    point and the fit repeated, as a sensitivity test, so that the size of the effect is
    on the record rather than argued about.

    Neither is a bootstrap. The bootstrap describes the scatter of 27 points about a model
    of a fixed form; these two describe the form itself, and they are much the larger.
    That is also why the scan itself is not bootstrapped: an interval two orders of
    magnitude narrower than the effect it sits inside adds nothing to the conclusion.
    adopted_boot carries the one full-strength interval, computed once by the caller at
    adopted_pct; without it the comparison keys below are None rather than invented.
    """
    if lam is None or db is None:
        lam, db = load_points()
    if offset_db is None:
        offset_db = -diagonal_summary(verbose=False)["offset_db"]

    scan = {}
    for p in pcts:
        r = fit_one("split", lam, db, floor_db=floor_db, n_real=n_real, pct=p)
        scan[f"p{p:g}"] = {
            "pct": float(p), "sigma_split": r["value"], "se": r["se"],
            "rms_db": r["rms_db"],
        }
        if verbose:
            print(f"    pct={p:5.1f}:  sigma_split = {r['value']:.5f} +/- {r['se']:.5f}"
                  f"   RMS = {r['rms_db']:.3f} dB")

    off = fit_one("split", lam, db + offset_db, floor_db=floor_db, n_real=n_real,
                  pct=adopted_pct)
    if verbose:
        print(f"    offset test, {offset_db:+.2f} dB on every point, at pct="
              f"{adopted_pct:g}:  sigma_split = {off['value']:.5f} +/- {off['se']:.5f}"
              f"   RMS = {off['rms_db']:.3f} dB")

    vals = [v["sigma_split"] for v in scan.values()] + [off["value"]]
    lo, hi = float(min(vals)), float(max(vals))
    if adopted_boot is None:
        b_lo = b_hi = b_src = factor = None
    else:
        b_lo, b_hi = adopted_boot["param_p05"], adopted_boot["param_p95"]
        b_src = f"adopted fit, n_boot={adopted_boot['n_boot']}"
        factor = (hi - lo) / (b_hi - b_lo)

    out = {
        "percentile_scan": scan,
        "offset_test_db": float(offset_db),
        "offset_test_sigma_split": off["value"],
        "offset_test_pct": float(adopted_pct),
        "offset_test_rms_db": off["rms_db"],
        "offset_test_note": ("a sensitivity test, not a correction: diagonal_summary() "
                             "finds the digitized dB scale and the paper's insertion-loss "
                             "range differ by different amounts at the two ends, which a "
                             "constant calibration offset cannot produce"),
        "adopted_pct": float(adopted_pct),
        "sigma_split_full_range": [lo, hi],
        "sigma_split_full_range_width": float(hi - lo),
        "sigma_split_range_factor": float(hi / lo),
        "adopted_bootstrap_param": None if b_lo is None else [float(b_lo), float(b_hi)],
        "adopted_bootstrap_param_width": None if b_lo is None else float(b_hi - b_lo),
        "adopted_bootstrap_source": b_src,
        "range_over_bootstrap_factor": None if factor is None else float(factor),
        "scan_is_bootstrapped": False,
        "scan_note": ("point estimates and RMS only: an interval at one percentile is "
                      "two orders of magnitude narrower than the spread across "
                      "percentiles, so bootstrapping every percentile cost most of the "
                      "runtime and changed no conclusion"),
    }
    if verbose:
        print(f"    sigma_split over every variant above: {lo:.5f} to {hi:.5f} "
              f"(width {hi - lo:.5f}, a factor of {hi / lo:.1f})")
        if factor is None:
            print("    no adopted-fit bootstrap was supplied, so no interval comparison")
        else:
            print(f"    parametric bootstrap of the adopted pct={adopted_pct:g} fit "
                  f"({b_src}): [{b_lo:.5f}, {b_hi:.5f}] (width {b_hi - b_lo:.5f})")
            print(f"    The model-form range is the larger of the two, by a factor of "
                  f"{factor:.0f}; the bootstrap describes the scatter of the points at "
                  f"one percentile, the range describes the choice of percentile.")
    return out


# --------------------------------------------------------------------------- Step 2c

def shape_check(lam=None, db=None, sigma_split=None, sigma_phase=SIGMA_ASSUMED,
                floor_db=FLOOR_DB, n_real=N_REAL, pct=PCT, verbose=True):
    """Does the fitted model explain the curve, or only its level?

    The fit reports an RMS, and an RMS on its own says nothing: it has to be read against
    what the most trivial possible model achieves on the same points. That model is a
    constant, whose least-squares value is the mean of the points and whose RMS is their
    standard deviation. If the bar model does not beat it by more than the stated per-point
    uncertainty, then everything the fit has extracted from the figure is one number.

    The peak-to-peak values are the same question asked directly: how much of the data's
    variation across the band the model puts back.
    """
    if lam is None or db is None:
        lam, db = load_points()
    if sigma_split is None:
        sigma_split = fit_one("split", lam, db, held=sigma_phase, floor_db=floor_db,
                              n_real=n_real, pct=pct)["value"]
    model = bar_model(lam, sigma_split, sigma_phase, floor_db, n_real, pct=pct)
    const = float(db.mean())
    const_rms = float(np.sqrt(np.mean((db - const) ** 2)))
    model_rms = float(np.sqrt(np.mean((db - model) ** 2)))
    out = {
        "constant_db": const,
        "constant_rms_db": const_rms,
        "model_rms_db": model_rms,
        "data_ptp_db": float(np.ptp(db)),
        "model_ptp_db": float(np.ptp(model)),
        "model_ptp_over_data_ptp": float(np.ptp(model) / np.ptp(db)),
        "rms_advantage_db": float(const_rms - model_rms),
        "point_sd_db": DIGITIZATION_SD_DB,
        "corr_model_data": float(np.corrcoef(model, db)[0, 1]),
        "sigma_split": float(sigma_split),
        "sigma_phase": float(sigma_phase),
        "pct": float(pct),
        "n_points": int(lam.size),
    }
    if verbose:
        print(f"    best constant = {const:.3f} dB, RMS = {const_rms:.4f} dB")
        print(f"    bar model at sigma_split={sigma_split:.5f}, "
              f"sigma_phase={sigma_phase:.2f}, pct={pct:g}: "
              f"RMS = {model_rms:.4f} dB")
        print(f"    peak-to-peak across the band: data {out['data_ptp_db']:.3f} dB, "
              f"model {out['model_ptp_db']:.4f} dB "
              f"({100 * out['model_ptp_over_data_ptp']:.2f}% of the data's)")
        sign = "better" if out["rms_advantage_db"] > 0 else "worse"
        print(f"    the model is {abs(out['rms_advantage_db']):.4f} dB {sign} than the "
              f"constant, against a stated per-point uncertainty of "
              f"{DIGITIZATION_SD_DB} dB")
    return out


def main(verbose=True, n_boot=ADOPTED_BOOT_N, param_seed=1, fig_path=FIG, n_real=N_REAL):
    lam, db = load_points()
    fits = {w: fit_one(w, lam, db, n_real=n_real) for w in ("split", "phase")}
    joint = fit_joint(lam, db, n_real=n_real)
    # A fit that sits at sigma = 0 has no interior optimum, so there is nothing for a
    # bootstrap to resample around; it is reported as a boundary result instead.
    boots = {w: (bootstrap_one(w, lam, db, n_boot=n_boot, param_seed=param_seed,
                               n_real=n_real, p0=fits[w]["value"])
                 if not fits[w]["at_bound"] else None)
             for w in ("split", "phase")}

    if verbose:
        print("Fit of the all-bar T32 model to the digitized Fig 4e points:")
        print(f"  {len(lam)} points over {FIT_RANGE_NM[0]}-{FIT_RANGE_NM[1]} nm, "
              f"n_real={n_real}, pct={PCT:g}, floor held at {FLOOR_DB:.0f} dB")
        for w in ("split", "phase"):
            f, b = fits[w], boots[w]
            name = ("coupler-split spread sigma_split" if w == "split"
                    else "arm-phase spread sigma_phase (rad)")
            if f["at_bound"]:
                held_only = float(bar_model(
                    lam, *((0.0, f["held_value"]) if w == "split"
                           else (f["held_value"], 0.0)),
                    FLOOR_DB, n_real).mean())
                print(f"  {name}: NO INTERIOR OPTIMUM, runs to {f['value']:.4f}")
                print(f"    with sigma_{f['held']} held at {f['held_value']:.2f} the model "
                      f"already gives {held_only:.2f} dB at zero {w} spread, against a data "
                      f"mean of {db.mean():.2f} dB, and this parameter can only add "
                      f"leakage; RMS at the bound = {f['rms_db']:.2f} dB")
                print(f"    no bootstrap: there is no interior optimum to resample around")
                continue
            print(f"  {name} = {f['value']:.4f} +/- {f['se']:.4f}  "
                  f"(sigma_{f['held']} held at {f['held_value']:.2f})")
            print(f"    fit RMS = {f['rms_db']:.2f} dB")
            print(f"    parametric bootstrap, +/-{DIGITIZATION_SD_DB} dB, "
                  f"{b['n_boot']} resamples ({b['n_param_failed']} failed): "
                  f"[{b['param_p05']:.4f}, {b['param_p95']:.4f}]")
            print(f"    {BOOTSTRAP_NOTE}")
        c = joint["correlation"]
        print(f"  joint two-parameter fit, NOT adopted, run only for its correlation "
              f"matrix:")
        print(f"    sigma_split = {joint['sigma_split']:.4f} +/- {joint['sigma_split_se']:.4f}, "
              f"sigma_phase = {joint['sigma_phase']:.4f} +/- {joint['sigma_phase_se']:.4f}, "
              f"RMS = {joint['rms_db']:.2f} dB")
        print(f"    correlation = [[{c[0][0]:+.4f}, {c[0][1]:+.4f}], "
              f"[{c[1][0]:+.4f}, {c[1][1]:+.4f}]]")
        print("    Each single fit has a 1x1 covariance, so its correlation matrix is "
              "[[1.0]] by construction.")
        print(f"  The digitized points are the band's upper envelope, so the model "
              f"reports the ensemble's {PCT:g}th percentile rather than its mean; "
              f"quantile_sensitivity() gives the fit at other percentiles.")

    if verbose:
        print("  does the model explain the curve or only its level?")
    shape = shape_check(lam, db, sigma_split=fits["split"]["value"], n_real=n_real,
                        verbose=verbose)

    if verbose:
        print("  sensitivity of sigma_split to the two choices the curve cannot settle:")
    sens = sensitivity(lam, db, n_real=n_real, adopted_boot=boots["split"],
                       verbose=verbose)

    if fig_path:
        _figure(lam, db, fits, boots, fig_path, n_real, verbose)

    out = {"n_points": int(lam.size), "fit_range_nm": list(FIT_RANGE_NM),
           "n_real": int(n_real), "floor_db": float(FLOOR_DB),
           "digitization_sd_db": DIGITIZATION_SD_DB,
           "pct": float(PCT),
           "adopted": False,
           "adopted_note": ("the fitted value was not adopted: the model fits these "
                            "points no better than a constant and the percentile choice "
                            "moves the result by a factor of 4.6"),
           "data_is_upper_envelope": True,
           "model": f"4x4 mesh all-bar T32, {PCT:g}th percentile of the fabrication "
                    f"ensemble, normalised to total output",
           "statistic_note": ("the digitized points are a peak-hold over the fast "
                              "wavelength ripple, so the model reports a high quantile of "
                              "the fabrication ensemble; fitting its mean instead absorbs "
                              "the quantile-to-mean offset into the fitted spread"),
           "joint_fit_not_adopted": joint,
           "sensitivity": sens,
           "shape_check": shape}
    for w in ("split", "phase"):
        block = dict(fits[w])
        if boots[w] is None:
            block["bootstrap"] = None
            block["bootstrap_note"] = ("not run: the fit has no interior optimum, so "
                                       "there is nothing to resample around")
        else:
            b = dict(boots[w])
            block["n_boot"] = b.pop("n_boot")
            block.update({f"boot_{k}": v for k, v in b.items()})
            block["bootstrap_note"] = BOOTSTRAP_NOTE
        out[f"sigma_{w}_fit"] = block
    return out


def _figure(lam, db, fits, boots, fig_path, n_real, verbose):
    """Overlay both single-parameter fits on the digitized points."""
    lf = np.linspace(lam.min(), lam.max(), 60)
    fig, ax = plt.subplots(figsize=(7, 4.4))
    ax.scatter(lam, db, s=26, color="#C44E52", zorder=3,
               label=f"digitized Fig 4e $T_{{32}}$ upper envelope (±{DIGITIZATION_SD_DB} dB)")
    ax.plot(lf, bar_model_mean(lf, fits["split"]["value"], SIGMA_ASSUMED, FLOOR_DB,
                               n_real), color="#8172B2", lw=1.5, ls=":",
            label=("ensemble mean at the same spread\n(the level; the points are its "
                   "envelope)"))
    styles = {"split": ("#4C72B0", "--", "coupler-split spread",
                        "$\\sigma_{\\mathrm{split}}$"),
              "phase": ("#55A868", "-", "arm-phase spread",
                        "$\\sigma_{\\mathrm{phase}}$")}
    for w in ("split", "phase"):
        f = fits[w]
        if f["at_bound"]:
            continue
        colour, ls, label, sym = styles[w]
        args = ((f["value"], f["held_value"]) if w == "split"
                else (f["held_value"], f["value"]))
        ax.plot(lf, bar_model(lf, *args, FLOOR_DB, n_real), color=colour, lw=2, ls=ls,
                label=(f"{label} fitted\n{sym}={f['value']:.4f} ± {f['se']:.4f}, "
                       f"other held at {f['held_value']:.2f}\nRMS={f['rms_db']:.2f} dB"))
    ax.set_xlabel("Wavelength (nm)"); ax.set_ylabel("Bar-state crosstalk (dB)")
    ax.set_title(f"Fabrication spread fitted to the chip's measured bar-state crosstalk\n"
                 f"(LightIN Fig 4e, all-bar $T_{{32}}$; envelope vs ensemble "
                 f"p{PCT:g})", fontsize=10)
    ax.legend(fontsize=7, loc="lower right"); ax.set_ylim(-30, -16)
    fig.tight_layout(); fig.savefig(fig_path, dpi=140)
    plt.close(fig)
    if verbose:
        print(f"  wrote {os.path.abspath(fig_path)}")


if __name__ == "__main__":
    print("--- are the two spreads separately identifiable? ---")
    identifiability()
    print("\n--- sensitivity to n_real ---")
    n_real_scatter()
    print("\n--- sensitivity to the ensemble quantile the model reports ---")
    quantile_sensitivity()
    print("\n--- fits ---")
    main()
