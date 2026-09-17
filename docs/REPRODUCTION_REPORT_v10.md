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
| 2 | 4×4 permutation matrices (Fig. 2d) | realised by routing | routing fidelity **0.999999999999<!--{unitary.perm_routing_fidelity[0]}-->** (both) | **B** |
| 3 | 4×4 random unitaries (Fig. 2h,i) | high-fidelity realisation | fidelity **1.000000<!--{unitary.random_mean_fidelity}-->**, \|·\| corr **1.000000<!--{unitary.random_mean_modulus_corr}-->** (ideal couplers) | **B** |
| 4 | Unitary effective bits @10 GBaud (Fig. 2f) | σ=0.0269 → **6.22 bit** | log₂(2/0.0269) = **6.2163<!--{unitary.enob_at_sigma_0.0269}--> bit** | **A exact** |
| 5 | Non-unitary 3×3 mesh (Fig. 2l) | modulus agreement | \|·\| corr **1.000000<!--{nonunitary.modulus_corr}-->**, max err **7.8e-16<!--{nonunitary.max_abs_err}-->** (ideal couplers) | **B** |
| 6 | Non-unitary input/output correlation (Fig. 2n) | measured on chip | not reproduced | **hardware — not reproduced** |
| 7 | Non-unitary effective bits (Fig. 2f) | σ=0.0453 → **5.47 bit** | log₂(2/0.0453) = **5.4643<!--{nonunitary.enob_at_sigma_0.0453}--> bit** | **A exact** |
| 8 | Iris classification, full set (Fig. 2o,p) | **94.67%** offline | **95.47%<!--{iris.seed_sweep.full_acc_mean}--> ± 1.26%<!--{iris.seed_sweep.full_acc_std}-->** over 10 seeds | **B** |
| 9 | Iris classification, held out | — (the paper's 93.33% is an on-chip measurement and is not comparable) | **89.33%<!--{iris.seed_sweep.test_acc_mean}--> ± 5.14%<!--{iris.seed_sweep.test_acc_std}-->** over 10 seeds | **B** |
| 10 | Iris identity control | — | **85.60%<!--{iris.identity_control.full_acc_mean}--> ± 0.44%<!--{iris.identity_control.full_acc_std}-->** full set, **81.56%<!--{iris.identity_control.test_acc_mean}--> ± 4.67%<!--{iris.identity_control.test_acc_std}-->** held out | control |
| 11 | Iris logistic baseline | — | **96.53%<!--{iris.logistic_baseline.full_acc_mean}--> ± 0.88%<!--{iris.logistic_baseline.full_acc_std}-->** full set, **94.89%<!--{iris.logistic_baseline.test_acc_mean}--> ± 3.45%<!--{iris.logistic_baseline.test_acc_std}-->** held out | control |
| 12 | On-chip latency | ~60 ps | n_g·L/c = **60.04<!--{latency_on_chip_ps}--> ps** (4.5 mm, n_g=4) | **A exact** |
| 13 | Throughput | **1.92 TOPS** | **1.92<!--{throughput_energy.tops}--> TOPS** from the Supp Note 3 op count | **consistency check** |
| 14 | Energy | **1.875 pJ/MAC** | 1.8<!--{throughput_energy.P_total_W}--> W ÷ 9.6e11<!--{throughput_energy.mac_rate}--> MAC·s⁻¹ = **1.875<!--{throughput_energy.energy_pj_per_mac}--> pJ/MAC** | **consistency check** |
| 15 | MRM locking (Fig. 3c) | monitoring peaks at high-ER lock | monitoring peak at bias **−0.448<!--{mrm.lock_bias}-->**; ER up to **18.46<!--{mrm.max_er_db}--> dB** | **B** (model) |
| 16 | Eye-diagram SNR / Q (Fig. 3d–f) | ~17–18 dB SNR, Q ~7–8 | illustrative model eye only | **hardware — not reproduced** |
| 17 | Switch crosstalk at 1560 nm, cross state (Fig. 4d) | −45 to <−20 dB | cross **−27.16<!--{switching.cross_xtalk_center_db[1]}--> to −21.06<!--{switching.cross_xtalk_center_db[0]}--> dB** | **model vs measurement** |
| 17b | Switch crosstalk at 1560 nm, bar state (Fig. 4e) | −45 to <−20 dB | bar **−106.67<!--{switching.bar_xtalk_center_db[1]}--> to −30.50<!--{switching.bar_xtalk_center_db[0]}--> dB**; both fabrication spreads are assumed at 0.02 (§6.3), and Fig 4e is a consistency check on that rather than a fit (§6.1) | **model vs measurement** |
| 18 | Switch crosstalk, worst inside the fitted range | <−15/−20 dB over >20 nm | cross **−16.77<!--{switching.cross_worst_xtalk_fitrange_db}--> dB** over 1549–1565 nm | **model vs measurement** |
| 19 | Switch crosstalk, worst extrapolated below the data | <−15/−20 dB over >20 nm | cross **−11.80<!--{switching.cross_worst_xtalk_extrapolated_db}--> dB** over 1530–1549 nm | **model vs measurement** |
| 20 | Mesh T20 model vs digitized Fig 4d | — | RMS **0.79<!--{fig4d_mesh_fit.rms_db}--> dB** over 25<!--{fig4d_mesh_fit.n_points}--> points (single-coupler proxy **1.05<!--{fig4d_fit.rms_db}--> dB**) | **fit to measurement** |
| 20e | Bar-state T32 model vs digitized Fig 4e | — | RMS **0.9013<!--{cross_check.fig4e_rms_at_assumed_spreads_db}--> dB** over 27<!--{fig4e_fit.n_points}--> points at the assumed spread, against **0.4170<!--{fig4e_fit.shape_check.constant_rms_db}--> dB** for the best constant on the same points: the model fixes the level and reproduces none of the wavelength structure, so it has no RMS advantage over a constant and the panel was not adopted as a fit (§6.1) | **model vs measurement** |
| 21 | Measured crosstalk spectra (Fig. 4d,e) | measured | not reproduced; the Fig 4d T20 curve is digitized and used as fit input, the Fig 4e T32 curve and the four Fig 4e diagonals are digitized and used as checks, the rest are not | **hardware — not reproduced** |
| 22 | On-chip insertion loss, 8 paths | **−1.85 to −2.99 dB** (8 measured paths) | **−1.40<!--{switching.onchip_il_max_db}--> to −1.80<!--{switching.onchip_il_min_db}--> dB** (8 modelled paths) | **model vs measurement** |
| 22b | Bar-state insertion loss, per path (Fig. 4e diagonals) | four digitized bar-state through paths, −1.48<!--{switching.bar_il_vs_fig4e.per_port[3].digitized_db}--> to −2.43<!--{switching.bar_il_vs_fig4e.per_port[0].digitized_db}--> dB over 1550<!--{switching.bar_il_vs_fig4e.band_nm[0]}-->–1574<!--{switching.bar_il_vs_fig4e.band_nm[1]}--> nm | model optimistic by **+0.38<!--{switching.bar_il_vs_fig4e.mean_signed_diff_db}--> dB** on average (**0.49<!--{switching.bar_il_vs_fig4e.mean_abs_diff_db}--> dB** absolute); the port-to-port ordering is **not** reproduced, the modelled fabric being symmetric under port reversal (§3, §6.1) | **model vs measurement** |
| 23 | PUF uniqueness, feed-forward mesh (Fig. 5) | **49.97%** (simulation) | **49.00%<!--{ppuf.population_sweep.uniqueness_mean}--> ± 0.34%<!--{ppuf.population_sweep.uniqueness_std}-->** over 10<!--{ppuf.population_sweep.n_seeds}--> population seeds (48.92%<!--{ppuf.uniqueness}--> on the single 100-die seed) | **B** |
| 24 | PUF uniformity, feed-forward mesh (Fig. 5) | **50.15%** (simulation) | **50.32%<!--{ppuf.population_sweep.uniformity_mean}--> ± 0.51%<!--{ppuf.population_sweep.uniformity_std}-->** over 10 seeds (49.39%<!--{ppuf.uniformity}--> on the single 100-die seed) | **B** |
| 25 | PUF reliability | 2.55% intra-die HD (experimental) | **0.72%<!--{ppuf.population_sweep.reliability_mean}-->** at a measurement-noise σ of **0.01<!--{ppuf.measurement_noise_sigma}--> rad** per MZI | **model vs measurement** |
| 23r | PUF uniqueness, recirculating mesh | **49.97%** (simulation) | **49.89%<!--{ppuf_recirc.C4_FREE_1.population_sweep.uniqueness_mean}--> ± 0.25%<!--{ppuf_recirc.C4_FREE_1.population_sweep.uniqueness_std}-->** (C4_FREE_1), **49.93%<!--{ppuf_recirc.C4_FREE_2.population_sweep.uniqueness_mean}--> ± 0.28%<!--{ppuf_recirc.C4_FREE_2.population_sweep.uniqueness_std}-->** (C4_FREE_2), over 10 seeds | **model vs simulation** |
| 24r | PUF uniformity, recirculating mesh | **50.15%** (simulation) | **50.01%<!--{ppuf_recirc.C4_FREE_1.population_sweep.uniformity_mean}--> ± 0.88%<!--{ppuf_recirc.C4_FREE_1.population_sweep.uniformity_std}-->** (C4_FREE_1), **49.88%<!--{ppuf_recirc.C4_FREE_2.population_sweep.uniformity_mean}--> ± 0.94%<!--{ppuf_recirc.C4_FREE_2.population_sweep.uniformity_std}-->** (C4_FREE_2) | **model vs simulation** |
| 25r | PUF reliability, recirculating mesh | 2.55% intra-die HD (experimental) | **0.76%<!--{ppuf_recirc.C4_FREE_1.population_sweep.reliability_mean}--> ± 0.06%<!--{ppuf_recirc.C4_FREE_1.population_sweep.reliability_std}-->** (C4_FREE_1), **0.77%<!--{ppuf_recirc.C4_FREE_2.population_sweep.reliability_mean}--> ± 0.06%<!--{ppuf_recirc.C4_FREE_2.population_sweep.reliability_std}-->** (C4_FREE_2), at an assumed noise | **model vs measurement** |
| 26 | PUF experimental, 2 dies | 57.71% / 42.62% / 2.55% | not reproduced | **hardware — not reproduced** |
| 27 | Recirculating-mesh solver | — | ring **2.9e-16<!--{recirculating.ring_rms}-->**, add-drop **8.4e-16<!--{recirculating.add_drop_rms}-->** vs analytic | **B** |

Row 25 carries a model input as well as a model output. The measurement-noise standard
deviation is 0.01<!--{ppuf.measurement_noise_sigma}--> rad per MZI (`measurement_noise_sigma`), and its source is recorded as
an assumed value, not taken from the paper (`measurement_noise_source`). The modelled
reliability scales with that value: a larger assumed noise flips more bits between
re-measurements and gives a larger intra-die Hamming distance, so 0.72%<!--{ppuf.population_sweep.reliability_mean}--> is a statement
about the assumption as much as about the mesh.

---

## 3. Notes on the modelling choices

Rows 2, 3 and 5 assume ideal 50:50 couplers. `lightin/puc.py` builds its universal 2-DOF
MZI from a wavelength-independent beamsplitter `(1/√2)[[1, i], [i, 1]]`, and `unitary.py`
and `nonunitary.py` are built on that block. The fidelities of 1.000000<!--{unitary.random_mean_fidelity}--> in rows 3 and 5
are therefore statements about the mesh algebra — that a Clements decomposition and an
SVD/diamond realisation are implemented correctly — and not about what this chip's
couplers would achieve.

The coupler actually fitted to the chip's own Fig 4d data is 50:50 at 1574.7<!--{fig4d_mesh_fit.lambda0_nm}--> nm, not at
the 1560 nm design wavelength (§6.1). At 1560 nm its power coupling is 0.462<!--{coupler.power_coupling_at_1560}-->
(`coupler.power_coupling_at_1560`) rather than 0.500, and that imbalance alone caps the
fidelity of the single-θ cross state at 0.9942<!--{expressivity.coupler_ceiling_fidelity_at_1560}--> (`coupler_ceiling_fidelity_at_1560`). Over
the 1530<!--{expressivity.coupler_ceiling_range_nm[0]}-->–1565<!--{expressivity.coupler_ceiling_range_nm[1]}--> nm sweep (`coupler_ceiling_range_nm`) the ceiling falls as low as 0.9469<!--{expressivity.coupler_ceiling_min_fidelity}-->
(`coupler_ceiling_min_fidelity`). Rows 3 and 5 should be read against that ceiling: the
ideal-coupler mesh reaches 1.000000<!--{unitary.random_mean_fidelity}-->, and a mesh built from the chip's own coupler would
not.

Unitary mesh (rows 2–3). Arbitrary unitaries are realised on a universal Clements
rectangular mesh of 2-DOF MZIs; the programming phases are fitted, then the realised
matrix is rebuilt independently from the physical MZI matrices, so fidelity = 1 is a
genuine check rather than a tautology. The permutations of Fig. 2d are treated the same
way: `_best_routing` optimises the single-θ mesh phases and reports the fraction of input
power that actually reaches each target port, giving 0.999999999999<!--{unitary.perm_routing_fidelity[0]}--> for both. A
permutation matrix compared against itself would give 1 by construction and would test
nothing, so the routing optimisation is what makes row 2 a measurement.

The paper's physical single-θ PUC (Eq. 1) has one DOF per cell and therefore limited
unitary expressivity, acknowledged in the paper's Discussion and quantified in §4.1.

Effective bits (rows 4, 7). The paper's 6.22 and 5.47 bit follow from
ENOB = log₂(range/σ) with range = 2 (outputs in [−1, 1]). Both reproduce to two decimals,
which also confirms the convention.

Non-unitary (rows 5–6). The SVD/diamond realisation is checked by element-modulus
agreement: correlation 1.000000<!--{nonunitary.modulus_corr}--> and maximum absolute error 7.8e-16<!--{nonunitary.max_abs_err}-->. That is the whole of
the simulation check. Fig. 2n is the chip's measured input/output correlation; comparing
the model's output vector against a copy of itself would return 1.0 while measuring
nothing, so no vector correlation is reported.

Iris (rows 8–11). The photonic layer is a trainable 4×4 unitary whose four detected
intensities feed a small learned linear readout, consistent with the paper's offline
training. Reporting a single seed is not defensible here: over 10 seeds (the seed drives
both the 70/30 stratified split and the 15 random restarts) the full-set accuracy is
95.47%<!--{iris.seed_sweep.full_acc_mean}--> ± 1.26%<!--{iris.seed_sweep.full_acc_std}--> and the held-out accuracy 89.33%<!--{iris.seed_sweep.test_acc_mean}--> ± 5.14%<!--{iris.seed_sweep.test_acc_std}-->. The paper's 94.67% sits
comfortably inside that spread, so agreement at one seed is not evidence of much.

Two controls put the number in context, both on the same splits:

* Identity control — the unitary frozen to I, only the readout trained: 85.60%<!--{iris.identity_control.full_acc_mean}--> ± 0.44%<!--{iris.identity_control.full_acc_std}-->
  full set, 81.56%<!--{iris.identity_control.test_acc_mean}--> ± 4.67%<!--{iris.identity_control.test_acc_std}--> held out. The programmable unitary is therefore worth about
  10<!--{iris.unitary_minus_identity_full_acc|pct}--> points, which is a real contribution.
* Logistic baseline — plain multinomial logistic regression on the same four standardized
  features: 96.53%<!--{iris.logistic_baseline.full_acc_mean}--> ± 0.88%<!--{iris.logistic_baseline.full_acc_std}--> full set, 94.89%<!--{iris.logistic_baseline.test_acc_mean}--> ± 3.45%<!--{iris.logistic_baseline.test_acc_std}--> held out. Because the two sweeps run
  the same seeds and the seed fixes the split, they can be differenced seed by seed
  (`paired_logistic_minus_photonic`). On the full set the logistic model is ahead by
  1.07<!--{iris.paired_logistic_minus_photonic.full_mean|pct}--> ± 1.30<!--{iris.paired_logistic_minus_photonic.full_std|pct}--> points, winning on 7<!--{iris.paired_logistic_minus_photonic.full_n_logistic_higher}--> of the 10 seeds, tying on 2<!--{iris.paired_logistic_minus_photonic.full_n_equal}--> and losing on 1<!--{iris.paired_logistic_minus_photonic.full_n_photonic_higher}-->; the
  absolute paired mean is smaller than the paired standard deviation, so that difference
  is within the seed-to-seed spread. On the held-out split it is ahead by 5.56<!--{iris.paired_logistic_minus_photonic.test_mean|pct}--> ± 3.67<!--{iris.paired_logistic_minus_photonic.test_std|pct}-->
  points, winning on 9<!--{iris.paired_logistic_minus_photonic.test_n_logistic_higher}--> seeds, tying on 1<!--{iris.paired_logistic_minus_photonic.test_n_equal}--> and losing on none; there the absolute paired
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
average half of the 90<!--{throughput_energy.P_pi_mW}--> mW π-power, gives 45<!--{throughput_energy.P_avg_per_mzi_mW}--> mW per cell and 1.8<!--{throughput_energy.P_total_W}--> W across the 40 cells;
dividing by the 4×4 MAC rate of 9.6e11<!--{throughput_energy.mac_rate}--> MAC·s⁻¹ at 10 GBaud yields 1.875<!--{throughput_energy.energy_pj_per_mac}--> pJ/MAC, and the
Supplementary op count gives 1.92<!--{throughput_energy.tops}--> TOPS. The 3 V across 100 Ω, the 90 mW, and the
96-operation count all come from Supplementary Note 3 and cannot be checked against the
main article.

Switching (rows 17–22). The 4-stage planar (Spanke-Beneš) topology is a rectangular mesh
of nearest-neighbour 2×2 switches. The cross-state crosstalk is produced by the
coupled-mode-theory coupler of §4.2 rather than by a hand-set slope; the bar-state
crosstalk is now produced by a coupler-split spread fitted to Fig 4e, with the arm-phase
spread still assumed, as the next paragraphs and §6.3 set out. The loss still comes from
assumed constants. At 1560 nm the model gives
cross-state crosstalk of −27.16<!--{switching.cross_xtalk_center_db[1]}--> to −21.06<!--{switching.cross_xtalk_center_db[0]}--> dB and bar-state −106.67<!--{switching.bar_xtalk_center_db[1]}--> to −30.50<!--{switching.bar_xtalk_center_db[0]}--> dB, against
the paper's −45 to <−20 dB.

The worst case over wavelength is reported as two separate numbers, because only one of
them is backed by data:

| Range | Status | Worst cross-state crosstalk |
|---|---|---|
| **1549–1565 nm** | inside the wavelengths digitized from Fig 4d (1549–1587 nm) | **−16.77<!--{switching.cross_worst_xtalk_fitrange_db}--> dB** |
| **1530–1549 nm** | below every digitized point; model extrapolation | **−11.80<!--{switching.cross_worst_xtalk_extrapolated_db}--> dB** |

Inside the fitted range, the model meets the −15 dB figure (worst −16.77<!--{switching.cross_worst_xtalk_fitrange_db}--> dB) but not the
−20 dB figure. These are predictions of a model constrained by one digitized port pair,
not measurements of the other port pairs. The digitized T20 curve itself reaches −14.1 dB
at 1549.0 nm, within its ±2 dB digitization uncertainty. (That −14.1 dB is read directly
from `data/fig4d_T20_digitized.csv` and is not a `results.json` value.) The extrapolated
number is 5.0 dB worse again, and it rests entirely on the model: no digitized point
exists below 1549 nm, so −11.80<!--{switching.cross_worst_xtalk_extrapolated_db}--> dB is what the coupled-mode-theory coupler predicts when
run past the edge of its own fit, not something the chip's published data supports. It
should be read as a projection, and it is the pessimistic half of the band.

The two states do not leak for the same reason, and `leak_mechanism_check` in
`results.json` separates them on one switch cell at 1560 nm.

The cross state leaks because a single directional-coupler design is 3-dB at only one
wavelength (§4.2). At 1560 nm the fitted coupler splits 0.462<!--{coupler.power_coupling_at_1560}--> rather than 0.500, and it is
that offset common to both couplers, rather than any difference between them, that the
cross state cannot cancel. Forcing both couplers to an exact 50:50 split drops the cell's
leakage from −25.69<!--{switching.leak_mechanism_check.cross_cell_leak_db_model}--> dB (`cross_cell_leak_db_model`) to −32.87<!--{switching.leak_mechanism_check.cross_cell_leak_db_ideal_coupler}--> dB
(`cross_cell_leak_db_ideal_coupler`), an improvement of 7.18<!--{switching.leak_mechanism_check.cross_ideal_coupler_improvement_db}--> dB, and the leakage moves with
wavelength because the split does. That is the mechanism behind rows 17–19.

The bar state leaks for a different reason. Its unintended-port amplitude is proportional
to the *difference* between the two couplers' coupling angles, which is fixed at
fabrication and does not depend on wavelength at all; the arm phase error contributes a
second, independent term. Both are drawn in `switching.py` from Gaussians. Their standard
deviations are `SIGMA_SPLIT` and `SIGMA_PHASE`, and exactly one of the two is now fitted:
Both are 0.02 with no recorded source (§6.3). The digitized Fig 4e curve was fitted for
`SIGMA_SPLIT` and the fitted value was not adopted, because on those points the model does
no better than a constant and the spread it returns moves by a factor of 4.6 with a choice
the figure does not fix; 0.02 lies inside that range, so the panel is recorded as a
consistency check (§6.1). Set both to zero and the bar state nulls exactly, below the
1e-20<!--[lightin.switching.ZERO_TOL]--> structural-zero threshold. Leave them and the cell leaks −29.81<!--{switching.leak_mechanism_check.bar_cell_leak_db_model}--> dB
(`bar_cell_leak_db_model`); ideal 50:50 couplers, which remove the split imbalance but
leave the phase error, give −32.87<!--{switching.leak_mechanism_check.bar_cell_leak_db_ideal_coupler}--> dB (`bar_cell_leak_db_ideal_coupler`).

The bar-state numbers are therefore a statement about two assumed spreads, and they would
move if either were set differently. What the measured panel adds is a bound rather than a
value: the leakage Fig 4e shows is where a 0.02 split spread puts it, and the two spreads
enter that one level in a combination a single curve cannot separate, so neither can be
read off it (§6.1).

Two mechanisms are ruled out by the same three cases. Unequal arm loss cannot produce
either state's leakage: the phase section is diag(e^(i(θ+ε)), 1), both entries of modulus
exactly 1, so the two arms carry identical loss (`ARM_LOSS_DB`), and every loss term in a
cell — the 0.1 dB coupler excess loss and the 0.25 dB per-stage propagation — is a scalar
prefactor on the whole 2×2 that reaches both output ports equally. Setting both arms to the
mean of the two arm losses is consequently a no-op: `bar_cell_leak_db_equal_arm_loss` =
−29.81<!--{switching.leak_mechanism_check.bar_cell_leak_db_equal_arm_loss}--> dB and `cross_cell_leak_db_equal_arm_loss` = −25.69<!--{switching.leak_mechanism_check.cross_cell_leak_db_equal_arm_loss}--> dB equal their `_model`
counterparts to the last digit, and the full-fabric bar-state centre range under that
substitution, `bar_center_db_equal_arm_loss`, is [−30.50<!--{switching.leak_mechanism_check.bar_center_db_equal_arm_loss[0]}-->, −106.67<!--{switching.leak_mechanism_check.bar_center_db_equal_arm_loss[1]}-->] dB — the shipped
`bar_xtalk_center_db` unchanged. Coupler dispersion is ruled out for the bar
state alone: moving the fitted 3-dB wavelength by 14.7 nm shifts the bar-state values by
hundredths of a dB while the cross-state values move by several.

Both states report 0<!--{switching.cross_structural_zeros}--> structural zeros (`cross_structural_zeros` and
`bar_structural_zeros`): no port pair was excluded from the crosstalk statistics for
carrying no power, so the numbers above are over every off-target path. A pair is counted
as a structural zero only when its raw linear transmission falls below 1e-20<!--[lightin.switching.ZERO_TOL]-->, and the test
is made on that raw power rather than on a decibel value, so no additive constant can
manufacture a floor. The lowest bar-state entry, input 0 to output 3, sits at a raw
transmission well below the rest (−106.67<!--{switching.bar_xtalk_center_db[1]}--> dB); reaching that port takes three off-target
couplings, which is why it is so far below the rest and why it is a real model prediction
rather than a numerical artefact. Each of those three couplings is one factor of the
coupler-imbalance and arm-phase terms above, so −106.67<!--{switching.bar_xtalk_center_db[1]}--> dB is roughly three times as far
from the paper's data as the −30.50<!--{switching.bar_xtalk_center_db[0]}--> dB entry is. Neither should be read as a crosstalk the
chip would show at that port: the Fig 4e curve constrains one port pair, T32, and the
model carries one assumed spread to all sixteen.

The fitted crosstalk floor of −26.2<!--{switching.chip_crosstalk_floor_db}--> dB (`chip_crosstalk_floor_db`) is recorded in
`switching.py` as `FIG4D_FLOOR_DB` and is deliberately not added to any crosstalk this
module reports. Adding it would state a floor the mesh model does not predict. Its meaning
runs the other way: modelled crosstalk below −26.2<!--{switching.chip_crosstalk_floor_db}--> dB is not reached on the chip.

The on-chip insertion loss of row 22 is the transmission of each intended path through the
fabric alone, which carries the mesh's propagation and coupler excess losses and no
grating couplers. Over the eight intended paths — four inputs in the all-cross state and
four in the all-bar state — the model gives −1.40<!--{switching.onchip_il_max_db}--> to −1.80<!--{switching.onchip_il_min_db}--> dB (`onchip_il_min_db`,
`onchip_il_max_db`), against the paper's measured −1.85<!--{switching.onchip_il_paper_range_db[1]}--> to −2.99<!--{switching.onchip_il_paper_range_db[0]}--> dB
(`onchip_il_paper_range_db`). The two ranges do not overlap: the model's most-lossy path,
at −1.80<!--{switching.onchip_il_min_db}--> dB, is still 0.05<!--{switching.onchip_il_gap_nearest_db}--> dB better than the paper's least-lossy measured path at
−1.85<!--{switching.onchip_il_paper_range_db[1]}--> dB. End to end the model is optimistic by 0.45<!--{switching.onchip_il_gap_least_lossy_db}--> dB at the least-lossy end and by
1.19<!--{switching.onchip_il_gap_most_lossy_db}--> dB at the most-lossy end. The loss parameters were left unchanged rather than tuned
   to close that gap, so the disagreement stays visible. Separately, the fibre-to-fibre
   link budget at 1560 nm is 11.43<!--{switching.fibre_to_fibre_loss_db}--> dB (`fibre_to_fibre_loss_db`), dominated by the two
   grating couplers; it is a different quantity from the on-chip loss and is not
   comparable with the paper's on-chip range.

Row 22b is the same disagreement measured a different way, and it is the sharper of the
two. The paper quotes one range over eight paths and does not say which path or which
switch state either end belongs to, so row 22 can only compare a range with a range. The
four digitized Fig 4e diagonals are four *measured* bar-state insertion losses, one per
intended path, so they can be compared path by path. Over 1550.0<!--{switching.bar_il_vs_fig4e.band_nm[0]}-->–1574.0<!--{switching.bar_il_vs_fig4e.band_nm[1]}--> nm the model is
optimistic on average by 0.38<!--{switching.bar_il_vs_fig4e.mean_signed_diff_db}--> dB (0.49<!--{switching.bar_il_vs_fig4e.mean_abs_diff_db}--> dB absolute), the same direction and about the same
size as row 22 gives.

The per-path comparison also shows something the range comparison cannot, and it is a
disagreement in shape rather than in level. **The fabric model is symmetric under port
reversal: it gives port 0 and port 3 the same loss, −1.40<!--{switching.bar_il_vs_fig4e.per_port[0].model_db}--> dB, and port 1 and port 2 the
same loss, −1.80<!--{switching.bar_il_vs_fig4e.per_port[1].model_db}--> dB. The four digitized losses instead fall monotonically with port index,
the measured transmission rising from −2.43<!--{switching.bar_il_vs_fig4e.per_port[0].digitized_db}--> dB at port 0 through −2.27<!--{switching.bar_il_vs_fig4e.per_port[1].digitized_db}--> and −1.75<!--{switching.bar_il_vs_fig4e.per_port[2].digitized_db}--> dB to
−1.48<!--{switching.bar_il_vs_fig4e.per_port[3].digitized_db}--> dB at port 3.** Of the six port pairs the model orders 2<!--{switching.bar_il_vs_fig4e.pairs_ordered_correctly}--> correctly and 2<!--{switching.bar_il_vs_fig4e.pairs_ordered_wrongly}--> wrongly,
and ties the remaining 2<!--{switching.bar_il_vs_fig4e.pairs_tied_in_the_model}-->, which is what a symmetric model must do against an asymmetric
chip.

A likely explanation, *proposed rather than tested*: `switching.fabric_matrix` contains
only the mesh — the MZIs and the propagation between them — and the preprint records that
while the waveguide lengths between MZIs inside the square mesh are designed to be equal,
the lengths from the gratings to the MZIs are not, and those grating sections carry no
phase shifter, so their mismatch cannot be calibrated out (preprint §3, recorded in
`docs/PREPRINT_NOTES.md`). A per-port loss that rises across the array would sit in
exactly those sections, outside the fabric this model represents, and a model containing
only a port-symmetric mesh cannot produce it however its loss constants are set. This
reproduction does not model the grating-to-MZI sections at all, so the explanation is a
proposal: it would be tested by adding them with their per-port lengths and seeing whether
the measured ordering follows. Nothing in `switching.py` was changed in response; the
comparison is recorded in `switching.bar_il_vs_fig4e` and discussed in §6.1.

PUF (rows 23–26). A response is a property of one die. The mesh is built once per die as
θ = π·challenge + ε (+ measurement noise), with ε that die's fixed per-MZI phase error;
equal-power light enters the two diagonal ports 0 and N−1 of that single mesh, and bit *i*
compares the two outputs of pair (2i, 2i+1). Both compared intensities therefore come from
the same physical chip. Both injections are needed: in a feed-forward mesh, reaching output
*k* from input 0 costs *k* cross-couplings, so single-edge injection leaves power decaying
monotonically with port index and biases every pair towards its even member; the diagonal
pair has mirror-image decay and the bias cancels.

On one 100-die seed the feed-forward model gives uniqueness 48.92%<!--{ppuf.uniqueness}-->, uniformity 49.39%<!--{ppuf.uniformity}-->,
intra-die reliability 0.74%<!--{ppuf.reliability_intra_die_HD}--> and a tie fraction of 0.0<!--{ppuf.tie_fraction}-->. Across 10<!--{ppuf.population_sweep.n_seeds}--> population seeds of 40
dies it gives 49.00%<!--{ppuf.population_sweep.uniqueness_mean}--> ± 0.34%<!--{ppuf.population_sweep.uniqueness_std}-->, 50.32%<!--{ppuf.population_sweep.uniformity_mean}--> ± 0.51%<!--{ppuf.population_sweep.uniformity_std}--> and 0.72%<!--{ppuf.population_sweep.reliability_mean}--> ± 0.08%<!--{ppuf.population_sweep.reliability_std}-->. The spread across seeds is
comparable to the differences discussed below, so single-seed figures are labelled as such
wherever they appear.

The arm-length mean is negative. `ppuf.py` had recorded the per-MZI arm-length difference as
N(+0.08 um, 0.11 um); the preprint gives N(-0.08 um, 0.11 um) (section 2.5, and §6.4 below),
and the sign is corrected here. It moves the three PUF metrics very little: uniqueness
0.4901 to 0.4892<!--{ppuf.uniqueness}-->, uniformity 0.5012 to 0.4939<!--{ppuf.uniformity}-->, reliability 0.00719 to 0.00735<!--{ppuf.reliability_intra_die_HD}-->, every change
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
**9 response bits**, all 9<!--{ppuf_recirc.live_pairs}--> of which carry light. With no fabrication error every compared
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
| paper, 100-die simulation | **49.97%<!--{ppuf_recirc.vs_feedforward.paired_uniqueness.paper_uniqueness}-->** | **50.15%** | 2.55% (experimental, 2 dies) |
| recirculating, C4_FREE_1 | 49.89%<!--{ppuf_recirc.C4_FREE_1.population_sweep.uniqueness_mean}--> ± 0.25%<!--{ppuf_recirc.C4_FREE_1.population_sweep.uniqueness_std}--> | 50.01%<!--{ppuf_recirc.C4_FREE_1.population_sweep.uniformity_mean}--> ± 0.88%<!--{ppuf_recirc.C4_FREE_1.population_sweep.uniformity_std}--> | 0.76%<!--{ppuf_recirc.C4_FREE_1.population_sweep.reliability_mean}--> ± 0.06%<!--{ppuf_recirc.C4_FREE_1.population_sweep.reliability_std}--> |
| recirculating, C4_FREE_2 | 49.93%<!--{ppuf_recirc.C4_FREE_2.population_sweep.uniqueness_mean}--> ± 0.28%<!--{ppuf_recirc.C4_FREE_2.population_sweep.uniqueness_std}--> | 49.88%<!--{ppuf_recirc.C4_FREE_2.population_sweep.uniformity_mean}--> ± 0.94%<!--{ppuf_recirc.C4_FREE_2.population_sweep.uniformity_std}--> | 0.77%<!--{ppuf_recirc.C4_FREE_2.population_sweep.reliability_mean}--> ± 0.06%<!--{ppuf_recirc.C4_FREE_2.population_sweep.reliability_std}--> |
| feed-forward | 49.00%<!--{ppuf.population_sweep.uniqueness_mean}--> ± 0.34%<!--{ppuf.population_sweep.uniqueness_std}--> | 50.32%<!--{ppuf.population_sweep.uniformity_mean}--> ± 0.51%<!--{ppuf.population_sweep.uniformity_std}--> | 0.72%<!--{ppuf.population_sweep.reliability_mean}--> ± 0.08%<!--{ppuf.population_sweep.reliability_std}--> |

Differenced seed by seed, the recirculating model's uniqueness minus the feed-forward
model's is +0.88%<!--{ppuf_recirc.vs_feedforward.paired_uniqueness.mean}--> ± 0.42%<!--{ppuf_recirc.vs_feedforward.paired_uniqueness.std}--> over the 10 seeds. The absolute paired mean exceeds the paired
standard deviation, so by the rule used for the Iris comparison that is **a consistent
difference** rather than seed-to-seed noise: the recirculating model's uniqueness sits
nearer the paper's 49.97%<!--{ppuf_recirc.vs_feedforward.paired_uniqueness.paper_uniqueness}--> on all 10<!--{ppuf_recirc.vs_feedforward.paired_uniqueness.n_seeds_recirc_closer}--> of the 10 seeds, the feed-forward model on none, with
none tied. That much survives the sweep.

What does not survive is the exactness. The single-seed run reported earlier, in which the
recirculating model returned 49.97%<!--{ppuf_recirc.C4_FREE_1.uniqueness}--> against the paper's 49.97%<!--{ppuf_recirc.vs_feedforward.paired_uniqueness.paper_uniqueness}-->, was one draw from a
distribution whose mean is 49.89%<!--{ppuf_recirc.C4_FREE_1.population_sweep.uniqueness_mean}--> ± 0.25%<!--{ppuf_recirc.C4_FREE_1.population_sweep.uniqueness_std}-->; the paper's value sits 0.3 sample standard
deviations from that mean. The match to four significant figures was luck, and no claim
that this model reproduces the paper's uniqueness exactly is supportable. What the sweep
supports is narrower: over 40-die populations the recirculating model is consistently the
nearer of the two, by 0.88<!--{ppuf_recirc.vs_feedforward.paired_uniqueness.mean|pct}--> points, with both models inside a point of the paper.

**What agreement on uniqueness is worth.** A uniqueness near 50% is the default outcome of
comparing two nominally identical outputs, not a discriminating result: any construction in
which the two compared ports are exchangeable produces it, including the exchangeable model
this reproduction rejected at its first audit. Matching 49.97%<!--{ppuf_recirc.vs_feedforward.paired_uniqueness.paper_uniqueness}--> is therefore weak evidence
on its own, and the two models matching it equally well is what one would expect rather
than a coincidence. The evidence that the response is driven by the device physics is the
sensitivity sweep, not the headline number: uniqueness climbs from 0.2412<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[0].uniqueness}--> at
sigma = 0.001<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[0].sigma_phase}--> to 0.5011<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[5].uniqueness}--> at sigma = 3.0<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[5].sigma_phase}-->, the tie fraction falls from 0.5141<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[0].tie_fraction}--> to 0.0000<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[5].tie_fraction}-->, and
all 9<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[0].live_pairs}--> response pairs carry light throughout, so the bits are being set by the manufacturing
spread rather than by the construction of the comparison.

