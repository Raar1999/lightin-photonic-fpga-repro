# LightIN — reproduction report

Paper: Zhu *et al.*, "LightIN: a versatile silicon-integrated photonic FPGA…",
*Light: Science & Applications* 15:165 (2026).

This report states exactly what was reproduced, how faithfully, and what could not be
reproduced. Every value in the "This reproduction" columns is read from `results.json` as
emitted by `scripts/run_all.py`; nothing is transcribed from an earlier draft. Values in
the "Paper value" columns are the paper's own, quoted from its Methods and Supplementary
Note 3 for comparison only — they are not outputs of this code and do not appear in
`results.json`. The few diagnostics computed outside `results.json` are labelled where
they appear.

The supplementary file (MOESM1_ESM.docx) is not distributed with this repository, so
values attributed to it can be checked only against a copy of the supplementary.

`results.json` was generated on Python 3.11.9, Windows-10-10.0.26200-SP0, with numpy
2.4.4, scipy 1.17.1, scikit-learn 1.9.0 and matplotlib 3.11.1 (the `environment` block;
`requirements-lock.txt` pins those versions plus pytest 9.1.1). The Iris accuracies move
slightly with the scipy and scikit-learn versions, so they are only reproducible against
the versions recorded there.

---

## 1. What "reproduce" can mean here

The paper combines (a) a fabricated SOI photonic chip (40 PUCs, 4×4 square recirculating
mesh), (b) a software configuration framework, and (c) experimental demonstrations. Two of
the three buckets can be reproduced without the chip:

* Bucket A — definitions and arithmetic. Exactly reproducible (the PUC matrix, the
  effective-bit formula, propagation latency).
* Bucket B — simulations the paper itself ran. Reproducible by re-implementing them
  (unitary/non-unitary realisation, the offline-trained Iris network, the 100-die PUF
  statistics, the differentiator principle, the switch topology/crosstalk model).
* Bucket C — physical measurements. Not reproducible without the chip (measured
  eye-diagram SNR/Q, measured crosstalk spectra, the measured non-unitary input/output
  correlation of Fig. 2n, the 2-die experimental PUF).

Nothing in bucket C is fabricated here; those rows are marked hardware — not reproduced.

A third label is used for the energy and throughput rows: consistency check. Those numbers
reproduce arithmetically, but every input to the arithmetic comes from Supplementary
Note 3 rather than from anything this code can verify, so a match confirms the derivation,
not the device.

The design wavelength is 1560 nm throughout (matrix multiplication, coupler, switch);
1555 nm is the micro-ring locking experiment and 1545 nm the grating-coupler peak.

---

## 2. Results: paper vs this reproduction

