"""
Coupled-mode-theory (CMT) directional coupler and link models for 220 nm SOI.

Replaces the earlier toy/lossless coupler with a physically grounded, wavelength-
dependent model parameterised from the silicon-photonics literature:

* Strip-waveguide propagation loss ~ 2 dB/cm
  (2.14 dB/cm, arXiv:2111.01792; 2.2 +/- 0.8 dB/cm over 19 dies, arXiv:1203.0767;
   ~2 dB/cm typical review value, nanoph-2023-0836).
* Directional-coupler dispersion: power coupling drifts with wavelength
  (kappa varies ~0.60 -> 0.82 over 1500-1600 nm for a 100 nm gap, arXiv:2302.13177);
  the standard CMT fit form is K(lambda) = A sin^2(k'(lambda) L + phi0)
  (Ghent pub_4030; US 9,445,165). A 3-dB straight DC hits 50:50 at one wavelength only.
* Grating coupler: ~4.4 dB insertion loss, ~45 nm 1.5-dB bandwidth, peak ~1545 nm
  (arXiv:1203.0767); 1-dB bandwidth ~38 nm (PMC10576773).
* Directional-coupler excess loss ~ 0.1-0.8 dB (Optica jlt-35-22-4916).

These let us model the *measured-style* dispersion of the LightIN couplers (the exact
chip values are not published; parameters here are literature-typical and the model is
fittable to real data via fit_dc_dispersion()).
"""

import numpy as np

# --- Device constants from the LightIN paper (Methods) + supplementary ---
LAMBDA0 = 1560.0       # nm, matrix-multiplication design wavelength (Methods)
DC_LAMBDA_3DB = 1574.7  # nm, 3-dB point from fitting the mesh T20 model to digitized Fig 4d (scripts/fit_fig4.py); design wavelength is 1560 nm.
# The fit draws the fabrication spreads from switching.SIGMA_SPLIT and SIGMA_PHASE, both
# assumed at 0.02, and takes this wavelength and the slope as its free parameters, so it
# is solved in one pass: refitting at the converged values reproduces them exactly. The
# fitted value is 1574.6785 +/- 0.6093 nm, so 1560 nm lies outside the interval.
DC_SLOPE = 0.0026      # rad/nm, coupling-phase dispersion slope of the same fit
LAMBDA_MRM = 1555.0    # nm, MRM wavelength-locking experiment (Methods)
N_GROUP = 4.0          # group index, stated in paper ("group index of 4")
N_EFF = 2.36           # phase index, 450x220 nm SOI strip TE @1560 nm (geometry-derived)
DC_LENGTH_UM = 11.5    # directional-coupler length (Methods)
DC_GAP_NM = 200.0      # directional-coupler gap (Methods)
WG_WIDTH_NM = 450.0    # waveguide width (Methods)
SQUARE_SIDE_UM = 500.0 # square-mesh unit side length (Methods) -> loop length
ARM_LENGTH_UM = 208.0  # MZI arm length (Methods)
HEATER_LENGTH_UM = 100.0  # phase-shifter heater length (Methods)
PROP_LOSS_DB_CM = 2.0  # strip-waveguide propagation loss (~2.14 dB/cm, arXiv:2111.01792)

# --- Ground truth for the synthetic demo coupler dataset (_demo_measured_dataset) ---
DEMO_LAMBDA0 = 1560.0  # nm, fixed reference wavelength of the synthetic demo dataset; independent of the chip coupler fit
# Generator and fitter both reference kappa0 to DEMO_LAMBDA0, so the fitted kappa0 is
# directly comparable to DEMO_TRUE_KAPPA0 whatever DC_LAMBDA_3DB happens to be.
DEMO_TRUE_KAPPA0 = 0.5      # power coupling at DEMO_LAMBDA0
DEMO_TRUE_SLOPE = 0.0042    # rad/nm, linear coupling-phase dispersion
DEMO_TRUE_QUAD = -8e-6      # rad/nm^2, higher-order term the CMT fit form cannot represent


