"""
Non-unitary matrix multiplication via the diamond structure.

A general (non-unitary) matrix M factorises by SVD as  M = U @ S @ Vh, with U, Vh
unitary and S diagonal non-negative. The paper's diamond mesh realises exactly this:
two unitary sub-meshes around a layer of variable attenuators (the singular values).
Passive optics cannot provide gain, so we realise M / s_max (singular values scaled to
<= 1) and report the matrix up to that global scale -- the modulus pattern (Fig. 2l) is
scale-equivariant. The paper's input/output correlation (Fig. 2n) is measured on the
chip, so the simulation check of this mesh is the modulus agreement alone.
"""

import numpy as np
from .unitary import fit_unitary
from .metrics import matrix_fidelity, correlation


def svd_realise(M, fit_meshes=True, seed=0):
    """Realise non-unitary M via SVD; optionally verify each unitary on a mesh.

    Returns dict with the reconstructed matrix, the (scaled) singular values, the
    unitary-mesh fidelities, and the element-modulus correlation to the target.
    """
    U, s, Vh = np.linalg.svd(M)
    s_scaled = s / s.max()                      # passive: attenuators in [0, 1]
    S = np.diag(s_scaled)

    info = {"singular_values": s, "singular_values_scaled": s_scaled}

    if fit_meshes:
        _, U_real, fU = fit_unitary(U, seed=seed)
        _, Vh_real, fV = fit_unitary(Vh, seed=seed + 100)
        info["mesh_fidelity_U"] = fU
        info["mesh_fidelity_Vh"] = fV
        M_real = U_real @ S @ Vh_real
    else:
        M_real = U @ S @ Vh

    M_target_scaled = M / s.max()
    info["target_scaled"] = M_target_scaled
    info["realised"] = M_real
    info["modulus_corr"] = correlation(np.abs(M_target_scaled), np.abs(M_real))
    info["max_abs_err"] = float(np.max(np.abs(np.abs(M_target_scaled) - np.abs(M_real))))
    return info


def vector_test(M, n_trials=256, seed=0):
    """Apply M (scaled) to many random input vectors; return the theoretical outputs.

    The measured counterpart of these outputs is the chip's, so no correlation between
    theory and experiment can be computed here (paper Fig. 2n is a chip measurement).
    """
    rng = np.random.default_rng(seed)
    s_max = np.linalg.svd(M, compute_uv=False).max()
    Ms = M / s_max
    X = rng.uniform(-1, 1, size=(M.shape[1], n_trials))
    return Ms @ X


def run(verbose=True):
    """Reproduce the non-unitary 3x3 result."""
    rng = np.random.default_rng(7)
    M = rng.uniform(-1, 1, size=(3, 3)) + 1j * rng.uniform(-1, 1, size=(3, 3))
    info = svd_realise(M, fit_meshes=True, seed=3)
    if verbose:
        print(f"[non-unitary 3x3] mesh fidelity U={info['mesh_fidelity_U']:.6f}, "
              f"Vh={info['mesh_fidelity_Vh']:.6f}")
        print(f"[non-unitary 3x3] element-modulus correlation = {info['modulus_corr']:.6f}, "
              f"max |.| error = {info['max_abs_err']:.2e}")
    return info


if __name__ == "__main__":
    run()