| # | Result (figure) | Paper value | This reproduction | Tier |
|---|---|---|---|---|
| 1 | PUC unitarity / cross-bar (Eq. 1) | unitary, cross & bar states | unitarity err ≤ 1e-32 (test assertion, computed outside `results.json`); cross/bar correct | **A exact** |
| 2 | 4×4 permutation matrices (Fig. 2d) | realised by routing | routing fidelity **0.999999999999** (both) | **B** |
| 3 | 4×4 random unitaries (Fig. 2h,i) | high-fidelity realisation | fidelity **1.000000**, \|·\| corr **1.000000** (ideal couplers) | **B** |
| 4 | Unitary effective bits @10 GBaud (Fig. 2f) | σ=0.0269 → **6.22 bit** | log₂(2/0.0269) = **6.2163 bit** | **A exact** |
| 5 | Non-unitary 3×3 mesh (Fig. 2l) | modulus agreement | \|·\| corr **1.000000**, max err **7.8e-16** (ideal couplers) | **B** |
| 6 | Non-unitary input/output correlation (Fig. 2n) | measured on chip | not reproduced | **hardware — not reproduced** |
| 7 | Non-unitary effective bits (Fig. 2f) | σ=0.0453 → **5.47 bit** | log₂(2/0.0453) = **5.4643 bit** | **A exact** |
| 8 | Iris classification, full set (Fig. 2o,p) | **94.67%** offline | **95.47% ± 1.26%** over 10 seeds | **B** |
| 9 | Iris classification, held out | 93.33% on-chip (hardware) | **89.33% ± 5.14%** over 10 seeds | **B** |
| 10 | Iris identity control | — | **85.60% ± 0.44%** full set, **81.56% ± 4.67%** held out | control |
| 11 | Iris logistic baseline | — | **96.53% ± 0.88%** full set, **94.89% ± 3.45%** held out | control |
| 12 | On-chip latency | ~60 ps | n_g·L/c = **60.04 ps** (4.5 mm, n_g=4) | **A exact** |
| 13 | Throughput | **1.92 TOPS** | **1.92 TOPS** from the Supp Note 3 op count | **consistency check** |
| 14 | Energy | **1.875 pJ/MAC** | 1.8 W ÷ 9.6e11 MAC·s⁻¹ = **1.875 pJ/MAC** | **consistency check** |
| 15 | MRM locking (Fig. 3c) | monitoring peaks at high-ER lock | monitoring peak at bias **−0.448**; ER up to **18.46 dB** | **B** (model) |
| 16 | Eye-diagram SNR / Q (Fig. 3d–f) | ~17–18 dB SNR, Q ~7–8 | illustrative model eye only | **hardware — not reproduced** |
| 17 | Switch crosstalk at 1560 nm (Fig. 4d,e) | −45 to <−20 dB | cross **−27.16 to −21.06 dB**; bar **−106.67 to −30.50 dB** | **B** (physical) |
| 18 | Switch crosstalk, worst inside the fitted range | <−15/−20 dB over >20 nm | cross **−16.77 dB** over 1549–1565 nm | **B** (physical) |
| 19 | Switch crosstalk, worst extrapolated below the data | <−15/−20 dB over >20 nm | cross **−11.80 dB** over 1530–1549 nm | **B** (model, extrapolated) |
| 20 | Mesh T20 model vs digitized Fig 4d | — | RMS **0.79 dB** over 25 points (single-coupler proxy **1.05 dB**) | **B** |
| 21 | Measured crosstalk spectra (Fig. 4d,e) | measured | not reproduced | **hardware — not reproduced** |
| 22 | On-chip insertion loss, 8 paths | **−1.85 to −2.99 dB** (8 measured paths) | **−1.40 to −1.80 dB** (8 modelled paths) | **B** |
| 23 | PUF uniqueness, 100 dies (Fig. 5) | **49.97%** (simulation) | **49.01%** | **B** |
| 24 | PUF uniformity, 100 dies (Fig. 5) | **50.15%** (simulation) | **50.12%** | **B** |
| 25 | PUF reliability | 2.55% intra-die HD (experimental) | **0.72%** at a measurement-noise σ of **0.01 rad** per MZI | **B** (model) |
| 26 | PUF experimental, 2 dies | 57.71% / 42.62% / 2.55% | not reproduced | **hardware — not reproduced** |
| 27 | Recirculating-mesh solver | — | ring **2.9e-16**, add-drop **8.4e-16** vs analytic | **B** |

Row 25 carries a model input as well as a model output. The measurement-noise standard
deviation is 0.01 rad per MZI (`measurement_noise_sigma`), and its source is recorded as
an assumed value, not taken from the paper (`measurement_noise_source`). The modelled
reliability scales with that value: a larger assumed noise flips more bits between
re-measurements and gives a larger intra-die Hamming distance, so 0.72% is a statement
about the assumption as much as about the mesh.

---

## 3. Notes on the modelling choices

Rows 2, 3 and 5 assume ideal 50:50 couplers. `lightin/puc.py` builds its universal 2-DOF
MZI from a wavelength-independent beamsplitter `(1/√2)[[1, i], [i, 1]]`, and `unitary.py`
and `nonunitary.py` are built on that block. The fidelities of 1.000000 in rows 3 and 5
are therefore statements about the mesh algebra — that a Clements decomposition and an
SVD/diamond realisation are implemented correctly — and not about what this chip's
couplers would achieve.

The coupler actually fitted to the chip's own Fig 4d data is 50:50 at 1574.7 nm, not at
the 1560 nm design wavelength (§6.1). At 1560 nm its power coupling is 0.462
(`coupler.power_coupling_at_1560`) rather than 0.500, and that imbalance alone caps the
fidelity of the single-θ cross state at 0.9942 (`coupler_ceiling_fidelity_at_1560`). Over
the 1530–1565 nm sweep (`coupler_ceiling_range_nm`) the ceiling falls as low as 0.9469
(`coupler_ceiling_min_fidelity`). Rows 3 and 5 should be read against that ceiling: the
ideal-coupler mesh reaches 1.000000, and a mesh built from the chip's own coupler would
not.

Unitary mesh (rows 2–4). Arbitrary unitaries are realised on a universal Clements
rectangular mesh of 2-DOF MZIs; the programming phases are fitted, then the realised
matrix is rebuilt independently from the physical MZI matrices, so fidelity = 1 is a
genuine check rather than a tautology. The permutations of Fig. 2d are treated the same
way: `_best_routing` optimises the single-θ mesh phases and reports the fraction of input
power that actually reaches each target port, giving 0.999999999999 for both. A
permutation matrix compared against itself would give 1 by construction and would test
nothing, so the routing optimisation is what makes row 2 a measurement.

