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

Rows labelled model vs measurement compare a model in this code with a quantity the paper
measured on the chip. They are neither re-implementations of a simulation the paper ran nor
hardware results.

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
| 9 | Iris classification, held out | — (the paper's 93.33% is an on-chip measurement and is not comparable) | **89.33% ± 5.14%** over 10 seeds | **B** |
| 10 | Iris identity control | — | **85.60% ± 0.44%** full set, **81.56% ± 4.67%** held out | control |
| 11 | Iris logistic baseline | — | **96.53% ± 0.88%** full set, **94.89% ± 3.45%** held out | control |
| 12 | On-chip latency | ~60 ps | n_g·L/c = **60.04 ps** (4.5 mm, n_g=4) | **A exact** |
| 13 | Throughput | **1.92 TOPS** | **1.92 TOPS** from the Supp Note 3 op count | **consistency check** |
| 14 | Energy | **1.875 pJ/MAC** | 1.8 W ÷ 9.6e11 MAC·s⁻¹ = **1.875 pJ/MAC** | **consistency check** |
| 15 | MRM locking (Fig. 3c) | monitoring peaks at high-ER lock | monitoring peak at bias **−0.448**; ER up to **18.46 dB** | **B** (model) |
| 16 | Eye-diagram SNR / Q (Fig. 3d–f) | ~17–18 dB SNR, Q ~7–8 | illustrative model eye only | **hardware — not reproduced** |
| 17 | Switch crosstalk at 1560 nm, cross state (Fig. 4d) | −45 to <−20 dB | cross **−27.16 to −21.48 dB** | **model vs measurement** |
| 17b | Switch crosstalk at 1560 nm, bar state (Fig. 4e) | −45 to <−20 dB | bar **−107.80 to −31.16 dB**, from a coupler-split spread fitted to Fig 4e, `SIGMA_SPLIT` = **0.0182** with a full range of **0.0152–0.0707** across the percentile scan and the calibration offset test, and an arm-phase spread still assumed (§6.1, §6.3) | **fit to measurement** |
| 18 | Switch crosstalk, worst inside the fitted range | <−15/−20 dB over >20 nm | cross **−17.03 dB** over 1549–1565 nm | **model vs measurement** |
| 19 | Switch crosstalk, worst extrapolated below the data | <−15/−20 dB over >20 nm | cross **−11.90 dB** over 1530–1549 nm | **model vs measurement** |
| 20 | Mesh T20 model vs digitized Fig 4d | — | RMS **0.79 dB** over 25 points (single-coupler proxy **1.05 dB**) | **fit to measurement** |
| 20e | Bar-state T32 model vs digitized Fig 4e | — | RMS **0.4176 dB** over 27 points, against **0.4170 dB** for the best constant on the same points: the model fixes the level and reproduces none of the wavelength structure, so it has no RMS advantage over a constant (§6.1) | **fit to measurement** |
| 21 | Measured crosstalk spectra (Fig. 4d,e) | measured | not reproduced; one curve from each panel is digitized and used as fit input, the other fourteen are not | **hardware — not reproduced** |
| 22 | On-chip insertion loss, 8 paths | **−1.85 to −2.99 dB** (8 measured paths) | **−1.40 to −1.80 dB** (8 modelled paths) | **model vs measurement** |
| 23 | PUF uniqueness, feed-forward mesh (Fig. 5) | **49.97%** (simulation) | **49.00% ± 0.34%** over 10 population seeds (48.92% on the single 100-die seed) | **B** |
| 24 | PUF uniformity, feed-forward mesh (Fig. 5) | **50.15%** (simulation) | **50.32% ± 0.51%** over 10 seeds (49.39% on the single 100-die seed) | **B** |
| 25 | PUF reliability | 2.55% intra-die HD (experimental) | **0.72%** at a measurement-noise σ of **0.01 rad** per MZI | **model vs measurement** |
| 23r | PUF uniqueness, recirculating mesh | **49.97%** (simulation) | **49.89% ± 0.25%** (C4_FREE_1), **49.93% ± 0.28%** (C4_FREE_2), over 10 seeds | **model vs simulation** |
| 24r | PUF uniformity, recirculating mesh | **50.15%** (simulation) | **50.01% ± 0.88%** (C4_FREE_1), **49.88% ± 0.94%** (C4_FREE_2) | **model vs simulation** |
| 25r | PUF reliability, recirculating mesh | 2.55% intra-die HD (experimental) | **0.76% ± 0.06%** (C4_FREE_1), **0.77% ± 0.06%** (C4_FREE_2), at an assumed noise | **model vs measurement** |
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

Unitary mesh (rows 2–3). Arbitrary unitaries are realised on a universal Clements
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
of nearest-neighbour 2×2 switches. The cross-state crosstalk is produced by the
coupled-mode-theory coupler of §4.2 rather than by a hand-set slope; the bar-state
crosstalk is now produced by a coupler-split spread fitted to Fig 4e, with the arm-phase
spread still assumed, as the next paragraphs and §6.3 set out. The loss still comes from
assumed constants. At 1560 nm the model gives
cross-state crosstalk of −27.16 to −21.48 dB and bar-state −107.80 to −31.16 dB, against
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

The two states do not leak for the same reason, and `leak_mechanism_check` in
`results.json` separates them on one switch cell at 1560 nm.

The cross state leaks because a single directional-coupler design is 3-dB at only one
wavelength (§4.2). At 1560 nm the fitted coupler splits 0.462 rather than 0.500, and it is
that offset common to both couplers, rather than any difference between them, that the
cross state cannot cancel. Forcing both couplers to an exact 50:50 split drops the cell's
leakage from −25.69 dB (`cross_cell_leak_db_model`) to −32.87 dB
(`cross_cell_leak_db_ideal_coupler`), an improvement of 7.18 dB, and the leakage moves with
wavelength because the split does. That is the mechanism behind rows 17–19.

The bar state leaks for a different reason. Its unintended-port amplitude is proportional
to the *difference* between the two couplers' coupling angles, which is fixed at
fabrication and does not depend on wavelength at all; the arm phase error contributes a
second, independent term. Both are drawn in `switching.py` from Gaussians. Their standard
deviations are `SIGMA_SPLIT` and `SIGMA_PHASE`, and exactly one of the two is now fitted:
`SIGMA_SPLIT` = 0.0182, with a full range of 0.0152–0.0707 across the percentile scan and
the calibration offset test, comes from the digitized Fig 4e curve (§6.1), while
`SIGMA_PHASE` is still 0.02 rad with no recorded source (§6.3). Set both to zero and the
bar state nulls exactly, below the 1e-20 structural-zero threshold. Leave them and the
cell leaks −30.20 dB (`bar_cell_leak_db_model`); ideal 50:50 couplers, which remove the
split imbalance but leave the phase error, give −32.87 dB
(`bar_cell_leak_db_ideal_coupler`).

The bar-state numbers are therefore no longer a statement about two assumed spreads. They
rest on one measured quantity and one assumption, and the measured one is the dominant of
the two: at the fitted point the model's sensitivity to `SIGMA_SPLIT` is about fifty times
its sensitivity to `SIGMA_PHASE` (§6.1). What the single curve cannot do is separate them,
so `SIGMA_PHASE` is held rather than fitted, and the bar-state values would still move if
it were set differently.

Two mechanisms are ruled out by the same three cases. Unequal arm loss cannot produce
either state's leakage: the phase section is diag(e^(i(θ+ε)), 1), both entries of modulus
exactly 1, so the two arms carry identical loss (`ARM_LOSS_DB`), and every loss term in a
cell — the 0.1 dB coupler excess loss and the 0.25 dB per-stage propagation — is a scalar
prefactor on the whole 2×2 that reaches both output ports equally. Setting both arms to the
mean of the two arm losses is consequently a no-op: `bar_cell_leak_db_equal_arm_loss` =
−30.20 dB and `cross_cell_leak_db_equal_arm_loss` = −25.69 dB equal their `_model`
counterparts to the last digit, and the full-fabric bar-state centre range under that
substitution, `bar_center_db_equal_arm_loss`, is [−31.16, −107.80] dB — the shipped
`bar_xtalk_center_db` unchanged. Coupler dispersion is ruled out for the bar
state alone: moving the fitted 3-dB wavelength by 14.7 nm shifts the bar-state values by
hundredths of a dB while the cross-state values move by several.

Both states report 0 structural zeros (`cross_structural_zeros` and
`bar_structural_zeros`): no port pair was excluded from the crosstalk statistics for
carrying no power, so the numbers above are over every off-target path. A pair is counted
as a structural zero only when its raw linear transmission falls below 1e-20, and the test
is made on that raw power rather than on a decibel value, so no additive constant can
manufacture a floor. The lowest bar-state entry, input 0 to output 3, sits at a raw
transmission well below the rest (−107.80 dB); reaching that port takes three off-target
couplings, which is why it is so far below the rest and why it is a real model prediction
rather than a numerical artefact. Each of those three couplings is one factor of the
coupler-imbalance and arm-phase terms above, so −107.80 dB is roughly three times as far
from the paper's data as the −31.16 dB entry is. Neither should be read as a crosstalk
the chip would show at that port: the Fig 4e curve constrains one port pair, T32, and the
model carries that one fitted spread to the other fifteen.

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

On one 100-die seed the feed-forward model gives uniqueness 48.92%, uniformity 49.39%,
intra-die reliability 0.74% and a tie fraction of 0.0. Across 10 population seeds of 40
dies it gives 49.00% ± 0.34%, 50.32% ± 0.51% and 0.72% ± 0.08%. The spread across seeds is
comparable to the differences discussed below, so single-seed figures are labelled as such
wherever they appear.

The arm-length mean is negative. `ppuf.py` had recorded the per-MZI arm-length difference as
N(+0.08 um, 0.11 um); the preprint gives N(-0.08 um, 0.11 um) (section 2.5, and §6.4 below),
and the sign is corrected here. It moves the three PUF metrics very little: uniqueness
0.4901 to 0.4892, uniformity 0.5012 to 0.4939, reliability 0.00719 to 0.00735, every change
below 0.008. The mean phase itself flips from +0.7604 to -0.7604 rad.

**The PUF on the recirculating mesh (rows 23r-25r).** The chip's PUF runs on the 4x4
square recirculating mesh, so a model on that mesh is the topologically faithful one.
`lightin/ppuf.py` is kept because it is far cheaper and because its behaviour is already
characterised, not because it is the better model of the device. `lightin/square_mesh.py`
builds the 40-cell mesh -- 25 vertices on a 5x5 lattice, 40 edges, one PUC per edge, all
inter-MZI waveguides of equal length as the preprint states -- and `lightin/ppuf_recirc.py`
runs the PUF on it.

The rotation is the *half* turn, not the quarter turn, and that follows from the
preprint's own port layout. The 20 optical ports sit on two opposite edges (§6.4). A
quarter turn of the lattice carries {top, bottom} to {left, right}, mapping the
port-bearing edges onto the two edges that carry no ports, so it cannot preserve the port
set; the half turn (r, c) -> (4-r, 4-c) does. Under the half turn the 40 cells fall into
**20 orbits of two**, with no cell fixed.

The challenge is applied **per orbit, not per cell**: both cells of an orbit take the same
phase, pi for a bit of 1 and 0 for a bit of 0. That is the paper's own design, not a choice
made here -- the preprint states that the same programming voltage is applied to the MZIs at
equivalent logical positions under the rotation (section 2.5). A challenge is therefore
**20 bits**. Two nominally equal-power beams enter one pair of optical ports exchanged by
the half turn, and each remaining port is compared with its half-turn image, giving
**9 response bits**, all 9 of which carry light. With no fabrication error every compared
pair is exactly equal and every bit is a tie, so the response is produced entirely by the
manufacturing spread.

The vertex wiring is a stated choice, not the paper's; §6.5 records how it was chosen and
what is conditional on it. Two wirings are carried, and every number is reported for both.

At the arm-length-derived spread, the three models over 10 independent population seeds
(40 dies x 64 challenges each; the spread quoted is the sample standard deviation across
seeds, which is the sampling spread of a metric computed on 40 dies, not an uncertainty of
the model):

| | uniqueness | uniformity | reliability (intra-die HD) |
|---|---|---|---|
| paper, 100-die simulation | **49.97%** | **50.15%** | 2.55% (experimental, 2 dies) |
| recirculating, C4_FREE_1 | 49.89% ± 0.25% | 50.01% ± 0.88% | 0.76% ± 0.06% |
| recirculating, C4_FREE_2 | 49.93% ± 0.28% | 49.88% ± 0.94% | 0.77% ± 0.06% |
| feed-forward | 49.00% ± 0.34% | 50.32% ± 0.51% | 0.72% ± 0.08% |

Differenced seed by seed, the recirculating model's uniqueness minus the feed-forward
model's is +0.88% ± 0.42% over the 10 seeds. The absolute paired mean exceeds the paired
standard deviation, so by the rule used for the Iris comparison that is **a consistent
difference** rather than seed-to-seed noise: the recirculating model's uniqueness sits
nearer the paper's 49.97% on all 10 of the 10 seeds, the feed-forward model on none, with
none tied. That much survives the sweep.

What does not survive is the exactness. The single-seed run reported earlier, in which the
recirculating model returned 49.97% against the paper's 49.97%, was one draw from a
distribution whose mean is 49.89% ± 0.25%; the paper's value sits 0.3 sample standard
deviations from that mean. The match to four significant figures was luck, and no claim
that this model reproduces the paper's uniqueness exactly is supportable. What the sweep
supports is narrower: over 40-die populations the recirculating model is consistently the
nearer of the two, by 0.88 points, with both models inside a point of the paper.

**What agreement on uniqueness is worth.** A uniqueness near 50% is the default outcome of
comparing two nominally identical outputs, not a discriminating result: any construction in
which the two compared ports are exchangeable produces it, including the exchangeable model
this reproduction rejected at its first audit. Matching 49.97% is therefore weak evidence
on its own, and the two models matching it equally well is what one would expect rather
than a coincidence. The evidence that the response is driven by the device physics is the
sensitivity sweep, not the headline number: uniqueness climbs from 0.2412 at
sigma = 0.001 to 0.5011 at sigma = 3.0, the tie fraction falls from 0.5141 to 0.0000, and
all 9 response pairs carry light throughout, so the bits are being set by the manufacturing
spread rather than by the construction of the comparison.

**Reliability is set by an assumed number.** `MEAS_NOISE_SIGMA` has no recorded source
(§6.3), and reliability is the metric it drives. Sweeping it over the recirculating model
(40 dies x 64 challenges, wiring C4_FREE_1):

| assumed noise sigma (rad) | uniqueness | uniformity | reliability | tie fraction |
|---|---|---|---|---|
| 0.002 | 0.4934 | 0.4805 | 0.0018 | 0.0000 |
| 0.005 | 0.4934 | 0.4805 | 0.0044 | 0.0000 |
| 0.010 | 0.4934 | 0.4805 | 0.0084 | 0.0000 |
| 0.020 | 0.4934 | 0.4805 | 0.0159 | 0.0000 |
| 0.050 | 0.4934 | 0.4805 | 0.0393 | 0.0000 |

No single swept value gives the paper's experimental 2.55%. It falls between sigma = 0.02
(1.59%) and sigma = 0.05 (3.93%); interpolating linearly between those two points puts it
at about **0.032 rad**, roughly three times the assumed 0.01. Uniqueness, uniformity and
the tie fraction do not move at all across the sweep, because they are computed from the
noise-free reference response; only reliability responds. The modelled reliability is
therefore a statement about the assumed noise rather than a prediction of the chip's 2.55%,
and the two should not be read as agreeing or disagreeing.

The spread sweep behaves the way a working PUF should, and the same way the feed-forward
model does (20 dies x 32 challenges, mu_phase = 0):

| sigma_phase (rad) | uniqueness | uniformity | tie fraction | reliability | live pairs |
|---|---|---|---|---|---|
| 0.001 | 0.2412 | 0.7604 | 0.5141 | 0.4345 | 9 |
| 0.010 | 0.4408 | 0.5668 | 0.1203 | 0.3352 | 9 |
| 0.100 | 0.4937 | 0.5059 | 0.0109 | 0.0672 | 9 |
| 0.500 | 0.4992 | 0.5021 | 0.0000 | 0.0120 | 9 |
| 1.050 | 0.5003 | 0.5014 | 0.0000 | 0.0086 | 9 |
| 3.000 | 0.5011 | 0.5201 | 0.0000 | 0.0062 | 9 |

(Wiring C4_FREE_1; C4_FREE_2 differs by at most 0.02 on any entry.) At sigma = 0.001 the
mesh is nearly nominal, more than half the pairs still tie, and reliability (0.4345) is
larger than uniqueness (0.2412) -- the non-functioning regime, the same signature the
feed-forward sweep shows at that spread. By sigma = 0.1 the ties are gone and uniqueness
is 0.4937.

The two wirings agree on uniqueness to 0.0002 on the single headline run, and their
population means differ by 0.04 points against a seed spread of about 0.25 points, well
inside the stated tolerance of 0.05. That is the check that the conclusion does not rest on
the wiring, and a test enforces it.

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
like. At the paper's spread the two separate by a factor of 67 (the ratio of the two
`results.json` values 0.48917 and 0.00735), which is what makes the response a signature.
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
unitary fidelity 1.000000, non-unitary modulus correlation 1.000000, PUF uniqueness
49.00% ± 0.34% against the paper's 49.97%, and PUF uniformity 50.32% ± 0.51% against
50.15%, both over 10 population seeds. The bucket-C items
are physical measurements and are left unreproduced rather than fabricated.

