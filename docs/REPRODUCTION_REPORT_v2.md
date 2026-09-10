# LightIN — reproduction report

Paper: Zhu *et al.*, "LightIN: a versatile silicon-integrated photonic FPGA…",
*Light: Science & Applications* 15:165 (2026).

This report states exactly what was reproduced, how faithfully, and what could not be
reproduced. **Every value in the "This reproduction" columns is read from `results.json`**
as emitted by `scripts/run_all.py`; nothing is transcribed from an earlier draft. Values in
the "Paper value" columns are the paper's own, quoted from its Methods and Supplementary
Note 3 for comparison only — they are not outputs of this code and do not appear in
`results.json`.

---

## 1. What "reproduce" can mean here

The paper combines (a) a **fabricated** SOI photonic chip (40 PUCs, 4×4 square
recirculating mesh), (b) a software configuration framework, and (c) experimental
demonstrations. Two of the three buckets can be reproduced without the chip:

* **Bucket A — definitions & arithmetic.** Exactly reproducible (the PUC matrix, the
  effective-bit formula, propagation latency).
* **Bucket B — simulations the paper itself ran.** Reproducible by re-implementing them
  (unitary/non-unitary realisation, the offline-trained Iris network, the 100-die PUF
  statistics, the differentiator principle, the switch topology/crosstalk model).
* **Bucket C — physical measurements.** *Not* reproducible without the chip (measured
  eye-diagram SNR/Q, measured crosstalk spectra, the measured non-unitary input/output
  correlation of Fig. 2n, the 2-die experimental PUF).

Nothing in bucket C is fabricated here; those rows are marked **hardware — not
reproduced**.

A third label is used for the energy and throughput rows: **consistency check**. Those
numbers reproduce arithmetically, but every input to the arithmetic comes from
Supplementary Note 3 rather than from anything this code can verify, so a match confirms
the derivation, not the device.

The design wavelength is **1560 nm** throughout (matrix multiplication, coupler, switch);
1555 nm is the micro-ring locking experiment and 1545 nm the grating-coupler peak.

---

## 2. Results: paper vs this reproduction

| # | Result (figure) | Paper value | This reproduction | Tier |
|---|---|---|---|---|
| 1 | PUC unitarity / cross-bar (Eq. 1) | unitary, cross & bar states | unitarity err ≤ 1e-32; cross/bar correct | **A exact** |
| 2 | 4×4 permutation matrices (Fig. 2d) | realised by routing | routing fidelity **0.999999999999** (both) | **B** |
| 3 | 4×4 random unitaries (Fig. 2h,i) | high-fidelity realisation | fidelity **1.000000**, \|·\| corr **1.000000** | **B** |
| 4 | Unitary effective bits @10 GBaud (Fig. 2f) | σ=0.0269 → **6.22 bit** | log₂(2/0.0269) = **6.2163 bit** | **A exact** |
| 5 | Non-unitary 3×3 mesh (Fig. 2l) | modulus agreement | \|·\| corr **1.000000**, max err **7.8e-16** | **B** |
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
| 17 | Switch crosstalk at 1560 nm (Fig. 4d,e) | −45 to <−20 dB | cross **−29.15 to −22.32 dB**; bar **−106.66 to −30.50 dB** | **B** (physical) |
| 18 | Switch crosstalk, worst over C-band | <−15/−20 dB over >20 nm | cross **−11.55 dB**; bar **−30.50 dB** (1530–1565 nm) | **B** (physical) |
| 19 | Measured crosstalk spectra (Fig. 4d,e) | measured | not reproduced | **hardware — not reproduced** |
| 20 | Fibre-to-fibre link budget | −1.85 to −2.99 dB on-chip (8 paths) | **11.43 dB** fibre-to-fibre, grating-dominated | **B** |
| 21 | PUF uniqueness, 100 dies (Fig. 5) | **49.97%** (simulation) | **49.01%** | **B** |
| 22 | PUF uniformity, 100 dies (Fig. 5) | **50.15%** (simulation) | **50.12%** | **B** |
| 23 | PUF reliability | 2.55% intra-die HD (experimental) | **0.72%** (model, clean noise) | **B** (model) |
| 24 | PUF experimental, 2 dies | 57.71% / 42.62% / 2.55% | not reproduced | **hardware — not reproduced** |
| 25 | Recirculating-mesh solver | — | ring **2.9e-16**, add-drop **8.4e-16** vs analytic | **B** |