def dc_power_coupling(lam, kappa0=0.5, slope=DC_SLOPE, lam0=DC_LAMBDA_3DB):
    """Power cross-coupling ratio of a directional coupler, 50:50 at lam0.

    K(lambda) = sin^2( arcsin(sqrt(kappa0)) + slope*(lambda - lam0) ).
    slope ~ 0.004 rad/nm gives a 3-dB DC whose split drifts ~+/-0.08 over +/-20 nm,
    consistent with measured strip-DC dispersion.
    """
    a0 = np.arcsin(np.sqrt(kappa0))
    return np.sin(a0 + slope * (np.asarray(lam, float) - lam0)) ** 2


def dc_field_matrix(lam, kappa0=0.5, slope=DC_SLOPE, excess_loss_db=0.1,
                    lam0=DC_LAMBDA_3DB):
    """2x2 field transfer of a (slightly lossy) directional coupler."""
    k = dc_power_coupling(lam, kappa0, slope, lam0)
    t, c = np.sqrt(1 - k), np.sqrt(k)
    amp = 10 ** (-excess_loss_db / 20.0)
    return amp * np.array([[t, 1j * c], [1j * c, t]], dtype=complex)


def mzi_single_theta(theta, lam, kappa0=0.5, slope=DC_SLOPE, excess_loss_db=0.1,
                     kappa0_b=None, arm_phase_err=0.0, lam0=DC_LAMBDA_3DB):
    """Single-internal-phase PUC built from two (dispersive) directional couplers.

    M = DC_b(lambda) . diag(e^{i(theta+arm_phase_err)}, 1) . DC_a(lambda).
    With identical ideal 3-dB couplers (lam=lam0) this reduces to the paper's Eq. 1 and
    reaches perfect cross/bar. Real MZIs have two independently fabricated couplers
    (kappa0 != kappa0_b) and small arm phase/length imbalance; these limit the achievable
    extinction (the 'arm imbalance' the paper notes) and make the bar state's crosstalk
    finite and wavelength dependent.
    """
    if kappa0_b is None:
        kappa0_b = kappa0
    DCa = dc_field_matrix(lam, kappa0, slope, excess_loss_db, lam0)
    DCb = dc_field_matrix(lam, kappa0_b, slope, excess_loss_db, lam0)
    P = np.diag([np.exp(1j * (theta + arm_phase_err)), 1.0])
    return DCb @ P @ DCa


def extinction_ratio_db(lam, kappa0=0.5, slope=DC_SLOPE, n=512, lam0=DC_LAMBDA_3DB):
    """Max/min through-port transmission over theta -> achievable extinction (dB).

    Returns None when the minimum transmission is an ideal null (below 1e-15). The
    model has no loss and no coupler imbalance at the 3-dB wavelength, so the ratio
    diverges: reporting a floored number there would state a finite extinction the
    model does not actually predict.
    """
    thetas = np.linspace(0, 2 * np.pi, n)
    p = np.array([np.abs(mzi_single_theta(th, lam, kappa0, slope, 0.0,
                                          lam0=lam0)[0, 0]) ** 2
                  for th in thetas])
    if p.min() < 1e-15:
        return None
    return 10 * np.log10(p.max() / p.min())


def grating_coupler_db(lam, peak_loss_db=4.4, lam_peak=1545.0, bw_1p5db=45.0):
    """Per-facet grating-coupler loss (dB). Quadratic roll-off; +1.5 dB at +/- bw/2."""
    k = 1.5 / (bw_1p5db / 2.0) ** 2
    return peak_loss_db + k * (np.asarray(lam, float) - lam_peak) ** 2


def propagation_loss_db(length_cm, alpha_db_cm=2.0):
    """Strip-waveguide propagation loss (dB)."""
    return alpha_db_cm * length_cm


def link_budget_db(lam=LAMBDA0, waveguide_cm=0.45, n_couplers_in_path=4,
                   dc_excess_db=0.1, n_grating=2):
    """End-to-end fibre-to-fibre loss budget (dB) at one wavelength."""
    return (n_grating * grating_coupler_db(lam)
            + propagation_loss_db(waveguide_cm)
            + n_couplers_in_path * dc_excess_db)