**Reliability is set by an assumed number.** `MEAS_NOISE_SIGMA` has no recorded source
(§6.3), and reliability is the metric it drives. Sweeping it over the recirculating model
(40 dies x 64 challenges, wiring C4_FREE_1):

| assumed noise sigma (rad) | uniqueness | uniformity | reliability | tie fraction |
|---|---|---|---|---|
| 0.002<!--{ppuf_recirc.C4_FREE_1.noise_sweep[0].meas_noise_sigma}--> | 0.4934<!--{ppuf_recirc.C4_FREE_1.noise_sweep[0].uniqueness}--> | 0.4805<!--{ppuf_recirc.C4_FREE_1.noise_sweep[0].uniformity}--> | 0.0018<!--{ppuf_recirc.C4_FREE_1.noise_sweep[0].reliability}--> | 0.0000<!--{ppuf_recirc.C4_FREE_1.noise_sweep[0].tie_fraction}--> |
| 0.005<!--{ppuf_recirc.C4_FREE_1.noise_sweep[1].meas_noise_sigma}--> | 0.4934<!--{ppuf_recirc.C4_FREE_1.noise_sweep[1].uniqueness}--> | 0.4805<!--{ppuf_recirc.C4_FREE_1.noise_sweep[1].uniformity}--> | 0.0044<!--{ppuf_recirc.C4_FREE_1.noise_sweep[1].reliability}--> | 0.0000<!--{ppuf_recirc.C4_FREE_1.noise_sweep[1].tie_fraction}--> |
| 0.010<!--{ppuf_recirc.C4_FREE_1.noise_sweep[2].meas_noise_sigma}--> | 0.4934<!--{ppuf_recirc.C4_FREE_1.noise_sweep[2].uniqueness}--> | 0.4805<!--{ppuf_recirc.C4_FREE_1.noise_sweep[2].uniformity}--> | 0.0084<!--{ppuf_recirc.C4_FREE_1.noise_sweep[2].reliability}--> | 0.0000<!--{ppuf_recirc.C4_FREE_1.noise_sweep[2].tie_fraction}--> |
| 0.020<!--{ppuf_recirc.C4_FREE_1.noise_sweep[3].meas_noise_sigma}--> | 0.4934<!--{ppuf_recirc.C4_FREE_1.noise_sweep[3].uniqueness}--> | 0.4805<!--{ppuf_recirc.C4_FREE_1.noise_sweep[3].uniformity}--> | 0.0159<!--{ppuf_recirc.C4_FREE_1.noise_sweep[3].reliability}--> | 0.0000<!--{ppuf_recirc.C4_FREE_1.noise_sweep[3].tie_fraction}--> |
| 0.050<!--{ppuf_recirc.C4_FREE_1.noise_sweep[4].meas_noise_sigma}--> | 0.4934<!--{ppuf_recirc.C4_FREE_1.noise_sweep[4].uniqueness}--> | 0.4805<!--{ppuf_recirc.C4_FREE_1.noise_sweep[4].uniformity}--> | 0.0393<!--{ppuf_recirc.C4_FREE_1.noise_sweep[4].reliability}--> | 0.0000<!--{ppuf_recirc.C4_FREE_1.noise_sweep[4].tie_fraction}--> |

