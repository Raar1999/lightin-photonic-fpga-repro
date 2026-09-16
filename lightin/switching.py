"""
4 x 4 optical switching on the square mesh (paper Fig. 4), physical-coupler version.

The 4-stage planar (Spanke-Benes) switch is a rectangular mesh of nearest-neighbour 2x2
switches. Each switch is a single-theta PUC built from two *dispersive* directional
couplers (lightin.coupler). The switch phase is set to ideal cross/bar at the design
wavelength (1560 nm) and held fixed; crosstalk vs wavelength then emerges from the real
coupler dispersion -- the physical mechanism behind Fig. 4d,e -- rather than a toy slope.

Reproducible: topology, the crosstalk-vs-wavelength mechanism, the loss budget from
literature-grounded values. NOT reproducible (hardware-only): the exact measured spectra,
which depend on this chip's couplers.
"""

import numpy as np
from .coupler import (mzi_single_theta, link_budget_db, LAMBDA0,
                      DC_LAMBDA_3DB, DC_SLOPE)

SIGMA_SPLIT = 0.02     # coupler-to-coupler power-split spread. Assumed, no source.
SIGMA_PHASE = 0.02     # rad, arm phase imbalance. Assumed, no source.
# Named rather than left as inline literals so that scripts/fit_fig4e.py can fit one of
# them to the digitized Fig 4e bar-state curve and the tests can pin the two models
# together. Both still carry the assumed value here.

FIG4D_FLOOR_DB = -26.2   # dB, crosstalk floor fitted to digitized Fig 4d alongside
# lam0 and slope. It is phenomenological: the mesh model has no term that produces
# it, so it is recorded here and deliberately not added to any crosstalk this
# module reports, which would state a floor the model does not predict.

THETA_CROSS = 0.0     # DC.DC = full cross at the 3-dB wavelength
THETA_BAR = np.pi     # bar at the 3-dB wavelength


def _layer_pairs(N, layer):
    start = layer % 2
    return [(i, i + 1) for i in range(start, N - 1, 2)]


def _embed(T2, m, n, N):
    U = np.eye(N, dtype=complex)
    U[m, m], U[m, n] = T2[0, 0], T2[0, 1]
    U[n, m], U[n, n] = T2[1, 0], T2[1, 1]
    return U


def fabric_matrix(state, lam, N=4, kappa0s=None, prop_db_per_stage=0.25,
                  lam0=None, slope=None):
    """NxN field transfer for an all-'cross'/'bar' config using dispersive couplers.

    lam0 and slope select the directional-coupler dispersion; None takes the fitted
    chip values DC_LAMBDA_3DB and DC_SLOPE.
    """
    lam0 = DC_LAMBDA_3DB if lam0 is None else lam0
    slope = DC_SLOPE if slope is None else slope
    n_mzi = N * (N - 1) // 2
    if kappa0s is None:
        kappa0s = np.full(n_mzi, 0.5)
    theta = THETA_CROSS if state == "cross" else THETA_BAR
    amp = 10 ** (-prop_db_per_stage / 20.0)
    U = np.eye(N, dtype=complex)
    k = 0
    for layer in range(N):
        L = np.eye(N, dtype=complex)
        for (m, n) in _layer_pairs(N, layer):
            M = mzi_single_theta(theta, lam, kappa0=kappa0s[k], slope=slope,
                                 excess_loss_db=0.1, lam0=lam0)
            L = _embed(M, m, n, N) @ L
            k += 1
        U = (amp * L) @ U
    return U


