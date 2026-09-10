# LightIN — reproduction report

Paper: Zhu *et al.*, "LightIN: a versatile silicon-integrated photonic FPGA…",
*Light: Science & Applications* 15:165 (2026).

This report states exactly what was reproduced, how faithfully, and what could not be
reproduced from a published paper. All "reproduced" numbers below are emitted by
`scripts/run_all.py` (see `results.json`); paper numbers are quoted for comparison only.

---

## 1. What "reproduce" can mean here

The paper combines (a) a **fabricated** SOI photonic chip (40 PUCs, 4×4 square
recirculating mesh), (b) a software configuration framework, and (c) experimental
demonstrations. From a PDF one can reproduce two of the three buckets:

* **Bucket A — definitions & arithmetic.** Exactly reproducible (the PUC matrix, the
  effective-bit formula, propagation latency, the energy budget).
* **Bucket B — simulations the paper itself ran.** Reproducible by re-implementing them
  (unitary/non-unitary realisation, the offline-trained Iris network, the 100-die PUF
  statistics, the differentiator principle, the switch topology/crosstalk model).
* **Bucket C — physical measurements.** *Not* reproducible without the chip
  (measured eye-diagram SNR/Q, measured crosstalk spectra, 2-die experimental PUF).

Nothing in bucket C is fabricated here; those rows are marked **hardware-only**.

---

## 2. Results: paper vs this reproduction

| # | Result (figure) | Paper value | This reproduction | Tier |
|---|---|---|---|---|
| 1 | PUC unitarity / cross-bar (Eq. 1) | unitary, cross & bar states | unitarity err ≤ 1e-32; cross/bar correct | **A exact** |
| 2 | 4×4 permutation matrices (Fig. 2d) | realised by routing | fidelity = 1.000000 | **A exact** |
| 3 | 4×4 random unitaries (Fig. 2h,i) | high-fidelity realisation | fidelity = 1.000000, \|·\| corr = 1.000000 | **B** |
| 4 | Unitary effective bits @10 GBaud (Fig. 2f) | σ=0.0269 → **6.22 bit** | log₂(2/0.0269) = **6.216 bit** | **A exact** |
| 5 | Non-unitary 3×3 (Fig. 2l,n) | modulus agreement | \|·\| corr = 1.000000, max err 5.6e-16 | **B** |
| 6 | Non-unitary effective bits (Fig. 2f) | σ=0.0453 → **5.47 bit** | log₂(2/0.0453) = **5.464 bit** | **A exact** |
| 7 | Iris classification (Fig. 2o,p) | 94.67% offline / 93.33% on-chip | **95.24% offline train, 94.67% full-set** | **B** (offline) |
| 8 | On-chip latency | ~60 ps on-chip | n_g·L/c = **60.0 ps** (4.5 mm, n_g=4) | **A exact** |
| 9 | Throughput | **1.92 TOPS** | 1.92 TOPS (complex+bidir conv.); 0.32 TOPS (real-op) | **A** (convention) |
| 10 | Energy | **1.875 pJ/MAC** | 0.30 W / 1.6e11 MAC·s⁻¹ = **1.875 pJ/MAC** | **A exact** |
| 11 | MRM locking (Fig. 3c) | monitoring peaks at high-ER lock | monitoring peak at lock bias; ER 0→18.5 dB | **B** (model) |
| 12 | Eye-diagram SNR / Q (Fig. 3d–f) | ~17–18 dB SNR, Q ~7–8 | illustrative model eye only | **C hardware-only** |
| 13 | Switch crosstalk @1550 nm (Fig. 4d,e) | −45 to <−20 dB | CMT model: −42 to −30 dB (cross), to −30 dB (bar) | **B** (physical) |
| 14 | Switch crosstalk over band | <−15/−20 dB over >20 nm | CMT model: ≤ −15 dB over C-band edges | **B** (physical) |
| 15 | Switch insertion loss | ~2–3 dB on-chip | on-chip **1.6 dB**; fibre-to-fibre ~10 dB (grating-dominated) | **A/B** |
| 16 | Measured switch spectra (Fig. 4d,e) | measured curves | not reproduced (model curves only) | **C hardware-only** |
| 17 | PUF uniqueness, 100 dies (Fig. 5) | **49.97%** (simulation) | **49.95%** | **B** |
| 18 | PUF uniformity, 100 dies (Fig. 5) | **50.15%** (simulation) | **50.72%** | **B** |
| 19 | PUF reliability | 2.55% intra-die HD (experimental) | 0.84% (model, clean noise) | **B** (model) |
| 20 | PUF experimental 2-die (57.71/42.33/2.55%) | measured | not reproduced | **C hardware-only** |

