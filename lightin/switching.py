"""
4 x 4 optical switching on the square mesh (paper Fig. 4), physical-coupler version.

The 4-stage planar (Spanke-Benes) switch is a rectangular mesh of nearest-neighbour 2x2
switches. Each switch is a single-theta PUC built from two *dispersive* directional
couplers (lightin.coupler). The switch phase is set to ideal cross/bar at the design
wavelength (1550 nm) and held fixed; crosstalk vs wavelength then emerges from the real
coupler dispersion -- the physical mechanism behind Fig. 4d,e -- rather than a toy slope.

Reproducible: topology, the crosstalk-vs-wavelength mechanism, the loss budget from
literature-grounded values. NOT reproducible (hardware-only): the exact measured spectra,
which depend on this chip's couplers.
"""

import numpy as np
from .coupler import mzi_single_theta, link_budget_db, LAMBDA0

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


def fabric_matrix(state, lam, N=4, kappa0s=None, prop_db_per_stage=0.25):
    """NxN field transfer for an all-'cross'/'bar' config using dispersive couplers."""
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
            M = mzi_single_theta(theta, lam, kappa0=kappa0s[k], slope=0.0029,
                                 excess_loss_db=0.1)
            L = _embed(M, m, n, N) @ L
            k += 1
        U = (amp * L) @ U
    return U


def transmission_spectra(state, lambdas, N=4, seed=0):
    rng = np.random.default_rng(seed)
    n_mzi = N * (N - 1) // 2
    kappa_a = np.clip(rng.normal(0.5, 0.02, size=n_mzi), 0.3, 0.7)   # two independently
    kappa_b = np.clip(rng.normal(0.5, 0.02, size=n_mzi), 0.3, 0.7)   # fabricated couplers
    arm_err = rng.normal(0, 0.02, size=n_mzi)                        # arm phase imbalance
    theta = THETA_CROSS if state == "cross" else THETA_BAR
    amp = 10 ** (-0.25 / 20.0)
    T = np.zeros((N, N, len(lambdas)))
    for li, lam in enumerate(lambdas):
        U = np.eye(N, dtype=complex)
        k = 0
        for layer in range(N):
            L = np.eye(N, dtype=complex)
            for (m, n) in _layer_pairs(N, layer):
                M = mzi_single_theta(theta, lam, kappa0=kappa_a[k], slope=0.0029,
                                     excess_loss_db=0.1, kappa0_b=kappa_b[k],
                                     arm_phase_err=arm_err[k])
                L = _embed(M, m, n, N) @ L
                k += 1
            U = (amp * L) @ U
        T[:, :, li] = np.abs(U) ** 2
    with np.errstate(divide="ignore"):
        return 10 * np.log10(T), (kappa_a, kappa_b)


ZERO_TOL = 1e-15    # linear transmission below this is a structural zero, not crosstalk


def crosstalk_summary(lambdas=None, N=4):
    if lambdas is None:
        lambdas = np.linspace(1530, 1565, 141)   # C-band
    out = {}
    for state in ("cross", "bar"):
        Tdb, _ = transmission_spectra(state, lambdas, N)
        U0 = fabric_matrix(state, LAMBDA0, N)
        intended = np.argmax(np.abs(U0) ** 2, axis=0)
        center = np.argmin(np.abs(lambdas - LAMBDA0))
        xt_center, il_center, xt_band, structural_zeros = [], [], [], 0
        for j in range(N):
            i_int = intended[j]
            il_center.append(Tdb[i_int, j, center])
            for i in range(N):
                if i == i_int:
                    continue
                # A port pair the topology forbids carries no power at all. That is a
                # structural zero, not a crosstalk level, so it is counted rather than
                # allowed to set the reported best or worst case.
                for value, bucket in ((Tdb[i, j, center], xt_center),
                                      (Tdb[i, j].max(), xt_band)):
                    if 10 ** (value / 10.0) < ZERO_TOL:
                        structural_zeros += 1
                    else:
                        bucket.append(value)
        out[state] = {
            "spectra_db": Tdb, "lambdas": lambdas, "intended": intended,
            "xtalk_center_db": ((float(np.max(xt_center)), float(np.min(xt_center)))
                                if xt_center else None),
            "onchip_loss_center_db": float(np.mean(il_center)),
            "worst_xtalk_over_cband_db": float(np.max(xt_band)) if xt_band else None,
            "structural_zeros": structural_zeros,
        }
    return out


def insertion_loss_budget(**kw):
    """Backwards-compatible: fibre-to-fibre link budget at 1550 nm (dB)."""
    return link_budget_db(**kw)


def run(verbose=True):
    s = crosstalk_summary()
    fl = link_budget_db()
    if verbose:
        for state in ("cross", "bar"):
            hi, lo = s[state]["xtalk_center_db"]
            print(f"[switching/{state}] crosstalk @1550nm: {lo:.1f} to {hi:.1f} dB; "
                  f"worst over C-band (1530-1565nm): {s[state]['worst_xtalk_over_cband_db']:.1f} dB; "
                  f"on-chip loss ~ {abs(s[state]['onchip_loss_center_db']):.1f} dB")
        print(f"[switching] fibre-to-fibre link budget @1550nm ~ {fl:.1f} dB "
              f"(grating-coupler dominated)")
        print("[switching] paper measured: -45 to <-20 dB @1560nm; <-15/-20 dB over >20nm.")
        print("[switching] crosstalk now arises from CMT coupler dispersion; measured spectra are hardware-only.")
    return s


if __name__ == "__main__":
    run()