def power_spectra(state, lambdas, N=4, seed=0, lam0=None, slope=None):
    """Per-port power transfer (linear, 0..1) vs wavelength, with coupler spread.

    Linear power is the primitive: a port pair the topology forbids is exactly 0 here,
    which is what distinguishes a structural zero from a small crosstalk level.
    transmission_spectra() is the dB view of the same array.

    lam0 and slope select the directional-coupler dispersion; None takes the fitted
    chip values DC_LAMBDA_3DB and DC_SLOPE. Passing them explicitly lets the mesh
    itself be fitted to measured spectra (scripts/fit_fig4.mesh_t20_model).
    """
    lam0 = DC_LAMBDA_3DB if lam0 is None else lam0
    slope = DC_SLOPE if slope is None else slope
    rng = np.random.default_rng(seed)
    n_mzi = N * (N - 1) // 2
    kappa_a = np.clip(rng.normal(0.5, SIGMA_SPLIT, size=n_mzi), 0.3, 0.7)  # two independently
    kappa_b = np.clip(rng.normal(0.5, SIGMA_SPLIT, size=n_mzi), 0.3, 0.7)  # fabricated couplers
    arm_err = rng.normal(0, SIGMA_PHASE, size=n_mzi)                       # arm phase imbalance
    theta = THETA_CROSS if state == "cross" else THETA_BAR
    amp = 10 ** (-0.25 / 20.0)
    T = np.zeros((N, N, len(lambdas)))
    for li, lam in enumerate(lambdas):
        U = np.eye(N, dtype=complex)
        k = 0
        for layer in range(N):
            L = np.eye(N, dtype=complex)
            for (m, n) in _layer_pairs(N, layer):
                M = mzi_single_theta(theta, lam, kappa0=kappa_a[k], slope=slope,
                                     excess_loss_db=0.1, kappa0_b=kappa_b[k],
                                     arm_phase_err=arm_err[k], lam0=lam0)
                L = _embed(M, m, n, N) @ L
                k += 1
            U = (amp * L) @ U
        T[:, :, li] = np.abs(U) ** 2
    return T, (kappa_a, kappa_b)


def transmission_spectra(state, lambdas, N=4, seed=0, lam0=None, slope=None):
    """Per-port power transfer (dB) vs wavelength; dB view of power_spectra().

    An exactly forbidden port pair maps to -inf, which is the honest dB value. No
    constant is added to keep the logarithm finite: doing so would report a
    crosstalk level the model does not predict.
    """
    T, kappas = power_spectra(state, lambdas, N, seed, lam0, slope)
    with np.errstate(divide="ignore"):
        return 10 * np.log10(T), kappas


ZERO_TOL = 1e-20    # raw linear power below this is a structural zero, not crosstalk


def _db(power):
    with np.errstate(divide="ignore"):
        return float(10 * np.log10(power))


def crosstalk_summary(lambdas=None, N=4):
    if lambdas is None:
        lambdas = np.linspace(1530, 1565, 141)   # C-band
    out = {}
    for state in ("cross", "bar"):
        T, _ = power_spectra(state, lambdas, N)
        U0 = fabric_matrix(state, LAMBDA0, N)
        intended = np.argmax(np.abs(U0) ** 2, axis=0)
        center = np.argmin(np.abs(lambdas - LAMBDA0))
        xt_center, il_center, xt_band, structural_zeros = [], [], [], 0
        for j in range(N):
            i_int = intended[j]
            il_center.append(_db(T[i_int, j, center]))
            for i in range(N):
                if i == i_int:
                    continue
                # A port pair the topology forbids carries no power at all. That is a
                # structural zero, not a crosstalk level, so it is counted rather than
                # allowed to set the reported best or worst case. The test is on the
                # raw linear power, never on a dB value that a floor could have set.
                for power, bucket in ((T[i, j, center], xt_center),
                                      (T[i, j].max(), xt_band)):
                    if power < ZERO_TOL:
                        structural_zeros += 1
                    else:
                        bucket.append(_db(power))
        with np.errstate(divide="ignore"):
            Tdb = 10 * np.log10(T)
        out[state] = {
            "spectra_db": Tdb, "lambdas": lambdas, "intended": intended,
            "xtalk_center_db": ((float(np.max(xt_center)), float(np.min(xt_center)))
                                if xt_center else None),
            "onchip_loss_center_db": float(np.mean(il_center)),
            "worst_xtalk_over_cband_db": float(np.max(xt_band)) if xt_band else None,
            "structural_zeros": structural_zeros,
        }
    return out


def worst_cross_xtalk_db(lambdas):
    """Worst (highest) cross-state crosstalk over a wavelength grid, in dB.

    Same definition as worst_xtalk_over_cband_db: the maximum over every unintended
    output port and every wavelength, with structural zeros excluded.
    """
    return crosstalk_summary(lambdas=np.asarray(lambdas, float))["cross"]["worst_xtalk_over_cband_db"]