Five results do not simply confirm the paper:

1. The switch crosstalk the model predicts depends on whether data exists for the range in
   question. Inside the fitted range, the model meets the −15 dB figure (worst −16.77 dB)
   but not the −20 dB figure. These are predictions of a model constrained by one digitized
   port pair, not measurements of the other port pairs. The digitized T20 curve itself
   reaches −14.1 dB at 1549.0 nm, within its ±2 dB digitization uncertainty. Extrapolated
   below the data, over 1530–1549 nm, the model degrades to −11.80 dB — but that half of
   the band has no digitized point behind it and is a model projection.
2. The coupler's 3-dB wavelength is not the design wavelength. Fitting the mesh model to
   Fig 4d puts it at 1574.2 nm, with the parametric bootstrap interval [1572.3, 1577.7] nm.
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
5. The modelled on-chip insertion loss, −1.40 to −1.80 dB over eight paths, is lower than
   the paper's measured −1.85 to −2.99 dB. The loss parameters are assumed rather than
   taken from the paper, and they were not tuned to close the gap.

The three physics extensions (§4) make the model mechanistic rather than descriptive: the
single-θ expressivity limit is quantified (0.5605 mean fidelity to arbitrary U(4), rising
to 1.000000 only with the full 2-DOF mesh), explaining the paper's choice of matrix classes;
the switch crosstalk emerges from a coupled-mode-theory coupler fitted to the chip's
measured spectrum, while the loss comes from assumed constants that are lower than the
measured range; and the full recirculating mesh is solved with a feedback-capable
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