No single swept value gives the paper's experimental 2.55%. It falls between sigma = 0.02<!--{ppuf_recirc.C4_FREE_1.noise_sweep[3].meas_noise_sigma}-->
(1.59%<!--{ppuf_recirc.C4_FREE_1.noise_sweep[3].reliability}-->) and sigma = 0.05<!--{ppuf_recirc.C4_FREE_1.noise_sweep[4].meas_noise_sigma}--> (3.93%<!--{ppuf_recirc.C4_FREE_1.noise_sweep[4].reliability}-->); interpolating linearly between those two points puts it
at about **0.032 rad**, roughly three times the assumed 0.01<!--{ppuf.measurement_noise_sigma}-->. Uniqueness, uniformity and
the tie fraction do not move at all across the sweep, because they are computed from the
noise-free reference response; only reliability responds. The modelled reliability is
therefore a statement about the assumed noise rather than a prediction of the chip's 2.55%,
and the two should not be read as agreeing or disagreeing.

The spread sweep behaves the way a working PUF should, and the same way the feed-forward
model does (20 dies x 32 challenges, mu_phase = 0):

| sigma_phase (rad) | uniqueness | uniformity | tie fraction | reliability | live pairs |
|---|---|---|---|---|---|
| 0.001<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[0].sigma_phase}--> | 0.2412<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[0].uniqueness}--> | 0.7604<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[0].uniformity}--> | 0.5141<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[0].tie_fraction}--> | 0.4345<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[0].reliability}--> | 9<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[0].live_pairs}--> |
| 0.010<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[1].sigma_phase}--> | 0.4408<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[1].uniqueness}--> | 0.5668<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[1].uniformity}--> | 0.1203<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[1].tie_fraction}--> | 0.3352<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[1].reliability}--> | 9<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[1].live_pairs}--> |
| 0.100<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[2].sigma_phase}--> | 0.4937<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[2].uniqueness}--> | 0.5059<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[2].uniformity}--> | 0.0109<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[2].tie_fraction}--> | 0.0672<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[2].reliability}--> | 9<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[2].live_pairs}--> |
| 0.500<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[3].sigma_phase}--> | 0.4992<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[3].uniqueness}--> | 0.5021<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[3].uniformity}--> | 0.0000<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[3].tie_fraction}--> | 0.0120<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[3].reliability}--> | 9<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[3].live_pairs}--> |
| 1.050<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[4].sigma_phase}--> | 0.5003<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[4].uniqueness}--> | 0.5014<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[4].uniformity}--> | 0.0000<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[4].tie_fraction}--> | 0.0086<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[4].reliability}--> | 9<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[4].live_pairs}--> |
| 3.000<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[5].sigma_phase}--> | 0.5011<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[5].uniqueness}--> | 0.5201<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[5].uniformity}--> | 0.0000<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[5].tie_fraction}--> | 0.0062<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[5].reliability}--> | 9<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[5].live_pairs}--> |