The paper's physical single-θ PUC (Eq. 1) has one DOF per cell and therefore limited
unitary expressivity, acknowledged in the paper's Discussion and quantified in §4.1.

Effective bits (rows 4, 7). The paper's 6.22 and 5.47 bit follow from
ENOB = log₂(range/σ) with range = 2 (outputs in [−1, 1]). Both reproduce to two decimals,
which also confirms the convention.

Non-unitary (rows 5–6). The SVD/diamond realisation is checked by element-modulus
agreement: correlation 1.000000 and maximum absolute error 7.8e-16. That is the whole of
the simulation check. Fig. 2n is the chip's measured input/output correlation; comparing
the model's output vector against a copy of itself would return 1.0 while measuring
nothing, so no vector correlation is reported.

Iris (rows 8–11). The photonic layer is a trainable 4×4 unitary whose four detected
intensities feed a small learned linear readout, consistent with the paper's offline
training. Reporting a single seed is not defensible here: over 10 seeds (the seed drives
both the 70/30 stratified split and the 15 random restarts) the full-set accuracy is
95.47% ± 1.26% and the held-out accuracy 89.33% ± 5.14%. The paper's 94.67% sits
comfortably inside that spread, so agreement at one seed is not evidence of much.

Two controls put the number in context, both on the same splits:

* Identity control — the unitary frozen to I, only the readout trained: 85.60% ± 0.44%
  full set, 81.56% ± 4.67% held out. The programmable unitary is therefore worth about
  10 points, which is a real contribution.
* Logistic baseline — plain multinomial logistic regression on the same four standardized
  features: 96.53% ± 0.88% full set, 94.89% ± 3.45% held out. Because the two sweeps run
  the same seeds and the seed fixes the split, they can be differenced seed by seed
  (`paired_logistic_minus_photonic`). On the full set the logistic model is ahead by
  1.07 ± 1.30 points, winning on 7 of the 10 seeds, tying on 2 and losing on 1; the
  absolute paired mean is smaller than the paired standard deviation, so that difference
  is within the seed-to-seed spread. On the held-out split it is ahead by 5.56 ± 3.67
  points, winning on 9 seeds, tying on 1 and losing on none; there the absolute paired
  mean exceeds the paired standard deviation, so that is a consistent difference. The Iris
  demonstration shows that the mesh can be trained to classify; it does not show that the
  mesh classifies better than a multinomial logistic regression with 15 parameters (four
  weights for each of three classes, plus three biases).

The paper's 94.67% equals 142/150 and also 71/75, and its 93.33% equals 140/150, 70/75,
42/45 and 28/30. The published values therefore do not establish whether the paper
evaluated on all 150 samples or on a held-out subset. The full-set column is compared with
94.67% on the assumption that the paper evaluated on all 150 samples, and that assumption
is not established.

Energy and throughput (rows 13–14). Reported as consistency checks, not as reproductions.
The derivation is the paper's own: 40 PUCs, each biased at E[θ] = π/2 and so drawing on
average half of the 90 mW π-power, gives 45 mW per cell and 1.8 W across the 40 cells;
dividing by the 4×4 MAC rate of 9.6e11 MAC·s⁻¹ at 10 GBaud yields 1.875 pJ/MAC, and the
Supplementary op count gives 1.92 TOPS. The 3 V across 100 Ω, the 90 mW, and the
96-operation count all come from Supplementary Note 3 and cannot be checked against the
main article.

Switching (rows 17–22). The 4-stage planar (Spanke-Beneš) topology is a rectangular mesh
of nearest-neighbour 2×2 switches, with crosstalk and loss produced by the coupled-mode-
theory coupler of §4.2 rather than a hand-set slope. At 1560 nm the model gives
cross-state crosstalk of −27.16 to −21.06 dB and bar-state −106.67 to −30.50 dB, against
the paper's −45 to <−20 dB.

The worst case over wavelength is reported as two separate numbers, because only one of
them is backed by data:

| Range | Status | Worst cross-state crosstalk |
|---|---|---|
| **1549–1565 nm** | inside the wavelengths digitized from Fig 4d (1549–1587 nm) | **−16.77 dB** |
| **1530–1549 nm** | below every digitized point; model extrapolation | **−11.80 dB** |

Inside the fitted range, the model meets the −15 dB figure (worst −16.77 dB) but not the
−20 dB figure. These are predictions of a model constrained by one digitized port pair,
not measurements of the other port pairs. The digitized T20 curve itself reaches −14.1 dB
at 1549.0 nm, within its ±2 dB digitization uncertainty. (That −14.1 dB is read directly
from `data/fig4d_T20_digitized.csv` and is not a `results.json` value.) The extrapolated
number is 5.0 dB worse again, and it rests entirely on the model: no digitized point
exists below 1549 nm, so −11.80 dB is what the coupled-mode-theory coupler predicts when
run past the edge of its own fit, not something the chip's published data supports. It
should be read as a projection, and it is the pessimistic half of the band.

