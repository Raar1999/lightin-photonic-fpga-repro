"""
Photonic PUF on the 4x4 square *recirculating* mesh (40 cells), following the preprint.

The vertex wiring is a stated choice, not the paper's. The paper's Fig. 1 layout was not
available, so results from this mesh are conditional on the wiring and are reported for
both WIRING_A and WIRING_B.

`lightin/ppuf.py` runs the same PUF on a feed-forward rectangular mesh and is left alone;
this module is the topologically faithful version, and the two are compared in the report.
Signatures, defaults and returned keys match `ppuf.py` key for key so the two can be put
side by side, with two stated exceptions: a `wiring` argument, and `n_meas` defaulting to 3
re-measurements per (die, challenge) rather than 5.

Design, taken from the preprint (arXiv:2504.01463v2 section 2.5) rather than invented
-------------------------------------------------------------------------------------
The preprint states that the PUF is rotationally symmetric, that the same programming
voltage is applied to the MZIs at equivalent logical positions under that rotation, that two
nominally equal-power beams enter diagonally opposite input ports, and that a response bit
is 1 when the first output of a corresponding pair is at least as large as the second. Each
of those becomes one element of this model.

* **Orbits.** The quarter turn (r, c) -> (c, 4-r) of `square_mesh` permutes the 40 cells in
  10 orbits of 4. No cell is fixed, because the rotation carries horizontal edges to
  vertical ones. The orbits are listed by `square_mesh.edge_orbits()` in a fixed,
  die-independent order.
* **Challenge.** One bit per orbit, so a challenge is **10 bits**, not 40. Every cell in an
  orbit gets the same phase, pi for a bit of 1 and 0 for a bit of 0, which is the preprint's
  "same voltage at equivalent logical positions". That die's fixed per-cell error and fresh
  per-call measurement noise are then added per cell, and it is only those that break the
  symmetry.
* **Injection.** Equal amplitude, equal phase, at one pair of external ports exchanged by
  the half turn: the first such pair in `square_mesh.boundary_ports` order. Those are the
  diagonally opposite ports of the preprint.
* **Output pairing.** Each remaining external port is paired with its half-turn image,
  giving **11 response bits** from the 24 external ports once the 2 injection ports are set
  aside. Bit i is 1 when the first port of the pair carries at least as much power as the
  second, with the `1e-12` tie tolerance and tie counting of `ppuf.py`.

Because the phases are constant on orbits and the injection is half-turn symmetric, the
whole nominal configuration is invariant under the half turn, so every compared pair is
*exactly* equal in a die with no fabrication error and every bit is a tie. The response is
therefore produced entirely by the manufacturing spread, which is the same property the
feed-forward model has and what makes uniqueness a function of that spread.

Wiring caveat
-------------
This construction needs the boundary port set to be closed under the rotation. It is, for
WIRING_A. It is not for WIRING_B, which cannot be rotation-equivariant at all (see
`square_mesh`), and whose unmatched ends are not carried into one another by the quarter
turn. WIRING_B therefore cannot express the preprint's design; it is still accepted here,
with its output ports paired consecutively in boundary order instead, so that the two
wirings can be compared, but its numbers are not an instance of the preprint's PUF and the
symmetry the design rests on does not hold for it. `pairing_is_rotational(wiring)` reports
which case applies.
"""

import numpy as np

from . import square_mesh as SM
from .square_mesh import WIRING_A, WIRING_B                      # noqa: F401  (re-exported)
from .metrics import hamming_distance
from .ppuf import TIE_TOL, MEAS_NOISE_SIGMA, MEAS_NOISE_SOURCE, phase_stats_from_arm_length

N_CELLS = 40            # PUCs in the mesh, one per edge of the 4x4 grid
LAMBDA_NM = 1560.0      # design wavelength (paper Methods), the PUF is evaluated here
N_MEAS_DEFAULT = 3      # re-measurements per (die, challenge) for reliability


def orbits():
    """The 10 quarter-turn orbits of the 40 cells, in fixed order."""
    return SM.edge_orbits()


def orbit_of_cell():
    """Array of length 40 giving each cell's orbit index."""
    out = np.empty(N_CELLS, dtype=int)
    for i, orb in enumerate(orbits()):
        for k in orb:
            out[k] = i
    return out


def n_challenge_bits():
    """Number of challenge bits: one per rotational orbit."""
    return len(orbits())


def _half_turn_pairs(wiring):
    """External ports grouped into half-turn pairs, in fixed boundary order."""
    ports = SM.boundary_ports(wiring)
    pairs, used = [], set()
    for p in ports:
        if p in used:
            continue
        q = SM.half_turn_port(p)
        if q not in used and q in set(ports) and q != p:
            used.update((p, q))
            pairs.append((p, q))
    return pairs