**Fig 4e digitized, and the coupler-split spread decided by that data.** Fig 4e is a 2×2
array of sub-panels, one per input port, each carrying four output curves against
wavelength over 1550–1590 nm and 0 to −25 dB. The curve matching the digitized Fig 4d port
pair, T20, is in the top-left sub-panel and is **not drawn at all**: in the all-bar state it
lies below the panel's −25 dB axis limit across the whole range, as do T10 and T30. The
only off-diagonal curve visible across the full wavelength span is **T32**, in the
bottom-left sub-panel, and that is the one digitized
(`data/fig4e_bar_digitized.csv`, 27 points over 1550–1589 nm).

That curve is drawn as a filled band whose *lower* edge the −25 dB axis limit cuts off at
every wavelength, so its centre cannot be read. What the CSV tabulates is the band's upper
envelope — a peak-hold over the fast wavelength ripple — read to ±0.3 dB, one standard
deviation, from the tick-fit residual (0.03 dB), the top-edge scatter inside the ±0.5 nm
window (0.10 dB) and the placement of the line centre from its top edge (0.19 dB). That is
far tighter than the ±2 dB of the Fig 4d file because this dB scale is anchored to five
tick marks per axis with sub-pixel residuals rather than to figure-read endpoints. That
the tabulated trace is an envelope, and not a level, is the reason the model is compared
at a high percentile of its fabrication ensemble rather than at its mean, which is the
next paragraph. The four diagonal through paths of the same figure are digitized
separately, on the same anchoring procedure, and compared with the paper's measured
on-chip insertion loss further down.