---

## 3. Notes on the modelling choices

**Unitary mesh (rows 2–4).** Arbitrary unitaries are realised on a universal Clements
rectangular mesh of 2-DOF MZIs; the programming phases are *fitted*, then the realised
matrix is rebuilt independently from the physical MZI matrices, so fidelity = 1 is a
genuine check rather than a tautology. The permutations of Fig. 2d are treated the same
way: `_best_routing` optimises the single-θ mesh phases and reports the fraction of input
power that actually reaches each target port, giving **0.999999999999** for both. A
permutation matrix compared against itself would give 1 by construction and would test
nothing, so the routing optimisation is what makes row 2 a measurement.

The paper's physical single-θ PUC (Eq. 1) has one DOF per cell and therefore limited
unitary expressivity — acknowledged in the paper's Discussion, and quantified in §4.1.

**Effective bits (rows 4, 7).** The paper's 6.22 and 5.47 bit follow from
ENOB = log₂(range/σ) with range = 2 (outputs in [−1, 1]). Both reproduce to two decimals,
which also confirms the convention.

**Non-unitary (rows 5–6).** The SVD/diamond realisation is checked by element-modulus
agreement: correlation **1.000000** and maximum absolute error **7.8e-16**. That is the
whole of the simulation check. Fig. 2n is the chip's measured input/output correlation;
comparing the model's output vector against a copy of itself would return 1.0 while
measuring nothing, so no vector correlation is reported.

**Iris (rows 8–11).** The photonic layer is a trainable 4×4 unitary whose four detected
intensities feed a small learned linear readout, consistent with the paper's *offline*
training. Reporting a single seed is not defensible here: over 10 seeds (the seed drives
both the 70/30 stratified split and the 15 random restarts) the full-set accuracy is
**95.47% ± 1.26%** and the held-out accuracy **89.33% ± 5.14%**. The paper's 94.67% sits
comfortably inside that spread, so agreement at one seed is not evidence of much.

Two controls put the number in context, both on the same splits:

* **Identity control** — the unitary frozen to I, only the readout trained: **85.60% ±
  0.44%** full set, **81.56% ± 4.67%** held out. The programmable unitary is therefore
  worth about 10 points, which is a real contribution.
* **Logistic baseline** — plain multinomial logistic regression on the same four
  standardized features: **96.53% ± 0.88%** full set, **94.89% ± 3.45%** held out. This
  **beats the photonic layer on both quantities**, by 1.06 and 5.56 points. The Iris
  demonstration shows that the mesh can be trained to classify; it does not show that the
  mesh classifies better than a four-parameter linear model.

The paper's 94.67% and 93.33% are exactly 142/150 and 140/150 and are not integer ratios
of any smaller plausible evaluation set, so they are almost certainly over all 150
samples. The full-set column is therefore the comparable quantity; the held-out column is
reported separately and is *not* the paper's 93.33%, which is an on-chip measurement.

**Energy and throughput (rows 13–14).** Reported as consistency checks, not as
reproductions. The derivation is the paper's own: 40 PUCs, each biased at E[θ] = π/2 and
so drawing on average half of the 90 mW π-power, gives **45 mW per cell and 1.8 W across
the 40 cells**; dividing by the 4×4 MAC rate of **9.6e11 MAC·s⁻¹** at 10 GBaud yields
**1.875 pJ/MAC**, and the Supplementary op count gives **1.92 TOPS**. The 3 V across
100 Ω, the 90 mW, and the 96-operation count all come from Supplementary Note 3 and
cannot be checked against the main article.