The mechanism in both ranges is the same: a single directional-coupler design is 3-dB at
only one wavelength (§4.2), and away from it the couplers are imbalanced and the switches
leak. Both states report 0 structural zeros (`cross_structural_zeros` and
`bar_structural_zeros`): no port pair was excluded from the crosstalk statistics for
carrying no power, so the numbers above are over every off-target path. A pair is counted
as a structural zero only when its raw linear transmission falls below 1e-20, and the test
is made on that raw power rather than on a decibel value, so no additive constant can
manufacture a floor. The lowest bar-state entry, input 0 to output 3, sits at a raw
transmission of 2.2e-11 (−106.67 dB); reaching that port takes three off-target couplings,
which is why it is so far below the rest and why it is nevertheless a real model
prediction rather than a numerical artefact.

The fitted crosstalk floor of −26.2 dB (`chip_crosstalk_floor_db`) is recorded in
`switching.py` as `FIG4D_FLOOR_DB` and is deliberately not added to any crosstalk this
module reports. Adding it would state a floor the mesh model does not predict. Its meaning
runs the other way: modelled crosstalk below −26.2 dB is not reached on the chip.

The on-chip insertion loss of row 22 is the transmission of each intended path through the
fabric alone, which carries the mesh's propagation and coupler excess losses and no
grating couplers. Over the eight intended paths — four inputs in the all-cross state and
four in the all-bar state — the model gives −1.40 to −1.80 dB (`onchip_il_min_db`,
`onchip_il_max_db`), against the paper's measured −1.85 to −2.99 dB
(`onchip_il_paper_range_db`). The two ranges do not overlap: the model's most-lossy path,
at −1.80 dB, is still 0.05 dB better than the paper's least-lossy measured path at
−1.85 dB. End to end the model is optimistic by 0.45 dB at the least-lossy end and by
1.19 dB at the most-lossy end. The loss parameters were left unchanged rather than tuned
to close that gap, so the disagreement stays visible. Separately, the fibre-to-fibre link budget at 1560 nm is 11.43 dB
(`fibre_to_fibre_loss_db`), dominated by the two grating couplers; it is a different
quantity from the on-chip loss and is not comparable with the paper's on-chip range.

PUF (rows 23–26). A response is a property of one die. The mesh is built once per die as
θ = π·challenge + ε (+ measurement noise), with ε that die's fixed per-MZI phase error;
equal-power light enters the two diagonal ports 0 and N−1 of that single mesh, and bit *i*
compares the two outputs of pair (2i, 2i+1). Both compared intensities therefore come from
the same physical chip. Both injections are needed: in a feed-forward mesh, reaching output
*k* from input 0 costs *k* cross-couplings, so single-edge injection leaves power decaying
monotonically with port index and biases every pair towards its even member; the diagonal
pair has mirror-image decay and the bias cancels.

At the arm-length-derived spread the model gives uniqueness 49.01%, uniformity 50.12%,
intra-die reliability 0.72% and a tie fraction of 0.0.

Because the response is driven by physics rather than by construction, uniqueness is a
function of the manufacturing spread, and the sweep is the honest way to report it
(`sensitivity_sweep`, 40 dies × 64 challenges, μ_phase = 0):

| σ_phase (rad) | uniqueness | uniformity | tie fraction | reliability |
|---|---|---|---|---|
| 0.001 | 0.2164 | 0.5177 | 0.0074 | 0.2198 |
| 0.010 | 0.2193 | 0.5133 | 0.0000 | 0.1623 |
| 0.100 | 0.2225 | 0.5126 | 0.0000 | 0.0258 |
| 0.500 | 0.2835 | 0.5151 | 0.0000 | 0.0073 |
| 1.050 | 0.4818 | 0.5103 | 0.0000 | 0.0069 |
| 3.000 | 0.4971 | 0.5040 | 0.0000 | 0.0069 |

The tie fraction is the share of compared pairs whose two intensities differ by less than
the tie tolerance of 1e-12 (`ppuf.tie_tol`); ties are resolved as 1 and counted rather than
hidden. At σ = 0.001 the mesh is still essentially a permutation, only the two routed
outputs carry power, and the tie fraction is non-zero. That regime is also where
reliability (0.2198) is as large as uniqueness (0.2164): the bits are being set by
measurement noise rather than by the die, which is exactly what a non-functioning PUF looks
like. At the paper's spread the two separate by a factor of 68 (the ratio of the two
`results.json` values 0.49005 and 0.00719), which is what makes the response a signature.
The PUF test judges the low-spread case by reliability rather than by a uniqueness bound,
because a symmetric comparison of two ports is randomised by any nonzero spread and only
measurement noise distinguishes a working PUF from a non-working one.

