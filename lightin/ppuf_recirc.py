"""
Photonic PUF on the 4x4 square *recirculating* mesh (40 cells), following the preprint.

The vertex wiring is a stated choice, not the paper's. The paper's Fig. 1 layout was not
available, so results from this mesh are conditional on the wiring and are reported for
both WIRING_C4_FREE_1 and WIRING_C4_FREE_2.

`lightin/ppuf.py` runs the same PUF on a feed-forward rectangular mesh and is left alone;
this module is the topologically faithful version, and the two are compared in the report.
Signatures, defaults and returned keys match `ppuf.py` key for key so the two can be put
side by side, with two stated exceptions: a `wiring` argument, and `n_meas` defaulting to 3
re-measurements per (die, challenge) rather than 5.

Which rotation, and why it is the half turn
-------------------------------------------
The preprint puts 20 optical ports on two opposite edges (section 4.1) and says the PUF is
rotationally symmetric with two equal-power beams entering diagonally opposite ports
(section 2.5). A quarter turn of the lattice carries {top, bottom} to {left, right}, so it
maps the port-bearing edges onto the two that carry no ports and cannot preserve the stated
port set. The half turn (r, c) -> (4-r, 4-c) does preserve it. The half turn is therefore
the rotation this design can actually be built on, and everything below uses it.

Design, taken from the preprint rather than invented
----------------------------------------------------
* **Orbits.** The half turn permutes the 40 cells in **20 orbits of size 2**; no cell is
  fixed. `square_mesh.half_turn_orbits()` lists them in a fixed, die-independent order.
* **Challenge.** One bit per orbit, so a challenge is **20 bits**. Both cells of an orbit
  take the same phase, pi for a bit of 1 and 0 for a bit of 0 -- the preprint's "same
  voltage at equivalent logical positions under the rotation" (section 2.5). The die's
  fixed per-cell error and fresh per-call measurement noise are added per cell afterwards,
  and only those break the symmetry.
* **Injection.** Equal amplitude and equal phase at one pair of optical ports exchanged by
  the half turn, which is what "diagonally opposite" means here: one on the top edge and
  its image on the bottom.
* **Output pairing.** Each remaining optical port is paired with its half-turn image,
  giving **9 response bits** from the 20 ports once the 2 injection ports are set aside.
  Bit i is 1 when the first port of the pair carries at least as much power as the second,
  with the `1e-12` tie tolerance and tie counting of `ppuf.py`. All 9 pairs carry light;
  see `io_plan` for how the ports and the injected pair are chosen.

Because the phases are constant on orbits and the injection is half-turn symmetric, the
nominal configuration is invariant under the half turn, so every compared pair is exactly
equal in a die with no fabrication error and every bit is a tie. The response is produced
entirely by the manufacturing spread, which is the property that makes uniqueness a
function of that spread.

Reliability uses 3 re-measurements per (die, challenge).
"""

import numpy as np

from . import square_mesh as SM
from . import wiring_search as WS
from .metrics import hamming_distance
from .ppuf import TIE_TOL, MEAS_NOISE_SIGMA, MEAS_NOISE_SOURCE, phase_stats_from_arm_length

N_CELLS = 40            # PUCs in the mesh, one per edge of the 4x4 grid
LAMBDA_NM = 1560.0      # design wavelength (paper Methods), the PUF is evaluated here
N_MEAS_DEFAULT = 3      # re-measurements per (die, challenge) for reliability


def wirings():
    """[(name, rule)] for the two wirings selected by `wiring_search`."""
    return WS.selected()


def default_wiring():
    """The first selected wiring, used when a caller does not name one."""
    return WS.selected()[0][1]


def orbits():
    """The 20 half-turn orbits of the 40 cells, in fixed order."""
    return SM.half_turn_orbits()


def orbit_of_cell():
    """Array of length 40 giving each cell's half-turn orbit index."""
    out = np.empty(N_CELLS, dtype=int)
    for i, orb in enumerate(orbits()):
        for k in orb:
            out[k] = i
    return out


