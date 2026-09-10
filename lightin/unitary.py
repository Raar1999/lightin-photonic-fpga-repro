"""
Bidirectional unitary matrix multiplication on a universal rectangular mesh.

The paper realises 4x4 unitary matrices on the square mesh (rectangular sub-topology,
Fig. 2c). Here we build a universal Clements rectangular mesh of 2-DOF MZIs, FIT the
mesh phases to a target unitary, then RECONSTRUCT the realised matrix by multiplying
the physical MZI transfer matrices. The reconstruction is independent of the fit, so a
fidelity ~ 1 is a genuine check that the mesh realises the target (the "programming
phases" are the fitted values).

Permutation matrices (Fig. 2d) are realised exactly by routing (cross/bar) states.
"""

import numpy as np
from scipy.optimize import least_squares

from .puc import mzi_matrix, embed
from .metrics import matrix_fidelity, correlation


def _layer_pairs(N, layer):
    start = layer % 2
    return [(i, i + 1) for i in range(start, N - 1, 2)]


def mesh_unitary(params, N):
    """Build the NxN mesh unitary from a flat parameter vector.

    Layout: N layers of MZIs (Clements rectangular) + N output phases.
    params = [theta_0, phi_0, theta_1, phi_1, ..., out_phase_0, ..., out_phase_{N-1}].
    """
    n_mzi = N * (N - 1) // 2
    th = params[0:2 * n_mzi:2]
    ph = params[1:2 * n_mzi:2]
    out_phases = params[2 * n_mzi:2 * n_mzi + N]

    U = np.eye(N, dtype=complex)
    k = 0
    for layer in range(N):
        L = np.eye(N, dtype=complex)
        for (m, n) in _layer_pairs(N, layer):
            L = embed(mzi_matrix(th[k], ph[k]), m, n, N) @ L
            k += 1
        U = L @ U
    U = np.diag(np.exp(1j * out_phases)) @ U
    return U


def n_params(N):
    return N * (N - 1) + N


def fit_unitary(U_target, seed=0, restarts=6):
    """Find mesh phases realising U_target. Returns (params, U_realised, fidelity)."""
    N = U_target.shape[0]

    def residual(p):
        diff = mesh_unitary(p, N) - U_target
        return np.concatenate([diff.real.ravel(), diff.imag.ravel()])

    best = None
    rng = np.random.default_rng(seed)
    for _ in range(restarts):
        p0 = rng.uniform(0, 2 * np.pi, n_params(N))
        sol = least_squares(residual, p0, method="lm", max_nfev=20000)
        U_real = mesh_unitary(sol.x, N)
        fid = matrix_fidelity(U_target, U_real)
        if best is None or fid > best[2]:
            best = (sol.x, U_real, fid)
        if fid > 1 - 1e-9:
            break
    return best


def random_unitary(N, seed=0):
    """Haar-random NxN unitary via QR of a complex Gaussian."""
    rng = np.random.default_rng(seed)
    z = (rng.standard_normal((N, N)) + 1j * rng.standard_normal((N, N))) / np.sqrt(2)
    q, r = np.linalg.qr(z)
    d = np.diag(r) / np.abs(np.diag(r))
    return q * d


# --- The paper's two explicit 4x4 permutation matrices (Fig. 2d) ---
PERM_1 = np.array([[0, 0, 1, 0],
                   [1, 0, 0, 0],
                   [0, 1, 0, 0],
                   [0, 0, 0, 1]], dtype=complex)
PERM_2 = np.array([[0, 1, 0, 0],
                   [1, 0, 0, 0],
                   [0, 0, 0, 1],
                   [0, 0, 1, 0]], dtype=complex)


def run(verbose=True):
    """Reproduce the unitary-matrix results; returns a dict of outcomes."""
    out = {}

    # 1) Permutation matrices: the routing fidelity is optimised over the single-theta
    #    mesh phases, so it measures what the physical cells can actually deliver.
    #    Imported here rather than at module scope: expressivity imports this module.
    from .expressivity import _best_routing, _build_single

    for name, P in [("perm_1", PERM_1), (("perm_2"), PERM_2)]:
        routing = _best_routing(_build_single, 6, P, restarts=10, seed=0)
        out[name] = {"routing_fidelity": routing}
        if verbose:
            print(f"[{name}] single-theta routing realisation, "
                  f"routing fidelity = {routing:.6f}")

    # 2) Two Haar-random 4x4 unitaries fitted onto the mesh (Fig. 2h,i).
    fids, corrs = [], []
    realised = {}
    for s in (1, 2):
        U = random_unitary(4, seed=s)
        _, U_real, fid = fit_unitary(U, seed=s)
        corr = correlation(np.abs(U), np.abs(U_real))
        fids.append(fid); corrs.append(corr)
        realised[f"random_{s}"] = {"target": U, "realised": U_real,
                                    "fidelity": fid, "modulus_corr": corr}
        if verbose:
            print(f"[random_{s}] mesh-fitted unitary, fidelity = {fid:.6f}, "
                  f"|.|-correlation = {corr:.6f}")
    out["random"] = realised
    out["random_mean_fidelity"] = float(np.mean(fids))
    out["random_mean_modulus_corr"] = float(np.mean(corrs))
    return out


if __name__ == "__main__":
    run()