---

## 4. Physics extensions (beyond the first-pass models)

### 4.1 Single-θ PUC expressivity (`expressivity.py`) — paper Discussion, made explicit

The paper's PUC (Eq. 1) has one thermo-optic phase shifter, so one DOF per cell. A
universal N-mode interferometer needs N² real DOF; a rectangular mesh of single-θ cells
supplies only N(N−1)/2. For N = 4 that is 6 DOF inside a 16-dimensional U(4), rising to 10
with output phases and 16 only for the full 2-DOF mesh.

Best-fit fidelity to Haar-random U(4) climbs the same ladder: 0.5605 for single-θ, 0.8264
with output phases, 1.000000 for the universal 2-DOF mesh. This is why the paper
demonstrates permutations and specific realisable matrices rather than arbitrary unitaries.
A unitary generated by a single-θ mesh is recovered to fidelity 1.0000, and permutations
are routed at fidelity 0.999999999999.

Separately from the DOF limit, the coupler imposes its own ceiling on the single-θ cross
state. Over 1530–1565 nm that ceiling falls to 0.9469; at the 1560 nm design wavelength it
is 0.9942. Both follow from the coupler being 50:50 at 1574.7 nm (§6.1) rather than at the
design wavelength.

### 4.2 Coupled-mode-theory coupler with real dispersion (`coupler.py`)

The coupler is a CMT directional coupler with literature-grounded SOI dispersion and loss,
and it is fitted to the chip's own measured crosstalk (§6.1). A single straight directional
coupler is 3-dB at one wavelength; away from it the split is imbalanced and the MZI
extinction is capped.

At its 3-dB wavelength the model's extinction ratio is reported as null, not as a number:
the couplers are exactly balanced there and the two arms carry equal loss, so the null is
ideal and the ratio diverges. Reporting a floored value such as 120 dB would state a finite
extinction the model does not predict. Off that wavelength the extinction is finite and
physical: 22.34 dB at 1560 nm and 11.04 dB at 1520 nm. The fibre-to-fibre link budget is
11.43 dB, dominated by the two grating couplers.

The `demo_fit_kappa0` = 0.4980 and `demo_fit_slope` = 0.004370 entries in `results.json`
are recovered from the synthetic `_demo_measured_dataset`, not from chip data, and are
labelled as such by `demo_fit_note`. That dataset has its own fixed reference wavelength,
`DEMO_LAMBDA0` = 1560 nm, written to `results.json` as `demo_fit_lam0_nm`; generator and
fitter both use it, so the recovered values are directly comparable with the generator's
own `demo_true_kappa0` = 0.5 and `demo_true_slope` = 0.0042. That reference wavelength is
deliberately independent of `DC_LAMBDA_3DB`: the demo exercises the fitting routine and
says nothing about this chip, so tying it to the chip's fitted 3-dB point would make a
change in the chip fit look like a change in the demo. The κ₀ agreement to 0.002 is a
genuine recovery check; the 4.1% slope offset is the generator's quadratic dispersion term,
which the two-parameter CMT fit form cannot represent. Referencing generator and fitter to
different wavelengths would shift the fitted κ₀ by roughly slope × Δλ without the fit itself
changing, which measures the choice of reference wavelength rather than the quality of the
fit. None of these four numbers says anything about this chip.

### 4.3 Full square *recirculating* mesh with feedback (`recirculating.py`)

The matrix-multiply functions use a feedforward rectangular sub-mesh, but the full chip
recirculates: light returns through closed loops, so the transfer function is rational and
has poles. That needs a linear solve, o = (I − S·C)⁻¹ S·b. The solver is validated against
the analytic all-pass ring to RMS 2.9e-16 and the add-drop ring to 8.4e-16; the 4-PUC
square plaquette conserves energy to 1.1e-15, and the full 40-PUC recirculating bus solves
with an energy-conservation deviation of 8.9e-16.

---

## 5. Bottom line

Of the paper's headline quantitative claims, the bucket-A items (PUC unitarity, the
6.2163 / 5.4643-bit ENOB values, 60.04 ps latency) reproduce exactly. The bucket-B
simulations reproduce closely and on independent code: routing fidelity 0.999999999999,
unitary fidelity 1.000000, non-unitary modulus correlation 1.000000, PUF uniqueness 49.01%
against the paper's 49.97%, and PUF uniformity 50.12% against 50.15%. The bucket-C items
are physical measurements and are left unreproduced rather than fabricated.