def pairing_is_rotational(wiring=WIRING_A):
    """True when this wiring's external ports are closed under the rotation.

    False means the preprint's rotational pairing cannot be formed and the consecutive
    fallback is used, so the design's symmetry does not hold for that wiring.
    """
    ports = SM.boundary_ports(wiring)
    return {SM.half_turn_port(p) for p in ports} == set(ports)


def port_plan(wiring=WIRING_A):
    """(injection_ports, response_pairs) for a wiring, both fixed and die-independent.

    The vertex wiring is a stated choice, not the paper's. The paper's Fig. 1 layout was
    not available, so results from this mesh are conditional on the wiring and are
    reported for both WIRING_A and WIRING_B.
    """
    if pairing_is_rotational(wiring):
        pairs = _half_turn_pairs(wiring)
        return list(pairs[0]), pairs[1:]
    # WIRING_B: not rotation-closed, so fall back to consecutive pairs in boundary order
    ports = SM.boundary_ports(wiring)
    return list(ports[:2]), [(ports[i], ports[i + 1]) for i in range(2, len(ports) - 1, 2)]


def n_response_bits(wiring=WIRING_A):
    """Number of response bits this wiring yields."""
    return len(port_plan(wiring)[1])


def response(challenge, eps, N=None, meas_noise=0.0, rng=None, wiring=WIRING_A,
             lam_nm=LAMBDA_NM):
    """One response from one die on the recirculating mesh.

    The vertex wiring is a stated choice, not the paper's. The paper's Fig. 1 layout was
    not available, so results from this mesh are conditional on the wiring and are
    reported for both WIRING_A and WIRING_B.

    challenge is one bit per rotational orbit (length `n_challenge_bits()`); every cell of
    an orbit takes phase pi*bit. eps is the die's fixed per-cell error, length 40, and the
    measurement noise is drawn fresh per call when meas_noise and rng are both given.

    N is accepted and ignored: the mesh is fixed at 40 cells. It is in the signature only
    so that this function and `ppuf.response` can be called the same way.

    Returns (bits, n_ties): an integer array of `n_response_bits(wiring)` bits, and the
    number of tied pairs. Ties are resolved as 1 and counted, as in `ppuf.py`.
    """
    challenge = np.asarray(challenge, dtype=float)
    if challenge.shape != (n_challenge_bits(),):
        raise ValueError(f"challenge must have {n_challenge_bits()} bits, "
                         f"got shape {challenge.shape}")
    eps = np.asarray(eps, dtype=float)
    if eps.shape != (N_CELLS,):
        raise ValueError(f"eps must have {N_CELLS} entries, got shape {eps.shape}")

    noise = 0.0
    if meas_noise and rng is not None:
        noise = rng.normal(0, meas_noise, size=N_CELLS)
    theta = np.pi * challenge[orbit_of_cell()] + eps + noise

    inj_ports, pairs = port_plan(wiring)
    ports = SM.boundary_ports(wiring)
    mesh = SM.build_mesh(theta, wiring, inputs=inj_ports, outputs=ports)
    amp = 1.0 / np.sqrt(len(inj_ports))
    o = mesh.solve(lam_nm, {p: amp for p in inj_ports})
    inten = {p: float(np.abs(o[mesh.pidx[p]]) ** 2) for p in ports}

    diff = np.array([inten[a] - inten[b] for a, b in pairs])
    tied = np.abs(diff) < TIE_TOL
    bits = (diff > 0).astype(int)
    bits[tied] = 1
    return bits, int(tied.sum())