def n_challenge_bits():
    """Number of challenge bits: one per half-turn orbit."""
    return len(orbits())


LIVE_PROBE_SEED = 0     # the fixed reference die the port selection is scored on
_PLAN_CACHE = {}


def io_plan(wiring):
    """(optical_ports, injection_ports, response_pairs), chosen by a stated rule.

    The vertex wiring is a stated choice, not the paper's. The paper's Fig. 1 layout was
    not available, so results from this mesh are conditional on the wiring.

    The preprint fixes the count and placement -- 20 ports, ten per opposite edge -- but
    not which boundary end each attaches to, nor which diagonal pair is injected. Those are
    chosen here by search, on the stated criterion that every response pair should actually
    carry light: over all ten-subsets of the free top-edge ends (their half-turn images
    supplying the bottom ten) and all ten choices of injection pair, take the plan that
    leaves the most response pairs above 1e-12 on one fixed reference die, breaking ties by
    the fixed port order. A pair that carries no light in any die is a bit that can never
    be anything but a tie, so this is a design criterion rather than a fitted parameter:
    the reference die is fixed, the thresholds are not tuned, and nothing about the dies
    later evaluated enters the choice.
    """
    key = tuple(sorted((a, b) for a, b in wiring.items()))
    if key in _PLAN_CACHE:
        return _PLAN_CACHE[key]
    import itertools
    top = SM.free_top_ends(wiring)
    mu, sg = phase_stats_from_arm_length()
    g = SM.grating_amplitude(LAMBDA_NM)
    best = None
    for combo in itertools.combinations(range(len(top)), SM.N_OPTICAL_PORTS // 2):
        ctop = [top[i] for i in combo]
        gp = ctop + [SM.half_turn_port(p) for p in ctop]
        allpairs = WS.half_turn_pairs(gp)
        if len(allpairs) != SM.N_OPTICAL_PORTS // 2:
            continue
        for idx in range(len(allpairs)):
            inj = list(allpairs[idx])
            rest = [p for j, p in enumerate(allpairs) if j != idx]
            rng = np.random.default_rng(LIVE_PROBE_SEED)
            eps = rng.normal(mu, sg, N_CELLS)
            theta = np.pi * rng.integers(0, 2, len(orbits()))[orbit_of_cell()] + eps
            mesh = SM.io_mesh_from_ports(theta, wiring, gp, inputs=inj)
            o = mesh.solve(LAMBDA_NM, {p: g / np.sqrt(len(inj)) for p in inj})
            I = {p: float(np.abs(g * o[mesh.pidx[p]]) ** 2) for p in gp}
            live = sum(1 for a, b in rest if I[a] > 1e-12 and I[b] > 1e-12)
            cand = (live, tuple(gp), tuple(inj), tuple(rest))
            if best is None or cand[0] > best[0]:
                best = cand
    _PLAN_CACHE[key] = (list(best[1]), list(best[2]), [tuple(x) for x in best[3]])
    return _PLAN_CACHE[key]


def port_plan(wiring):
    """(injection_ports, response_pairs) for a wiring, fixed and die-independent."""
    _gp, inj, pairs = io_plan(wiring)
    return inj, pairs


def n_response_bits(wiring):
    """Number of response bits this wiring yields."""
    return len(port_plan(wiring)[1])


def response(challenge, eps, N=None, meas_noise=0.0, rng=None, wiring=None,
             lam_nm=LAMBDA_NM):
    """One response from one die on the recirculating mesh.

    The vertex wiring is a stated choice, not the paper's. The paper's Fig. 1 layout was
    not available, so results from this mesh are conditional on the wiring.

    challenge is one bit per half-turn orbit (length `n_challenge_bits()`); both cells of
    an orbit take phase pi*bit. eps is the die's fixed per-cell error, length 40, and the
    measurement noise is drawn fresh per call when meas_noise and rng are both given.

    N is accepted and ignored: the mesh is fixed at 40 cells. It is in the signature only
    so that this function and `ppuf.response` can be called the same way.

    Returns (bits, n_ties). Ties are resolved as 1 and counted, as in `ppuf.py`.
    """
    wiring = default_wiring() if wiring is None else wiring
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

    gp, inj_ports, pairs = io_plan(wiring)
    mesh = SM.io_mesh_from_ports(theta, wiring, gp, inputs=inj_ports)
    g = SM.grating_amplitude(lam_nm)
    amp = g / np.sqrt(len(inj_ports))
    o = mesh.solve(lam_nm, {p: amp for p in inj_ports})
    inten = {p: float(np.abs(g * o[mesh.pidx[p]]) ** 2) for p in mesh.optical_ports}

    diff = np.array([inten[a] - inten[b] for a, b in pairs])
    tied = np.abs(diff) < TIE_TOL
    bits = (diff > 0).astype(int)
    bits[tied] = 1
    return bits, int(tied.sum())


def live_pairs(wiring, eps=None, lam_nm=LAMBDA_NM, seed=0):
    """How many response pairs have both outputs above 1e-12 for one sample die."""
    wiring = default_wiring() if wiring is None else wiring
    rng = np.random.default_rng(seed)
    if eps is None:
        mu, sg = phase_stats_from_arm_length()
        eps = rng.normal(mu, sg, size=N_CELLS)
    gp, inj_ports, pairs = io_plan(wiring)
    theta = np.pi * rng.integers(0, 2, n_challenge_bits())[orbit_of_cell()] + eps
    mesh = SM.io_mesh_from_ports(theta, wiring, gp, inputs=inj_ports)
    g = SM.grating_amplitude(lam_nm)
    o = mesh.solve(lam_nm, {p: g / np.sqrt(len(inj_ports)) for p in inj_ports})
    I = {p: float(np.abs(g * o[mesh.pidx[p]]) ** 2) for p in mesh.optical_ports}
    return sum(1 for a, b in pairs if I[a] > 1e-12 and I[b] > 1e-12)


def evaluate(n_dies=100, n_challenges=128, N=None, sigma_phase=None, mu_phase=None,
             meas_noise=MEAS_NOISE_SIGMA, n_meas=N_MEAS_DEFAULT, seed=0, wiring=None):
    """Uniqueness, uniformity, reliability and tie fraction on the recirculating mesh.

    The vertex wiring is a stated choice, not the paper's. The paper's Fig. 1 layout was
    not available, so results from this mesh are conditional on the wiring.

    Same definitions and the same returned keys as `ppuf.evaluate`, so the two models can
    be compared key by key. Two differences are deliberate: `n_meas` defaults to 3 rather
    than 5, because a solve of the recirculating mesh costs far more than a feed-forward
    matrix product; and `N` is ignored, the mesh being fixed at 40 cells.
    """
    wiring = default_wiring() if wiring is None else wiring
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
        "live_pairs": live_pairs(wiring, seed=seed),
    }


