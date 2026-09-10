"""
Expressivity of the single-theta PUC mesh (paper's Discussion, explicit).

The paper's PUC (Eq. 1) has ONE thermo-optic phase shifter -> one DOF per cell. A
universal N-mode interferometer needs N^2 real DOF; a rectangular mesh of single-theta
PUCs supplies only N(N-1)/2 (no internal-splitting control, no output phases). So the
reachable set is a low-dimensional submanifold of U(N): for N=4, 6 DOF inside 16.

This module makes that explicit:
  * DOF counting along a phase-shifter ladder.
  * Best-fit fidelity to Haar-random U(4) for: single-theta (6), single-theta + output
    phases (10), and the universal 2-DOF mesh (16). Universality returns only at the top.
  * Permutations and 'realizable' (forward-generated) unitaries ARE reachable exactly by
    single-theta meshes -- which is why the paper demonstrates those classes.
  * The coupler-imbalance ceiling on fidelity using the dispersive MZI.
"""

import numpy as np
from scipy.optimize import minimize

from .puc import puc_matrix, mzi_matrix, embed
from .unitary import fit_unitary, random_unitary, mesh_unitary, n_params, PERM_1, PERM_2
from .metrics import matrix_fidelity
from .coupler import mzi_single_theta


def _layer_pairs(N, layer):
    start = layer % 2
    return [(i, i + 1) for i in range(start, N - 1, 2)]


def single_theta_mesh(thetas, N, out_phases=None, block=puc_matrix):
    """Mesh of single-DOF cells; optional output phases."""
    U = np.eye(N, dtype=complex)
    k = 0
    for layer in range(N):
        L = np.eye(N, dtype=complex)
        for (m, n) in _layer_pairs(N, layer):
            L = embed(block(thetas[k]), m, n, N) @ L
            k += 1
        U = L @ U
    if out_phases is not None:
        U = np.diag(np.exp(1j * out_phases)) @ U
    return U


def n_mzi(N):
    return N * (N - 1) // 2


def dof_counts(N=4):
    """Real DOF along the phase-shifter ladder vs dim U(N) = N^2."""
    m = n_mzi(N)
    return {"single_theta": m,
            "single_theta+output_phases": m + N,
            "two_dof_universal": N * (N - 1) + N,
            "dim_U(N)": N * N}


def _best_fit_infidelity(build_fn, n_par, U_target, restarts=8, seed=0):
    N = U_target.shape[0]

    def infid(p):
        V = build_fn(p, N)
        return 1.0 - matrix_fidelity(U_target, V)

    rng = np.random.default_rng(seed)
    best = 1.0
    for _ in range(restarts):
        p0 = rng.uniform(0, 2 * np.pi, n_par)
        sol = minimize(infid, p0, method="Nelder-Mead",
                       options={"maxiter": 8000, "xatol": 1e-8, "fatol": 1e-12})
        best = min(best, float(sol.fun))
    return best


def _build_single(p, N):
    return single_theta_mesh(p, N)


def _build_single_out(p, N):
    m = n_mzi(N)
    return single_theta_mesh(p[:m], N, out_phases=p[m:m + N])


def haar_fidelity_gap(n_samples=12, N=4, seed=0):
    """Best-fit fidelity to Haar-random U(N) for each rung of the ladder."""
    rng = np.random.default_rng(seed)
    res = {"single_theta": [], "single_theta+output_phases": [], "two_dof_universal": []}
    for s in range(n_samples):
        U = random_unitary(N, seed=int(rng.integers(1e9)))
        res["single_theta"].append(
            1 - _best_fit_infidelity(_build_single, n_mzi(N), U, seed=s))
        res["single_theta+output_phases"].append(
            1 - _best_fit_infidelity(_build_single_out, n_mzi(N) + N, U, seed=s))
        _, _, fid = fit_unitary(U, seed=s, restarts=6)
        res["two_dof_universal"].append(fid)
    return {k: np.array(v) for k, v in res.items()}


def _routing_fidelity(V, P):
    """Fraction of input power delivered to the permutation's target ports (mean)."""
    N = P.shape[0]
    target = np.argmax(np.abs(P), axis=0)   # output port for each input
    col_power = np.sum(np.abs(V) ** 2, axis=0) + 1e-12
    return float(np.mean([np.abs(V[target[i], i]) ** 2 / col_power[i] for i in range(N)]))