def evaluate(n_dies=100, n_challenges=128, N=None, sigma_phase=None, mu_phase=None,
             meas_noise=MEAS_NOISE_SIGMA, n_meas=N_MEAS_DEFAULT, seed=0,
             wiring=WIRING_A):
    """Uniqueness, uniformity, reliability and tie fraction on the recirculating mesh.

    The vertex wiring is a stated choice, not the paper's. The paper's Fig. 1 layout was
    not available, so results from this mesh are conditional on the wiring and are
    reported for both WIRING_A and WIRING_B.

    Same definitions and the same returned keys as `ppuf.evaluate`, so the two models can
    be compared key by key. Two differences are deliberate: `n_meas` defaults to 3 rather
    than 5, because a solve of the recirculating mesh costs far more than a feed-forward
    matrix product; and `N` is ignored, the mesh being fixed at 40 cells.

    Defaults derive the per-cell phase Gaussian from the arm-length-difference
    distribution N(-0.08 um, 0.11 um) via `ppuf.phase_stats_from_arm_length`.
    """
    if sigma_phase is None or mu_phase is None:
        mu_phase, sigma_phase = phase_stats_from_arm_length()
    rng = np.random.default_rng(seed)
    n_bits = n_response_bits(wiring)
    n_c = n_challenge_bits()

    challenges = rng.integers(0, 2, size=(n_challenges, n_c))
    eps = rng.normal(mu_phase, sigma_phase, size=(n_dies, N_CELLS))

    references = np.zeros((n_dies, n_challenges, n_bits), dtype=int)
    n_ties = 0
    rl_acc, rcnt = 0.0, 0
    for d in range(n_dies):
        for c in range(n_challenges):
            ref, t = response(challenges[c], eps[d], wiring=wiring)
            references[d, c] = ref
            n_ties += t
            for _ in range(n_meas):
                meas, _ = response(challenges[c], eps[d], meas_noise=meas_noise,
                                   rng=rng, wiring=wiring)
                rl_acc += hamming_distance(ref, meas)
                rcnt += 1
    tie_fraction = n_ties / float(n_dies * n_challenges * n_bits)
    reliability = rl_acc / rcnt

    uq_acc, cnt = 0.0, 0
    for i in range(n_dies):
        for j in range(i + 1, n_dies):
            uq_acc += np.mean(references[i] != references[j])
            cnt += 1
    uniqueness = uq_acc / cnt
    uniformity = float(np.mean(references))
    prop1_per_die = references.reshape(n_dies, -1).mean(axis=1)

    return {
        "uniqueness": float(uniqueness),
        "uniformity": float(uniformity),
        "reliability": float(reliability),
        "reliability_intra_die_HD": float(reliability),
        "tie_fraction": float(tie_fraction),
        "prop1_per_die": prop1_per_die,
        "n_dies": n_dies, "n_challenges": n_challenges, "response_bits": n_bits,
        "challenge_bits": n_c,
        "wiring": wiring[0],
        "pairing_is_rotational": bool(pairing_is_rotational(wiring)),
    }


def sensitivity_sweep(sigmas=(0.001, 0.01, 0.1, 0.5, 1.05, 3.0), n_dies=40,
                      n_challenges=64, seed=1, wiring=WIRING_A):
    """Uniqueness, uniformity, tie fraction and reliability vs manufacturing spread.

    The vertex wiring is a stated choice, not the paper's. The paper's Fig. 1 layout was
    not available, so results from this mesh are conditional on the wiring and are
    reported for both WIRING_A and WIRING_B.

    Each row is `evaluate` at that per-cell phase sigma with mu_phase = 0, so the only
    thing that varies is how far the fabricated phases scatter from their nominal value.
    """
    rows = []
    for s in sigmas:
        res = evaluate(n_dies=n_dies, n_challenges=n_challenges,
                       sigma_phase=float(s), mu_phase=0.0, seed=seed, wiring=wiring)
        rows.append({"sigma_phase": float(s),
                     "uniqueness": res["uniqueness"],
                     "uniformity": res["uniformity"],
                     "tie_fraction": res["tie_fraction"],
                     "reliability": res["reliability"]})
    return rows


def run(verbose=True, n_dies=40, n_challenges=64, wiring=WIRING_A):
    """Evaluate the recirculating PUF and print a summary.

    The vertex wiring is a stated choice, not the paper's. The paper's Fig. 1 layout was
    not available, so results from this mesh are conditional on the wiring and are
    reported for both WIRING_A and WIRING_B.
    """
    res = evaluate(n_dies=n_dies, n_challenges=n_challenges, wiring=wiring)
    res["measurement_noise_sigma"] = MEAS_NOISE_SIGMA
    res["measurement_noise_source"] = MEAS_NOISE_SOURCE
    if verbose:
        print(f"[PPUF-recirc/{wiring[0]}] 40-cell square recirculating mesh, "
              f"{res['challenge_bits']}-bit challenge, {res['response_bits']}-bit response, "
              f"rotational pairing: {res['pairing_is_rotational']}")
        print(f"[PPUF-recirc/{wiring[0]}] {n_dies} dies x {n_challenges} challenges: "
              f"uniqueness {100*res['uniqueness']:.2f}%, "
              f"uniformity {100*res['uniformity']:.2f}%, "
              f"reliability {100*res['reliability']:.2f}%, "
              f"ties {100*res['tie_fraction']:.2f}%")
        print("[PPUF-recirc] wiring is a stated choice, not the paper's; numbers are "
              "conditional on it.")
    return res


if __name__ == "__main__":
    run()