**Switching (rows 17–20).** The 4-stage planar (Spanke-Beneš) topology is a rectangular
mesh of nearest-neighbour 2×2 switches, with crosstalk and loss produced by the
coupled-mode-theory coupler of §4.2 rather than a hand-set slope. At 1560 nm the model
gives cross-state crosstalk of **−29.15 to −22.32 dB** and bar-state **−106.66 to
−30.50 dB**, against the paper's −45 to <−20 dB.

Over the full C-band the agreement is weaker and is stated plainly: the **worst
cross-state crosstalk the code produces over 1530–1565 nm is −11.55 dB** (bar state
−30.50 dB). The paper claims better than −15/−20 dB over more than 20 nm, so the model is
about 4 dB short of the claim at the band edges. This is a consequence of a single
directional-coupler design being 3-dB at only one wavelength (§4.2): away from that
wavelength the couplers are imbalanced and the switches leak. Reporting the worst case
over the band the paper claims, rather than over a narrow window near the coupler's best
point, is what makes this row informative.

Both states report **0 structural zeros**: no port pair was excluded from the crosstalk
statistics for carrying no power, so the numbers above are over every off-target path.

**PUF (rows 21–24).** A response is a property of **one** die. The mesh is built once per
die as θ = π·challenge + ε (+ measurement noise), with ε that die's fixed per-MZI phase
error; equal-power light enters the two diagonal ports 0 and N−1 of that single mesh, and
bit *i* compares the two outputs of pair (2i, 2i+1). Both compared intensities therefore
come from the same physical chip. Both injections are needed: in a feed-forward mesh,
reaching output *k* from input 0 costs *k* cross-couplings, so single-edge injection
leaves power decaying monotonically with port index and biases every pair towards its
even member; the diagonal pair has mirror-image decay and the bias cancels.

At the arm-length-derived spread the model gives uniqueness **49.01%**, uniformity
**50.12%**, intra-die reliability **0.72%** and a **tie fraction of 0.0**.

Because the response is now driven by physics rather than by construction, uniqueness is
a *function* of the manufacturing spread, and the sweep is the honest way to report it
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
1e-12; ties are resolved as 1 and counted rather than hidden. At σ = 0.001 the mesh is
still essentially a permutation, only the two routed outputs carry power, and the tie
fraction is non-zero. That regime is also where reliability (0.2198) is as large as
uniqueness (0.2164): the bits are being set by measurement noise rather than by the die,
which is exactly what a non-functioning PUF looks like. At the paper's spread the two
separate by a factor of 70, which is what makes the response a signature.

---

## 4. Physics extensions (beyond the first-pass models)

### 4.1 Single-θ PUC expressivity (`expressivity.py`) — paper Discussion, made explicit

The paper's PUC (Eq. 1) has one thermo-optic phase shifter, so one DOF per cell. A
universal N-mode interferometer needs N² real DOF; a rectangular mesh of single-θ cells
supplies only N(N−1)/2. For N = 4 that is **6 DOF inside a 16-dimensional U(4)**, rising
to **10** with output phases and **16** only for the full 2-DOF mesh.

Best-fit fidelity to Haar-random U(4) climbs the same ladder: **0.5605** for single-θ,
**0.8264** with output phases, **1.000000** for the universal 2-DOF mesh. This is *why*
the paper demonstrates permutations and specific realisable matrices rather than arbitrary
unitaries. A unitary generated by a single-θ mesh is recovered to fidelity **1.0000**, and
permutations are routed at fidelity **0.999999999999**.

### 4.2 Coupled-mode-theory coupler with real dispersion (`coupler.py`)

The coupler is a CMT directional coupler with literature-grounded SOI dispersion and loss,
and it is fitted to the chip's own measured crosstalk (§6.1). A single straight
directional coupler is 3-dB at **one** wavelength; away from it the split is imbalanced
and the MZI extinction is capped.

At its 3-dB wavelength the model's extinction ratio is reported as **null**, not as a
number: the model contains no loss and no coupler imbalance there, so the minimum
transmission is an ideal null and the ratio diverges. Reporting a floored value such as
120 dB would state a finite extinction the model does not predict. Off that wavelength the
extinction is finite and physical: **23.91 dB at 1560 nm** and **10.71 dB at 1520 nm**.
The fibre-to-fibre link budget is **11.43 dB**, dominated by the two grating couplers.