Because the data is an envelope, the model is compared at the matching statistic: the
99th percentile of a 3200-realisation fabrication ensemble, not its mean. This
matters more than any other choice in the fit. Compared against the ensemble *mean* the
same 27 points return a coupler-split spread of 0.0479 — which is simply the 7.4 dB by
which this model's own 99th percentile sits above its own mean, absorbed into the fitted
parameter — and that value degrades the Fig 4d agreement from 0.79 to 2.65 dB RMS and moves
the refitted coupler 3-dB wavelength by 8.1 nm. It was rejected on the cross-check below,
which is the test `docs/FIG4E_SCOPE.md` pre-registered for exactly this.

**The two spreads are not separately identifiable from one curve.** The bar-state model is
flat in wavelength — it varies by 0.002 to 0.03 dB across 1550–1589 nm, against 1.62 dB of
structure in the digitized points — so one curve supplies one number, not a shape. A joint
two-parameter fit confirms it: σ_split comes back as 0.0185 ± 0.0305 — a standard error
larger than the value — while σ_phase runs to zero with a standard error of 12854, at
the same 0.42 dB RMS. Its covariance matrix is singular, so the correlation it reports is
an artifact of that singularity rather than a measurement of the trade-off. The fits are
therefore reported one at a time with the other held:

| | fitted | held | result | RMS |
|---|---|---|---|---|
| coupler-split spread | `SIGMA_SPLIT` | `SIGMA_PHASE` = 0.02 | **0.0182**, range **0.0152–0.0707** | **0.42 dB** |
| arm-phase spread | `SIGMA_PHASE` | `SIGMA_SPLIT` = 0.02 | **no interior optimum** | 0.79 dB |

The arm-phase fit has no solution, and that is a result rather than a failure: with
`SIGMA_SPLIT` held at 0.02 the model already gives −19.49 dB at zero arm-phase spread,
against a data mean of −20.16 dB, and the arm phase can only add leakage. The optimizer
runs to zero. So the digitized envelope wants *less* leakage than a 0.02 split spread alone
produces, which is why the fitted `SIGMA_SPLIT` comes out slightly below 0.02 rather than
above it.

**The model reproduces the level of the leakage and none of its shape.** An RMS figure
means nothing until it is read against the most trivial model that could be fitted to the
same points, which is a constant. The least-squares constant on the 27 digitized points is
−20.158 dB and its RMS is their standard deviation, 0.4170 dB. The bar model at the fitted
spread scores 0.4176 dB on the same points, which is 0.0006 dB *worse*. Across the band
the points vary by 1.620 dB peak to peak and the model by 0.0023 dB, 0.14% of that. So
this panel does not constrain a curve. It constrains one number, the level, and the
model's RMS advantage over a constant is zero to well inside the ±0.3 dB the CSV states
for each point. It is also why the RMS is the same at every percentile in the scan below:
the percentile decides where the flat model sits and nothing else. These are the
`fig4e_fit.shape_check` keys.

Bootstraps on the one well-posed fit, 500 resamples each, seeds 0 and 1, matching the Fig
4d procedure: pairs [0.0179, 0.0185] (0 failed fits), parametric at the CSV's ±0.3 dB
[0.0180, 0.0184] (0 failed). Both describe the scatter of the 27 points about a model
whose form is held fixed, and both are far narrower than the spread's real uncertainty,
which is dominated by things the bootstrap cannot see: the ensemble seed (0.16 dB at 3200
realisations) and, above all, the choice of percentile.