Four results do not simply confirm the paper, and they are the useful output of this
reproduction:

1. The switch crosstalk the model predicts depends on whether data exists for the range in
   question. Inside the fitted range, the model meets the −15 dB figure (worst −16.77 dB)
   but not the −20 dB figure. These are predictions of a model constrained by one digitized
   port pair, not measurements of the other port pairs. The digitized T20 curve itself
   reaches −14.1 dB at 1549.0 nm, within its ±2 dB digitization uncertainty. Extrapolated
   below the data, over 1530–1549 nm, the model degrades to −11.80 dB — but that half of
   the band has no digitized point behind it and is a model projection.
2. The coupler's 3-dB wavelength is not the design wavelength. Fitting the mesh model to
   Fig 4d puts it at 1574.7 nm, with the parametric bootstrap interval [1572.3, 1577.7] nm.
   Both bootstrap intervals exclude 1560 nm: the pairs interval [1573.7, 1575.5] nm by
   13.7 nm and the parametric interval by 12.3 nm (§6.1). The proxy and mesh models place
   λ₀ 3.7 nm apart. The bootstrap intervals describe the uncertainty within the mesh model,
   not the uncertainty in the choice of model. Both models exclude 1560 nm.
3. The ideal-coupler fidelities do not survive the chip's own coupler. Rows 3 and 5 reach
   1.000000 with ideal 50:50 couplers; the coupler fitted to Fig 4d caps the single-θ cross
   state at 0.9942 at 1560 nm, and at 0.9469 at the worst point of 1530–1565 nm.
4. A multinomial logistic regression with 15 parameters (four weights for each of three
   classes, plus three biases) is ahead of the photonic Iris classifier on the same splits.
   Differenced seed by seed, it leads by 1.07 ± 1.30 points on the full set, winning on 7
   of the 10 seeds, tying on 2 and losing on 1; the absolute paired mean is smaller than
   the paired standard deviation, so that difference is within the seed-to-seed spread. On
   the held-out split it leads by 5.56 ± 3.67 points, winning on 9 seeds, tying on 1 and
   losing on none; there the absolute paired mean exceeds the paired standard deviation, so
   that is a consistent difference. The identity control shows the unitary contributes about
   10 points over the readout alone, so the mesh is doing real work — but Iris does not
   discriminate a photonic classifier from a linear one.

The three physics extensions (§4) make the model mechanistic rather than descriptive: the
single-θ expressivity limit is quantified (0.5605 mean fidelity to arbitrary U(4), rising
to 1.000000 only with the full 2-DOF mesh), explaining the paper's choice of matrix classes;
the switch crosstalk and loss emerge from a coupled-mode-theory coupler fitted to the
chip's measured spectrum; and the full recirculating mesh is solved with a feedback-capable
scattering-matrix network validated to ~1e-15, showing how feedback adds poles and a
strictly larger function class than the feedforward sub-mesh.

---

## 6. Parameters grounded in the paper

The paper (`s41377-026-02209-5`) and its supplementary (`MOESM1_ESM.docx`) supply the
chip-specific values below. These are the paper's numbers, used as inputs to the model:

| Quantity | Paper value (Methods / Supp) | Used in |
|---|---|---|
| Group index n_g | 4.0 (stated) | latency (60.04 ps) |
| Phase index n_eff | ~2.36 (450×220 nm SOI TE, geometry) | recirculating, PPUF |
| Directional coupler | length 11.5 µm, gap 200 nm, 450 nm width | coupler geometry |
| Square-mesh unit side | 500 µm | recirculating loop length |
| MZI arm length | 208 µm | mesh segments |
| Heater | 100 µm, 3 V for π across 100 Ω → 90 mW, E[θ]=π/2 | energy |
| Energy derivation | 40 PUCs × 45 mW = 1.8 W ÷ 9.6e11 MAC·s⁻¹ | throughput.py |
| Throughput convention | 96 ops × 2 directions × 10 GBaud | throughput.py |
| PUF arm-length spread | N(μ=0.08 µm, σ=0.11 µm) → phase N(0.76, 1.05) rad | ppuf.py |
| PUF experimental (2 dies) | inter-die 57.71%, uniformity 42.62%, intra-die HD 2.55% | ppuf targets |
| PUF simulation (100 dies) | uniqueness 49.97%, uniformity 50.15% | ppuf targets |
| Switch crosstalk | −45 to <−20 dB at 1560 nm; <−15/−20 dB over >20 nm | switching targets |
| On-chip insertion loss | −1.85 to −2.99 dB (8 measured paths) | switching comparison |
| Design wavelengths | 1560 nm (matrix), 1555 nm (MRM), 1545 nm (grating peak) | all modules |
| MRM eye SNR / Q | 17.10 & 17.83 dB; Q 7.17–8.08 | mrm (hardware-only targets) |