def sensitivity_sweep(sigmas=(0.001, 0.01, 0.1, 0.5, 1.05, 3.0), n_dies=40,
                      n_challenges=64, seed=1, wiring=None):
    """Uniqueness, uniformity, tie fraction and reliability vs manufacturing spread.

    The vertex wiring is a stated choice, not the paper's. The paper's Fig. 1 layout was
    not available, so results from this mesh are conditional on the wiring.

    Each row is `evaluate` at that per-cell phase sigma with mu_phase = 0.
    """
    wiring = default_wiring() if wiring is None else wiring
    rows = []
    for s in sigmas:
        res = evaluate(n_dies=n_dies, n_challenges=n_challenges,
                       sigma_phase=float(s), mu_phase=0.0, seed=seed, wiring=wiring)
        rows.append({"sigma_phase": float(s),
                     "uniqueness": res["uniqueness"],
                     "uniformity": res["uniformity"],
                     "tie_fraction": res["tie_fraction"],
                     "reliability": res["reliability"],
                     "live_pairs": res["live_pairs"]})
    return rows


def population_sweep(seeds=range(10), n_dies=40, n_challenges=64, wiring=None):
    """Uniqueness, uniformity and reliability over several independent die populations.

    The vertex wiring is a stated choice, not the paper's. The paper's Fig. 1 layout was
    not available, so results from this mesh are conditional on the wiring.

    One `evaluate` per seed. The seed drives the whole draw -- the challenges, each die's
    fixed per-cell phase error and the measurement noise -- so the seeds give independent
    populations rather than re-measurements of one, and the spread across them is the
    sampling spread of a metric computed on n_dies dies, not an uncertainty of the model.

    Returns the per-seed lists and the mean and sample standard deviation of each metric.
    """
    wiring = default_wiring() if wiring is None else wiring
    seeds = list(seeds)
    rows = [evaluate(n_dies=n_dies, n_challenges=n_challenges, seed=s, wiring=wiring)
            for s in seeds]
    out = {"seeds": seeds, "n_seeds": len(seeds),
           "n_dies": n_dies, "n_challenges": n_challenges}
    for key in ("uniqueness", "uniformity", "reliability"):
        vals = [float(r[key]) for r in rows]
        arr = np.asarray(vals)
        out[f"{key}_per_seed"] = vals
        out[f"{key}_mean"] = float(arr.mean())
        out[f"{key}_std"] = float(arr.std(ddof=1)) if arr.size > 1 else 0.0
    return out