**The percentile is a modelling choice, and it is the larger uncertainty by two orders of
magnitude.** `PCT` is the quantile of the fabrication ensemble the model reports. It is
set by how many independent ripple samples fall inside one digitization window, which the
figure does not show. Refitting `SIGMA_SPLIT` at six percentiles, with `SIGMA_PHASE` held
at 0.02 and everything else unchanged:

| percentile | `SIGMA_SPLIT` | pairs bootstrap | parametric bootstrap | RMS |
|---|---|---|---|---|
| 50th | **0.0707** | [0.0697, 0.0719] | [0.0700, 0.0717] | 0.42 dB |
| 75th | **0.0418** | [0.0413, 0.0425] | [0.0414, 0.0423] | 0.42 dB |
| 90th | **0.0283** | [0.0279, 0.0287] | [0.0280, 0.0286] | 0.42 dB |
| 95th | **0.0237** | [0.0234, 0.0241] | [0.0235, 0.0240] | 0.42 dB |
| 99th | **0.0182** | [0.0180, 0.0185] | [0.0180, 0.0184] | 0.42 dB |
| 99.9th | **0.0152** | [0.0150, 0.0155] | [0.0151, 0.0154] | 0.42 dB |

The RMS is the same 0.42 dB at every one of them, so the data expresses no preference
between a spread of 0.0707 and one of 0.0152. A second variant tests the dB calibration:
every digitized point shifted by −0.35 dB, the difference between the digitized diagonals'
mean and the midpoint of the paper's insertion-loss range, returns 0.0175 at the adopted
percentile. That one is a sensitivity test and not a correction, for the reason given
under the diagonals below.

Across all 7 variants `SIGMA_SPLIT` runs from 0.0152 to 0.0707, a width of 0.0555, against
the adopted fit's parametric bootstrap interval [0.0180, 0.0184], a width of 0.0004. The
range is larger by a factor of 140. The two measure different things: the bootstrap
measures how far the 27 points scatter about a model of a fixed form, and the range
measures the form itself. Only the second is an honest headline, so `SIGMA_SPLIT` is
quoted as 0.0182 with 0.0152–0.0707 as its uncertainty and the bootstrap interval as a
subsidiary figure. The range is one-sided about the adopted value: the adopted 99th
percentile is the second highest in the scan, and every lower percentile demands *more*
fabrication spread to explain the same measured level. These are the
`fig4e_fit.sensitivity` keys.

**The digitized diagonals, against the paper's measured insertion loss.** The diagonal of
each sub-panel is an intended all-bar path, and all four are digitized
(`data/fig4e_diagonal_digitized.csv`, 18 wavelengths per trace, each sub-panel anchored to
its own tick marks). The opaque legend box hides 1574.5–1588.3 nm in every sub-panel, so
the 1.5 nm grid runs 1550.0–1574.0 nm and then resumes at 1589.0 nm, inside the roll-off
at the end of the scan; both spans are reported, because which one is used changes the
comparison by more than a decibel.

| trace | full band 1550–1589 nm | continuous 1550–1574 nm |
|---|---|---|
| T00 | −2.20 to −4.06 dB (mean −2.52) | −2.20 to −2.77 dB (mean −2.43) |
| T11 | −2.15 to −3.30 dB (mean −2.32) | −2.15 to −2.44 dB (mean −2.27) |
| T22 | −1.45 to −3.78 dB (mean −1.86) | −1.45 to −2.26 dB (mean −1.75) |
| T33 | −1.10 to −3.41 dB (mean −1.59) | −1.10 to −2.01 dB (mean −1.48) |
| **all four** | **−1.10 to −4.06 dB** | **−1.10 to −2.77 dB** |

The paper's measured range is −1.85 to −2.99 dB. **The two are not a constant apart.**
Over the full band the most-lossy end of the digitized set sits 1.07 dB below the paper's
and the least-lossy end 0.75 dB above it, so the two ends disagree by 1.82 dB. Over the
continuous segment alone they differ by 0.22 dB and 0.75 dB, 0.53 dB apart. A calibration
offset on the digitized dB scale would move both ends by the same amount, and neither
comparison does, so there is no offset to correct and the fitted spread above is not moved
by one.

Whether the digitized diagonals *agree* with the paper's range depends on what agreement
is being asked for. Every individual reading is plausible for a low-loss through path, and
over the full band the paper's range lies entirely inside the digitized one, so nothing in
the digitization contradicts the measurement. As ranges they do not match: the digitized
set reaches 0.75 dB less loss than the paper's least-lossy path and, at the band edge,
1.07 dB more than its most-lossy one.

The alternative explanation needs no calibration error and is not excluded here. The
paper's range covers 8 intended paths. Fig 4e is the all-bar configuration and draws 4 of
them; the other 4 are the all-cross paths, which belong to Fig 4d. So this is four of the
paper's eight paths compared against all eight. Which switch state the paper's range was
measured in, at what wavelength and over what band, is not recorded anywhere available
here: `docs/PREPRINT_NOTES.md` does not mention insertion loss at all, and the
transcription in the §6 table above carries only "−1.85 to −2.99 dB (8 measured paths)".
The repository cannot settle which of the two explanations holds, and it is left open
rather than closed by assumption. These are the `fig4e_diagonals` keys.

**The Fig 4d and Fig 4e fits are solved jointly.** The Fig 4d fit holds the fabrication
spreads and the Fig 4e fit holds the coupler, so the two were alternated until neither
moved. One pass from the previous state moves `DC_LAMBDA_3DB` from 1574.7 to 1574.2 nm —
inside that fit's own 0.61 nm standard error — and the next pass moves `SIGMA_SPLIT` by
8e-6, which is the fixed point. Both shipped constants reproduce their own refit: λ₀ to
0.03 nm and σ_split to 8e-6.