The `demo_fit_kappa0` = **0.5460** and `demo_fit_slope` = **0.004370** entries in
`results.json` are recovered from the synthetic `_demo_measured_dataset`, not from chip
data, and are labelled as such by `demo_fit_note`. They demonstrate that
`fit_dc_dispersion()` recovers CMT parameters; they say nothing about this chip.

### 4.3 Full square *recirculating* mesh with feedback (`recirculating.py`)

The matrix-multiply functions use a feedforward rectangular sub-mesh, but the full chip
recirculates: light returns through closed loops, so the transfer function is rational and
has poles. That needs a linear solve, o = (I − S·C)⁻¹ S·b. The solver is validated against
the analytic all-pass ring to RMS **2.9e-16** and the add-drop ring to **8.4e-16**; the
4-PUC square plaquette conserves energy to **1.1e-15**, and the full **40-PUC**
recirculating bus solves with an energy-conservation deviation of **8.9e-16**.

---

## 5. Bottom line

Of the paper's headline quantitative claims, the bucket-A items (PUC unitarity, the
6.2163 / 5.4643-bit ENOB values, 60.04 ps latency) reproduce **exactly**. The bucket-B
simulations reproduce **closely and on independent code**: routing fidelity
0.999999999999, unitary fidelity 1.000000, non-unitary modulus correlation 1.000000, PUF
uniqueness 49.01% against the paper's 49.97%, and PUF uniformity 50.12% against 50.15%.
The bucket-C items are physical measurements and are left unreproduced rather than
fabricated.

Three results do not simply confirm the paper, and they are the useful output of this
reproduction:

1. **The C-band switch crosstalk is about 4 dB worse than claimed.** The model's worst
   cross-state crosstalk over 1530–1565 nm is **−11.55 dB** against a claim of better than
   −15/−20 dB over more than 20 nm. The mechanism is coupler imbalance away from the 3-dB
   wavelength, and it follows from the chip's own Fig. 4d data (§6.1).
2. **The coupler's 3-dB wavelength is not the design wavelength.** The bootstrap puts it
   at **1571.0 nm** with a 5–95% interval of **[1570.1, 1572.0] nm**, which excludes
   1560 nm by roughly nine interval widths (§6.1).
3. **A four-feature logistic regression beats the photonic Iris classifier** on the same
   splits, on both the full set (96.53% vs 95.47%) and the held-out split (94.89% vs
   89.33%). The identity control shows the unitary contributes about 10 points over the
   readout alone, so the mesh is doing real work — but Iris does not discriminate a
   photonic classifier from a linear one.

The three physics extensions (§4) make the model mechanistic rather than descriptive: the
single-θ expressivity limit is quantified (0.5605 mean fidelity to arbitrary U(4), rising
to 1.000000 only with the full 2-DOF mesh), explaining the paper's choice of matrix
classes; the switch crosstalk and loss emerge from a coupled-mode-theory coupler fitted to
the chip's measured spectrum; and the full recirculating mesh is solved with a
feedback-capable scattering-matrix network validated to ~1e-15, showing how feedback adds
poles and a strictly larger function class than the feedforward sub-mesh.

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
| On-chip insertion loss | −1.85 to −2.99 dB (8 measured paths) | loss budget |
| Design wavelengths | 1560 nm (matrix), 1555 nm (MRM), 1545 nm (grating peak) | all modules |
| MRM eye SNR / Q | 17.10 & 17.83 dB; Q 7.17–8.08 | mrm (hardware-only targets) |

### 6.1 Fig 4d digitized, and the coupler 3-dB wavelength decided by that data

The all-cross-state T20 crosstalk curve was colour-digitized from Fig 4d
(`data/fig4d_T20_digitized.csv`, 25 points; dB scale anchored to figure-read endpoints,
~±2 dB) and the CMT model fitted with `scripts/fit_fig4.py`. Because the 25 points carry a
±2 dB reading uncertainty, a point fit alone says nothing about how well λ₀ is determined,
so the fit is bootstrapped: the (λ, dB) pairs are resampled with replacement and refitted
**500 times**, with **0 failed fits discarded**.