def fit_dc_dispersion(lam_data, kpow_data, p0=(0.5, 0.004), lam0=DC_LAMBDA_3DB):
    """Fit the CMT coupling form K(lambda)=sin^2(arcsin(sqrt(k0))+slope*(lam-lam0)).

    Returns (kappa0, slope, rms_residual), with kappa0 the power coupling at lam0.
    Use this on real measured coupler data.
    """
    from scipy.optimize import curve_fit

    def model(lam, k0, slope):
        return np.sin(np.arcsin(np.sqrt(np.clip(k0, 1e-6, 1 - 1e-6)))
                      + slope * (lam - lam0)) ** 2

    popt, _ = curve_fit(model, lam_data, kpow_data, p0=list(p0), maxfev=20000)
    resid = kpow_data - model(lam_data, *popt)
    return float(popt[0]), float(popt[1]), float(np.sqrt(np.mean(resid ** 2)))


def _demo_measured_dataset(seed=0, lam0=DEMO_LAMBDA0, kappa0=DEMO_TRUE_KAPPA0,
                           slope=DEMO_TRUE_SLOPE, quad=DEMO_TRUE_QUAD):
    """Synthetic-but-physical 'measured' coupler data (higher-order dispersion + noise).

    Stands in for real measurements; fit_dc_dispersion recovers the CMT parameters.
    lam0 defaults to DEMO_LAMBDA0, the dataset's own reference wavelength, and the demo
    fit is asked for the same lam0, so kappa0 here and the fitted kappa0 are the power
    coupling at one and the same wavelength. Referencing them to different wavelengths
    shifts the fitted kappa0 by roughly slope * (lam0_fit - lam0_gen) without the fit
    itself changing, which is why the demo does not follow DC_LAMBDA_3DB.
    """
    rng = np.random.default_rng(seed)
    lam = np.linspace(1520, 1580, 25)
    # quadratic dispersion in the coupling phase + measurement noise
    a = np.arcsin(np.sqrt(kappa0)) + slope * (lam - lam0) + quad * (lam - lam0) ** 2
    k = np.sin(a) ** 2 + rng.normal(0, 0.004, size=lam.shape)
    return lam, np.clip(k, 0, 1)


def run(verbose=True):
    out = {}
    out["extinction_at_3db_db"] = extinction_ratio_db(DC_LAMBDA_3DB)
    out["extinction_at_1560_db"] = extinction_ratio_db(1560.0)
    out["extinction_at_1520_db"] = extinction_ratio_db(1520.0)
    out["extinction_at_1580_db"] = extinction_ratio_db(1580.0)
    out["link_budget_db"] = link_budget_db()
    lam, kdata = _demo_measured_dataset()
    k0, slope, rms = fit_dc_dispersion(lam, kdata, lam0=DEMO_LAMBDA0)
    out["fit_kappa0"], out["fit_slope"], out["fit_rms"] = k0, slope, rms
    out["demo_true_kappa0"] = DEMO_TRUE_KAPPA0
    out["demo_true_slope"] = DEMO_TRUE_SLOPE
    out["demo_fit_lam0_nm"] = DEMO_LAMBDA0
    if verbose:
        def _db(v):
            return "unbounded (ideal null)" if v is None else f"{v:.1f} dB"
        print(f"[coupler] single-theta MZI extinction: "
              f"{_db(out['extinction_at_3db_db'])} @{DC_LAMBDA_3DB:.0f}nm (3-dB point), "
              f"{_db(out['extinction_at_1560_db'])} @1560nm, "
              f"{_db(out['extinction_at_1520_db'])} @1520nm, "
              f"{_db(out['extinction_at_1580_db'])} @1580nm "
              f"(coupler-imbalance limited off 3-dB point)")
        print(f"[coupler] fibre-to-fibre link budget @1560nm = {out['link_budget_db']:.1f} dB "
              f"(2x grating ~4.4 dB + ~2 dB/cm prop + DC excess)")
        print(f"[coupler] CMT dispersion fit to demo data @{DEMO_LAMBDA0:.0f}nm: "
              f"kappa0={k0:.3f} (true {DEMO_TRUE_KAPPA0:.3f}), "
              f"slope={slope:.4f} rad/nm (true {DEMO_TRUE_SLOPE:.4f}), "
              f"RMS residual={rms:.4f}")
    return out


if __name__ == "__main__":
    run()