**Cross-check against the other panel.** With the fitted spread in place and nothing
refitted, the Fig 4d mesh model scores 0.79 dB RMS on its own 25 points, against 0.82 dB
at the 0.02 spread it carried before. Adopting the Fig 4e result did not degrade the Fig
4d agreement; it improved it by 0.03 dB. The Fig 4e model scores 0.42 dB on its 27 points,
against 0.90 dB at the assumed spread. These are the `cross_check` keys in `results.json`.
(Figure: `figures/fig4e_digitized.png`.)

What that cross-check is, and is not, follows from which curves exist. The Fig 4d port
pair T20 is not drawn anywhere in Fig 4e, so T32 was digitized in its place, and there is
no port pair that both panels report. The cross-check therefore compares two *different*
port pairs of the same fabric, T20 in the all-cross state and T32 in the all-bar state,
and not the same pair measured twice. That makes it a test of whether one fitted coupler
and one fitted spread describe the whole fabric, which is the useful test, rather than a
repeat measurement of one path, which would not be.

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

### 6.3 Parameters not taken from the paper

Everything in the §6 table above is a value the paper or its supplementary states. The
model needs more numbers than that. The table below is every module-level constant and
every numeric default argument in `coupler.py`, `switching.py`, `ppuf.py`, `mrm.py`,
`recirculating.py` and `nn_iris.py` that represents a physical or model parameter and that
the §6 table does not attribute to the paper, together with the source recorded for it in
the code comments or in an earlier report. Numerical tolerances (`ZERO_TOL`, `TIE_TOL`),
sample sizes (die, challenge and bootstrap counts) and defined physical constants
(`C_LIGHT`) are excluded. Where nothing states where a value came from, the entry reads
"no source recorded" rather than being given a plausible citation.

| Parameter | Value | Used in | Source found |
|---|---|---|---|
| `DC_LAMBDA_3DB` | 1574.2 nm | `coupler.py:27`; every coupler and switch spectrum | §6.1 — fit of `mesh_t20_model` to the 25 points of `data/fig4d_T20_digitized.csv`, digitized from the paper's Fig 4d, solved jointly with `SIGMA_SPLIT` by alternating the two fits to a fixed point |
| `DC_SLOPE` | 0.0026 rad/nm | `coupler.py:28`; the same spectra | §6.1 — the same fit; pairs bootstrap [0.00239, 0.00285] rad/nm |
| `PROP_LOSS_DB_CM`, `alpha_db_cm`, `loss_db_cm` | 2.0 dB/cm | `coupler.py:38,111`; `recirculating.py:47,127,136,163,175,202,234,258` | `coupler.py` module docstring — 2.14 dB/cm (arXiv:2111.01792), 2.2 ± 0.8 dB/cm over 19 dies (arXiv:1203.0767), ~2 dB/cm (nanoph-2023-0836) |
| `excess_loss_db` | 0.1 dB per coupler | `coupler.py:60,69`, called from `switching.py:60,95` | `coupler.py` module docstring — directional-coupler excess loss ~0.1–0.8 dB (Optica jlt-35-22-4916) |
| `kappa0` (nominal split) | 0.5 | `coupler.py:49,60,69,88`; `switching.py:51` | no source recorded |
| `peak_loss_db` | 4.4 dB | `coupler.py:105`; fibre-to-fibre link budget | `coupler.py` module docstring — ~4.4 dB grating-coupler insertion loss (arXiv:1203.0767) |
| `bw_1p5db` | 45.0 nm | `coupler.py:105`; fibre-to-fibre link budget | `coupler.py` module docstring — ~45 nm 1.5-dB bandwidth (arXiv:1203.0767) |
| `waveguide_cm` | 0.45 cm | `coupler.py:116`; fibre-to-fibre link budget | the paper's 4.5 mm on-chip path length, the same length the latency row uses; `DOCUMENT_SEARCH_LIST_superseded.md` marks n_g = 4.0 and 4.5 mm as exact from the paper. Not listed in the §6 table. |
| `n_couplers_in_path` | 4 | `coupler.py:116`; fibre-to-fibre link budget | no source recorded |
| `n_grating` | 2 | `coupler.py:117`; fibre-to-fibre link budget | no source recorded |
| `DEMO_LAMBDA0` | 1560.0 nm | `coupler.py:41`; synthetic demo dataset only | no source recorded — §4.2 states it is deliberately independent of the chip fit and says nothing about this chip |
| `DEMO_TRUE_KAPPA0` | 0.5 | `coupler.py:44`; synthetic demo dataset only | no source recorded |
| `DEMO_TRUE_SLOPE` | 0.0042 rad/nm | `coupler.py:45`; synthetic demo dataset only | no source recorded |
| `DEMO_TRUE_QUAD` | −8e-6 rad/nm² | `coupler.py:46`; synthetic demo dataset only | no source recorded |
| `FIG4D_FLOOR_DB` | −26.2 dB | `switching.py:19`; recorded, not added to any reported crosstalk | §6.1 — fitted to the digitized Fig 4d alongside λ₀ and slope; §6.1 also states that its physical origin is not established |
| `prop_db_per_stage` | 0.25 dB per stage | `switching.py:40,86,224`; on-chip insertion loss, all switch spectra | no source recorded |
| `SIGMA_SPLIT` | 0.0182, clipped to [0.3, 0.7] | `switching.py`; bar-state crosstalk | §6.1 — fit of `bar_model` to the 27 points of `data/fig4e_bar_digitized.csv`, digitized from the paper's Fig 4e. Full range 0.0152–0.0707 over the percentile scan and the calibration offset test, which is the quoted uncertainty; the parametric bootstrap [0.0180, 0.0184] is 140 times narrower and covers only the scatter of the points |
| `SIGMA_PHASE` | 0.02 rad | `switching.py`; bar-state crosstalk | no source recorded — the Fig 4e curve constrains only the combination of the two spreads, so this one is held rather than fitted (§6.1) |
| `ARM_LOSS_DB` | (0.0, 0.0) dB | `switching.py:172`; the MZI phase section | no source recorded |
| `MEAS_NOISE_SIGMA` | 0.01 rad per MZI | `ppuf.py:30`; PUF reliability | recorded in the code itself, `MEAS_NOISE_SOURCE`: "assumed value, not taken from the paper; reliability scales with it" |
| `N` (PUF mesh ports) | 8 | `ppuf.py:57,68,99,162`; every PUF statistic | no source recorded |
| `r` (ring self-coupling) | 0.92 | `mrm.py:20,29`; monitoring curve and extinction ratio | no source recorded — §6.2 records that the MRM ring is not tabulated in the paper; `DOCUMENT_SEARCH_LIST_superseded.md` DOC-3 lists r as a value to be obtained, and it was not obtained |
| `a` (round-trip amplitude) | 0.90 | `mrm.py:20,29`; monitoring curve and extinction ratio | no source recorded — the same DOC-3 entry |
| `data_swing` | 0.9 rad | `mrm.py:29`; the two symbol levels | no source recorded — DOC-3 lists the V_swing/V_π conversion as outstanding |
| `bw` (eye one-pole bandwidth) | 0.45 per bit period | `mrm.py:65`; eye figure only | no source recorded — the eye is labelled illustrative |
| `noise` (eye detector noise) | 0.02 a.u. | `mrm.py:65`; eye figure only | no source recorded — the same |
| `ring_um` (all-pass validation ring) | 120.0 µm | `recirculating.py:127,136`; solver validation only | no source recorded — a validation geometry, not a chip value |
| `ring_um` / `base_um` (add-drop and bus rings) | 600.0 µm | `recirculating.py:163,175,233,267`; solver validation and the comb figure | no source recorded — the same |
| `detune` (ring-to-ring detuning) | 0.004 | `recirculating.py:233`; the comb figure | no source recorded — the same |
| `N_RESTARTS` | 15 | `nn_iris.py:22`; every Iris accuracy | no source recorded |
| `test_size` (Iris split) | 0.3 | `nn_iris.py:36`; every held-out Iris accuracy | no source recorded — §3 records that the paper's evaluation set is not established |
| L2 penalty on the trained parameters (inline literal) | 1e-4 | `nn_iris.py:76`; every Iris accuracy | no source recorded |

