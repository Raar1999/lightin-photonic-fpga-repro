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

## Status

The reproduction is complete at commit `11683de`, where `results.json` and the model code
behind it last changed; the commits after it are documentation and packaging, and none of
them touches a model value. Everything in the paper that can be reached without the
fabricated chip has been reproduced, and what cannot be is marked as such rather than
filled in.

The suite is 76 tests, and 773 numbers in this file and in
[`docs/REPRODUCTION_REPORT_v10.md`](docs/REPRODUCTION_REPORT_v10.md) are checked against the
code on every run: 703 against the values `results.json` holds, and 70 against the
module-level constants the model was given, which `results.json` does not record because
they are inputs to the model rather than outputs of it. The report's §6.3 table also cites
74 source lines, and each is checked to still point at the parameter it names. What sits
outside those checks is inventoried, with its provenance, in
[`docs/REPORT_UNCHECKED.md`](docs/REPORT_UNCHECKED.md).

On the machine and the library versions that wrote them — recorded in the `environment`
block of `results.json` and pinned in `requirements-lock.txt` — `results.json` and the
eleven figures in `figures/` regenerate byte for byte, so a full `python scripts/run_all.py`
leaves the working tree clean.

That has now been checked from outside this working copy as well. A clone of the public
repository, in a new virtual environment installed with `pip install -e .[dev]`, passed all
76 tests and ran the full pipeline in 19.5 minutes. Six of the 997 values in the
`results.json` it produced differed from the committed file, and all six were the recorded
numpy, scikit-learn and matplotlib versions, which that install resolves to the current
releases rather than to the pinned ones. The other 991 were identical, and the eleven
figures matched in pixel data, differing only in the matplotlib version that PNG metadata
carries. No computed value differed.

The work that remains is the report's open items (§7), in three groups: limitations that the
published material cannot resolve, disagreements left on record rather than tuned away, and
the work that would narrow either.

---

## Quick start

```bash
git clone https://github.com/Raar1999/lightin-photonic-fpga-repro.git
cd lightin-photonic-fpga-repro
python -m venv .venv && source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -e .                       # or: pip install -r requirements.txt
python scripts/run_all.py              # runs everything, writes results.json + figures/
pytest -q                              # 76 checks (or: PYTHONPATH=. python tests/test_reproduction.py)
```

On a typical laptop CPU, `scripts/run_all.py` takes about 22 minutes, most of which is
the ten-seed Iris sweep, the Fig 4d and Fig 4e bootstraps and the recirculating PUF, and
the test suite takes about 50 seconds. `python scripts/run_all.py --quick` runs a reduced
version in about 4 minutes — the Iris sweep drops to two seeds and every bootstrap to 50<!--[scripts.run_all.QUICK_N_BOOT]-->
resamples, and the outputs go to `results_quick.json` and `figures_quick/` so a quick run
never overwrites the reported ones. No datasets to
download (Iris ships with scikit-learn; the two digitized curves are in `data/`).
results.json was generated with the package versions in requirements-lock.txt; the Iris
accuracies can differ slightly with other versions of scipy and scikit-learn.

---

## What it reproduces (headline numbers)

All "reproduction" values below come from `scripts/run_all.py`.

