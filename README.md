# LightIN — computational reproduction of a silicon photonic FPGA

![tests](https://github.com/Raar1999/lightin-photonic-fpga-repro/actions/workflows/tests.yml/badge.svg)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![license](https://img.shields.io/badge/license-Apache--2.0-lightgrey)
![status](https://img.shields.io/badge/status-reproduction-orange)

A from-scratch simulation reproduction of

> Y. Zhu *et al.*, "LightIN: a versatile silicon-integrated photonic field programmable
> gate array with an intelligent configuration framework for next-generation AI clusters,"
> *Light: Science & Applications* **15**, 165 (2026). doi:10.1038/s41377-026-02209-5

This repository aims to reproduce each result in the paper that can be reproduced
**without the fabricated silicon-photonic chip** — i.e. (i) definitions and arithmetic, and
(ii) the simulations the paper itself ran — and it clearly marks the measured hardware
quantities that are *not* reproducible from a PDF. No numbers are fabricated: every
reported value is emitted by running the code, with the paper's value shown alongside only
for comparison. The PUF is simulated on a feed-forward mesh rather than on the chip's
recirculating mesh; see the report's open items.

---

## Quick start

```bash
git clone https://github.com/Raar1999/lightin-photonic-fpga-repro.git
cd lightin-photonic-fpga-repro
python -m venv .venv && source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -e .                       # or: pip install -r requirements.txt
python scripts/run_all.py              # runs everything, writes results.json + figures/
pytest -q                              # 29 checks (or: PYTHONPATH=. python tests/test_reproduction.py)
```

On a typical laptop CPU, `scripts/run_all.py` takes about 15 minutes, most of which is
the ten-seed Iris sweep and the Fig 4d bootstraps, and the test suite takes about
22 seconds. `python scripts/run_all.py --quick` runs a reduced version in about
5 minutes — the Iris sweep drops to two seeds and both Fig 4d bootstraps to 50 resamples,
and the outputs go to `results_quick.json` and `figures_quick/` so a quick run never
overwrites the reported ones. No datasets to
download (Iris ships with scikit-learn; the one digitized curve is in `data/`).
results.json was generated with the package versions in requirements-lock.txt; the Iris
accuracies can differ slightly with other versions of scipy and scikit-learn.

---

## What it reproduces (headline numbers)

All "reproduction" values below come from `scripts/run_all.py`.

| Result | Paper | This repo | Tier |
|---|---|---|---|
| PUC unitarity / cross-bar (Eq. 1) | unitary | err ≤ 1e-32 | exact |
| 4×4 unitary realisation (Fig 2h,i) | high fidelity | fidelity 1.000000 with ideal couplers; the coupler fitted to Fig 4d limits the single-θ cross state to **0.9942** at 1560 nm | sim |
| 4×4 permutations (Fig 2d) | realised by routing | routing fidelity **0.999999999999** | sim |
| Effective bits @10 GBaud (Fig 2f) | σ=0.0269 → **6.22 bit** | log₂(2/σ)=**6.216** | exact |
| Non-unitary 3×3 mesh (Fig 2l) | modulus match | corr 1.0, err 7.8e-16 | sim |
| Non-unitary input/output correlation (Fig 2n) | measured on chip | not reproduced | hardware — not reproduced |
| Iris unitary NN, full set (Fig 2o,p) | 94.67% offline (evaluation set not stated) | **95.47% ± 1.26%** (10 seeds) | sim |
| Iris unitary NN, held out | — (paper's 93.33% is on-chip) | 89.33% ± 5.14% (10 seeds) | sim |
| Iris identity control (unitary frozen to I) | — | 85.60% ± 0.44% full set, 81.56% ± 4.67% held out | control |
| Iris logistic baseline (same 4 features, same splits) | — | 96.53% ± 0.88% full set, 94.89% ± 3.45% held out | control |
| On-chip latency | ~60 ps | n_g·L/c = **60.0 ps** | exact |
| Energy | **1.875 pJ/MAC** | 1.8 W / 0.96 TMAC·s⁻¹ = **1.875**. 3 V, 100 Ω, 90 mW heater parameters and the 96-operation count are taken from Supplementary Note 3 and cannot be checked from the main article. | consistency check |
| Throughput | **1.92 TOPS** | 96 ops × 2 dir × 10 GBaud = **1.92**. 3 V, 100 Ω, 90 mW heater parameters and the 96-operation count are taken from Supplementary Note 3 and cannot be checked from the main article. | consistency check |
| Switch crosstalk (Fig 4d,e) | −45 to <−20 dB | mesh model fitted to Fig 4d: −27.2 to −21.1 dB at 1560 nm; worst −16.8 dB over the fitted 1549–1565 nm, −11.8 dB extrapolated over 1530–1549 nm; bar-state values rest on assumed fabrication spreads (report §6.3) | model vs measurement |
| On-chip insertion loss | −1.85 to −2.99 dB (8 paths) | **−1.40 to −1.80 dB** (8 modelled paths) | model vs measurement |
| PUF uniqueness, 100 dies (Fig 5) | **49.97%** | **49.01%** | sim |
| PUF uniformity, 100 dies (Fig 5) | **50.15%** | **50.12%** | sim |
| Recirculating-mesh solver | — | ring/add-drop match analytic to **1e-15** | sim |

The energy and throughput rows use the paper's **own derivation** (Supplementary Note 3),
not a guessed op-count — see [`docs/REPRODUCTION_REPORT_v5.md`](docs/REPRODUCTION_REPORT_v5.md) §6.

**Not reproduced — hardware-only, left blank rather than faked:** measured eye-diagram SNR
(17.10 / 17.83 dB) and Q factors (7.17–8.08), the raw measured crosstalk spectra, the
measured non-unitary input/output correlation (Fig 2n), and the 2-die experimental PUF
numbers. These require the physical device.

---

## Architecture

The paper's chip is a **4×4 square recirculating mesh** of 40 programmable unit cells
(PUCs = single-thermo-optic-phase MZIs). The same hardware is reconfigured into five
functions. This repo mirrors that structure: one small physics core, then one module per
function, plus two modules that extend the analysis into the chip's real device physics.

```
                         ┌─────────────────────────────────────────────┐
                         │  puc.py   PUC transfer matrix (Eq. 1)        │
   physics core          │  coupler.py   CMT directional coupler,       │
                         │       dispersion + loss (chip geometry)      │
                         │  metrics.py   ENOB, latency, Hamming, corr   │
                         └───────────────┬─────────────────────────────┘
                                         │ building blocks
        ┌───────────────┬───────────────┼───────────────┬───────────────┐
        ▼               ▼               ▼               ▼               ▼
  unitary.py      nonunitary.py     nn_iris.py       mrm.py        switching.py
  4×4 unitary     3×3 via SVD /     1-layer          MRM λ-lock     4-stage planar
  on universal    diamond mesh      unitary NN       via photonic   switch, crosstalk
  mesh (Fig 2)    (Fig 2)           on Iris (Fig 2)  differentiator from coupler
        │                                             (Fig 3)        dispersion (Fig 4)
        │                                                                  │
        ▼                                                                  ▼
   ppuf.py  one-die photonic PUF with diagonal injection      throughput.py  1.92 TOPS
   uniqueness / uniformity / reliability (Fig 5)              & 1.875 pJ/MAC (consistency check)

   ── analysis extensions (beyond first-pass reproduction) ────────────────────────────
   expressivity.py   single-θ PUC is 6-DOF inside U(4)=16-dim → limited; ladder to universal
   recirculating.py  scattering-matrix-network solver WITH feedback loops (poles/resonances)
```

### Two ideas worth knowing before reading the code

1. **Feedforward vs recirculating.** The matrix-multiply functions use a *feedforward*
   rectangular sub-mesh — a product of MZI layers (`unitary.py`, `nonunitary.py`). The full
   chip *recirculates*: light returns through closed loops, so the transfer function has
   **poles**. That needs a linear solve, `o = (I − S·C)⁻¹ S·b`, implemented in
   `recirculating.py` and validated against the analytic ring to ~1e-15.

2. **Single-θ expressivity limit.** The paper's PUC has one phase shifter → one DOF. A
   universal 4-mode interferometer needs 16 real DOF; a single-θ mesh supplies only 6.
   `expressivity.py` quantifies this: best-fit fidelity to random U(4) is ~0.56 for
   single-θ, rising to 1.0 only with the full 2-DOF mesh. This is *why* the paper
   demonstrates permutations and specific realizable unitaries.

### Module reference

| Module | Paper section | Role |
|---|---|---|
| `lightin/puc.py` | Eq. 1, Fig 1 | PUC transfer matrix; cross/bar; universal 2-DOF MZI |
| `lightin/coupler.py` | Fig 4, Methods | CMT directional coupler with chip geometry, dispersion, loss; `fit_dc_dispersion()` |
| `lightin/metrics.py` | Fig 2f, Methods | ENOB (6.22/5.47 bit), latency (60 ps), Hamming, correlation, fidelity |
| `lightin/unitary.py` | Fig 2c–i | 4×4 unitary on a universal mesh; permutations by routing |
| `lightin/nonunitary.py` | Fig 2l–n | 3×3 non-unitary via SVD / diamond mesh |
| `lightin/nn_iris.py` | Fig 2o,p | one-layer unitary NN, Iris accuracy + confusion matrix |
| `lightin/mrm.py` | Fig 3 | MRM wavelength locking via a photonic differentiator |
| `lightin/switching.py` | Fig 4 | 4-stage planar 4×4 switch; crosstalk from coupler dispersion |
| `lightin/ppuf.py` | Fig 5 | one-die photonic PUF with diagonal injection: uniqueness / uniformity / reliability |
| `lightin/expressivity.py` | Discussion | single-θ DOF ladder; coupler-imbalance fidelity ceiling |
| `lightin/recirculating.py` | square recirculating mesh | scattering-matrix solver with feedback; rings; 2D plaquette; FIR vs IIR |
| `lightin/throughput.py` | Abstract, Supp Note 3 | 1.92 TOPS and 1.875 pJ/MAC from the paper's derivation |

---

## Repository layout

```
lightin-photonic-fpga-repro/
├── README.md                         ← you are here
├── LICENSE                           Apache-2.0
├── pyproject.toml                    installable package metadata
├── requirements.txt
├── requirements-lock.txt             pinned versions that produced results.json
├── CITATION.cff
├── results.json                      last run's consolidated numbers
├── lightin/                          the package (12 modules)
├── scripts/
│   ├── run_all.py                    run every module, write results.json + figures/
│   └── fit_fig4.py                   fit the coupler to the digitized Fig 4d crosstalk
├── tests/
│   └── test_reproduction.py          29 checks (pytest or standalone)
├── data/
│   └── fig4d_T20_digitized.csv       colour-digitized chip crosstalk (with provenance header)
├── .github/
│   └── workflows/tests.yml           CI: the test suite on Python 3.11, 3.12 and 3.13
├── figures/                          10 generated figures (regenerated by run_all.py)
└── docs/
    ├── REPRODUCTION_REPORT_v5.md     full scope map, per-result table, parameter provenance
    ├── REPRODUCTION_REPORT_v4.md     the previous report
    ├── REPRODUCTION_REPORT_v3.md     the report before that
    ├── REPRODUCTION_REPORT_v2.md     earlier report, kept for history
    ├── REPRODUCTION_REPORT.md        the first-pass report
    └── DOCUMENT_SEARCH_LIST_superseded.md   superseded; kept for history
```

---

## How to run

**Install** (editable, so `import lightin` and the scripts work anywhere):

```bash
pip install -e .
```

or without installing, prefix commands with `PYTHONPATH=.`.

**Everything at once** — prints a consolidated table, writes `results.json`, regenerates
all figures into `figures/`:

```bash
python scripts/run_all.py
```

**One function at a time** — each module runs standalone:

```bash
python -m lightin.unitary        # unitary matrix realisation + fidelity
python -m lightin.nonunitary     # non-unitary SVD/diamond
python -m lightin.nn_iris        # Iris unitary NN + confusion matrix
python -m lightin.ppuf           # PUF uniqueness / uniformity / reliability
python -m lightin.switching      # switch crosstalk + loss budget
python -m lightin.coupler        # CMT coupler: extinction, link budget, dispersion fit
python -m lightin.expressivity   # single-θ expressivity ladder
python -m lightin.recirculating  # feedback solver: ring/add-drop validation, plaquette, FIR vs IIR
python -m lightin.throughput     # exact energy + TOPS derivation
python -m lightin.mrm            # MRM differentiator monitoring / locking
```

**Fit the coupler to the chip's measured crosstalk** (digitized Fig 4d):

```bash
python scripts/fit_fig4.py       # → mesh fit λ₀=1574.7 nm, slope=0.00261 rad/nm, floor −26.2 dB, RMS 0.79 dB; writes figures/fig4_digitized.png
```

**Tests:**

```bash
pytest -q
# or, with no pytest installed:
PYTHONPATH=. python tests/test_reproduction.py
```

---

## Parameter provenance (chip-grounded)

The chip parameters below were taken from the paper's Methods and Supplementary
(details in [`docs/REPRODUCTION_REPORT_v5.md`](docs/REPRODUCTION_REPORT_v5.md) §6). The
parameters that are not from the paper, with their sources where recorded, are listed in
docs/REPRODUCTION_REPORT_v5.md §6.3:

- group index **n_g = 4.0** (stated); phase index **n_eff ≈ 2.36** (450×220 nm SOI TE)
- directional coupler **11.5 µm long, 200 nm gap**; square-mesh unit **500 µm**; arm **208 µm**
- heater **3 V for π across 100 Ω → 90 mW**, E[θ]=π/2 → **45 mW/MZI**, ×40 → **1.8 W**
- PUF arm-length spread **N(0.08 µm, 0.11 µm)** → phase N(0.76, 1.05) rad via n_eff
- coupler dispersion **fitted to the digitized Fig 4d crosstalk** (`scripts/fit_fig4.py`)

The superseded document search list is kept for history only; current parameter
provenance is in docs/REPRODUCTION_REPORT_v5.md §6.

---

## Scope

Four categories (full table in the report):

- **Exact** — definitions/arithmetic reproduced to machine precision: PUC, 6.22/5.47-bit,
  60 ps latency.
- **Simulation** — the paper's own simulations, re-implemented on independent code:
  unitary/non-unitary fidelity, Iris across seeds, PUF ~49%/~50%, ring solver.
- **Model vs measurement** — the switch crosstalk and on-chip insertion loss, where a model
  in this code is compared with a quantity measured on the chip.
- **Hardware-only** — left unreproduced rather than fabricated: measured eye SNR/Q, raw
  measured spectra, 2-die experimental PUF.
- **Consistency check** — energy (1.875 pJ/MAC) and throughput (1.92 TOPS), reproduced
  arithmetically from inputs stated only in Supplementary Note 3.

Two caveats carried in the code: (1) the plain real-op throughput is 0.32 TOPS —
the 1.92 TOPS figure follows the paper's stated complex + bidirectional + PD-squared-add
convention; (2) the Iris readout adds a small learned linear layer on the detected
intensities (standard for photonic classifiers), because a single-θ mesh alone has limited
unitary expressivity, as the paper's Discussion concedes and `expressivity.py` quantifies.

---

## References

- Zhu *et al.*, *Light: Sci. Appl.* **15**, 165 (2026) — the reproduced paper.
- Directional-coupler dispersion, propagation loss, grating-coupler references and the
  provenance of each borrowed parameter are listed in
  [`docs/REPRODUCTION_REPORT_v5.md`](docs/REPRODUCTION_REPORT_v5.md) §6.3. The superseded
  document search list is kept for history only; current parameter provenance is in
  docs/REPRODUCTION_REPORT_v5.md §6.

## License

Apache-2.0 — see [`LICENSE`](LICENSE). This is an independent reproduction; it is not
affiliated with or endorsed by the original authors.
