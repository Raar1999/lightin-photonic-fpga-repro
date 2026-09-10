"""
Photonic physical unclonable function (PPUF), paper Fig. 5.

The chip uses a rotationally-symmetric recirculating mesh. Two equal-power lights enter
diagonal ports; challenges are voltage patterns setting MZIs to cross/bar; the response
bit r_i = 1 if output o_{i,1} >= o_{i,2} else 0. Manufacturing variations (arm-length /
phase scatter, fixed per die) make the response unique per die, while the same die
reproduces its response (reliability).

This is directly reproducible: the paper itself reports the 100-die uniqueness 49.97%
and uniformity 50.15% from a *simulation* with a Gaussian arm-difference distribution.
We model an 8-mode mesh of the paper's single-phase-shifter PUCs (Eq. 1). Rotational
symmetry is captured by feeding the two diagonal injections through the same die errors
in rotated (permuted) order, so the ideal (error-free) paired outputs tie and bits are
driven purely by manufacturing randomness.
"""

import numpy as np
from .puc import puc_matrix, embed
from .metrics import hamming_distance


def _layer_pairs(N, layer):
    start = layer % 2
    return [(i, i + 1) for i in range(start, N - 1, 2)]


def _mesh_single_theta(N, thetas):
    """Build NxN mesh from single-theta PUCs (paper Eq. 1), one theta per MZI."""
    U = np.eye(N, dtype=complex)
    k = 0
    for layer in range(N):
        L = np.eye(N, dtype=complex)
        for (m, n) in _layer_pairs(N, layer):
            L = embed(puc_matrix(thetas[k]), m, n, N) @ L
            k += 1
        U = L @ U
    return U


def n_mzi(N):
    return N * (N - 1) // 2


def response(challenge, eps, perm, N=8, meas_noise=0.0, rng=None):
    """One response: theta = pi*challenge + eps (+ measurement noise).

    Two injections (ports 0 and N-1) experience die errors in normal vs permuted order;
    bit i = 1 if intensity from injection-1 >= injection-2 at output i.
    """
    noise = 0.0
    if meas_noise and rng is not None:
        noise = rng.normal(0, meas_noise, size=n_mzi(N))
    # Two rotationally-symmetric halves: identical nominal routing and injection;
    # they differ only in which physical devices' errors they see (eps vs rotated eps).
    # At eps = 0 the two halves tie; manufacturing error alone decides each bit.
    theta_a = np.pi * challenge + eps + noise
    theta_b = np.pi * challenge + eps[perm] + noise
    Ua = _mesh_single_theta(N, theta_a)
    Ub = _mesh_single_theta(N, theta_b)
    e0 = np.zeros(N, complex); e0[0] = 1.0
    Ia = np.abs(Ua @ e0) ** 2
    Ib = np.abs(Ub @ e0) ** 2
    return (Ia >= Ib).astype(int)


def phase_stats_from_arm_length(mu_um=0.08, sigma_um=0.11, n_eff=2.36, lam_nm=1560.0):
    """Convert the paper's per-MZI arm-length-difference Gaussian to a phase Gaussian.

    Paper (Methods/Supp Note 8): the initial length difference between the two arms in
    every MZI follows N(mu = 0.08 um, sigma = 0.11 um). Phase = 2*pi*n_eff*dL/lambda.
    """
    rad_per_um = 2 * np.pi * n_eff / (lam_nm * 1e-3)   # lam in um
    return mu_um * rad_per_um, sigma_um * rad_per_um


def evaluate(n_dies=100, n_challenges=128, N=8, sigma_phase=None, mu_phase=None,
             meas_noise=0.01, n_meas=10, seed=0):
    """Compute uniqueness, uniformity, reliability over simulated dies.

    Defaults derive the per-MZI phase Gaussian from the paper's arm-length-difference
    distribution N(0.08 um, 0.11 um) via phase_stats_from_arm_length().
    """
    if sigma_phase is None or mu_phase is None:
        mu_phase, sigma_phase = phase_stats_from_arm_length()
    rng = np.random.default_rng(seed)
    M = n_mzi(N)
    perm = rng.permutation(N - 1)
    perm = np.concatenate([perm, [M - 1]]) if M > N - 1 else perm
    perm = rng.permutation(M)                                  # rotation map on MZIs

    challenges = rng.integers(0, 2, size=(n_challenges, M))
    eps = rng.normal(mu_phase, sigma_phase, size=(n_dies, M))  # per-MZI, fixed per die

    # responses[d, c, :] -> 8-bit response
    responses = np.zeros((n_dies, n_challenges, N), dtype=int)
    for d in range(n_dies):
        for c in range(n_challenges):
            responses[d, c] = response(challenges[c], eps[d], perm, N=N)

    # Uniqueness: mean pairwise inter-die Hamming distance
    uq_acc, cnt = 0.0, 0
    for i in range(n_dies):
        for j in range(i + 1, n_dies):
            uq_acc += np.mean(responses[i] != responses[j]); cnt += 1
    uniqueness = uq_acc / cnt

    # Uniformity: proportion of 1s per die, averaged
    uniformity = float(np.mean(responses))

    # Reliability: intra-die HD across repeated noisy measurements (first 8 dies)
    rl_acc, rcnt = 0.0, 0
    for d in range(min(8, n_dies)):
        for c in range(n_challenges):
            ref = response(challenges[c], eps[d], perm, N=N, meas_noise=0.0, rng=rng)
            for _ in range(n_meas):
                meas = response(challenges[c], eps[d], perm, N=N,
                                meas_noise=meas_noise, rng=rng)
                rl_acc += hamming_distance(ref, meas); rcnt += 1
    reliability = rl_acc / rcnt

    # uniformity distribution (proportion of 1s per die) for the histogram (Fig.5e)
    prop1_per_die = responses.reshape(n_dies, -1).mean(axis=1)

    return {
        "uniqueness": float(uniqueness),
        "uniformity": float(uniformity),
        "reliability_intra_die_HD": float(reliability),
        "prop1_per_die": prop1_per_die,
        "n_dies": n_dies, "n_challenges": n_challenges, "response_bits": N,
    }


def run(verbose=True, n_dies=100):
    mu_p, sig_p = phase_stats_from_arm_length()
    res = evaluate(n_dies=n_dies)
    if verbose:
        print(f"[PPUF] per-MZI arm-length diff N(0.08, 0.11) um -> phase "
              f"N(mu={mu_p:.2f}, sigma={sig_p:.2f}) rad (via n_eff=2.36)")
        print(f"[PPUF] uniqueness (inter-die HD) = {100*res['uniqueness']:.2f}%   "
              f"(paper sim: 49.97%; exp 2-die: 57.71%; ideal 50%)")
        print(f"[PPUF] uniformity (prop. of 1s)  = {100*res['uniformity']:.2f}%   "
              f"(paper sim: 50.15%; exp 2-die: 42.62%; ideal 50%)")
        print(f"[PPUF] reliability (intra-die HD)= {100*res['reliability_intra_die_HD']:.2f}%  "
              f"(paper exp: 2.55%; lower is better)")
    return res


if __name__ == "__main__":
    run()