def noise_sweep(sigmas=(0.002, 0.005, 0.01, 0.02, 0.05), n_dies=40, n_challenges=64,
                seed=1, wiring=None):
    """The PUF metrics against the assumed per-cell measurement noise.

    The vertex wiring is a stated choice, not the paper's. The paper's Fig. 1 layout was
    not available, so results from this mesh are conditional on the wiring.

    `MEAS_NOISE_SIGMA` is an assumed value with no recorded source, and reliability is the
    metric it drives: a larger assumed noise flips more bits between re-measurements of one
    die. Uniqueness, uniformity and the tie fraction are computed from the noise-free
    reference response and should not move with it, which this sweep also checks.
    """
    wiring = default_wiring() if wiring is None else wiring
    rows = []
    for s in sigmas:
        res = evaluate(n_dies=n_dies, n_challenges=n_challenges, meas_noise=float(s),
                       seed=seed, wiring=wiring)
        rows.append({"meas_noise_sigma": float(s),
                     "uniqueness": res["uniqueness"],
                     "uniformity": res["uniformity"],
                     "reliability": res["reliability"],
                     "tie_fraction": res["tie_fraction"]})
    return rows


def run(verbose=True, n_dies=40, n_challenges=64, wiring=None, name=None):
    """Evaluate the recirculating PUF and print a summary.

    The vertex wiring is a stated choice, not the paper's. The paper's Fig. 1 layout was
    not available, so results from this mesh are conditional on the wiring.
    """
    if wiring is None:
        name, wiring = wirings()[0]
    res = evaluate(n_dies=n_dies, n_challenges=n_challenges, wiring=wiring)
    res["wiring"] = name
    res["measurement_noise_sigma"] = MEAS_NOISE_SIGMA
    res["measurement_noise_source"] = MEAS_NOISE_SOURCE
    if verbose:
        print(f"[PPUF-recirc/{name}] 40-cell square recirculating mesh, 20 optical ports, "
              f"{res['challenge_bits']}-bit challenge, {res['response_bits']}-bit response, "
              f"{res['live_pairs']} live pairs")
        print(f"[PPUF-recirc/{name}] {n_dies} dies x {n_challenges} challenges: "
              f"uniqueness {100*res['uniqueness']:.2f}%, "
              f"uniformity {100*res['uniformity']:.2f}%, "
              f"reliability {100*res['reliability']:.2f}%, "
              f"ties {100*res['tie_fraction']:.2f}%")
        print("[PPUF-recirc] wiring is a stated choice, not the paper's; numbers are "
              "conditional on it.")
    return res


if __name__ == "__main__":
    run()