### 6.1 Fig 4d digitized, and the coupler 3-dB wavelength decided by that data

The all-cross-state T20 crosstalk curve was colour-digitized from Fig 4d
(`data/fig4d_T20_digitized.csv`, 25 points spanning 1549–1587 nm; dB scale anchored to
figure-read endpoints, ~±2 dB) and fitted with `scripts/fit_fig4.py`.

Two models are fitted to the same 25 points, with the same three free parameters (λ₀, slope,
floor):

| | `crosstalk_model` — single-coupler proxy | `mesh_t20_model` — 4×4 mesh T20 |
|---|---|---|
| what it evaluates | one directional-coupler pair, 10·log₁₀[(1−2κ)² + floor] | the full 4-stage fabric of `switching.py`, T20 normalised to total output power |
| λ₀ | **1571.0 nm** | **1574.7 ± 0.6 nm** |
| slope | **0.0029 rad/nm** | **0.00261 ± 0.00012 rad/nm** |
| floor | **−25.2 dB** | **−26.2 ± 0.4 dB** |
| **RMS over the 25 points** | **1.05 dB** | **0.79 dB** |
| pairs bootstrap, λ₀ 5–95% | [1570.1, 1572.0] nm | [1573.7, 1575.5] nm |
| pairs bootstrap, slope 5–95% | [0.0026, 0.0033] | [0.00239, 0.00285] |
| parametric bootstrap, λ₀ 5–95% | — | [1572.3, 1577.7] nm |
| parametric bootstrap, slope 5–95% | — | [0.00219, 0.00306] |

The mesh fit is the one used for `DC_LAMBDA_3DB`, because the proxy's λ₀ is not a property
of the mesh. The proxy is a formula for a single coupler pair. The chip's T20 path crosses
four stages, and the interference along that path displaces the T20 null away from the
wavelength at which the couplers themselves are 50:50. Evaluated on a 0.1 nm grid from 1540
to 1600 nm at the fitted mesh parameters, the floor-free null of T20/Tout sits at 1569.7 nm
while the couplers are 50:50 at 1574.7 nm — a 5.0 nm displacement. (That grid scan is a
diagnostic computed from `mesh_t20_model`; it is not a `results.json` value.) The proxy,
having no multi-stage path, has nowhere to put those 5 nm except into λ₀, which is why it
reports 1571.0 nm. Its λ₀ is a parameter of the proxy formula; the mesh's λ₀ is the coupler
parameter the rest of the code needs. The mesh also fits the data better, 0.79 dB against
1.05 dB, on the same points with the same number of free parameters.

Both bootstraps are run on the mesh model, 500 resamples each, 0 failed fits discarded in
either:

* The pairs bootstrap resamples the (λ, dB) pairs with replacement and refits. Its interval
  reflects only the scatter of the points about the model. λ₀ [1573.7, 1575.5] nm, slope
  [0.00239, 0.00285] rad/nm.
* The parametric bootstrap keeps all 25 wavelengths and adds Gaussian noise of 2.0 dB
  standard deviation (`digitization_sd_db`) to each dB value, treating the CSV header's
  ±2 dB as one standard deviation. Its interval therefore also carries the digitization
  uncertainty, which the pairs bootstrap cannot see. λ₀ [1572.3, 1577.7] nm, slope
  [0.00219, 0.00306] rad/nm.

The parametric interval is 2.9× wider on λ₀ and is the more honest of the two, because the
dominant uncertainty in this dataset is how accurately a curve could be read off a published
figure, not how the 25 points scatter about the model. (Both the 2.9× ratio and the interval
widths quoted below are arithmetic on the `results.json` percentile values.)

The decision rule was: if 1560.0 nm falls inside the λ₀ interval, keep 1560 nm as the
coupler's 3-dB wavelength; otherwise adopt the fitted value. 1560.0 nm lies outside both
intervals — 13.7 nm below the pairs lower bound (7.5 interval widths) and 12.3 nm below the
parametric lower bound (2.3 interval widths) — so the second branch applies. `coupler.py`
therefore defines

```python
DC_LAMBDA_3DB = 1574.7  # nm, 3-dB point from fitting the mesh T20 model to digitized Fig 4d
DC_SLOPE = 0.0026       # rad/nm, coupling-phase dispersion slope of the same fit
```