Two of these carry more weight than the rest. The 0.25 dB per-stage propagation loss sets
the on-chip insertion loss that §5 item 5 reports as low against the paper's measurement,
and `MEAS_NOISE_SIGMA` sets the PUF reliability of row 25. Neither was tuned to improve
agreement with the paper. The 0.02 rad arm-phase spread still sets part of the bar-state
crosstalk, but it no longer sets it outright: `SIGMA_SPLIT` is now fitted and dominates it
by about fifty to one (§6.1).

### 6.4 Details taken from the preprint

A second source is used from here on: Y. Zhu *et al.*, "Versatile silicon integrated photonic
processor: a reconfigurable solution for next-generation AI clusters", arXiv:2504.01463v2.
It is an **earlier version** of the published article this repository reproduces, and some of
its numbers differ from the published ones. **Wherever the two disagree the published value
is the one kept**, with one stated exception noted below. `docs/PREPRINT_NOTES.md` carries
the same material with the section reference for every item.

**Chip and mesh**

* The chip carries 20 optical ports, split equally between two opposite edges and coupled
  through two fibre arrays, with the gratings spaced 222.22 µm apart (preprint §4.1;
  the fibre arrays are also mentioned in §2.1).
* The chip footprint is 3.8 × 3 mm², and the mesh waveguides are 450 nm wide
  (preprint §4.1).
* The waveguide lengths between MZIs inside the square mesh are designed to be equal,
  whereas the lengths from the gratings to the MZIs are not; those grating sections carry
  no phase shifter, so their mismatch cannot be calibrated out (preprint §3).
* For the unitary function a rectangular mesh is embedded in the square mesh: the vertical
  MZIs and the horizontal MZIs on the edges act as routing cells, and part of the
  horizontal MZIs act as the functional cells (preprint §2.1, compilation).

**PUF design**

* The PUF design is rotationally symmetric. Two nominally equal-power beams enter
  diagonally opposite input ports, and because the structure is symmetric under the
  rotation the powers leaving corresponding output ports are equal in the nominal device
  (preprint §2.5).
* A challenge bit is a programming voltage, its high level nominally the cross state and
  its low level nominally the bar state, and the same voltage is applied to every MZI that
  sits at an equivalent logical position under the rotation (preprint §2.5).
* A response bit is 1 when the first output of a corresponding pair is at least as large as
  the second, and 0 otherwise (preprint §2.5).
* The simulated 100-die arm-length difference between the two arms of every MZI is Gaussian
  with mean −0.08 µm and standard deviation 0.11 µm (preprint §2.5).

**Where the preprint and the published article disagree**

Published values are those already recorded in this repository, in `results.json` and in
§6 above. The published value is kept in every case.

| Quantity | Preprint (arXiv:2504.01463v2) | Published (this repository) | Same? |
|---|---|---|---|
| Intra-die Hamming distance, 2 dies | 2.55% (§2.5) | 2.55% | same |
| Inter-die Hamming distance, 2 dies | 57.71% (§2.5) | 57.71% | same |
| Two-die uniformity (mean proportion of '1') | 42.33% (§2.5) | 42.62% | **differs** |
| 100-die simulated uniqueness | 49.97% (§2.5) | 49.97% | same |
| 100-die simulated uniformity | 50.15% (§2.5) | 50.15% | same |
| Switch crosstalk at 1560 nm | at least −20 dB, up to −40 dB (§2.4) | −45 to <−20 dB | **differs** (best case 5 dB apart) |
| Switch crosstalk bandwidth | under −15/−20 dB over more than **2 nm** (§2.4) | over more than **20 nm** | **differs** by a factor of ten |
| Unitary effective bits | 10.7 bits at σ² = 0.0012 (§2.2) | 6.22 bits at σ = 0.0269 | **differs** |
| Non-unitary effective bits | 7.32 bits at σ² = 0.0125 (§2.2) | 5.47 bits at σ = 0.0453 | **differs** |
| Arm-length difference mean μ | −0.08 µm (§2.5) | +0.08 µm as transcribed in `ppuf.py` | **differs in sign** |