Over the fitted wavelength range of **1549–1587 nm**:

* coupler 3-dB wavelength **λ₀ = 1571.0 nm**, 5–95% interval **[1570.1, 1572.0] nm**
* dispersion slope **0.0030 rad/nm**, 5–95% interval **[0.0026, 0.0033] rad/nm**

The decision rule was: if 1560.0 nm falls inside the λ₀ interval, keep 1560 nm as the
coupler's 3-dB wavelength; otherwise adopt the fitted value. **1560.0 nm lies outside
[1570.1, 1572.0] nm** — about 10 nm below the lower bound, roughly nine interval widths —
so the second branch applies. `coupler.py` therefore defines

```python
DC_LAMBDA_3DB = 1571.0  # nm, 3-dB point fitted to digitized Fig 4d
```

and `dc_power_coupling` and `fit_dc_dispersion` take it as their default `lam0`, while
`LAMBDA0 = 1560.0` remains the **design** wavelength. The two are different quantities and
the data says they are ~11 nm apart. The consequence is physical, not cosmetic: at 1560 nm
the power coupling is 0.468 rather than 0.500, the MZI extinction falls to 23.91 dB, and
the C-band worst-case switch crosstalk degrades to −11.55 dB.

A precise per-point digitization of the other three overlapping curves in each panel is
noise-limited, so only the cleanest curve (T20) was extracted; the stated geometry
(11.5 µm, 200 nm gap) anchors the rest. (Figure: `figures/fig4_digitized.png`.)

### 6.2 What is still genuinely unavailable

* Measured eye-diagram SNR/Q (17.10 / 17.83 dB, Q 7.17–8.08) are link measurements and
  remain **hardware-only**, though the model's locking principle and the target values are
  both confirmed.
* The measured non-unitary input/output correlation (Fig. 2n) requires the chip.
* The measured crosstalk spectra (Fig. 4d,e) require the chip; only the digitized T20
  curve is available, and it is used as fit input rather than reproduced.
* The 2-die experimental PUF numbers require two fabricated dies.
* The MRM ring radius / FSR (self-developed MRM) is not tabulated; the MRM model stays
  qualitative, using the 0.1 ns differentiator delay and the 1555 nm carrier.
* Table SI 2 PDK sub-values (per-ADC loss, edge-coupler loss) did not extract cleanly.
  They drive only the 32×32 / 64×64 scaling projection, not the 4×4 results, which use the
  directly-stated measured path losses.

---

## 7. Open items

* The PUF is simulated on a feed-forward rectangular mesh, whereas the chip's PUF runs on
  the 40-cell recirculating square mesh; re-running the PUF with `lightin/recirculating.py`
  is outstanding.
* The PUF test judges the low-spread case by reliability rather than by a uniqueness
  bound, because a symmetric comparison of two ports is randomised by any nonzero spread
  and only measurement noise distinguishes a working PUF from a non-working one.
* `scripts/run_all.py` takes about 7 minutes, of which about 325 s is the ten-seed Iris
  sweep; a `--quick` option that runs a single seed would shorten routine regeneration.
* The coupler 3-dB wavelength took the non-default branch of the §6.1 decision rule: the
  fitted 1571.0 nm is used as `lam0` in place of the 1560 nm design wavelength, because
  1560 nm falls outside the bootstrap interval.
* `lightin/expressivity.py` labels its coupler-imbalance ceiling "@1550nm" while sweeping
  1530–1565 nm and reporting the maximum, which now falls near 1571 nm. The label is
  wrong; the reported fidelity ceiling (min **0.9445** over the sweep) is not.
* The Iris accuracies depend on the installed scipy and scikit-learn versions: with
  `nn_iris.py` unchanged, seed 0 currently yields a full-set accuracy of 95.33% where an
  earlier environment recorded 94.67%. The seed sweep bounds this, but the environment is
  not pinned; a lockfile would make the Iris numbers reproducible across machines.