(Wiring C4_FREE_1; C4_FREE_2 differs by at most 0.02 on any entry.) At sigma = 0.001 the
mesh is nearly nominal, more than half the pairs still tie, and reliability (0.4345<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[0].reliability}-->) is
larger than uniqueness (0.2412<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[0].uniqueness}-->) -- the non-functioning regime, the same signature the
feed-forward sweep shows at that spread. By sigma = 0.1 the ties are gone and uniqueness
is 0.4937<!--{ppuf_recirc.C4_FREE_1.sensitivity_sweep[2].uniqueness}-->.

The two wirings agree on uniqueness to 0.0002<!--{ppuf_recirc.wiring_robustness.uniqueness_difference}--> on the single headline run, and their
population means differ by 0.046<!--{ppuf_recirc.wiring_uniqueness_gap|pct}--> points against a seed spread of about 0.25<!--{ppuf_recirc.C4_FREE_1.population_sweep.uniqueness_std|pct}--> points, well
inside the stated tolerance of 0.05<!--{ppuf_recirc.wiring_robustness.tolerance}-->. That is the check that the conclusion does not rest on
the wiring, and a test enforces it.

Because the response is driven by physics rather than by construction, uniqueness is a
function of the manufacturing spread, and the sweep is the honest way to report it
(`sensitivity_sweep`, 40 dies × 64 challenges, μ_phase = 0):

| σ_phase (rad) | uniqueness | uniformity | tie fraction | reliability |
|---|---|---|---|---|
| 0.001<!--{ppuf.sensitivity_sweep[0].sigma_phase}--> | 0.2164<!--{ppuf.sensitivity_sweep[0].uniqueness}--> | 0.5177<!--{ppuf.sensitivity_sweep[0].uniformity}--> | 0.0074<!--{ppuf.sensitivity_sweep[0].tie_fraction}--> | 0.2198<!--{ppuf.sensitivity_sweep[0].reliability}--> |
| 0.010<!--{ppuf.sensitivity_sweep[1].sigma_phase}--> | 0.2193<!--{ppuf.sensitivity_sweep[1].uniqueness}--> | 0.5133<!--{ppuf.sensitivity_sweep[1].uniformity}--> | 0.0000<!--{ppuf.sensitivity_sweep[1].tie_fraction}--> | 0.1623<!--{ppuf.sensitivity_sweep[1].reliability}--> |
| 0.100<!--{ppuf.sensitivity_sweep[2].sigma_phase}--> | 0.2225<!--{ppuf.sensitivity_sweep[2].uniqueness}--> | 0.5126<!--{ppuf.sensitivity_sweep[2].uniformity}--> | 0.0000<!--{ppuf.sensitivity_sweep[2].tie_fraction}--> | 0.0258<!--{ppuf.sensitivity_sweep[2].reliability}--> |
| 0.500<!--{ppuf.sensitivity_sweep[3].sigma_phase}--> | 0.2835<!--{ppuf.sensitivity_sweep[3].uniqueness}--> | 0.5151<!--{ppuf.sensitivity_sweep[3].uniformity}--> | 0.0000<!--{ppuf.sensitivity_sweep[3].tie_fraction}--> | 0.0073<!--{ppuf.sensitivity_sweep[3].reliability}--> |
| 1.050<!--{ppuf.sensitivity_sweep[4].sigma_phase}--> | 0.4818<!--{ppuf.sensitivity_sweep[4].uniqueness}--> | 0.5103<!--{ppuf.sensitivity_sweep[4].uniformity}--> | 0.0000<!--{ppuf.sensitivity_sweep[4].tie_fraction}--> | 0.0069<!--{ppuf.sensitivity_sweep[4].reliability}--> |
| 3.000<!--{ppuf.sensitivity_sweep[5].sigma_phase}--> | 0.4971<!--{ppuf.sensitivity_sweep[5].uniqueness}--> | 0.5040<!--{ppuf.sensitivity_sweep[5].uniformity}--> | 0.0000<!--{ppuf.sensitivity_sweep[5].tie_fraction}--> | 0.0069<!--{ppuf.sensitivity_sweep[5].reliability}--> |

The tie fraction is the share of compared pairs whose two intensities differ by less than
the tie tolerance of 1e-12<!--{ppuf.tie_tol}--> (`ppuf.tie_tol`); ties are resolved as 1 and counted rather than
hidden. At σ = 0.001 the mesh is still essentially a permutation, only the two routed
outputs carry power, and the tie fraction is non-zero. That regime is also where
reliability (0.2198<!--{ppuf.sensitivity_sweep[0].reliability}-->) is as large as uniqueness (0.2164<!--{ppuf.sensitivity_sweep[0].uniqueness}-->): the bits are being set by
measurement noise rather than by the die, which is exactly what a non-functioning PUF looks
like. At the paper's spread the two separate by a factor of 67<!--{ppuf.uniqueness_over_reliability}-->
(`uniqueness_over_reliability`, the ratio of the two `results.json` values 0.48917<!--{ppuf.uniqueness}-->
and 0.00735<!--{ppuf.reliability_intra_die_HD}-->), which is what makes the response a signature.
The PUF test judges the low-spread case by reliability rather than by a uniqueness bound,
because a symmetric comparison of two ports is randomised by any nonzero spread and only
measurement noise distinguishes a working PUF from a non-working one.

---

## 4. Physics extensions (beyond the first-pass models)

### 4.1 Single-θ PUC expressivity (`expressivity.py`) — paper Discussion, made explicit

The paper's PUC (Eq. 1) has one thermo-optic phase shifter, so one DOF per cell. A
universal N-mode interferometer needs N² real DOF; a rectangular mesh of single-θ cells
supplies only N(N−1)/2. For N = 4 that is 6<!--{expressivity.dof.single_theta}--> DOF inside a 16<!--{expressivity.dof.dim_U(N)}-->-dimensional U(4), rising to 10<!--{expressivity.dof.single_theta+output_phases}-->
with output phases and 16<!--{expressivity.dof.two_dof_universal}--> only for the full 2-DOF mesh.

Best-fit fidelity to Haar-random U(4) climbs the same ladder: 0.5605<!--{expressivity.haar_fidelity_mean.single_theta}--> for single-θ, 0.8264<!--{expressivity.haar_fidelity_mean.single_theta+output_phases}-->
with output phases, 1.000000<!--{expressivity.haar_fidelity_mean.two_dof_universal}--> for the universal 2-DOF mesh. This is why the paper
demonstrates permutations and specific realisable matrices rather than arbitrary unitaries.
A unitary generated by a single-θ mesh is recovered to fidelity 1.0000<!--{expressivity.realizable_unitary_fidelity}-->, and permutations
are routed at fidelity 0.999999999999<!--{unitary.perm_routing_fidelity[0]}-->.

Separately from the DOF limit, the coupler imposes its own ceiling on the single-θ cross
state. Over 1530<!--{expressivity.coupler_ceiling_range_nm[0]}-->–1565<!--{expressivity.coupler_ceiling_range_nm[1]}--> nm that ceiling falls to 0.9469<!--{expressivity.coupler_ceiling_min_fidelity}-->; at the 1560 nm design wavelength it
is 0.9942<!--{expressivity.coupler_ceiling_fidelity_at_1560}-->. Both follow from the coupler being 50:50 at 1574.7<!--{fig4d_mesh_fit.lambda0_nm}--> nm (§6.1) rather than at the
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
physical: 22.34<!--{coupler.extinction_at_1560_db}--> dB at 1560 nm and 11.04<!--{coupler.extinction_at_1520_db}--> dB at 1520 nm. The fibre-to-fibre link budget is
11.43<!--{coupler.link_budget_db}--> dB, dominated by the two grating couplers.

The `demo_fit_kappa0` = 0.4980<!--{coupler.demo_fit_kappa0}--> and `demo_fit_slope` = 0.004370<!--{coupler.demo_fit_slope}--> entries in `results.json`
are recovered from the synthetic `_demo_measured_dataset`, not from chip data, and are
labelled as such by `demo_fit_note`. That dataset has its own fixed reference wavelength,
`DEMO_LAMBDA0` = 1560<!--{coupler.demo_fit_lam0_nm}--> nm, written to `results.json` as `demo_fit_lam0_nm`; generator and
fitter both use it, so the recovered values are directly comparable with the generator's
own `demo_true_kappa0` = 0.5<!--{coupler.demo_true_kappa0}--> and `demo_true_slope` = 0.0042<!--{coupler.demo_true_slope}-->. That reference wavelength is
deliberately independent of `DC_LAMBDA_3DB`: the demo exercises the fitting routine and
says nothing about this chip, so tying it to the chip's fitted 3-dB point would make a
change in the chip fit look like a change in the demo. The κ₀ agreement to 0.002<!--{coupler.demo_kappa0_abs_error}--> is a
genuine recovery check; the 4.1%<!--{coupler.demo_slope_offset_frac}--> slope offset is the generator's quadratic dispersion term,
which the two-parameter CMT fit form cannot represent. Referencing generator and fitter to
different wavelengths would shift the fitted κ₀ by roughly slope × Δλ without the fit itself
changing, which measures the choice of reference wavelength rather than the quality of the
fit. None of these four numbers says anything about this chip.

### 4.3 Full square *recirculating* mesh with feedback (`recirculating.py`)

The matrix-multiply functions use a feedforward rectangular sub-mesh, but the full chip
recirculates: light returns through closed loops, so the transfer function is rational and
has poles. That needs a linear solve, o = (I − S·C)⁻¹ S·b. The solver is validated against
the analytic all-pass ring to RMS 2.9e-16<!--{recirculating.ring_rms}--> and the add-drop ring to 8.4e-16<!--{recirculating.add_drop_rms}-->; the 4-PUC
square plaquette conserves energy to 1.1e-15<!--{recirculating.plaquette_unitarity_dev}-->, and the full 40<!--{recirculating.n_pucs_big}-->-PUC recirculating bus solves
with an energy-conservation deviation of 2.7e-15<!--{recirculating.big_unitarity_dev}-->.

---

## 5. Bottom line

Of the paper's headline quantitative claims, the bucket-A items (PUC unitarity, the
6.2163<!--{unitary.enob_at_sigma_0.0269}--> / 5.4643<!--{nonunitary.enob_at_sigma_0.0453}-->-bit ENOB values, 60.04<!--{latency_on_chip_ps}--> ps latency) reproduce exactly. The bucket-B
simulations reproduce closely and on independent code: routing fidelity 0.999999999999<!--{unitary.perm_routing_fidelity[0]}-->,
unitary fidelity 1.000000<!--{unitary.random_mean_fidelity}-->, non-unitary modulus correlation 1.000000<!--{nonunitary.modulus_corr}-->, PUF uniqueness
49.00%<!--{ppuf.population_sweep.uniqueness_mean}--> ± 0.34%<!--{ppuf.population_sweep.uniqueness_std}--> against the paper's 49.97%<!--{ppuf_recirc.vs_feedforward.paired_uniqueness.paper_uniqueness}-->, and PUF uniformity 50.32%<!--{ppuf.population_sweep.uniformity_mean}--> ± 0.51%<!--{ppuf.population_sweep.uniformity_std}--> against
50.15%, both over 10<!--{ppuf.population_sweep.n_seeds}--> population seeds. The bucket-C items
are physical measurements and are left unreproduced rather than fabricated.

Six results do not simply confirm the paper:

1. The switch crosstalk the model predicts depends on whether data exists for the range in
   question. Inside the fitted range, the model meets the −15 dB figure (worst −16.77<!--{switching.cross_worst_xtalk_fitrange_db}--> dB)
   but not the −20 dB figure. These are predictions of a model constrained by one digitized
   port pair, not measurements of the other port pairs. The digitized T20 curve itself
   reaches −14.1 dB at 1549.0 nm, within its ±2 dB digitization uncertainty. Extrapolated
   below the data, over 1530–1549 nm, the model degrades to −11.80<!--{switching.cross_worst_xtalk_extrapolated_db}--> dB — but that half of
   the band has no digitized point behind it and is a model projection.
