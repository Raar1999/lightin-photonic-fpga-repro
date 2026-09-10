"""
Automatic MRM wavelength locking via a photonic differentiator (paper Fig. 3).

Principle (reproduced as a model): a high extinction ratio (ER) means a large amplitude
gap between logic '1' and '0'. The chip is configured as a differentiator -- split,
delay one copy, subtract -- so the photodetected monitoring signal is proportional to
the squared amplitude difference between adjacent differing symbols, i.e. to |E1 - E0|^2.
Tracking and maximising this signal with the ring heater locks the modulator to the
laser at high ER.

What is reproducible: the monitoring-signal-vs-bias shape and the locking principle.
What is NOT (hardware-only): the measured eye-diagram SNR (~17-18 dB) and Q factors,
which come from the fabricated MRM + optical link. The eye diagrams below are a model
for illustration and are not claimed to match the measured values.
"""

import numpy as np


def mrm_through(detuning, r=0.92, a=0.90):
    """All-pass micro-ring through-port complex transmission vs round-trip detuning phi.

    t = (r - a e^{i*phi}) / (1 - r a e^{i*phi}),  phi = detuning (radians).
    """
    e = np.exp(1j * detuning)
    return (r - a * e) / (1 - r * a * e)


def symbol_fields(bias, data_swing=0.9, r=0.92, a=0.90):
    """Optical fields for logic '1' and '0' at a given heater bias (center detuning)."""
    E1 = mrm_through(bias + data_swing / 2, r, a)
    E0 = mrm_through(bias - data_swing / 2, r, a)
    return E1, E0


def extinction_ratio(bias, **kw):
    E1, E0 = symbol_fields(bias, **kw)
    p1, p0 = abs(E1) ** 2, abs(E0) ** 2
    hi, lo = max(p1, p0), min(p1, p0)
    return 10 * np.log10((hi + 1e-9) / (lo + 1e-9))


def monitoring_signal(bias, transition_prob=0.5, **kw):
    """Differentiator monitoring power ~ P(transition) * |E1 - E0|^2."""
    E1, E0 = symbol_fields(bias, **kw)
    return transition_prob * np.abs(E1 - E0) ** 2


def sweep_bias(bias_range=(-1.2, 1.2), n=400, **kw):
    bias = np.linspace(*bias_range, n)
    mon = np.array([monitoring_signal(b, **kw) for b in bias])
    er = np.array([extinction_ratio(b, **kw) for b in bias])
    lock_bias = bias[np.argmax(er)]
    return {"bias": bias, "monitoring": mon, "er_db": er, "lock_bias": float(lock_bias)}


def eye_data(bias, n_bits=600, sps=32, bw=0.45, noise=0.02, seed=0, **kw):
    """Model NRZ eye: bit stream -> ring -> bandwidth-limited -> overlaid traces."""
    rng = np.random.default_rng(seed)
    bits = rng.integers(0, 2, n_bits)
    E1, E0 = symbol_fields(bias, **kw)
    levels = np.where(bits == 1, abs(E1) ** 2, abs(E0) ** 2)
    wf = np.repeat(levels, sps).astype(float)
    # simple one-pole bandwidth limit
    alpha = bw
    filt = np.empty_like(wf); acc = wf[0]
    for i in range(len(wf)):
        acc = alpha * wf[i] + (1 - alpha) * acc
        filt[i] = acc
    filt += rng.normal(0, noise, size=filt.shape)
    # fold into 2-bit-wide eye windows
    win = 2 * sps
    usable = (len(filt) // win) * win
    eye = filt[:usable].reshape(-1, win)
    t = np.linspace(0, 2, win)
    return t, eye


def run(verbose=True):
    sw = sweep_bias()
    if verbose:
        peak_idx = np.argmax(sw["monitoring"])
        print(f"[MRM lock] differentiator delay = 0.1 ns for 10 Gb/s (paper, Fig 3)")
        print(f"[MRM lock] monitoring signal peaks at bias = {sw['bias'][peak_idx]:.3f} (a.u.)")
        print(f"[MRM lock] max-ER lock bias = {sw['lock_bias']:.3f}, "
              f"ER at lock = {sw['er_db'].max():.1f} dB (model)")
        print(f"[MRM lock] ER away from lock (bias=0) = {extinction_ratio(0.0):.1f} dB (model)")
        print("[MRM lock] paper measured (hardware-only): eye SNR 17.10 & 17.83 dB; "
              "Q factors 7.17-8.08; carrier 1555 nm.")
    return sw


if __name__ == "__main__":
    run()
