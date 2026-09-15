"""
Photonic physical unclonable function (PPUF), paper Fig. 5.

The chip uses a rotationally-symmetric recirculating mesh. Two equal-power lights enter
diagonal ports; challenges are voltage patterns setting MZIs to cross/bar; the response
bit r_i = 1 if output o_{i,1} >= o_{i,2} else 0. Manufacturing variations (arm-length /
phase scatter, fixed per die) make the response unique per die, while the same die
reproduces its response (reliability).

The model here builds ONE mesh per die: theta = pi*challenge + eps + measurement noise,
where eps is that die's fixed per-MZI phase error. Equal-power light enters the two
diagonal ports 0 and N-1 of that single mesh, and response bit i compares the two
outputs of pair (2i, 2i+1) of that same physical die, so a response is a property of one
fabricated chip rather than of a comparison between two copies. Both injections are
needed: in a feed-forward mesh, reaching output k from input 0 costs k cross-couplings,
so single-edge injection leaves power decaying monotonically with port index and biases
every pair towards its even member. The diagonal pair has mirror-image decay and the
bias cancels. With eps = 0 every PUC is exactly cross or bar, the mesh is a permutation,
and only the two routed outputs carry power. Manufacturing spread lifts the degeneracy,
which is what makes the response a signature, so uniqueness is a function of the spread
(see sensitivity_sweep).
"""

import numpy as np
from .puc import puc_matrix, embed
from .metrics import hamming_distance

TIE_TOL = 1e-12     # intensity difference below this is a tie, not a decided bit

MEAS_NOISE_SIGMA = 0.01   # rad, per-MZI phase noise added on each re-measurement
MEAS_NOISE_SOURCE = ("assumed value, not taken from the paper; "
                     "reliability scales with it")


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


def _intensities(challenge, eps, N=8, meas_noise=0.0, rng=None):
    """Output intensities of one die for equal-power injection at ports 0 and N-1."""
    noise = 0.0
    if meas_noise and rng is not None:
        noise = rng.normal(0, meas_noise, size=n_mzi(N))
    theta = np.pi * np.asarray(challenge, dtype=float) + eps + noise
    U = _mesh_single_theta(N, theta)
    v = (U[:, 0] + U[:, N - 1]) / np.sqrt(2.0)
    return np.abs(v) ** 2


def response(challenge, eps, N=8, meas_noise=0.0, rng=None):
    """One response from one die: theta = pi*challenge + eps (+ measurement noise).

    "Two equal-power lights enter diagonal ports" (module docstring), so the output
    field of the single mesh U is v = (U[:,0] + U[:,N-1]) / sqrt(2). Bit i = 1 if
    |v[2i]|^2 > |v[2i+1]|^2, 0 if it is less, and a tie if the two differ by less than
    TIE_TOL. Ties are resolved as 1 and counted.

    eps is the die's fixed per-MZI manufacturing phase error, length n_mzi(N); the noise
    is drawn fresh per call when meas_noise and rng are both given.

    Returns (bits, n_ties): an integer array of N//2 bits, and the number of tied pairs.
    """
    inten = _intensities(challenge, eps, N=N, meas_noise=meas_noise, rng=rng)
    diff = inten[0::2] - inten[1::2]
    tied = np.abs(diff) < TIE_TOL
    bits = (diff > 0).astype(int)
    bits[tied] = 1
    return bits, int(tied.sum())


def phase_stats_from_arm_length(mu_um=-0.08, sigma_um=0.11, n_eff=2.36, lam_nm=1560.0):
    """Convert the paper's per-MZI arm-length-difference Gaussian to a phase Gaussian.

    Paper (Methods/Supp Note 8): the initial length difference between the two arms in
    every MZI follows N(mu = -0.08 um, sigma = 0.11 um). Phase = 2*pi*n_eff*dL/lambda.
    The sign is the preprint's (arXiv:2504.01463v2 section 2.5); see docs/PREPRINT_NOTES.md.
    """
    rad_per_um = 2 * np.pi * n_eff / (lam_nm * 1e-3)   # lam in um
    return mu_um * rad_per_um, sigma_um * rad_per_um


