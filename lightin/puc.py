"""
Programmable Unit Cell (PUC) and Mach-Zehnder building blocks.

Reproduces the physical PUC of Zhu et al., Light Sci. Appl. (2026) 15:165, Eq. (1):

    T_PUC = j * exp(j theta/2) * [[ sin(theta/2),  cos(theta/2)],
                                  [ cos(theta/2), -sin(theta/2)]]

This is a *single thermo-optic phase shifter* MZI: one degree of freedom per cell.
As the paper notes in its Discussion, a single-phase-shifter MZI has limited unitary
expressivity (arm imbalance + only one DOF). For building *universal* meshes we also
provide the standard 2-DOF MZI (internal phase theta + external phase phi), which is
the mathematical object whose phases the chip is programmed to approximate.
"""

import numpy as np


def puc_matrix(theta: float) -> np.ndarray:
    """Paper Eq. (1). Single-theta thermo-optic PUC, 2x2 unitary up to global phase."""
    h = theta / 2.0
    inner = np.array([[np.sin(h), np.cos(h)],
                      [np.cos(h), -np.sin(h)]], dtype=complex)
    return 1j * np.exp(1j * h) * inner


def puc_state(theta: float) -> str:
    """Identify cross/bar from intensity extrema of the single-theta PUC."""
    T = puc_matrix(theta)
    bar_power = abs(T[0, 0]) ** 2          # input 0 -> output 0
    cross_power = abs(T[1, 0]) ** 2        # input 0 -> output 1
    return "bar" if bar_power > cross_power else "cross"


def mzi_matrix(theta: float, phi: float) -> np.ndarray:
    """
    Universal 2-DOF MZI used as the building block of universal meshes:
        external phase phi -> 50:50 BS -> internal phase theta -> 50:50 BS
    Returns a 2x2 SU(2)-class unitary with two free parameters.
    """
    bs = (1 / np.sqrt(2)) * np.array([[1, 1j], [1j, 1]], dtype=complex)
    pe = np.diag([np.exp(1j * phi), 1.0])          # external phase on top arm
    pi = np.diag([np.exp(1j * theta), 1.0])        # internal phase on top arm
    return bs @ pi @ bs @ pe


def embed(T2: np.ndarray, m: int, n: int, N: int) -> np.ndarray:
    """Embed a 2x2 block acting on modes (m, n) into an NxN identity."""
    U = np.eye(N, dtype=complex)
    U[m, m] = T2[0, 0]; U[m, n] = T2[0, 1]
    U[n, m] = T2[1, 0]; U[n, n] = T2[1, 1]
    return U


def thermo_optic_phase(voltage, v_pi, v_offset=0.0):
    """
    Thermo-optic phase vs applied voltage. Heater phase ~ power ~ V^2.
    Phase = pi * ((V - v_offset)/v_pi)^2  (monotone branch used for the LUT).
    """
    v = np.asarray(voltage, dtype=float)
    return np.pi * ((v - v_offset) / v_pi) ** 2


if __name__ == "__main__":
    # Sanity: PUC is unitary up to global phase; cross at theta=0, bar at theta=pi.
    for th in [0.0, np.pi / 2, np.pi, 3 * np.pi / 2]:
        T = puc_matrix(th)
        unit_err = np.max(np.abs(T.conj().T @ T - np.eye(2)))
        print(f"theta={th:6.3f}  state={puc_state(th):5s}  unitarity_err={unit_err:.2e}")