while `LAMBDA0 = 1560.0` remains the design wavelength. The two are different quantities and
the data says they are about 15 nm apart. The consequence is physical, not cosmetic: at
1560 nm the power coupling is 0.462 rather than 0.500, the MZI extinction falls to 22.34 dB,
the single-θ unitary fidelity ceiling drops to 0.9942, and the worst-case switch crosstalk
inside the fitted range is −16.77 dB.

The two models disagree about λ₀ by 3.7 nm, which is six times the mesh fit's own standard
error and larger than the pairs bootstrap interval. That gap is model-form uncertainty: it
measures the choice between a single-coupler formula and the full four-stage fabric, and
neither bootstrap interval contains it, because both resample the data under one fixed
model.

The crosstalk floor is a fitted parameter whose physical origin is not established from the
paper. Both models need a floor term to reproduce the plateau near −25 dB in the middle of
the digitized curve, and the mesh fit puts it at −26.2 ± 0.4 dB. Nothing in the paper
identifies what produces it. Candidate mechanisms — residual phase error, back-reflection,
leakage paths outside the modelled topology, or a noise floor of the measurement set-up —
are not distinguished by a single digitized curve, and this reproduction does not claim to
know which applies. The value is recorded as `FIG4D_FLOOR_DB` and used only to fit, and to
mark the level below which modelled crosstalk is not physically reached.

A precise per-point digitization of the other three overlapping curves in each panel is
noise-limited, so only the cleanest curve (T20) was extracted; the stated geometry (11.5 µm,
200 nm gap) anchors the rest. (Figure: `figures/fig4_digitized.png`, which overlays both
fits.)

### 6.2 What is still genuinely unavailable

* Measured eye-diagram SNR/Q (17.10 / 17.83 dB, Q 7.17–8.08) are link measurements and
  remain hardware-only.
* The measured non-unitary input/output correlation (Fig. 2n) requires the chip.
* The measured crosstalk spectra (Fig. 4d,e) require the chip; only the digitized T20 curve
  is available, and it is used as fit input rather than reproduced.
* The 2-die experimental PUF numbers require two fabricated dies.
* The MRM ring radius / FSR (self-developed MRM) is not tabulated; the MRM model stays
  qualitative, using the 0.1 ns differentiator delay and the 1555 nm carrier.
* Table SI 2 PDK sub-values (per-ADC loss, edge-coupler loss) did not extract cleanly. They
  drive only the 32×32 / 64×64 scaling projection, not the 4×4 results, which use the
  directly-stated measured path losses.

---

## 7. Open items

* The PUF is simulated on a feed-forward rectangular mesh, whereas the chip's PUF runs on
  the 40-cell recirculating square mesh; re-running the PUF with `lightin/recirculating.py`
  is outstanding.
* `python -m pytest -q` takes about 90 seconds on this machine, down from about three
  minutes, because `test_fig4d_digitized_fit` now calls only the two single fits
  (`fit_proxy` and `fit_mesh`) instead of `fit_fig4.main()` with its bootstraps. A full
  `python scripts/run_all.py` takes about 15 minutes; `python scripts/run_all.py --quick`
  runs the same pipeline in about 5 minutes with the Iris seed sweep cut to two seeds and
  both Fig 4d bootstraps to 50 resamples, writing `results_quick.json` and `figures_quick/`
  so that a quick run never overwrites the reported outputs. Quick-mode numbers are noisier
  and are not the ones quoted here.
* The insertion-loss parameters in `switching.py` (0.25 dB per stage and 0.1 dB coupler
  excess loss, both code constants rather than `results.json` values) have now been checked
  against the paper's measured on-chip range. The model gives −1.40 to −1.80 dB over the
  eight intended paths against the paper's measured −1.85 to −2.99 dB, so the two ranges do
  not overlap and the model is optimistic by 0.45 dB at the least-lossy end and 1.19 dB at
  the most-lossy end. The parameters were left unchanged, so the disagreement is on record
  rather than tuned away.
* The paper's Iris evaluation set is not established from the published values.
* The coupler 3-dB wavelength carries a model-form uncertainty (3.7 nm between the proxy and
  mesh models) that the bootstrap intervals do not include.
* The Iris accuracies depend on the installed scipy and scikit-learn versions: with
  `nn_iris.py` unchanged, seed 0 currently yields a full-set accuracy of 95.33% where an
  earlier environment recorded 94.67%. The environment is now pinned by
  `requirements-lock.txt` and recorded in the `environment` block, but the size of that
  variation across versions has not been measured, so how far the numbers move on another
  stack remains unknown.
* The −25 dB crosstalk floor in Fig 4d is modelled only as a fitted constant; whether it
  comes from the device (phase error, back-reflection, leakage paths) or from the
  measurement set-up is not established.