2. The coupler's 3-dB wavelength is not the design wavelength. Fitting the mesh model to
   Fig 4d puts it at 1574.7<!--{fig4d_mesh_fit.lambda0_nm}--> nm, with the parametric bootstrap interval
   [1572.3<!--{fig4d_mesh_fit.lambda0_param_p05_nm}-->, 1577.7<!--{fig4d_mesh_fit.lambda0_param_p95_nm}-->] nm.
   Both bootstrap intervals exclude 1560 nm: the pairs interval [1573.7<!--{fig4d_mesh_fit.lambda0_pairs_p05_nm}-->, 1575.5<!--{fig4d_mesh_fit.lambda0_pairs_p95_nm}-->] nm by
   13.7 nm and the parametric interval by 12.3 nm (§6.1). The proxy and mesh models place
   λ₀ 3.6<!--{fig4d_mesh_fit.lambda0_minus_proxy_nm}--> nm apart. The bootstrap intervals describe the uncertainty within the mesh model,
   not the uncertainty in the choice of model. Both models exclude 1560 nm.
3. The ideal-coupler fidelities do not survive the chip's own coupler. Rows 3 and 5 reach
   1.000000<!--{unitary.random_mean_fidelity}--> with ideal 50:50 couplers; the coupler fitted to Fig 4d caps the single-θ cross
   state at 0.9942<!--{expressivity.coupler_ceiling_fidelity_at_1560}--> at 1560 nm, and at 0.9469<!--{expressivity.coupler_ceiling_min_fidelity}--> at the worst point of 1530<!--{expressivity.coupler_ceiling_range_nm[0]}-->–1565<!--{expressivity.coupler_ceiling_range_nm[1]}--> nm.
4. A multinomial logistic regression with 15 parameters (four weights for each of three
   classes, plus three biases) is ahead of the photonic Iris classifier on the same splits.
   Differenced seed by seed, it leads by 1.07<!--{iris.paired_logistic_minus_photonic.full_mean|pct}--> ± 1.30<!--{iris.paired_logistic_minus_photonic.full_std|pct}--> points on the full set, winning on 7<!--{iris.paired_logistic_minus_photonic.full_n_logistic_higher}-->
   of the 10 seeds, tying on 2<!--{iris.paired_logistic_minus_photonic.full_n_equal}--> and losing on 1<!--{iris.paired_logistic_minus_photonic.full_n_photonic_higher}-->; the absolute paired mean is smaller than
   the paired standard deviation, so that difference is within the seed-to-seed spread. On
   the held-out split it leads by 5.56<!--{iris.paired_logistic_minus_photonic.test_mean|pct}--> ± 3.67<!--{iris.paired_logistic_minus_photonic.test_std|pct}--> points, winning on 9<!--{iris.paired_logistic_minus_photonic.test_n_logistic_higher}--> seeds, tying on 1<!--{iris.paired_logistic_minus_photonic.test_n_equal}--> and
   losing on none; there the absolute paired mean exceeds the paired standard deviation, so
   that is a consistent difference. The identity control shows the unitary contributes about
   10<!--{iris.unitary_minus_identity_full_acc|pct}--> points over the readout alone, so the mesh is doing real work — but Iris does not
   discriminate a photonic classifier from a linear one.
5. The modelled on-chip insertion loss, −1.40<!--{switching.onchip_il_max_db}--> to −1.80<!--{switching.onchip_il_min_db}--> dB over eight paths, is lower than
   the paper's measured −1.85<!--{switching.onchip_il_paper_range_db[1]}--> to −2.99<!--{switching.onchip_il_paper_range_db[0]}--> dB. Per path against the four digitized Fig 4e
   bar-state diagonals the model is optimistic by 0.38<!--{switching.bar_il_vs_fig4e.mean_signed_diff_db}--> dB on average and does not
   reproduce the port-to-port ordering. The loss parameters are assumed rather than taken
   from the paper, and they were not tuned to close the gap.

6. The published Fig 4e does not constrain the fabrication spread in this model. The
   measured bar-state leakage is flat across the band to within the digitization
   uncertainty, while the model's dependence on wavelength is two orders of magnitude
   smaller than the data's scatter, so the panel fixes a level and not a curve. The panel
   was digitized, the model was fitted to it, and the fitted spread was not adopted: it
   scores 0.4176<!--{fig4e_fit.shape_check.model_rms_db}--> dB RMS against 0.4170<!--{fig4e_fit.shape_check.constant_rms_db}--> dB for a best-fit constant on the same 27<!--{fig4e_fit.n_points}--> points,
   and it ranges from 0.0152<!--{fig4e_fit.sensitivity.sigma_split_full_range[0]}--> to 0.0707<!--{fig4e_fit.sensitivity.sigma_split_full_range[1]}-->, a factor of 4.6<!--{fig4e_fit.sensitivity.sigma_split_range_factor}-->, with the ensemble percentile the
   data cannot choose. The assumed 0.02<!--{cross_check.sigma_split}--> lies inside that range, and `SIGMA_SPLIT` keeps
   it.

The three physics extensions (§4) make the model mechanistic rather than descriptive: the
single-θ expressivity limit is quantified (0.5605<!--{expressivity.haar_fidelity_mean.single_theta}--> mean fidelity to arbitrary U(4), rising
to 1.000000<!--{expressivity.haar_fidelity_mean.two_dof_universal}--> only with the full 2-DOF mesh), explaining the paper's choice of matrix classes;
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
| Group index n_g | 4.0<!--[lightin.coupler.N_GROUP]--> (stated) | latency (60.04<!--{latency_on_chip_ps}--> ps) |
| Phase index n_eff | ~2.36<!--[lightin.coupler.N_EFF]--> (450×220 nm SOI TE, geometry) | recirculating, PPUF |
| Directional coupler | length 11.5<!--[lightin.coupler.DC_LENGTH_UM]--> µm, gap 200<!--[lightin.coupler.DC_GAP_NM]--> nm, 450<!--[lightin.coupler.WG_WIDTH_NM]--> nm width | coupler geometry |
| Square-mesh unit side | 500<!--[lightin.coupler.SQUARE_SIDE_UM]--> µm | recirculating loop length |
| MZI arm length | 208<!--[lightin.coupler.ARM_LENGTH_UM]--> µm | mesh segments |
| Heater | 100<!--[lightin.coupler.HEATER_LENGTH_UM]--> µm, 3 V for π across 100 Ω → 90<!--{throughput_energy.P_pi_mW}--> mW, E[θ]=π/2 | energy |
| Energy derivation | 40 PUCs × 45<!--{throughput_energy.P_avg_per_mzi_mW}--> mW = 1.8<!--{throughput_energy.P_total_W}--> W ÷ 9.6e11<!--{throughput_energy.mac_rate}--> MAC·s⁻¹ | throughput.py |
| Throughput convention | 96 ops × 2 directions × 10 GBaud | throughput.py |
| PUF arm-length spread | N(μ=0.08 µm, σ=0.11 µm) → phase N(0.76, 1.05) rad | ppuf.py |
| PUF experimental (2 dies) | inter-die 57.71%, uniformity 42.62%, intra-die HD 2.55% | ppuf targets |
| PUF simulation (100 dies) | uniqueness 49.97%<!--{ppuf_recirc.vs_feedforward.paired_uniqueness.paper_uniqueness}-->, uniformity 50.15% | ppuf targets |
| Switch crosstalk | −45 to <−20 dB at 1560 nm; <−15/−20 dB over >20 nm | switching targets |
| On-chip insertion loss | −1.85<!--{switching.onchip_il_paper_range_db[1]}--> to −2.99<!--{switching.onchip_il_paper_range_db[0]}--> dB (8 measured paths) | switching comparison |
| Design wavelengths | 1560<!--[lightin.coupler.LAMBDA0]--> nm (matrix), 1555<!--[lightin.coupler.LAMBDA_MRM]--> nm (MRM), 1545 nm (grating peak) | all modules |
| MRM eye SNR / Q | 17.10 & 17.83 dB; Q 7.17–8.08 | mrm (hardware-only targets) |

### 6.1 Fig 4d digitized, and the coupler 3-dB wavelength decided by that data

The all-cross-state T20 crosstalk curve was colour-digitized from Fig 4d
(`data/fig4d_T20_digitized.csv`, 25<!--{fig4d_mesh_fit.n_points}--> points spanning 1549–1587 nm; dB scale anchored to
figure-read endpoints, ~±2 dB) and fitted with `scripts/fit_fig4.py`.

Two models are fitted to the same 25<!--{fig4d_mesh_fit.n_points}--> points, with the same three free parameters (λ₀, slope,
floor):

| | `crosstalk_model` — single-coupler proxy | `mesh_t20_model` — 4×4 mesh T20 |
|---|---|---|
| what it evaluates | one directional-coupler pair, 10·log₁₀[(1−2κ)² + floor] | the full 4-stage fabric of `switching.py`, T20 normalised to total output power |
| λ₀ | **1571.0<!--{fig4d_fit.lambda0_nm}--> nm** | **1574.7<!--{fig4d_mesh_fit.lambda0_nm}--> ± 0.6<!--{fig4d_mesh_fit.lambda0_se_nm}--> nm** |
| slope | **0.0029<!--{fig4d_fit.slope_rad_nm}--> rad/nm** | **0.00261<!--{fig4d_mesh_fit.slope}--> ± 0.00012<!--{fig4d_mesh_fit.slope_se}--> rad/nm** |
| floor | **−25.2<!--{fig4d_fit.floor_db}--> dB** | **−26.2<!--{fig4d_mesh_fit.floor_db}--> ± 0.4<!--{fig4d_mesh_fit.floor_se_db}--> dB** |
| **RMS over the 25<!--{fig4d_mesh_fit.n_points}--> points** | **1.05<!--{fig4d_fit.rms_db}--> dB** | **0.79<!--{fig4d_mesh_fit.rms_db}--> dB** |
| pairs bootstrap, λ₀ 5–95% | [1570.1<!--{fig4d_fit.lambda0_p05_nm}-->, 1572.0<!--{fig4d_fit.lambda0_p95_nm}-->] nm | [1573.7<!--{fig4d_mesh_fit.lambda0_pairs_p05_nm}-->, 1575.5<!--{fig4d_mesh_fit.lambda0_pairs_p95_nm}-->] nm |
| pairs bootstrap, slope 5–95% | [0.0026<!--{fig4d_fit.slope_p05}-->, 0.0033<!--{fig4d_fit.slope_p95}-->] | [0.00239<!--{fig4d_mesh_fit.slope_pairs_p05}-->, 0.00285<!--{fig4d_mesh_fit.slope_pairs_p95}-->] |
| parametric bootstrap, λ₀ 5–95% | — | [1572.3<!--{fig4d_mesh_fit.lambda0_param_p05_nm}-->, 1577.7<!--{fig4d_mesh_fit.lambda0_param_p95_nm}-->] nm |
| parametric bootstrap, slope 5–95% | — | [0.00219<!--{fig4d_mesh_fit.slope_param_p05}-->, 0.00306<!--{fig4d_mesh_fit.slope_param_p95}-->] |

The mesh fit is the one used for `DC_LAMBDA_3DB`, because the proxy's λ₀ is not a property
of the mesh. The proxy is a formula for a single coupler pair. The chip's T20 path crosses
four stages, and the interference along that path displaces the T20 null away from the
wavelength at which the couplers themselves are 50:50. Evaluated on a 0.1 nm grid from 1540
to 1600 nm at the fitted mesh parameters, the floor-free null of T20/Tout sits at 1569.7 nm
while the couplers are 50:50 at 1574.7 nm — a 5.0 nm displacement. (That grid scan is a
diagnostic computed from `mesh_t20_model`; it is not a `results.json` value.) The proxy,
having no multi-stage path, has nowhere to put those 5 nm except into λ₀, which is why it
reports 1571.0 nm. Its λ₀ is a parameter of the proxy formula; the mesh's λ₀ is the coupler
parameter the rest of the code needs. The mesh also fits the data better, 0.79<!--{fig4d_mesh_fit.rms_db}--> dB against
1.05<!--{fig4d_fit.rms_db}--> dB, on the same points with the same number of free parameters.

Both bootstraps are run on the mesh model, 500<!--{fig4d_fit.n_boot}--> resamples each, 0<!--{fig4d_mesh_fit.n_pairs_failed}--> failed fits discarded in
either:

* The pairs bootstrap resamples the (λ, dB) pairs with replacement and refits. Its interval
  reflects only the scatter of the points about the model. λ₀ [1573.7<!--{fig4d_mesh_fit.lambda0_pairs_p05_nm}-->, 1575.5<!--{fig4d_mesh_fit.lambda0_pairs_p95_nm}-->] nm, slope
  [0.00239<!--{fig4d_mesh_fit.slope_pairs_p05}-->, 0.00285<!--{fig4d_mesh_fit.slope_pairs_p95}-->] rad/nm.
* The parametric bootstrap keeps all 25<!--{fig4d_mesh_fit.n_points}--> wavelengths and adds Gaussian noise of 2.0<!--{fig4d_mesh_fit.digitization_sd_db}--> dB
  standard deviation (`digitization_sd_db`) to each dB value, treating the CSV header's
  ±2 dB as one standard deviation. Its interval therefore also carries the digitization
  uncertainty, which the pairs bootstrap cannot see. λ₀ [1572.3<!--{fig4d_mesh_fit.lambda0_param_p05_nm}-->, 1577.7<!--{fig4d_mesh_fit.lambda0_param_p95_nm}-->] nm, slope
  [0.00219<!--{fig4d_mesh_fit.slope_param_p05}-->, 0.00306<!--{fig4d_mesh_fit.slope_param_p95}-->] rad/nm.