ARM_LOSS_DB = (0.0, 0.0)   # per-arm loss of the MZI phase section, both arms
# The model's phase section is diag(exp(i(theta+arm_phase_err)), 1): both entries have
# modulus exactly 1, so the two arms are equally lossy. Loss enters a cell only through
# the two couplers' excess_loss_db and the per-stage propagation amplitude, both of
# which are scalar prefactors on the whole 2x2 and so cannot feed an unintended port.
# The pair is named here so leak_mechanism_check() can substitute its mean.


def _cell_variant(theta, lam, kappa0_a, kappa0_b, arm_phase_err,
                  arm_loss_db=ARM_LOSS_DB, ideal_coupler=False,
                  excess_loss_db=0.1, slope=None, lam0=None):
    """One switch cell with each leakage term separately overridable.

    Reproduces coupler.mzi_single_theta exactly under its defaults (asserted in
    tests/test_reproduction.py); diagnostic only, nothing in the results path calls it
    with non-default arguments except leak_mechanism_check().

    ideal_coupler forces both couplers to an exact 50:50 split at lam, discarding both
    the fabricated spread and the fitted dispersion. arm_loss_db is a (arm1, arm2) pair
    in dB applied inside the phase section.
    """
    from .coupler import dc_power_coupling
    slope = DC_SLOPE if slope is None else slope
    lam0 = DC_LAMBDA_3DB if lam0 is None else lam0
    if ideal_coupler:
        ka = kb = 0.5
    else:
        ka = dc_power_coupling(lam, kappa0_a, slope, lam0)
        kb = dc_power_coupling(lam, kappa0_b, slope, lam0)
    amp = 10 ** (-excess_loss_db / 20.0)
    DCa = amp * np.array([[np.sqrt(1 - ka), 1j * np.sqrt(ka)],
                          [1j * np.sqrt(ka), np.sqrt(1 - ka)]], dtype=complex)
    DCb = amp * np.array([[np.sqrt(1 - kb), 1j * np.sqrt(kb)],
                          [1j * np.sqrt(kb), np.sqrt(1 - kb)]], dtype=complex)
    g = 10 ** (-np.asarray(arm_loss_db, float) / 20.0)
    P = np.diag([g[0] * np.exp(1j * (theta + arm_phase_err)), g[1] + 0j])
    return DCb @ P @ DCa


def _cell_draws(N=4, seed=0):
    """The per-MZI coupler splits and arm phase errors power_spectra() draws."""
    rng = np.random.default_rng(seed)
    n_mzi = N * (N - 1) // 2
    kappa_a = np.clip(rng.normal(0.5, SIGMA_SPLIT, size=n_mzi), 0.3, 0.7)
    kappa_b = np.clip(rng.normal(0.5, SIGMA_SPLIT, size=n_mzi), 0.3, 0.7)
    arm_err = rng.normal(0, SIGMA_PHASE, size=n_mzi)
    return kappa_a, kappa_b, arm_err


def _center_range_with_arm_loss(state, arm_loss_db, lambdas=None, N=4, seed=0):
    """Full-fabric crosstalk range at 1560 nm with a given per-arm loss pair.

    Same construction and same structural-zero rule as crosstalk_summary(); the only
    difference is that the cells are built by _cell_variant so arm_loss_db can be set.
    """
    if lambdas is None:
        lambdas = np.linspace(1530, 1565, 141)
    kappa_a, kappa_b, arm_err = _cell_draws(N, seed)
    theta = THETA_CROSS if state == "cross" else THETA_BAR
    amp = 10 ** (-0.25 / 20.0)
    center = int(np.argmin(np.abs(lambdas - LAMBDA0)))
    lam = float(lambdas[center])
    U = np.eye(N, dtype=complex)
    k = 0
    for layer in range(N):
        L = np.eye(N, dtype=complex)
        for (m, n) in _layer_pairs(N, layer):
            M = _cell_variant(theta, lam, kappa_a[k], kappa_b[k], arm_err[k],
                              arm_loss_db=arm_loss_db)
            L = _embed(M, m, n, N) @ L
            k += 1
        U = (amp * L) @ U
    T = np.abs(U) ** 2
    intended = np.argmax(np.abs(fabric_matrix(state, LAMBDA0, N)) ** 2, axis=0)
    xt = [_db(T[i, j]) for j in range(N) for i in range(N)
          if i != intended[j] and T[i, j] >= ZERO_TOL]
    return [float(np.max(xt)), float(np.min(xt))] if xt else None