def evaluate(n_dies=100, n_challenges=128, N=8, sigma_phase=None, mu_phase=None,
             meas_noise=MEAS_NOISE_SIGMA, n_meas=5, seed=0):
    """Compute uniqueness, uniformity, reliability and tie fraction over simulated dies.

    Defaults derive the per-MZI phase Gaussian from the paper's arm-length-difference
    distribution N(-0.08 um, 0.11 um) via phase_stats_from_arm_length().

    Uniqueness, uniformity and tie_fraction are computed from the noise-free reference
    response of each (die, challenge). Reliability is the mean fractional Hamming
    distance between that reference and n_meas re-measurements at meas_noise, averaged
    over every die and challenge, so it is directly comparable with uniqueness: a PUF
    works only when repeated measurements of one die agree far better than two dies do.
    """
    if sigma_phase is None or mu_phase is None:
        mu_phase, sigma_phase = phase_stats_from_arm_length()
    rng = np.random.default_rng(seed)
    M = n_mzi(N)
    n_bits = N // 2

    challenges = rng.integers(0, 2, size=(n_challenges, M))
    eps = rng.normal(mu_phase, sigma_phase, size=(n_dies, M))  # per-MZI, fixed per die

    # references[d, c, :] -> N//2-bit noise-free reference response
    references = np.zeros((n_dies, n_challenges, n_bits), dtype=int)
    n_ties = 0
    rl_acc, rcnt = 0.0, 0
    for d in range(n_dies):
        for c in range(n_challenges):
            ref, t = response(challenges[c], eps[d], N=N)   # noise = 0
            references[d, c] = ref
            n_ties += t
            for _ in range(n_meas):
                meas, _ = response(challenges[c], eps[d], N=N,
                                   meas_noise=meas_noise, rng=rng)
                rl_acc += hamming_distance(ref, meas); rcnt += 1
    tie_fraction = n_ties / float(n_dies * n_challenges * n_bits)
    reliability = rl_acc / rcnt

    # Uniqueness: mean pairwise inter-die Hamming distance
    uq_acc, cnt = 0.0, 0
    for i in range(n_dies):
        for j in range(i + 1, n_dies):
            uq_acc += np.mean(references[i] != references[j]); cnt += 1
    uniqueness = uq_acc / cnt

    # Uniformity: proportion of 1s per die, averaged
    uniformity = float(np.mean(references))

    # uniformity distribution (proportion of 1s per die) for the histogram (Fig.5e)
    prop1_per_die = references.reshape(n_dies, -1).mean(axis=1)

    return {
        "uniqueness": float(uniqueness),
        "uniformity": float(uniformity),
        "reliability": float(reliability),
        # same quantity under the name the earlier results.json and figures use
        "reliability_intra_die_HD": float(reliability),
        "tie_fraction": float(tie_fraction),
        "prop1_per_die": prop1_per_die,
        "n_dies": n_dies, "n_challenges": n_challenges, "response_bits": n_bits,
    }


def pair_class_fractions(sigma_phase, n_dies=40, n_challenges=64, N=8, mu_phase=0.0,
                         seed=1, lit=0.1, dark=0.01):
    """Classify the compared pairs (2i, 2i+1) by their noise-free intensities.

    lit-lit: both above `lit`. lit-dark: one above `lit`, the other below `dark`.
    dark-dark: both below `dark`. A pair with an intensity between the two thresholds
    is in none of the three classes, so the fractions need not sum to 1.
    """
    rng = np.random.default_rng(seed)
    M = n_mzi(N)
    challenges = rng.integers(0, 2, size=(n_challenges, M))
    eps = rng.normal(mu_phase, float(sigma_phase), size=(n_dies, M))
    n_ll = n_ld = n_dd = n_tot = 0
    for d in range(n_dies):
        for c in range(n_challenges):
            inten = _intensities(challenges[c], eps[d], N=N)
            a, b = inten[0::2], inten[1::2]
            n_ll += int(np.count_nonzero((a > lit) & (b > lit)))
            n_ld += int(np.count_nonzero(((a > lit) & (b < dark)) |
                                         ((b > lit) & (a < dark))))
            n_dd += int(np.count_nonzero((a < dark) & (b < dark)))
            n_tot += a.size
    return {"sigma_phase": float(sigma_phase),
            "lit_lit": n_ll / n_tot, "lit_dark": n_ld / n_tot,
            "dark_dark": n_dd / n_tot, "n_pairs": n_tot}