def _best_routing(build_fn, n_par, P, restarts=10, seed=0):
    N = P.shape[0]

    def neg_route(p):
        return 1.0 - _routing_fidelity(build_fn(p, N), P)

    rng = np.random.default_rng(seed)
    best = 0.0
    for _ in range(restarts):
        p0 = rng.uniform(0, 2 * np.pi, n_par)
        sol = minimize(neg_route, p0, method="Nelder-Mead",
                       options={"maxiter": 8000, "fatol": 1e-12})
        best = max(best, 1.0 - float(sol.fun))
    return best


def permutation_reachability():
    """Permutations: single-theta realises the *routing pattern* (intensity); adding
    output phases recovers exact gate fidelity (phase included)."""
    out = {}
    for name, P in [("perm_1", PERM_1), ("perm_2", PERM_2)]:
        routing = _best_routing(_build_single, n_mzi(4), P)
        gate_with_phases = 1 - _best_fit_infidelity(_build_single_out, n_mzi(4) + 4, P,
                                                     restarts=10)
        out[name] = {"routing_single_theta": routing,
                     "gate_fidelity_with_output_phases": gate_with_phases}
    return out


def realizable_unitary_reachability(seed=0):
    """A unitary GENERATED by a single-theta mesh is, by construction, reachable."""
    rng = np.random.default_rng(seed)
    thetas = rng.uniform(0, 2 * np.pi, n_mzi(4))
    U = single_theta_mesh(thetas, 4)
    inf = _best_fit_infidelity(_build_single, n_mzi(4), U, restarts=10)
    return 1 - inf


def coupler_imbalance_ceiling(lambdas=None):
    """Fidelity of the single-theta CROSS state to ideal swap vs wavelength.

    Uses the dispersive MZI; off the 3-dB wavelength, coupler imbalance caps fidelity.
    """
    if lambdas is None:
        lambdas = np.linspace(1530, 1565, 71)
    swap = np.array([[0, 1], [1, 0]], dtype=complex)
    fids = []
    for lam in lambdas:
        M = mzi_single_theta(0.0, lam, excess_loss_db=0.0)   # lossless: isolate imbalance
        fids.append(matrix_fidelity(swap, M))
    return lambdas, np.array(fids)


def run(verbose=True):
    dof = dof_counts(4)
    gap = haar_fidelity_gap(n_samples=12, seed=1)
    perms = permutation_reachability()
    realiz = realizable_unitary_reachability()
    lam, ceil = coupler_imbalance_ceiling()
    out = {"dof": dof, "haar_gap": gap, "perms": perms, "realizable": realiz,
           "coupler_ceiling_lambdas": lam, "coupler_ceiling_fidelity": ceil,
           # the design wavelength is not on the default grid and is not where the
           # coupler is 50:50, so the ceiling there is reported as its own number
           "coupler_ceiling_at_1560": float(
               coupler_imbalance_ceiling(np.array([1560.0]))[1][0])}
    if verbose:
        print(f"[expressivity] DOF for N=4: single-theta={dof['single_theta']}, "
              f"+output phases={dof['single_theta+output_phases']}, "
              f"2-DOF universal={dof['two_dof_universal']}, dim U(4)={dof['dim_U(N)']}")
        for k in ("single_theta", "single_theta+output_phases", "two_dof_universal"):
            v = gap[k]
            print(f"[expressivity] Haar-U(4) best-fit fidelity, {k:28s}: "
                  f"mean={v.mean():.3f}, min={v.min():.3f}, max={v.max():.3f}")
        print(f"[expressivity] permutations via single-theta routing: "
              f"perm_1={perms['perm_1']['routing_single_theta']:.4f}, "
              f"perm_2={perms['perm_2']['routing_single_theta']:.4f} "
              f"(gate fidelity with output phases: "
              f"{perms['perm_1']['gate_fidelity_with_output_phases']:.3f}/"
              f"{perms['perm_2']['gate_fidelity_with_output_phases']:.3f})")
        print(f"[expressivity] single-theta-realizable unitary recovered to "
              f"fidelity {realiz:.4f}")
        print(f"[expressivity] coupler-imbalance fidelity ceiling (cross state) over "
              f"{lam.min():.0f}-{lam.max():.0f}nm: "
              f"{ceil.max():.4f} @{lam[ceil.argmax()]:.0f}nm -> "
              f"{ceil.min():.4f} @{lam[ceil.argmin()]:.0f}nm; "
              f"{out['coupler_ceiling_at_1560']:.4f} @1560nm (design)")
    return out


if __name__ == "__main__":
    run()
