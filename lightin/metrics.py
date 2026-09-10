"""
Metrics used throughout the LightIN reproduction.

Key exact reproduction: the paper's effective-bit numbers.
At 10 GBaud the unitary core reaches correlation 0.9955 with sigma = 0.0269,
"corresponding to 6.22 bit"; the non-unitary core gives sigma = 0.0453 -> 5.47 bit.

These follow exactly from ENOB = log2(range / sigma) with range = 2 (outputs in [-1, 1]):
    log2(2 / 0.0269) = 6.216  ~ 6.22
    log2(2 / 0.0453) = 5.464  ~ 5.47
"""

import numpy as np


def enob(sigma: float, dynamic_range: float = 2.0) -> float:
    """Effective number of bits from output noise std (range/sigma convention)."""
    return float(np.log2(dynamic_range / sigma))


def correlation(theoretical: np.ndarray, experimental: np.ndarray) -> float:
    """Pearson correlation coefficient between flattened arrays.

    Complex inputs are stacked (real, imag) so the imaginary part is not discarded.
    """
    a = np.asarray(theoretical).ravel()
    b = np.asarray(experimental).ravel()
    if np.iscomplexobj(a) or np.iscomplexobj(b):
        a = np.concatenate([a.real, a.imag])
        b = np.concatenate([b.real, b.imag])
    return float(np.corrcoef(a.astype(float), b.astype(float))[0, 1])


def matrix_fidelity(U_target: np.ndarray, U_real: np.ndarray) -> float:
    """Normalised gate fidelity F = |Tr(U_target^dag U_real)|^2 / N^2."""
    N = U_target.shape[0]
    return float(np.abs(np.trace(U_target.conj().T @ U_real)) ** 2 / N ** 2)


def hamming_distance(r1: np.ndarray, r2: np.ndarray) -> float:
    """Fractional Hamming distance between two bit strings."""
    r1 = np.asarray(r1).astype(int).ravel()
    r2 = np.asarray(r2).astype(int).ravel()
    return float(np.mean(r1 != r2))


def propagation_latency(path_length_m: float, group_index: float = 4.0) -> float:
    """On-chip optical propagation latency t = n_g * L / c (seconds)."""
    c = 2.99792458e8
    return group_index * path_length_m / c


def compute_throughput_tops(N: int, baud: float, complex_mac_ops: int = 2,
                            directions: int = 1) -> float:
    """
    Throughput estimate for an NxN photonic matrix-vector multiplier.
    OPS = directions * N^2 * complex_mac_ops * baud.
    complex_mac_ops counts ops per MAC (2 for real mult+add; up to ~8 for a complex MAC).
    Returned in TOPS (1e12 ops/s). NOTE: value is convention-dependent (see report).
    """
    return directions * (N ** 2) * complex_mac_ops * baud / 1e12


def energy_per_mac_pj(heater_power_w: float, n_active_heaters: int,
                      N: int, baud: float, directions: int = 1) -> float:
    """
    Static-heater energy per MAC = (total heater power) / (MAC rate), in pJ/MAC.
    MAC rate = directions * N^2 * baud.
    """
    total_power = heater_power_w * n_active_heaters
    mac_rate = directions * (N ** 2) * baud
    return (total_power / mac_rate) * 1e12


if __name__ == "__main__":
    print("ENOB check (paper says 6.22 and 5.47):")
    print(f"  unitary  sigma=0.0269 -> {enob(0.0269):.3f} bit")
    print(f"  non-uni  sigma=0.0453 -> {enob(0.0453):.3f} bit")
    print("\nLatency check (paper says ~60 ps on-chip):")
    print(f"  L=4.5 mm, n_g=4 -> {propagation_latency(4.5e-3)*1e12:.1f} ps")
    print(f"  + 100 ps pulse (10 GBaud) -> {propagation_latency(4.5e-3)*1e12 + 100:.1f} ps total")