| Result | Paper | This repo | Tier |
|---|---|---|---|
| PUC unitarity / cross-bar (Eq. 1) | unitary | err ≤ 1e-32 | exact |
| 4×4 unitary realisation (Fig 2h,i) | high fidelity | fidelity 1.000000<!--{unitary.random_mean_fidelity}--> with ideal couplers; the coupler fitted to Fig 4d limits the single-θ cross state to **0.9942<!--{expressivity.coupler_ceiling_fidelity_at_1560}-->** at 1560 nm | sim |
| 4×4 permutations (Fig 2d) | realised by routing | routing fidelity **0.999999999999<!--{unitary.perm_routing_fidelity[0]}-->** | sim |
| Effective bits @10 GBaud (Fig 2f) | σ=0.0269 → **6.22 bit** | log₂(2/σ)=**6.216<!--{unitary.enob_at_sigma_0.0269}-->** | exact |
| Non-unitary 3×3 mesh (Fig 2l) | modulus match | corr 1.0<!--{nonunitary.modulus_corr}-->, err 7.8e-16<!--{nonunitary.max_abs_err}--> | sim |
| Non-unitary input/output correlation (Fig 2n) | measured on chip | not reproduced | hardware — not reproduced |
| Iris unitary NN, full set (Fig 2o,p) | 94.67% offline (evaluation set not stated) | **95.47%<!--{iris.seed_sweep.full_acc_mean}--> ± 1.26%<!--{iris.seed_sweep.full_acc_std}-->** (10 seeds) | sim |
| Iris unitary NN, held out | — (paper's 93.33% is on-chip) | 89.33%<!--{iris.seed_sweep.test_acc_mean}--> ± 5.14%<!--{iris.seed_sweep.test_acc_std}--> (10 seeds) | sim |
| Iris identity control (unitary frozen to I) | — | 85.60%<!--{iris.identity_control.full_acc_mean}--> ± 0.44%<!--{iris.identity_control.full_acc_std}--> full set, 81.56%<!--{iris.identity_control.test_acc_mean}--> ± 4.67%<!--{iris.identity_control.test_acc_std}--> held out | control |
| Iris logistic baseline (same 4 features, same splits) | — | 96.53%<!--{iris.logistic_baseline.full_acc_mean}--> ± 0.88%<!--{iris.logistic_baseline.full_acc_std}--> full set, 94.89%<!--{iris.logistic_baseline.test_acc_mean}--> ± 3.45%<!--{iris.logistic_baseline.test_acc_std}--> held out | control |
| On-chip latency | ~60 ps | n_g·L/c = **60.0<!--{latency_on_chip_ps}--> ps** | exact |
| Energy | **1.875 pJ/MAC** | 1.8<!--{throughput_energy.P_total_W}--> W / 0.96 TMAC·s⁻¹ = **1.875<!--{throughput_energy.energy_pj_per_mac}-->**. 3 V, 100 Ω, 90<!--{throughput_energy.P_pi_mW}--> mW heater parameters and the 96-operation count are taken from Supplementary Note 3 and cannot be checked from the main article. | consistency check |
| Throughput | **1.92 TOPS** | 96 ops × 2 dir × 10 GBaud = **1.92<!--{throughput_energy.tops}-->**. 3 V, 100 Ω, 90<!--{throughput_energy.P_pi_mW}--> mW heater parameters and the 96-operation count are taken from Supplementary Note 3 and cannot be checked from the main article. | consistency check |
| Switch crosstalk (Fig 4d,e) | −45 to <−20 dB | cross state, mesh model fitted to Fig 4d: -27.2<!--{switching.cross_xtalk_center_db[1]}--> to -21.1<!--{switching.cross_xtalk_center_db[0]}--> dB at 1560 nm; worst -16.8<!--{switching.cross_worst_xtalk_fitrange_db}--> dB over the fitted 1549–1565 nm, -11.8<!--{switching.cross_worst_xtalk_extrapolated_db}--> dB extrapolated over 1530–1549 nm. Bar state: -106.7<!--{switching.bar_xtalk_center_db[1]}--> to -30.5<!--{switching.bar_xtalk_center_db[0]}--> dB at 1560 nm from an **assumed** coupler-split spread of **0.02<!--{cross_check.sigma_split}-->**; the digitized Fig 4e curve was fitted for that spread and the fit was **not adopted**, because the model does no better on those points than a constant and the result ranges over a factor of 4.6<!--{fig4e_fit.sensitivity.sigma_split_range_factor}--> with a choice the figure does not fix (report §6.1). The arm-phase spread is assumed too | model vs measurement |
| Bar-state insertion loss, per path (Fig 4e diagonals) | four digitized bar-state through paths, -1.48<!--{switching.bar_il_vs_fig4e.per_port[3].digitized_db}--> to -2.43<!--{switching.bar_il_vs_fig4e.per_port[0].digitized_db}--> dB over 1550<!--{switching.bar_il_vs_fig4e.band_nm[0]}-->–1574<!--{switching.bar_il_vs_fig4e.band_nm[1]}--> nm | model optimistic by **+0.38<!--{switching.bar_il_vs_fig4e.mean_signed_diff_db}--> dB** on average (**0.49<!--{switching.bar_il_vs_fig4e.mean_abs_diff_db}--> dB** absolute); port-to-port ordering **not** reproduced | model vs measurement |
| On-chip insertion loss | −1.85<!--{switching.onchip_il_paper_range_db[1]}--> to −2.99<!--{switching.onchip_il_paper_range_db[0]}--> dB (8 paths) | **-1.40<!--{switching.onchip_il_max_db}--> to -1.80<!--{switching.onchip_il_min_db}--> dB** (8 modelled paths) | model vs measurement |
| PUF uniqueness, feed-forward mesh (Fig 5) | **49.97%<!--{ppuf_recirc.vs_feedforward.paired_uniqueness.paper_uniqueness}-->** | **49.00%<!--{ppuf.population_sweep.uniqueness_mean}--> ± 0.34%<!--{ppuf.population_sweep.uniqueness_std}-->** over 10<!--{ppuf.population_sweep.n_seeds}--> population seeds | sim |
| PUF uniformity, feed-forward mesh (Fig 5) | **50.15%** | **50.32%<!--{ppuf.population_sweep.uniformity_mean}--> ± 0.51%<!--{ppuf.population_sweep.uniformity_std}-->** over 10 seeds | sim |
| PUF uniqueness, recirculating mesh | **49.97%<!--{ppuf_recirc.vs_feedforward.paired_uniqueness.paper_uniqueness}-->** | **49.89%<!--{ppuf_recirc.C4_FREE_1.population_sweep.uniqueness_mean}--> ± 0.25%<!--{ppuf_recirc.C4_FREE_1.population_sweep.uniqueness_std}-->** / **49.93%<!--{ppuf_recirc.C4_FREE_2.population_sweep.uniqueness_mean}--> ± 0.28%<!--{ppuf_recirc.C4_FREE_2.population_sweep.uniqueness_std}-->** (two stated wirings, 10 seeds) | sim |
| PUF uniformity, recirculating mesh | **50.15%** | **50.01%<!--{ppuf_recirc.C4_FREE_1.population_sweep.uniformity_mean}--> ± 0.88%<!--{ppuf_recirc.C4_FREE_1.population_sweep.uniformity_std}-->** / **49.88%<!--{ppuf_recirc.C4_FREE_2.population_sweep.uniformity_mean}--> ± 0.94%<!--{ppuf_recirc.C4_FREE_2.population_sweep.uniformity_std}-->** (two stated wirings) | sim |
| Recirculating-mesh solver | — | ring/add-drop match analytic to **1e-15** | sim |

The energy and throughput rows use the paper's **own derivation** (Supplementary Note 3),
not a guessed op-count — see [`docs/REPRODUCTION_REPORT_v10.md`](docs/REPRODUCTION_REPORT_v10.md) §6.

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
| `lightin/square_mesh.py` | Fig 1, Methods | 4×4 square recirculating mesh: 25 vertices, 40 cells, 20 optical ports |
| `lightin/wiring_search.py` | — | searches the half-turn-invariant vertex wirings and selects two |
| `lightin/ppuf_recirc.py` | Fig 5 | the PUF on the recirculating mesh, challenge applied per rotational orbit |
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
├── lightin/                          the package (15 modules)
├── scripts/
│   ├── run_all.py                    run every module, write results.json + figures/
│   ├── fit_fig4.py                   fit the coupler to the digitized Fig 4d crosstalk
│   └── fit_fig4e.py                  fit the bar-state spread to the digitized Fig 4e crosstalk
├── tests/
│   ├── test_reproduction.py             55 checks (pytest or standalone)
│   ├── test_report_consistency.py       5 checks: the report and README against results.json
│   ├── test_constants_documented.py     2 checks: the §6.3 parameter table against the modules
│   ├── test_source_lines_documented.py  2 checks: the §6.3 file:line citations against those files
│   ├── test_transcriptions_agree.py     3 checks: values the code records in more than one place
│   ├── test_probe_stability.py          4 checks: the probes report_environment.py prints in CI
│   ├── test_restart_degeneracy.py       3 checks: the stored Iris restart table against a fresh fit
│   └── test_iris_fit_deterministic.py   2 checks: the seed-0 Iris fit repeated in one process
├── data/
│   ├── fig4d_T20_digitized.csv       colour-digitized cross-state crosstalk (with provenance header)
│   ├── fig4e_bar_digitized.csv       colour-digitized bar-state crosstalk (with provenance header)
│   └── fig4e_diagonal_digitized.csv  colour-digitized bar-state through paths T00/T11/T22/T33
├── .github/
│   └── workflows/tests.yml           CI: the test suite on Python 3.11, 3.12 and 3.13
├── figures/                          11 generated figures (regenerated by run_all.py)
└── docs/
    ├── REPRODUCTION_REPORT_v10.md    full scope map, per-result table, parameter provenance
    ├── REPRODUCTION_REPORT_v9.md     the previous report
    ├── REPRODUCTION_REPORT_v8.md     the report before that
    ├── REPRODUCTION_REPORT_v7.md     earlier reports, kept for history
    ├── REPRODUCTION_REPORT_v6.md
    ├── REPRODUCTION_REPORT_v5.md
    ├── REPRODUCTION_REPORT_v4.md
    ├── REPRODUCTION_REPORT_v3.md
    ├── REPRODUCTION_REPORT_v2.md
    ├── REPRODUCTION_REPORT.md        the first-pass report
    ├── PREPRINT_NOTES.md             details taken from the arXiv preprint, and where it differs
    ├── FIG4E_SCOPE.md                the plan that the Fig 4e digitization followed
    ├── REPORT_UNCHECKED.md           report and README numbers outside the consistency test
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

**Fit the coupler to the chip's measured crosstalk** (digitized Fig 4d and Fig 4e):

```bash
python scripts/fit_fig4.py       # → mesh fit λ₀=1574.2 nm, slope=0.00264 rad/nm, floor -26.2 dB, RMS 0.79 dB; writes figures/fig4_digitized.png
python scripts/fit_fig4e.py      # → bar-state coupler-split spread fitted at 0.0182 (range 0.0152-0.0707) and NOT adopted; writes figures/fig4e_digitized.png
```

**Tests:**

```bash
pytest -q
# or, to run the main verification file by itself, without the pytest runner
# (it still imports pytest, for one approx comparison and one raises check):
PYTHONPATH=. python tests/test_reproduction.py
```

Every number in the headline table above, and in
[`docs/REPRODUCTION_REPORT_v10.md`](docs/REPRODUCTION_REPORT_v10.md), that comes from
`results.json` carries its path in an HTML comment that GitHub does not render, and
`tests/test_report_consistency.py` checks all of them against the file on every run; a path
may add `|pct` where the document writes a fraction as percentage points, or `|abs` where it
carries a sign in words. The parameter table in the report's §6.3 is checked the same way
against the modules rather than against `results.json`, by
`tests/test_constants_documented.py`, since those are the constants the model was given
rather than anything it produced. The numbers left outside both checks — the paper's own
values, default arguments and inline literals, arithmetic on other values — are listed with
their provenance in [`docs/REPORT_UNCHECKED.md`](docs/REPORT_UNCHECKED.md).

---

## Parameter provenance (chip-grounded)

The chip parameters below were taken from the paper's Methods and Supplementary
(details in [`docs/REPRODUCTION_REPORT_v10.md`](docs/REPRODUCTION_REPORT_v10.md) §6). The
parameters that are not from the paper, with their sources where recorded, are listed in
docs/REPRODUCTION_REPORT_v10.md §6.3:

- group index **n_g = 4.0<!--[lightin.coupler.N_GROUP]-->** (stated); phase index **n_eff ≈ 2.36<!--[lightin.coupler.N_EFF]-->** (450<!--[lightin.coupler.WG_WIDTH_NM]-->×220 nm SOI TE)
- directional coupler **11.5<!--[lightin.coupler.DC_LENGTH_UM]--> µm long, 200<!--[lightin.coupler.DC_GAP_NM]--> nm gap**; square-mesh unit **500<!--[lightin.coupler.SQUARE_SIDE_UM]--> µm**; arm **208<!--[lightin.coupler.ARM_LENGTH_UM]--> µm**
- heater **3 V for π across 100 Ω → 90 mW**, E[θ]=π/2 → **45 mW/MZI**, ×40 → **1.8 W**
- PUF arm-length spread **N(−0.08 µm, 0.11 µm)** → phase N(−0.76, 1.05) rad via n_eff
  (the sign is the preprint's; see docs/PREPRINT_NOTES.md)
- coupler dispersion **fitted to the digitized Fig 4d crosstalk** (`scripts/fit_fig4.py`)
- bar-state coupler-split spread **assumed at 0.02<!--[lightin.switching.SIGMA_SPLIT]-->**, not fitted: the digitized Fig 4e
  crosstalk was fitted for it (`scripts/fit_fig4e.py`) and the fitted value was **not
  adopted**, the model doing no better on those points than a constant and the result
  ranging from **0.0152<!--{fig4e_fit.sensitivity.sigma_split_full_range[0]}--> to 0.0707<!--{fig4e_fit.sensitivity.sigma_split_full_range[1]}-->** with a choice the figure does not fix. 0.02<!--{cross_check.sigma_split}-->
  falls inside that range, so the panel is a consistency check rather than a source. The
  arm-phase spread is assumed for the same reason one curve cannot separate the two

The superseded document search list is kept for history only; current parameter
provenance is in docs/REPRODUCTION_REPORT_v10.md §6.

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
  [`docs/REPRODUCTION_REPORT_v10.md`](docs/REPRODUCTION_REPORT_v10.md) §6.3. The superseded
  document search list is kept for history only; current parameter provenance is in
  docs/REPRODUCTION_REPORT_v10.md §6.

## License

Apache-2.0 — see [`LICENSE`](LICENSE). This is an independent reproduction; it is not
affiliated with or endorsed by the original authors.