def leak_mechanism_check(lam=LAMBDA0, cell=0, N=4, seed=0):
    """Which term in the model sets the leakage into a cell's unintended port.

    Takes one switch cell (the mesh's `cell`-th MZI, with the splits and arm phase
    error power_spectra() draws for it) at `lam`, in each state, and reports the
    unintended-port transmission in dB for the model as it stands, for both arms set
    to the mean of the two arm losses, and for ideal 50:50 couplers. A value whose
    linear leakage falls below ZERO_TOL is reported as None rather than as a large
    negative dB number, on the same rule crosstalk_summary() uses.
    """
    kappa_a, kappa_b, arm_err = _cell_draws(N, seed)
    mean_arm_loss = float(np.mean(ARM_LOSS_DB))
    out = {}
    for state, theta in (("bar", THETA_BAR), ("cross", THETA_CROSS)):
        # bar sends 0->0, so its leak is the off-diagonal; cross sends 0->1.
        idx = (1, 0) if state == "bar" else (0, 0)
        for suffix, kw in (("model", {}),
                           ("equal_arm_loss",
                            {"arm_loss_db": (mean_arm_loss, mean_arm_loss)}),
                           ("ideal_coupler", {"ideal_coupler": True})):
            M = _cell_variant(theta, lam, kappa_a[cell], kappa_b[cell],
                              arm_err[cell], **kw)
            p = float(np.abs(M[idx]) ** 2)
            out[f"{state}_cell_leak_db_{suffix}"] = _db(p) if p >= ZERO_TOL else None
    out["bar_center_db_equal_arm_loss"] = _center_range_with_arm_loss(
        "bar", (mean_arm_loss, mean_arm_loss), N=N, seed=seed)
    return out


ONCHIP_IL_PAPER_RANGE_DB = [-2.99, -1.85]   # paper's measured on-chip insertion loss


def onchip_insertion_loss(lam=1560.0, N=4):
    """Transmission of each intended path through the fabric alone, in dB.

    The fabric model carries the mesh's own losses -- propagation across four stages
    and the directional-coupler excess loss -- and no grating couplers, so these
    numbers are comparable with the paper's measured on-chip insertion loss rather
    than with the fibre-to-fibre budget in link_budget_db().

    Covers both all-cross and all-bar, four inputs each: eight intended paths.
    Returns min_db, max_db and paths as [state, input, output, loss_db].
    """
    paths = []
    for state in ("cross", "bar"):
        U = fabric_matrix(state, lam, N)
        T = np.abs(U) ** 2
        for j in range(N):
            i = int(np.argmax(T[:, j]))
            paths.append([state, j, i, _db(T[i, j])])
    losses = [p[3] for p in paths]
    return {"min_db": float(min(losses)), "max_db": float(max(losses)),
            "paths": paths}


def insertion_loss_budget(**kw):
    """Backwards-compatible: fibre-to-fibre link budget at 1560 nm (dB)."""
    return link_budget_db(**kw)


def run(verbose=True):
    s = crosstalk_summary()
    fl = link_budget_db()
    if verbose:
        for state in ("cross", "bar"):
            hi, lo = s[state]["xtalk_center_db"]
            print(f"[switching/{state}] crosstalk @1560nm: {lo:.1f} to {hi:.1f} dB; "
                  f"worst over C-band (1530-1565nm): {s[state]['worst_xtalk_over_cband_db']:.1f} dB; "
                  f"on-chip loss ~ {abs(s[state]['onchip_loss_center_db']):.1f} dB")
        print(f"[switching] fibre-to-fibre link budget @1560nm ~ {fl:.1f} dB "
              f"(grating-coupler dominated)")
        print("[switching] paper measured: -45 to <-20 dB @1560nm; <-15/-20 dB over >20nm.")
        print("[switching] crosstalk now arises from CMT coupler dispersion; measured spectra are hardware-only.")
    return s


if __name__ == "__main__":
    run()