Two of these need more than a value comparison.

**The effective-bit rows differ in convention as well as in value.** The preprint's figures
are log₂(2/σ²) on the variance: log₂(2/0.0012) = 10.70 and log₂(2/0.0125) = 7.32. The
published figures are log₂(2/σ) on the standard deviation: log₂(2/0.0269) = 6.2163 and
log₂(2/0.0453) = 5.4643. `lightin/metrics.py` implements the published convention, and the
noise figures themselves also moved between versions (σ² = 0.0012 corresponds to
σ = 0.0346, not to the published 0.0269). Neither the convention nor the noise figure
carries over, so nothing from the preprint is used for these rows.

**The arm-length mean differs in sign only.** The preprint states μ = −0.08 µm. `ppuf.py`
recorded μ = +0.08 µm and attributed it to the published Methods and Supplementary Note 8.
The published article is not distributed with this repository, so which of the two carries
the sign error cannot be checked here. The sign is corrected to −0.08 µm on the preprint's
authority, which is the one case in this repository where a preprint value is preferred to
a transcribed published one; it is flagged here because it is an exception to the rule
stated at the top of this subsection.

### 6.5 The vertex wiring, and what is conditional on it

The mesh's cells and their lengths follow the preprint, but how the waveguides are routed
where four cells meet does not: the paper's Fig. 1 layout was not available. That routing
is a stated choice, and every number from the recirculating mesh is conditional on it.

It was searched rather than picked. An interior vertex of the lattice carries **eight**
ports, not four -- each of the four incident PUC ends has two waveguides -- so a vertex
wiring is a perfect matching of eight labelled ports, of which there are 7!! = 105; a
degree-3 boundary vertex has six ports and 15 matchings. `lightin/wiring_search.py`
generates all 105 and keeps the **25** that are invariant under the half turn. Of those,
**twelve** reach all 40 cells from one injection port with both injected beams able to
interfere. The two best by a stated ranking -- all cells reachable, then interference, then
the port split, then the number of response pairs carrying light -- are `WIRING_C4_FREE_1`
and `WIRING_C4_FREE_2`.

The enumeration is exhaustive over *uniform* rules, one matching applied at every vertex.
It is **not** exhaustive over all global wirings, since a real layout may use different
matchings at different vertices; that space is not enumerated, and nothing here is a
theorem about every wiring of the lattice.

The preprint fixes the port count and placement -- 20 ports, ten on each of two opposite
edges -- but not which boundary end each attaches to. `lightin/square_mesh.py` attaches a
grating waveguide of a stated 250 um to each of 20 boundary ends, ten on the top edge and
their half-turn images on the bottom, so that the set of 20 maps onto itself under the half
turn. Which ten, and which pair is injected, are chosen by search on the stated criterion
that every response pair should carry light. Under equal grating lengths that waveguide is
a common factor and cancels out of every comparison; the preprint says the real sections
are *not* equal, and that non-uniformity is not modelled.

Boundary ends that carry no grating are left terminated rather than declared external.
With that accounting the lossless mesh conserves energy exactly, which is the check that
the wiring neither loses nor creates power.

---

## 7. Open items

* `python -m pytest -q` takes about 45 seconds on this machine, because
  `test_fig4d_digitized_fit` calls only the two single fits (`fit_proxy` and `fit_mesh`)
  instead of `fit_fig4.main()` with its bootstraps, `test_iris_accuracy` runs five random
  restarts rather than the fifteen the reported accuracies use, and every Fig 4e check
  runs at a few hundred fabrication realisations rather than 3200. The best restart is
  kept, so the test's accuracy is a lower bound on the reported one. A full `python
  scripts/run_all.py` takes about 62 minutes, most of it the Fig 4e bootstrap and the
  percentile scan above it; `python scripts/run_all.py --quick` runs the same pipeline
  with the Iris seed sweep cut to two seeds and every Fig 4d and Fig 4e bootstrap to 50
  resamples, writing `results_quick.json` and `figures_quick/` so that a quick run never
  overwrites the reported outputs. Quick-mode numbers are noisier and are not the ones
  quoted here.
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
* The rotational symmetry of the PUF design is reproduced from the preprint's description,
  but the specific MZI index groups shown in the paper's Fig. 5 were not read, so the orbit
  construction here may not match the chip's.
* The population spread of the PUF metrics is reported across ten seeds; the die counts
  used here (40 for the sweeps, 100 for the headline run) are smaller than a full
  characterisation would use.
* The vertex wiring of the recirculating mesh is a stated choice, not the paper's, and the
  search over it is exhaustive only over uniform rules (§6.5). Every recirculating-PUF number
  is conditional on that choice, mitigated but not removed by the two wirings agreeing to
  0.0002 on uniqueness.
* One of the two fabrication spreads is still assumed, because the bar-state data
  constrains only their combination.
* Twenty-two of the parameters in §6.3 have no source recorded anywhere in this
  repository: the nominal 0.5 coupler split; `n_couplers_in_path` = 4 and `n_grating` = 2 in the link
  budget; the four synthetic-demo constants `DEMO_LAMBDA0`, `DEMO_TRUE_KAPPA0`,
  `DEMO_TRUE_SLOPE` and `DEMO_TRUE_QUAD`; the 0.25 dB per-stage propagation loss; the 0.02
  rad arm-phase spread `SIGMA_PHASE` and `ARM_LOSS_DB` in `switching.py`;
  the 8-port PUF mesh size; the MRM ring's `r` = 0.92, `a` = 0.90 and `data_swing` = 0.9
  together with the eye model's `bw` = 0.45 and `noise` = 0.02; the 120 µm and 600 µm
  validation-ring lengths and the 0.004 ring detuning in `recirculating.py`; and
  `N_RESTARTS` = 15, the 0.3 test fraction and the 1e-4 L2 penalty in `nn_iris.py`. Each is
  a value someone chose. `MEAS_NOISE_SIGMA` is the one assumed parameter whose status is
  already recorded in the code; the rest are not.