def sensitivity_sweep(sigmas=(0.001, 0.01, 0.1, 0.5, 1.05, 3.0), n_dies=40,
                      n_challenges=64, seed=1):
    """Uniqueness, uniformity, tie fraction and reliability vs manufacturing spread.

    Each row is evaluate() at that per-MZI phase sigma with mu_phase = 0, so the only
    thing that varies is how far the fabricated phases scatter from their nominal value.
    """
    rows = []
    for s in sigmas:
        res = evaluate(n_dies=n_dies, n_challenges=n_challenges,
                       sigma_phase=float(s), mu_phase=0.0, seed=seed)
        rows.append({"sigma_phase": float(s),
                     "uniqueness": res["uniqueness"],
                     "uniformity": res["uniformity"],
                     "tie_fraction": res["tie_fraction"],
                     "reliability": res["reliability"]})
    return rows


def population_sweep(seeds=range(10), n_dies=40, n_challenges=64):
    """Uniqueness, uniformity and reliability over several independent die populations.

    One `evaluate` per seed. The seed drives the whole draw -- the challenges, each die's
    fixed per-MZI phase error and the measurement noise -- so the seeds give independent
    populations rather than re-measurements of one, and the spread across them is the
    sampling spread of a metric computed on n_dies dies, not an uncertainty of the model.

    Returns the per-seed lists and the mean and sample standard deviation of each metric.
    """
    seeds = list(seeds)
    rows = [evaluate(n_dies=n_dies, n_challenges=n_challenges, seed=s) for s in seeds]
    out = {"seeds": seeds, "n_seeds": len(seeds),
           "n_dies": n_dies, "n_challenges": n_challenges}
    for key in ("uniqueness", "uniformity", "reliability"):
        vals = [float(r[key]) for r in rows]
        arr = np.asarray(vals)
        out[f"{key}_per_seed"] = vals
        out[f"{key}_mean"] = float(arr.mean())
        out[f"{key}_std"] = float(arr.std(ddof=1)) if arr.size > 1 else 0.0
    return out


def run(verbose=True, n_dies=100):
    mu_p, sig_p = phase_stats_from_arm_length()
    res = evaluate(n_dies=n_dies)
    res["measurement_noise_sigma"] = MEAS_NOISE_SIGMA
    res["measurement_noise_source"] = MEAS_NOISE_SOURCE
    res["sensitivity_sweep"] = sensitivity_sweep()
    res["pair_classes"] = [pair_class_fractions(s) for s in (0.001, 1.05)]
    if verbose:
        print(f"[PPUF] per-MZI arm-length diff N(-0.08, 0.11) um -> phase "
              f"N(mu={mu_p:.2f}, sigma={sig_p:.2f}) rad (via n_eff=2.36)")
        print(f"[PPUF] uniqueness (inter-die HD) = {100*res['uniqueness']:.2f}%   "
              f"(paper sim: 49.97%; exp 2-die: 57.71%; ideal 50%)")
        print(f"[PPUF] uniformity (prop. of 1s)  = {100*res['uniformity']:.2f}%   "
              f"(paper sim: 50.15%; exp 2-die: 42.62%; ideal 50%)")
        print(f"[PPUF] reliability (intra-die HD)= {100*res['reliability']:.2f}%  "
              f"(paper exp: 2.55%; lower is better)")
        print(f"[PPUF] tie fraction              = {100*res['tie_fraction']:.2f}%   "
              f"(undecided pairs, resolved as 1)")
        print(f"[PPUF] measurement noise sigma    = {MEAS_NOISE_SIGMA} rad per MZI "
              f"({MEAS_NOISE_SOURCE})")
        print("[PPUF] sensitivity to per-MZI phase spread (mu_phase = 0):")
        print(f"       {'sigma_phase':>12s}  {'uniqueness':>11s}  {'uniformity':>11s}"
              f"  {'tie_fraction':>13s}  {'reliability':>12s}")
        for row in res["sensitivity_sweep"]:
            print(f"       {row['sigma_phase']:12.3f}  {row['uniqueness']:11.4f}"
                  f"  {row['uniformity']:11.4f}  {row['tie_fraction']:13.4f}"
                  f"  {row['reliability']:12.4f}")
        print("[PPUF] compared-pair classes from the noise-free intensities "
              "(lit > 0.1, dark < 0.01):")
        print(f"       {'sigma_phase':>12s}  {'lit-lit':>9s}  {'lit-dark':>9s}"
              f"  {'dark-dark':>10s}")
        for pc in res["pair_classes"]:
            print(f"       {pc['sigma_phase']:12.3f}  {pc['lit_lit']:9.4f}"
                  f"  {pc['lit_dark']:9.4f}  {pc['dark_dark']:10.4f}")
    return res


if __name__ == "__main__":
    run()