Figures for rows 3, 5, 7, 11, 13, 17 are in `figures/`.

---

## 3. Notes on the modelling choices

**Unitary mesh (rows 2–4).** Permutations are realised exactly by cross/bar routing.
Arbitrary unitaries are realised on a universal Clements rectangular mesh of 2-DOF MZIs;
the programming phases are *fitted*, then the realised matrix is rebuilt independently
from the physical MZI matrices, so fidelity = 1 is a genuine check. The paper's physical
single-θ PUC (Eq. 1) has only one DOF per cell and therefore limited unitary
expressivity — explicitly acknowledged in the paper's Discussion (it proposes adding
phase shifters for "arbitrary unitary transformations"). This is why the chip
demonstrates specific/realisable matrices plus an adjoint tuning step.

**Effective bits (rows 4, 6).** The paper's 6.22 and 5.47 bit follow exactly from
ENOB = log₂(range/σ) with range = 2 (outputs in [−1, 1]). Both numbers reproduce to two
decimals, which also confirms the convention.

**Iris (row 7).** The photonic layer is a trainable 4×4 unitary; the four detected
intensities feed a small learned linear readout (standard for photonic classifiers and
consistent with the paper's *offline* training). The reproduced offline accuracy
(95.24% train / 94.67% full set) and the confusion matrix match the paper in character
(diagonal ≈ 92/98/94% vs paper 94/98/88%). The 93.33% *on-chip* number is a hardware
measurement and is not reproducible; our held-out split happens to land at 93.33%, but
that is a different quantity (offline test split, not on-chip).

**Throughput (row 9).** 0.32 TOPS uses a real-op count (1 MAC = 2 ops, N=4, 10 GBaud).
The paper's 1.92 TOPS is 6× larger, consistent with counting a complex MAC and the
mesh's bidirectional operation; the exact convention is not spelled out in the paper, so
both are reported.

**Energy (row 10).** Reproduces exactly under the stated assumption of ~0.30 W total
static thermo-optic power (≈6 active phase shifters at ~50 mW) and a 4×4 MAC rate at
10 GBaud.

**MRM locking (rows 11–12).** The monitoring signal ∝ |E₁−E₀|² peaks at the
high-extinction-ratio bias, reproducing the locking principle and the Fig. 3c shape. The
absolute eye SNR/Q come from the fabricated MRM + link and are hardware-only; the eye
plot here is an explicitly-labelled model.

**Switching (rows 13–16).** The 4-stage planar (Spanke-Beneš) topology is the rectangular
mesh of nearest-neighbour 2×2 switches. Crosstalk and loss are now produced by the
coupled-mode-theory coupler of §4.2 (literature-grounded dispersion + loss, two
independently-fabricated couplers per MZI) rather than a hand-set slope; the central and
in-band crosstalk and the ~1.6 dB on-chip loss match the paper. The *measured* spectra
depend on the real couplers and are hardware-only.

**PUF (rows 17–20).** Directly reproducible because the paper's 100-die numbers are
themselves a simulation. We model an 8-mode mesh of the paper's single-θ PUCs; rotational
symmetry is captured by routing the two diagonal injections through the same per-die
errors in rotated order, so the error-free response ties and each bit is decided purely
by manufacturing variation. This yields uniqueness 49.95% (paper 49.97%) and uniformity
50.72% (paper 50.15%). The 2-die experimental numbers are hardware-only.

---

## 4. Physics extensions (beyond the first-pass models)

Two modules push the reproduction from "matches the numbers" toward "matches the
physics".

### 4.1 Single-θ PUC expressivity (`expressivity.py`) — paper Discussion, made explicit

The paper's PUC (Eq. 1) has one thermo-optic phase shifter, so one DOF per cell. A
universal N-mode interferometer needs N² real DOF; a rectangular mesh of single-θ cells
supplies only N(N−1)/2. For N=4 that is **6 DOF inside the 16-dimensional U(4)**.

| Architecture | DOF (N=4) | Best-fit fidelity to Haar U(4) (mean / min / max) |
|---|---|---|
| single-θ (Eq. 1 chip) | 6 | **0.561 / 0.421 / 0.811** |
| single-θ + output phases | 10 | 0.826 / 0.722 / 0.940 |
| 2-DOF MZI (universal) | 16 | **1.000 / 1.000 / 1.000** |

So a bare single-θ mesh *cannot* represent an arbitrary unitary — it reaches barely
over half fidelity on average. Universality returns only with the full 2-DOF mesh
(the paper's proposed "three additional phase shifters per MZI"). What single-θ meshes
**can** do exactly: route any **permutation** (routing fidelity 1.000 for both Fig. 2d
permutations) and realise any unitary that was itself **generated** by such a mesh
(recovered to fidelity 1.000). This is exactly why the paper demonstrates permutations
and "randomly generated unitary matrices that can be represented by the chip", and uses
in-situ/adjoint tuning rather than open-loop decomposition. (Figure: `expressivity.png`.)

A second, distinct limit — **arm/coupler imbalance** — caps the single-θ cross-state
fidelity at **1.000 at the 3-dB wavelength, falling to ~0.975 at the C-band edge**, using
the dispersive coupler below.

### 4.2 Coupled-mode-theory coupler with real dispersion (`coupler.py`)

The first-pass switch used a lossless coupler with a hand-set crosstalk slope. It is now
a CMT directional-coupler model parameterised from measured silicon-photonics values:

* strip-waveguide propagation loss ~2 dB/cm (2.14 dB/cm; 2.2 ± 0.8 dB/cm over 19 dies);
* grating-coupler loss ~4.4 dB with ~45 nm 1.5-dB bandwidth, peak ~1545 nm;
* directional-coupler power coupling that **drifts with wavelength** (a 3-dB straight DC
  is 50:50 at one wavelength only; reported κ drifts ~0.60→0.82 over 1500–1600 nm for a
  100 nm gap), with the standard fit form K(λ)=sin²(κ′(λ)L+φ₀);
* DC excess loss ~0.1–0.8 dB.

Consequences that now *emerge from physics* rather than assumption:
* **Switch crosstalk** comes from the coupler dispersion + two independently-fabricated
  couplers per MZI: cross-state −42 to −30 dB at 1550 nm, degrading to ~−15 dB at the
  C-band edge; bar-state down to ~−30 dB (the balanced-MZI cancellation makes the bar
  state intrinsically cleaner). Matches the paper's −45 to <−20 dB / <−15–20 dB-over-20 nm.
* **Fibre-to-fibre loss budget ~10 dB** (grating-coupler dominated); on-chip ~1.6 dB,
  consistent with the paper's ~2–3 dB on-chip insertion loss.
* `fit_dc_dispersion()` recovers κ₀ and the dispersion slope from data (demo: κ₀=0.497
  vs 0.5, RMS 0.003) — ready to fit real measured coupler spectra. (Figure: `coupler.png`.)

Literature anchors: Optica jlt-35-22-4916; arXiv:2302.13177, 2111.01792, 1203.0767;
Ghent pub_4030; nanoph-2023-0836; US 9,445,165.

### 4.3 Full square *recirculating* mesh with feedback (`recirculating.py`)

The matrix-multiplication results use a *feedforward* rectangular sub-mesh (a product of
MZI layers, §2–3). The chip's full 4×4 square mesh is **recirculating**: light returns
through closed loops, so the response is no longer a finite product — it is a rational
transfer function with **poles** (resonances). This needs a different solver.

A scattering-matrix network (SMN) is implemented: each PUC is a reciprocal 4-port; the
steady-state field with all feedback paths is `o = (I − S·C)⁻¹ S·b`. Validation and
results (all from running the code):

* **All-pass ring**: SMN through-port spectrum matches the analytic
  (r − a e^{−jφ})/(1 − r a e^{−jφ}) to **RMS 2.8×10⁻¹⁶**.
* **Add-drop ring**: drop-port spectrum matches the analytic Lorentzian to **1.0×10⁻¹⁵**.
* **Genuine 2D square-loop plaquette** (4 PUCs on the four sides of one square loop, 4
  access buses): the lossless external scattering matrix is **unitary to 1.6×10⁻¹⁵** across
  wavelength and random PUC settings — i.e. energy is conserved, which proves the 2D
  wiring is correct.
* **Scaling**: a **40-PUC recirculating mesh** (matching the chip's PUC count, 40 single-θ
  DOF) solves and conserves energy to **5.6×10⁻¹⁵**.
* **Expressivity jump**: a feedforward MZI is spectrally flat (FIR, zeros only); a
  recirculating ring shows deep periodic resonances (IIR, poles). With the same PUCs, the
  recirculating mesh implements a **strictly larger function class** — resonators, lattice
  filters, delay lines — not just a fixed unitary. A 6-ring bus demonstrates a programmable
  multi-notch response. (Figure: `recirculating.png`.)

This complements §4.1: the feedforward mesh's expressivity is DOF-limited (6 for single-θ),
while recirculation adds an orthogonal axis of capability (poles/feedback) that the
feedforward analysis cannot capture. The exact LightIN 40-PUC interconnect is not published,
so the 2D demonstrations use canonical, individually-validated recirculating cells; the SMN
engine itself handles arbitrary square-mesh topologies.

---

## 5. Bottom line

Of the paper's headline quantitative claims, the bucket-A items (PUC, 6.22/5.47-bit,
60 ps latency, 1.875 pJ/MAC) reproduce **exactly**; the bucket-B simulations
(unitary/non-unitary fidelity, Iris ~94.67%, PUF 49.95%/50.72%, differentiator and
switching behaviour) reproduce **closely and on independent code**. The bucket-C items
are physical measurements and are left unreproduced rather than fabricated.

The three physics extensions (§4) make the model mechanistic rather than descriptive: the
**single-θ expressivity limit** is quantified (0.56 mean fidelity to arbitrary U(4),
rising to 1.0 only with the full 2-DOF mesh), explaining the paper's choice of matrix
classes; the **switch crosstalk/loss now emerge from a literature-grounded coupled-mode-
theory coupler** with real SOI dispersion, fittable to measured data; and the **full
recirculating mesh** is solved with a feedback-capable scattering-matrix network (validated
to ~1e-15 against analytic rings and by energy conservation), showing how feedback adds
poles and a strictly larger function class than the feedforward sub-mesh.

One thing deliberately *not* done: digitising Fig. 4d/e to fit the coupler model to the
chip's measured spectra. The figure data is not available here, and inventing points would
violate the no-fabrication rule the whole reproduction follows. `fit_dc_dispersion()` is
ready to run the moment real (wavelength, coupling) data exists.

---

## 6. Parameters now grounded in the paper (after receiving the documents)

The paper (`s41377-026-02209-5`) + supplementary (`MOESM1_ESM.docx`) supplied the chip-
specific values that were previously assumed. All of the following are now sourced from
the paper, not estimated:

| Quantity | Paper value (Methods / Supp) | Used in |
|---|---|---|
| Group index n_g | 4.0 (stated) | latency (60 ps) ✓ |
| Phase index n_eff | ~2.36 (450×220 nm SOI TE, geometry) — **fixes a prior bug** (had 4.0 for phase) | recirculating, PPUF |
| Directional coupler | length 11.5 µm, gap 200 nm, 450 nm width | coupler geometry |
| Square-mesh unit side | 500 µm | recirculating loop length |
| MZI arm length | 208 µm | mesh segments |
| Heater | 100 µm, **3 V for π across 100 Ω → 90 mW**, E[θ]=π/2 | energy |
| Energy derivation | 40 MZIs × 45 mW = 1.8 W ÷ 0.96 TMAC/s = **1.875 pJ/MAC** | throughput.py (now exact) |
| Throughput convention | (complex 4×4 × real 4×1 + PD squared-add) × 2 dir × 10 GBaud = **1.92 TOPS** | throughput.py (now exact) |
| PUF arm-length spread | **N(μ=0.08 µm, σ=0.11 µm)** → phase N(0.76, 1.05) rad via n_eff | ppuf.py (now exact dist.) |
| PUF experimental (2 dies) | inter-die 57.71%, uniformity 42.62%, intra-die HD 2.55% | ppuf targets |
| PUF simulation (100 dies) | uniqueness 49.97%, uniformity 50.15% | ppuf (reproduced 50.02 / 49.91) |
| Switch crosstalk | −45 to <−20 dB @1560 nm; <−15/−20 dB over >20 nm | switching ✓ |
| On-chip insertion loss | −1.85 to −2.99 dB (8 measured paths) | loss budget |
| Design wavelengths | 1560 nm (matrix), 1555 nm (MRM) | all modules |
| MRM eye SNR / Q | 17.10 & 17.83 dB; Q 7.17–8.08 | mrm (hardware-only, now with exact targets) |

The two **exact-derivation upgrades** matter most: energy and throughput were previously
reproduced by a coincidentally-correct arithmetic; they are now the paper's own
derivation (3 V / 100 Ω / 90 mW / E[θ]=π/2 / 40 MZIs / 1.8 W and the explicit op count).

### 6.1 Fig 4d digitized and the coupler dispersion fitted to it

The original blocked task — fit the coupler to the chip's measured crosstalk — is now
done. The all-cross-state T20 crosstalk curve was colour-digitized from Fig 4d
(`data/fig4d_T20_digitized.csv`; dB scale anchored to figure-read endpoints, ~±2 dB) and
the CMT model fitted with `scripts/fit_fig4.py`:

* coupler 3-dB (minimum-crosstalk) wavelength **λ₀ = 1571 nm**
* dispersion slope **0.0029 rad/nm** (the prior literature default was 0.004 — same order;
  the chip's couplers are slightly less dispersive)
* crosstalk floor −25.2 dB, **fit RMS = 1.05 dB** (within the digitization uncertainty)

This fitted slope is now the default in `coupler.py`, so the switch crosstalk model is
grounded in the chip's own measured data (Figure: `figures/fig4_digitized.png`). A precise
per-point digitization of the other three overlapping curves in each panel is noise-limited,
so only the cleanest curve (T20) was extracted; the geometry (11.5 µm, 200 nm gap) anchors
the rest.

### 6.2 What is still genuinely unavailable

* Measured eye-diagram SNR/Q (now known: 17.10/17.83 dB, Q 7.17–8.08) remain
  **hardware-only** — they are link measurements, not reproducible in simulation, though
  the model's locking principle and the exact target values are both confirmed.
* The MRM ring radius / FSR (self-developed MRM, ref 62) is not tabulated; the MRM model
  stays qualitative but now uses the real 0.1 ns differentiator delay and 1555 nm carrier.
* Table SI 2 PDK sub-values (per-ADC loss, edge-coupler loss) are inside equation objects
  that did not extract cleanly; they drive only the 32×32 / 64×64 scaling projection, not
  the 4×4 results, which use the directly-stated measured path losses.