The parametric interval is 2.9× wider on λ₀ and is the more honest of the two, because the
dominant uncertainty in this dataset is how accurately a curve could be read off a published
figure, not how the 25<!--{fig4d_mesh_fit.n_points}--> points scatter about the model. (Both the 2.9× ratio and the interval
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
1560 nm the power coupling is 0.462<!--{coupler.power_coupling_at_1560}--> rather than 0.500, the MZI extinction falls to 22.34<!--{coupler.extinction_at_1560_db}--> dB,
the single-θ unitary fidelity ceiling drops to 0.9942<!--{expressivity.coupler_ceiling_fidelity_at_1560}-->, and the worst-case switch crosstalk
inside the fitted range is −16.77<!--{switching.cross_worst_xtalk_fitrange_db}--> dB.

The two models disagree about λ₀ by 3.6<!--{fig4d_mesh_fit.lambda0_minus_proxy_nm}--> nm, which is six times the mesh fit's own standard
error and larger than the pairs bootstrap interval. That gap is model-form uncertainty: it
measures the choice between a single-coupler formula and the full four-stage fabric, and
neither bootstrap interval contains it, because both resample the data under one fixed
model.

The crosstalk floor is a fitted parameter whose physical origin is not established from the
paper. Both models need a floor term to reproduce the plateau near −25 dB in the middle of
the digitized curve, and the mesh fit puts it at −26.2<!--{fig4d_mesh_fit.floor_db}--> ± 0.4<!--{fig4d_mesh_fit.floor_se_db}--> dB. Nothing in the paper
identifies what produces it. Candidate mechanisms — residual phase error, back-reflection,
leakage paths outside the modelled topology, or a noise floor of the measurement set-up —
are not distinguished by a single digitized curve, and this reproduction does not claim to
know which applies. The value is recorded as `FIG4D_FLOOR_DB` and used only to fit, and to
mark the level below which modelled crosstalk is not physically reached.

A precise per-point digitization of the other three overlapping curves in each panel is
noise-limited, so only the cleanest curve (T20) was extracted; the stated geometry (11.5 µm,
200 nm gap) anchors the rest. (Figure: `figures/fig4_digitized.png`, which overlays both
fits.)

**Fig 4e digitized, and what that panel did and did not settle.** Fig 4e is a 2×2 array of
sub-panels, one per input port, each carrying four output curves against wavelength over
1550–1590 nm and 0 to −25 dB. The curve matching the digitized Fig 4d port pair, T20, is
in the top-left sub-panel and is **not drawn at all**: in the all-bar state it lies below
the panel's −25 dB axis limit across the whole range, as do T10 and T30. The only
off-diagonal curve visible across the full wavelength span is **T32**, in the bottom-left
sub-panel, and that is the one digitized (`data/fig4e_bar_digitized.csv`, 27<!--{fig4e_fit.n_points}--> points over
1550<!--{fig4e_fit.fit_range_nm[0]}-->–1589<!--{fig4e_fit.fit_range_nm[1]}--> nm). The four diagonals — the intended all-bar paths — were digitized separately
(`data/fig4e_diagonal_digitized.csv`).

The work `docs/FIG4E_SCOPE.md` planned was carried out in full: the panel was digitized,
the bar-state model was fitted to it, the fit was bootstrapped, and its sensitivity to
every choice the figure does not fix was measured. **The fitted value was not adopted.**
`SIGMA_SPLIT` keeps the assumed 0.02<!--{cross_check.sigma_split}--> it has always carried, and the panel is recorded
below as a consistency check on that assumption rather than as a measurement replacing it.
`results.json` carries the whole fit under `fig4e_fit`, with `adopted: false` and the
reason on `adopted_note`. The three paragraphs that follow are that reason.

**The model fits these points no better than a constant.** An RMS figure means nothing
until it is read against the most trivial model that could be fitted to the same points,
which is a constant. The least-squares constant on the 27<!--{fig4e_fit.n_points}--> digitized points is −20.158<!--{fig4e_fit.shape_check.constant_db}--> dB
and its RMS is their standard deviation, 0.4170<!--{fig4e_fit.shape_check.constant_rms_db}--> dB. The bar model at its own best-fit
spread scores 0.4176<!--{fig4e_fit.shape_check.model_rms_db}--> dB, which is 0.0006<!--{fig4e_fit.shape_check.rms_advantage_db|abs}--> dB *worse*. Across the band the measured points
vary by 1.620<!--{fig4e_fit.shape_check.data_ptp_db}--> dB peak to peak and the model by 0.0022<!--{fig4e_fit.shape_check.model_ptp_db}--> dB, 0.14%<!--{fig4e_fit.shape_check.model_ptp_over_data_ptp}--> of that. The model's
wavelength dependence is two orders of magnitude below the scatter of the data, so the
panel fixes a level and not a curve, and a level is one number. These are the
`fig4e_fit.shape_check` keys.

**The spread that level implies depends on a choice the figure does not show.** The
digitized T32 trace is the upper envelope of a filled band whose lower edge the −25 dB
axis limit cuts off at every wavelength, so each point is a peak-hold over the fast
wavelength ripple rather than a level, and its model counterpart is a high quantile of the
fabrication ensemble rather than the mean. Which quantile is a judgement about how many
independent ripple samples fall inside one digitization window, and the figure does not
show it. Refitting at six percentiles, with `SIGMA_PHASE` held at 0.02<!--{fig4e_fit.sigma_split_fit.held_value}-->:

| percentile | fitted `SIGMA_SPLIT` | standard error | RMS |
|---|---|---|---|
| 50th | **0.0707<!--{fig4e_fit.sensitivity.percentile_scan.p50.sigma_split}-->** | ±0.0007<!--{fig4e_fit.sensitivity.percentile_scan.p50.se}--> | 0.418<!--{fig4e_fit.sensitivity.percentile_scan.p50.rms_db}--> dB |
| 75th | **0.0418<!--{fig4e_fit.sensitivity.percentile_scan.p75.sigma_split}-->** | ±0.0004<!--{fig4e_fit.sensitivity.percentile_scan.p75.se}--> | 0.416<!--{fig4e_fit.sensitivity.percentile_scan.p75.rms_db}--> dB |
| 90th | **0.0283<!--{fig4e_fit.sensitivity.percentile_scan.p90.sigma_split}-->** | ±0.0003<!--{fig4e_fit.sensitivity.percentile_scan.p90.se}--> | 0.417<!--{fig4e_fit.sensitivity.percentile_scan.p90.rms_db}--> dB |
| 95th | **0.0237<!--{fig4e_fit.sensitivity.percentile_scan.p95.sigma_split}-->** | ±0.0002<!--{fig4e_fit.sensitivity.percentile_scan.p95.se}--> | 0.418<!--{fig4e_fit.sensitivity.percentile_scan.p95.rms_db}--> dB |
| 99th | **0.0182<!--{fig4e_fit.sensitivity.percentile_scan.p99.sigma_split}-->** | ±0.0002<!--{fig4e_fit.sensitivity.percentile_scan.p99.se}--> | 0.418<!--{fig4e_fit.sensitivity.percentile_scan.p99.rms_db}--> dB |
| 99.9th | **0.0152<!--{fig4e_fit.sensitivity.percentile_scan.p99.9.sigma_split}-->** | ±0.0001<!--{fig4e_fit.sensitivity.percentile_scan.p99.9.se}--> | 0.417<!--{fig4e_fit.sensitivity.percentile_scan.p99.9.rms_db}--> dB |

The RMS is the same 0.42 dB at every one of them, so the data expresses no preference
between a spread of 0.0152<!--{fig4e_fit.sensitivity.sigma_split_full_range[0]}--> and one of 0.0707<!--{fig4e_fit.sensitivity.sigma_split_full_range[1]}-->. A further variant tests the dB calibration:
shifting every digitized point by −0.35<!--{fig4e_fit.sensitivity.offset_test_db}--> dB, the difference between the digitized
diagonals' mean and the midpoint of the paper's insertion-loss range, returns 0.0175<!--{fig4e_fit.sensitivity.offset_test_sigma_split}-->.
Across all 7 variants the fitted spread runs from 0.0152<!--{fig4e_fit.sensitivity.sigma_split_full_range[0]}--> to 0.0707<!--{fig4e_fit.sensitivity.sigma_split_full_range[1]}-->, **a factor of 4.6<!--{fig4e_fit.sensitivity.sigma_split_range_factor}-->**,
against a parametric bootstrap interval at the adopted percentile of [0.0180<!--{fig4e_fit.sensitivity.adopted_bootstrap_param[0]}-->, 0.0184<!--{fig4e_fit.sensitivity.adopted_bootstrap_param[1]}-->] —
narrower by a factor of 136<!--{fig4e_fit.sensitivity.range_over_bootstrap_factor}-->. The bootstrap measures how far 27<!--{fig4e_fit.n_points}--> points scatter about a
model of a fixed form; the range measures the form, and it is the larger by two orders of
magnitude. **The assumed 0.02<!--{cross_check.sigma_split}--> lies inside that range**, between the 95th and 99th
percentile entries. These are the `fig4e_fit.sensitivity` keys.

**What adopting the fit would have bought, and why that is not a gain.** Nothing is
refitted in this check. On the Fig 4e points the bar model scores 0.9013<!--{cross_check.fig4e_rms_at_assumed_spreads_db}--> dB RMS at the
assumed spread and 0.4176<!--{cross_check.fig4e_rms_at_fitted_spread_db}--> dB at the fitted 0.0182<!--{cross_check.fitted_spread_not_adopted}-->, an improvement of 0.4837<!--{cross_check.fig4e_rms_improvement_at_fitted_spread_db}--> dB. That
improvement is real and it is not evidence for the fitted value, because a plain constant
fitted to the same 27<!--{fig4e_fit.n_points}--> points scores 0.4170<!--{fig4e_fit.shape_check.constant_rms_db}--> dB — better than either. The whole of it is the
model's flat level being moved onto the data mean, which any single free parameter would
achieve; none of it is the model accounting for the shape of the curve. On the Fig 4d
points the same change costs 0.0104<!--{cross_check.fig4d_rms_penalty_at_fitted_spread_db}--> dB (0.7921<!--{cross_check.fig4d_rms_at_assumed_spreads_db}--> dB to 0.8025<!--{cross_check.fig4d_rms_at_fitted_spread_db}--> dB), which is far below the
±0.3<!--{fig4e_fit.digitization_sd_db}--> dB per-point digitization uncertainty and so is not resolvable either way. These are
the `cross_check` keys. (Figure: `figures/fig4e_digitized.png`, which overlays the fitted
model on the digitized points.)

**What the panel is evidence for.** It is a consistency check, and it passes: the measured
bar-state leakage is where a 0.02<!--{cross_check.sigma_split}--> coupler-split spread puts it, and no spread outside
roughly a factor of two either side of 0.02<!--{cross_check.sigma_split}--> would put it there at the 90th to 99.9th
percentiles. That is a real constraint and it is worth having. What it is not is a
measurement of the spread, because the quantity it constrains — one level — is shared
between two parameters that one curve cannot separate, and because the model that turns a
level into a spread has a free choice in it that the figure does not fix.

**The digitized diagonals, against the paper's measured insertion loss.** The diagonal of
each sub-panel is an intended all-bar path, and all four are digitized, each sub-panel
anchored to its own tick marks. The opaque legend box hides roughly 1574.5–1588.3 nm in
every sub-panel, so the 1.5 nm grid runs 1550.0<!--{fig4e_diagonals.continuous_band_nm[0]}-->–1574.0<!--{fig4e_diagonals.continuous_band_nm[1]}--> nm and then resumes at 1589.0<!--{fig4e_diagonals.band_nm[1]}--> nm,
inside the roll-off at the end of the scan where the drawn trace is half again as thick as
across the rest of the band. **Every comparison below is made over 1550–1574 nm only.**
Including the single 1589.0 nm point moves the four-diagonal range from −1.10<!--{fig4e_diagonals.combined_continuous.range_db[1]}--> … −2.77<!--{fig4e_diagonals.combined_continuous.range_db[0]}--> dB
to −1.10<!--{fig4e_diagonals.combined.range_db[1]}--> … −4.06<!--{fig4e_diagonals.combined.range_db[0]}--> dB, more than a decibel at the lossy end, which is why it is excluded and
why the exclusion is stated rather than assumed.

| trace | 1550–1574 nm (used) | 1550–1589 nm (band edge included) |
|---|---|---|
| T00 | −2.20<!--{fig4e_diagonals.per_diagonal_continuous.T00.max_db}--> to −2.77<!--{fig4e_diagonals.per_diagonal_continuous.T00.min_db}--> dB (mean −2.43<!--{fig4e_diagonals.per_diagonal_continuous.T00.mean_db}-->) | −2.20<!--{fig4e_diagonals.per_diagonal.T00.max_db}--> to −4.06<!--{fig4e_diagonals.per_diagonal.T00.min_db}--> dB |
| T11 | −2.15<!--{fig4e_diagonals.per_diagonal_continuous.T11.max_db}--> to −2.44<!--{fig4e_diagonals.per_diagonal_continuous.T11.min_db}--> dB (mean −2.27<!--{fig4e_diagonals.per_diagonal_continuous.T11.mean_db}-->) | −2.15<!--{fig4e_diagonals.per_diagonal.T11.max_db}--> to −3.30<!--{fig4e_diagonals.per_diagonal.T11.min_db}--> dB |
| T22 | −1.45<!--{fig4e_diagonals.per_diagonal_continuous.T22.max_db}--> to −2.26<!--{fig4e_diagonals.per_diagonal_continuous.T22.min_db}--> dB (mean −1.75<!--{fig4e_diagonals.per_diagonal_continuous.T22.mean_db}-->) | −1.45<!--{fig4e_diagonals.per_diagonal.T22.max_db}--> to −3.78<!--{fig4e_diagonals.per_diagonal.T22.min_db}--> dB |
| T33 | −1.10<!--{fig4e_diagonals.per_diagonal_continuous.T33.max_db}--> to −2.01<!--{fig4e_diagonals.per_diagonal_continuous.T33.min_db}--> dB (mean −1.48<!--{fig4e_diagonals.per_diagonal_continuous.T33.mean_db}-->) | −1.10<!--{fig4e_diagonals.per_diagonal.T33.max_db}--> to −3.41<!--{fig4e_diagonals.per_diagonal.T33.min_db}--> dB |
| **all four** | **−1.10<!--{fig4e_diagonals.combined_continuous.range_db[1]}--> to −2.77<!--{fig4e_diagonals.combined_continuous.range_db[0]}--> dB** | **−1.10<!--{fig4e_diagonals.combined.range_db[1]}--> to −4.06<!--{fig4e_diagonals.combined.range_db[0]}--> dB** |

The paper's measured range is −1.85<!--{fig4e_diagonals.paper_range_db[1]}--> to −2.99<!--{fig4e_diagonals.paper_range_db[0]}--> dB over 8<!--{fig4e_diagonals.paper_n_paths}--> intended paths. Over the window
used, the four digitized diagonals run −1.10<!--{fig4e_diagonals.combined_continuous.range_db[1]}--> to −2.77<!--{fig4e_diagonals.combined_continuous.range_db[0]}--> dB: the least-lossy end sits 0.75<!--{fig4e_diagonals.combined_continuous.least_lossy_end_minus_paper_db}--> dB
above the paper's and the most-lossy end 0.22<!--{fig4e_diagonals.combined_continuous.most_lossy_end_minus_paper_db}--> dB below it, so the two ends disagree by
0.53<!--{fig4e_diagonals.combined_continuous.end_difference_db}--> dB. A constant calibration offset on the digitized dB scale would move both ends by
the same amount, and this does not, so there is no offset to correct. The ready
alternative is that the sets differ: Fig 4e is the all-bar configuration and draws 4<!--{fig4e_diagonals.panel_n_paths}--> of
the paper's 8<!--{fig4e_diagonals.paper_n_paths}--> paths, the other 4 being the all-cross paths that belong to Fig 4d. Which
switch state the paper's range was measured in, at what wavelength and over what band, is
not recorded anywhere available here — `docs/PREPRINT_NOTES.md` does not mention insertion
loss at all — so the two cannot be reconciled from this repository. These are the
`fig4e_diagonals` keys.

**Modelled bar-state insertion loss, path by path.** The four digitized diagonals are four
*measured* bar-state insertion losses, one per intended path, so they support a comparison
the paper's single quoted range cannot: not only whether the modelled loss is in the right
place, but whether it varies across the four ports the way the chip does. The model here
is `switching.fabric_matrix` with nominal 50:50 couplers, so the intended-path loss is set
by the propagation and coupler excess-loss constants alone and no fabrication spread
enters it. Over 1550.0<!--{switching.bar_il_vs_fig4e.band_nm[0]}-->–1574.0<!--{switching.bar_il_vs_fig4e.band_nm[1]}--> nm, 17<!--{switching.bar_il_vs_fig4e.n_wavelengths}--> wavelengths:

| path | trace | model | digitized | model − digitized |
|---|---|---|---|---|
| 0 −> 0 | T00 | −1.40<!--{switching.bar_il_vs_fig4e.per_port[0].model_db}--> dB | −2.43<!--{switching.bar_il_vs_fig4e.per_port[0].digitized_db}--> dB | +1.03<!--{switching.bar_il_vs_fig4e.per_port[0].difference_db}--> dB |
| 1 −> 1 | T11 | −1.80<!--{switching.bar_il_vs_fig4e.per_port[1].model_db}--> dB | −2.27<!--{switching.bar_il_vs_fig4e.per_port[1].digitized_db}--> dB | +0.47<!--{switching.bar_il_vs_fig4e.per_port[1].difference_db}--> dB |
| 2 −> 2 | T22 | −1.80<!--{switching.bar_il_vs_fig4e.per_port[2].model_db}--> dB | −1.75<!--{switching.bar_il_vs_fig4e.per_port[2].digitized_db}--> dB | −0.05<!--{switching.bar_il_vs_fig4e.per_port[2].difference_db}--> dB |
| 3 −> 3 | T33 | −1.40<!--{switching.bar_il_vs_fig4e.per_port[3].model_db}--> dB | −1.48<!--{switching.bar_il_vs_fig4e.per_port[3].digitized_db}--> dB | +0.08<!--{switching.bar_il_vs_fig4e.per_port[3].difference_db}--> dB |
| | **mean** | | | **+0.38<!--{switching.bar_il_vs_fig4e.mean_signed_diff_db}--> dB** (abs 0.49<!--{switching.bar_il_vs_fig4e.mean_abs_diff_db}--> dB) |

The model is **optimistic** — it predicts less loss than the chip shows — by 0.38<!--{switching.bar_il_vs_fig4e.mean_signed_diff_db}--> dB on
average, 0.49<!--{switching.bar_il_vs_fig4e.mean_abs_diff_db}--> dB in absolute value, with the per-path difference running from −0.05<!--{switching.bar_il_vs_fig4e.per_port[2].difference_db}--> to
+1.03<!--{switching.bar_il_vs_fig4e.per_port[0].difference_db}--> dB. That is the same direction as the eight-path comparison against the paper's
quoted range in §3, and about the same size. **It does not reproduce the ordering of the
four ports.** The modelled fabric is symmetric under port reversal, so it returns two
distinct losses across four ports (T00 = T33 < T11 = T22), while the measured diagonals
are monotone in port index (T33 < T22 < T11 < T00). Of the six port pairs the model orders
2<!--{switching.bar_il_vs_fig4e.pairs_ordered_correctly}--> correctly and 2<!--{switching.bar_il_vs_fig4e.pairs_ordered_wrongly}--> wrongly, and ties the remaining 2<!--{switching.bar_il_vs_fig4e.pairs_tied_in_the_model}--> — which is what a symmetric model must
do against an asymmetric chip, and is a statement about the loss model rather than about
the fabrication spread. These are the `switching.bar_il_vs_fig4e` keys.

**The Fig 4d and Fig 4e fits are not coupled.** The Fig 4d mesh fit draws its fabrication
spreads from `SIGMA_SPLIT` and `SIGMA_PHASE` and takes the coupler's 3-dB wavelength and
slope as its free parameters. With both spreads assumed rather than fitted, there is
nothing to alternate with: one pass fixes λ₀ and the slope, and refitting at the converged
values reproduces them exactly. The fitted λ₀ is 1574.6785<!--{fig4d_mesh_fit.lambda0_nm}--> ± 0.6093<!--{fig4d_mesh_fit.lambda0_se_nm}--> nm, which is what
`DC_LAMBDA_3DB` = 1574.7 nm carries.

**Cross-check against the other panel.** The Fig 4d port pair T20 is not drawn anywhere in
Fig 4e, so T32 was digitized in its place, and there is no port pair that both panels
report. Any comparison between the two panels therefore compares two *different* port
pairs of the same fabric — T20 in the all-cross state and T32 in the all-bar state — and
not the same pair measured twice. That still tests whether one coupler fit and one assumed
spread describe the whole fabric, which is the useful test; it is not a repeat measurement
of one path.

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
| `DC_LAMBDA_3DB` | 1574.7<!--[lightin.coupler.DC_LAMBDA_3DB]--> nm | `coupler.py:27`; every coupler and switch spectrum | §6.1 — fit of `mesh_t20_model` to the 25<!--{fig4d_mesh_fit.n_points}--> points of `data/fig4d_T20_digitized.csv`, digitized from the paper's Fig 4d. Both fabrication spreads are assumed rather than fitted, so the fit is solved in one pass and refitting at the converged value reproduces it |
| `DC_SLOPE` | 0.0026<!--[lightin.coupler.DC_SLOPE]--> rad/nm | `coupler.py:32`; the same spectra | §6.1 — the same fit; pairs bootstrap [0.00239<!--{fig4d_mesh_fit.slope_pairs_p05}-->, 0.00285<!--{fig4d_mesh_fit.slope_pairs_p95}-->] rad/nm |
| `PROP_LOSS_DB_CM`, `alpha_db_cm`, `loss_db_cm` | 2.0<!--[lightin.coupler.PROP_LOSS_DB_CM]--> dB/cm | `coupler.py:42,129`; `recirculating.py:51,160,196` | `coupler.py` module docstring — 2.14 dB/cm (arXiv:2111.01792), 2.2 ± 0.8 dB/cm over 19 dies (arXiv:1203.0767), ~2 dB/cm (nanoph-2023-0836) |
| `excess_loss_db` / `DC_EXCESS_LOSS_DB` | 0.1<!--[lightin.coupler.DC_EXCESS_LOSS_DB]--> dB per coupler | `coupler.py:46,75,85`, called from `switching.py:76,111` | `coupler.py` module docstring — directional-coupler excess loss ~0.1–0.8 dB (Optica jlt-35-22-4916) |
| `kappa0` (nominal split) / `DC_KAPPA0_NOMINAL` | 0.5<!--[lightin.coupler.DC_KAPPA0_NOMINAL]--> | `coupler.py:45,63,74,84,104`; `switching.py:67` | no source recorded |
| `peak_loss_db` / `GRATING_PEAK_LOSS_DB` | 4.4<!--[lightin.coupler.GRATING_PEAK_LOSS_DB]--> dB | `coupler.py:47,122`; fibre-to-fibre link budget | `coupler.py` module docstring — ~4.4 dB grating-coupler insertion loss (arXiv:1203.0767) |
| `bw_1p5db` / `GRATING_BW_1P5DB_NM` | 45.0<!--[lightin.coupler.GRATING_BW_1P5DB_NM]--> nm | `coupler.py:49,123`; fibre-to-fibre link budget | `coupler.py` module docstring — ~45 nm 1.5-dB bandwidth (arXiv:1203.0767) |
| `waveguide_cm` / `LINK_WAVEGUIDE_CM` | 0.45<!--[lightin.coupler.LINK_WAVEGUIDE_CM]--> cm | `coupler.py:50,134`; fibre-to-fibre link budget | the paper's 4.5 mm on-chip path length, the same length the latency row uses; `DOCUMENT_SEARCH_LIST_superseded.md` marks n_g = 4.0 and 4.5 mm as exact from the paper. Not listed in the §6 table. |
| `n_couplers_in_path` / `LINK_N_COUPLERS` | 4<!--[lightin.coupler.LINK_N_COUPLERS]--> | `coupler.py:51,135`; fibre-to-fibre link budget | no source recorded |
| `n_grating` / `LINK_N_GRATING` | 2<!--[lightin.coupler.LINK_N_GRATING]--> | `coupler.py:52,136`; fibre-to-fibre link budget | no source recorded |
| `DEMO_LAMBDA0` | 1560.0<!--[lightin.coupler.DEMO_LAMBDA0]--> nm | `coupler.py:55`; synthetic demo dataset only | no source recorded — §4.2 states it is deliberately independent of the chip fit and says nothing about this chip |
| `DEMO_TRUE_KAPPA0` | 0.5<!--[lightin.coupler.DEMO_TRUE_KAPPA0]--> | `coupler.py:58`; synthetic demo dataset only | no source recorded |
| `DEMO_TRUE_SLOPE` | 0.0042<!--[lightin.coupler.DEMO_TRUE_SLOPE]--> rad/nm | `coupler.py:59`; synthetic demo dataset only | no source recorded |
| `DEMO_TRUE_QUAD` | −8e-6<!--[lightin.coupler.DEMO_TRUE_QUAD]--> rad/nm² | `coupler.py:60`; synthetic demo dataset only | no source recorded |
| `FIG4D_FLOOR_DB` | −26.2<!--[lightin.switching.FIG4D_FLOOR_DB]--> dB | `switching.py:34`; recorded, not added to any reported crosstalk | §6.1 — fitted to the digitized Fig 4d alongside λ₀ and slope; §6.1 also states that its physical origin is not established |
| `prop_db_per_stage` / `PROP_DB_PER_STAGE` | 0.25<!--[lightin.switching.PROP_DB_PER_STAGE]--> dB per stage | `switching.py:20,56,102,247`; on-chip insertion loss, all switch spectra | no source recorded |
| `SIGMA_SPLIT` | 0.02<!--[lightin.switching.SIGMA_SPLIT]-->, clipped to [0.3, 0.7] | `switching.py`; bar-state crosstalk | no source recorded — the digitized Fig 4e curve was fitted for it and the fitted value was not adopted, because the model does no better on those points than a constant and the result ranges over a factor of 4.6<!--{fig4e_fit.sensitivity.sigma_split_range_factor}--> with the ensemble percentile. 0.02<!--{cross_check.sigma_split}--> falls inside that range, so §6.1 records the panel as a consistency check on this value rather than a source for it |
| `SIGMA_PHASE` | 0.02<!--[lightin.switching.SIGMA_PHASE]--> rad | `switching.py`; bar-state crosstalk | no source recorded — the Fig 4e curve constrains only the combination of the two spreads, so this one is held rather than fitted (§6.1) |
| `ARM_LOSS_DB` | (0.0<!--[lightin.switching.ARM_LOSS_DB[0]]-->, 0.0<!--[lightin.switching.ARM_LOSS_DB[1]]-->) dB | `switching.py:188`; the MZI phase section | no source recorded |
| `MEAS_NOISE_SIGMA` | 0.01<!--[lightin.ppuf.MEAS_NOISE_SIGMA]--> rad per MZI | `ppuf.py:31`; PUF reliability | recorded in the code itself, `MEAS_NOISE_SOURCE`: "assumed value, not taken from the paper; reliability scales with it" |
| `N` (PUF mesh ports) / `N_PORTS` | 8<!--[lightin.ppuf.N_PORTS]--> | `ppuf.py:28,58,69,101`; every PUF statistic | no source recorded |
| `r` (ring self-coupling) / `RING_R` | 0.92<!--[lightin.mrm.RING_R]--> | `mrm.py:19,26,35`; monitoring curve and extinction ratio | no source recorded — §6.2 records that the MRM ring is not tabulated in the paper; `DOCUMENT_SEARCH_LIST_superseded.md` DOC-3 lists r as a value to be obtained, and it was not obtained |
| `a` (round-trip amplitude) / `RING_A` | 0.90<!--[lightin.mrm.RING_A]--> | `mrm.py:20,26,35`; monitoring curve and extinction ratio | no source recorded — the same DOC-3 entry |
| `data_swing` / `DATA_SWING_RAD` | 0.9<!--[lightin.mrm.DATA_SWING_RAD]--> rad | `mrm.py:21,35`; the two symbol levels | no source recorded — DOC-3 lists the V_swing/V_π conversion as outstanding |
| `bw` (eye one-pole bandwidth) / `EYE_BW` | 0.45<!--[lightin.mrm.EYE_BW]--> per bit period | `mrm.py:22,71`; eye figure only | no source recorded — the eye is labelled illustrative |
| `noise` (eye detector noise) / `EYE_NOISE` | 0.02<!--[lightin.mrm.EYE_NOISE]--> a.u. | `mrm.py:23,71`; eye figure only | no source recorded — the same |
| `ring_um` (all-pass validation ring) / `ALL_PASS_RING_UM` | 120.0<!--[lightin.recirculating.ALL_PASS_RING_UM]--> µm | `recirculating.py:23,160,169`; solver validation only | no source recorded — a validation geometry, not a chip value |
| `ring_um` / `base_um` (add-drop and bus rings) / `ADD_DROP_RING_UM` | 600.0<!--[lightin.recirculating.ADD_DROP_RING_UM]--> µm | `recirculating.py:24,181,196,208,267,302`; solver validation and the comb figure | no source recorded — the same |
| `detune` (ring-to-ring detuning) / `BUS_DETUNE` | 0.004<!--[lightin.recirculating.BUS_DETUNE]--> | `recirculating.py:25,267`; the comb figure | no source recorded — the same |
| `N_RESTARTS` | 15<!--[lightin.nn_iris.N_RESTARTS]--> | `nn_iris.py:22`; every Iris accuracy | no source recorded |
| `test_size` (Iris split) / `TEST_SIZE` | 0.3<!--[lightin.nn_iris.TEST_SIZE]--> | `nn_iris.py:23,38`; every held-out Iris accuracy | no source recorded — §3 records that the paper's evaluation set is not established |
| L2 penalty on the trained parameters / `L2_PENALTY` | 1e-4<!--[lightin.nn_iris.L2_PENALTY]--> | `nn_iris.py:24,78`; every Iris accuracy | no source recorded |

Two of these carry more weight than the rest. The 0.25 dB per-stage propagation loss sets
the on-chip insertion loss that §5 item 5 reports as low against the paper's measurement,
and `MEAS_NOISE_SIGMA` sets the PUF reliability of row 25. Neither was tuned to improve
agreement with the paper. The two 0.02 fabrication spreads set the bar-state crosstalk
outright, and the one measured panel that bears on them, Fig 4e, constrains only the
combination the two enter together (§6.1).

### 6.4 Details taken from the preprint

A second source is used from here on: Y. Zhu *et al.*, "Versatile silicon integrated photonic
processor: a reconfigurable solution for next-generation AI clusters", arXiv:2504.01463v2.
It is an **earlier version** of the published article this repository reproduces, and some of
its numbers differ from the published ones. **Wherever the two disagree the published value
is the one kept**, with one stated exception noted below. `docs/PREPRINT_NOTES.md` carries
the same material with the section reference for every item.

**Chip and mesh**

* The chip carries 20 optical ports, split equally between two opposite edges and coupled
  through two fibre arrays, with the gratings spaced 222.22<!--[lightin.square_mesh.GRATING_SPACING_UM]--> µm apart (preprint §4.1;
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
| 100-die simulated uniqueness | 49.97% (§2.5) | 49.97%<!--{ppuf_recirc.vs_feedforward.paired_uniqueness.paper_uniqueness}--> | same |
| 100-die simulated uniformity | 50.15% (§2.5) | 50.15% | same |
| Switch crosstalk at 1560 nm | at least −20 dB, up to −40 dB (§2.4) | −45 to <−20 dB | **differs** (best case 5 dB apart) |
| Switch crosstalk bandwidth | under −15/−20 dB over more than **2 nm** (§2.4) | over more than **20 nm** | **differs** by a factor of ten |
| Unitary effective bits | 10.7 bits at σ² = 0.0012 (§2.2) | 6.22 bits at σ = 0.0269 | **differs** |
| Non-unitary effective bits | 7.32 bits at σ² = 0.0125 (§2.2) | 5.47 bits at σ = 0.0453 | **differs** |
| Arm-length difference mean μ | −0.08 µm (§2.5) | +0.08 µm as transcribed in `ppuf.py` | **differs in sign** |

Two of these need more than a value comparison.

**The effective-bit rows differ in convention as well as in value.** The preprint's figures
are log₂(2/σ²) on the variance: log₂(2/0.0012) = 10.70 and log₂(2/0.0125) = 7.32. The
published figures are log₂(2/σ) on the standard deviation: log₂(2/0.0269) = 6.2163<!--{unitary.enob_at_sigma_0.0269}--> and
log₂(2/0.0453) = 5.4643<!--{nonunitary.enob_at_sigma_0.0453}-->. `lightin/metrics.py` implements the published convention, and the
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
grating waveguide of a stated 250<!--[lightin.square_mesh.GRATING_WG_UM]--> um to each of 20 boundary ends, ten on the top edge and
their half-turn images on the bottom, so that the set of 20 maps onto itself under the half
turn. Which ten, and which pair is injected, are chosen by search on the stated criterion
that every response pair should carry light. Under equal grating lengths that waveguide is
a common factor and cancels out of every comparison; the preprint says the real sections
are *not* equal, and that non-uniformity is not modelled.

Boundary ends that carry no grating are left terminated rather than declared external.
With that accounting the lossless mesh conserves energy exactly, which is the check that
the wiring neither loses nor creates power.

---

## Checking this report against the repository

Every number in this report that comes from `results.json` is written as the value followed
by an HTML comment naming its path, as in `1574.7<!--{fig4d_mesh_fit.lambda0_nm}--> nm`.
GitHub's renderer strips the comment, so it is invisible on the page and visible to
`tests/test_report_consistency.py`, which resolves each path and compares the stored value
with the written one at the precision it was written to. The test runs with the rest of the
suite, so a regenerated `results.json` that moves a number fails the suite until the
document is brought back into line. The numbers that carry no such comment are not
oversights: each is listed in [`docs/REPORT_UNCHECKED.md`](REPORT_UNCHECKED.md) with its
section and where it comes from, whether that is the paper, the preprint, a code constant,
arithmetic on other values, or a quantity computed outside `results.json`.

A path may carry one modifier after a pipe, which says how the written value was derived
from the stored one. `|pct` multiplies the stored value by 100, for a quantity this report
writes as a percentage-point difference where `results.json` stores a fraction -- the paired
Iris and PUF differences quoted in points. `|abs` compares magnitudes, for a quantity whose
sign this report carries in a word rather than a character, as the 0.0006 dB by which the
bar model is *worse* than a constant. A value that already carries a `%` sign must not also
carry `|pct`, and the test fails if both appear, so the scale is never applied twice. A
modifier that is not one of the two fails the test by name.

The parameter table in §6.3 is checked a different way, because `results.json` cannot
police it: that file records what the model produced, not the constants the model was given.
A row of that table whose name is a module-level constant carries a square-bracket comment
naming the module and attribute, as in `0.02<!--[lightin.switching.SIGMA_SPLIT]-->`, and
`tests/test_constants_documented.py` imports each one and compares it with the documented
value. All thirty-two rows are checked that way. Nineteen of them were default arguments or inline
literals with no name to import; each was given one and the defaults and call sites now
reference it, so the row names both the argument and the constant. Naming them changed no
value -- it is what brought them inside the check.

The same square-bracket markup is used outside that table, wherever either document states a
value that a module holds under a name: the chip geometry the §6 table takes from the paper's
Methods, the two design wavelengths, the grating pitch and waveguide length taken from the
preprint, the structural-zero threshold quoted in §3, and the geometry the README restates in
its own words. Those are the paper's and the preprint's numbers, but they are also
transcriptions, and the check is what keeps the transcription honest. Both the consistency
test and the constants test read `README.md` as well as this report, so a value cannot be
correct in one document and stale in the other.

Every row of that table, checked or not, names the file and line where its parameter lives,
and `tests/test_source_lines_documented.py` reads each cited line and requires it to name
the parameter or carry the documented value. Line numbers move when a module is edited, so
without that check a citation can go stale silently while every other test stays green.

`python -m pytest -q` takes about 50 seconds on this machine, because
`test_fig4d_digitized_fit` calls only the two single fits (`fit_proxy` and `fit_mesh`) instead
of `fit_fig4.main()` with its bootstraps, `test_iris_accuracy` runs five random restarts rather
than the fifteen the reported accuracies use, and every Fig 4e check runs at a few hundred
fabrication realisations rather than 3200. The best restart is kept, so the test's accuracy is
a lower bound on the reported one. A full `python scripts/run_all.py` takes about 22 minutes
and prints a per-block runtime summary at the end; `python scripts/run_all.py --quick` runs the
same pipeline with the Iris seed sweep cut to two seeds and every Fig 4d and Fig 4e bootstrap
to 50 resamples, writing `results_quick.json` and `figures_quick/` so that a quick run never
overwrites the reported outputs. Quick-mode numbers are noisier and are not the ones quoted
here.

When a number here disagrees with `results.json`, or with the module it documents, the
document is what changes.

---

## 7. Open items

### 7.1 Limitations that cannot be resolved from the published material

* The paper's Iris evaluation set is not established from the published values.
* The coupler 3-dB wavelength carries a model-form uncertainty (3.6 nm between the proxy and
  mesh models) that the bootstrap intervals do not include.
* The −25 dB crosstalk floor in Fig 4d is modelled only as a fitted constant; whether it
  comes from the device (phase error, back-reflection, leakage paths) or from the
  measurement set-up is not established.
* The rotational symmetry of the PUF design is reproduced from the preprint's description,
  but the specific MZI index groups shown in the paper's Fig. 5 were not read, so the orbit
  construction here may not match the chip's.
* The vertex wiring of the recirculating mesh is a stated choice, not the paper's, and the
  search over it is exhaustive only over uniform rules (§6.5). Every recirculating-PUF number
  is conditional on that choice, mitigated but not removed by the two wirings agreeing to
  0.0002 on uniqueness.
* One of the two fabrication spreads is still assumed, because the bar-state data
  constrains only their combination.
* The four digitized bar-state insertion losses are lower than the paper's quoted range at
  one end and higher at the other, and the repository does not record the switch state,
  wavelength or path set behind that quoted range, so the two cannot be reconciled from
  what is available here.

### 7.2 Disagreements on record

* The insertion-loss parameters in `switching.py` (0.25 dB per stage and 0.1 dB coupler
  excess loss, both code constants rather than `results.json` values) have now been checked
  against the paper's measured on-chip range. The model gives −1.40 to −1.80 dB over the
  eight intended paths against the paper's measured −1.85 to −2.99 dB, so the two ranges do
  not overlap and the model is optimistic by 0.45 dB at the least-lossy end and 1.19 dB at
  the most-lossy end. The parameters were left unchanged, so the disagreement is on record
  rather than tuned away.
* The chip's bar-state insertion loss falls monotonically with port index while the fabric
  model is symmetric under port reversal. Modelling the non-uniform grating-to-MZI
  waveguide sections described in the preprint would test whether those sections account
  for the difference.

### 7.3 Work that would resolve or narrow an item above

* The Iris accuracies depend on the installed scipy and scikit-learn versions: with
  `nn_iris.py` unchanged, seed 0 currently yields a full-set accuracy of 95.33% where an
  earlier environment recorded 94.67%. The environment is now pinned by `requirements-lock.txt`
  and recorded in the `environment` block, but the size of that variation across versions has
  not been measured, so how far the numbers move on another stack remains unknown. Measuring it
  would also narrow the item on the paper's Iris evaluation set, by separating how much of the
  difference from the published accuracies is the library stack.
* The population spread of the PUF metrics is reported across ten seeds; the die counts
  used here (40 for the sweeps, 100 for the headline run) are smaller than a full
  characterisation would use.
* Earlier report versions are not covered by the consistency test and are kept only as
  history.
* Twenty-three of the parameters in §6.3 have no source recorded anywhere in this repository:
  the nominal 0.5 coupler split; `n_couplers_in_path` = 4 and `n_grating` = 2 in the link
  budget; the four synthetic-demo constants `DEMO_LAMBDA0`, `DEMO_TRUE_KAPPA0`,
  `DEMO_TRUE_SLOPE` and `DEMO_TRUE_QUAD`; the 0.25 dB per-stage propagation loss; the two 0.02
  fabrication spreads `SIGMA_SPLIT` and `SIGMA_PHASE`, and `ARM_LOSS_DB`, in `switching.py`;
  the 8-port PUF mesh size; the MRM ring's `r` = 0.92, `a` = 0.90 and `data_swing` = 0.9
  together with the eye model's `bw` = 0.45 and `noise` = 0.02; the 120 µm and 600 µm
  validation-ring lengths and the 0.004 ring detuning in `recirculating.py`; and `N_RESTARTS` =
  15, the 0.3 test fraction and the 1e-4 L2 penalty in `nn_iris.py`. Each is a value someone
  chose. `MEAS_NOISE_SIGMA` is the one assumed parameter whose status is already recorded in
  the code; the rest are not. One of them, the 0.25 dB per-stage propagation loss, is a
  parameter behind the insertion-loss disagreement above, so sourcing it would say whether that
  gap is a parameter choice.
