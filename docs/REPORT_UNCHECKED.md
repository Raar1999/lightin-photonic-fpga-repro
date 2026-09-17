# Numbers in the report that the consistency test does not check

`tests/test_report_consistency.py` checks every number in `docs/REPRODUCTION_REPORT_v10.md`
and `README.md` that carries an HTML comment naming its `results.json` path. This file
records the numbers that carry no such comment, and why each one cannot carry one.

A number is listed here once, with every section it appears in, rather than once per
occurrence. Where a whole table of values shares one provenance, the table is listed as a
group and the per-value source stays in the table itself — copying thirty code constants
into a second document would create exactly the drift this campaign exists to remove.

Section numbers are the report's own. Values are written as the report writes them.

---

## 1. The paper's own values

Used as targets or as model inputs. They come from `s41377-026-02209-5` and its
supplementary, not from any computation in this repository.

| Value | Sections | What it is |
|---|---|---|
| 94.67% | §2, §3 | the paper's offline Iris accuracy |
| 93.33% | §2, §3 | the paper's on-chip Iris accuracy |
| 50.15% | §2, §3, §5, §6 | the paper's 100-die simulated PUF uniformity |
| 2.55% | §2, §3, §6 | the paper's 2-die experimental intra-die Hamming distance |
| 57.71% | §2, §6 | the paper's 2-die inter-die Hamming distance |
| 42.62% | §2, §6 | the paper's 2-die uniformity |
| 6.22, 5.47 | §2, §3, §6 | the paper's ENOB figures, quoted as published |
| 0.0269, 0.0453 | §2, §6 | the paper's noise standard deviations behind those ENOBs |
| −45, −20, −15 | §2, §3, §6 | the paper's crosstalk bounds |
| 20 (nm) | §2, §3, §6 | the paper's stated crosstalk bandwidth |
| ~60 (ps) | §2 | the paper's stated on-chip latency |
| 1.92, 1.875 | §2 | the paper's throughput and energy, in the "Paper value" column |
| 17–18 dB, Q 7–8, 17.10, 17.83, 7.17, 8.08 | §2, §6 | the paper's eye-diagram SNR and Q |
| 3, 96, 4.5 | §6 | the §6 paper-input table: the heater drive, the op count and the on-chip path length. The eight geometry values of that table -- the two indices, the coupler length, gap and width, the mesh side, the arm length and the heater length -- are transcribed into `coupler.py` as module-level constants, so each now carries a square-bracket comment and `tests/test_constants_documented.py` checks it |
| 1560, 1555, 1545 | §2, §3, §4, §5, §6 | the paper's design wavelengths. Where the §6 table states them as the design values they are checked against `coupler.LAMBDA0` and `coupler.LAMBDA_MRM`; the grating peak has no module-level name, and neither do the restatements elsewhere |
| 0.08, 0.11, 0.76, 1.05 | §3, §6 | the paper's PUF arm-length spread and the phase it implies |
| 49.97% where it appears in a "paper value" column with no adjacent published column | §2, §6 | see §2 below — the value *is* in `results.json` and is annotated wherever it is the repository's copy of it |

## 2. The preprint's values

From arXiv:2504.01463v2, quoted in §6.4 to compare with the published article. None is a
model output.

| Value | Section | What it is |
|---|---|---|
| 42.33% | §6 | preprint two-die uniformity, against the published 42.62% |
| −40, at least −20 | §6 | preprint crosstalk range |
| 2 (nm) | §6 | preprint crosstalk bandwidth, against the published 20 nm |
| 10.7, 10.70, 0.0012, 7.32, 0.0125, 0.0346 | §6 | preprint ENOB figures and the variance convention behind them |
| −0.08, +0.08 | §3, §6 | preprint arm-length mean, and the sign as `ppuf.py` had transcribed it |
| 20, 3.8, 3, 450 | §6 | preprint port count, footprint and waveguide widths. The grating pitch and the grating-to-MZI waveguide length are `square_mesh.GRATING_SPACING_UM` and `square_mesh.GRATING_WG_UM`, and are checked against those |

## 3. Code constants (§6.3 table, value column)

Nothing is listed here. These are inputs to the model, not outputs of it, so `results.json`
does not carry them and `tests/test_report_consistency.py` cannot reach them. Every one of
the thirty-two rows now names a constant defined at module level, carries a square-bracket
comment naming the module and attribute, and is imported and compared by
`tests/test_constants_documented.py`.

Nineteen of those constants were default arguments or inline literals with no name to
import. Each was given one -- `DC_EXCESS_LOSS_DB`, `DC_KAPPA0_NOMINAL`,
`GRATING_PEAK_LOSS_DB`, `GRATING_BW_1P5DB_NM`, `LINK_WAVEGUIDE_CM`, `LINK_N_COUPLERS`,
`LINK_N_GRATING`, `PROP_DB_PER_STAGE`, `N_PORTS`, `RING_R`, `RING_A`, `DATA_SWING_RAD`,
`EYE_BW`, `EYE_NOISE`, `ALL_PASS_RING_UM`, `ADD_DROP_RING_UM`, `BUS_DETUNE`, `TEST_SIZE`
and `L2_PENALTY` -- and the defaults and call sites now reference it. Each row names both
the argument and the constant, so the table still reads as a description of the function
signature. The values did not change; naming them is what brought them inside the check.

Where a row names more than one thing -- `PROP_LOSS_DB_CM`, `alpha_db_cm` and `loss_db_cm`,
all 2.0 dB/cm -- the row is checked through the module-level name, and the others are
default arguments carrying the same value.

The line citations of all thirty-two rows are checked by
`tests/test_source_lines_documented.py`, which requires each cited line to name the
parameter or carry the documented value.

The literature values quoted in the source column of that table — 2.14, 2.2 ± 0.8, 19 dies,
~2 dB/cm, 0.1–0.8 dB, ~4.4 dB, ~45 nm — are citations, not repository values.

The two code constants written inside the fenced Python block in §6.1 (`DC_LAMBDA_3DB` =
1574.7, `DC_SLOPE` = 0.0026) cannot be annotated at all: an HTML comment inside a fenced
code block renders as literal text on GitHub rather than disappearing. Both are checked
where §6.3 documents them.

## 4. Arithmetic on other values

Derived in the prose from numbers that are themselves checked. A value that is a difference
or a ratio of exactly two stored values is stored in its own right: `scripts/run_all.py`
computes it from the values its block already holds, and the report annotates it like any
other number. The second table below lists those. The first lists what carries no path,
because it is derived from more than two stored values, from something `results.json` does
not hold, or by a rule that is not arithmetic.

| Value | Section | Derivation | Why it cannot carry a path |
|---|---|---|---|
| 5.0 nm, 1569.7 nm | §3, §6 | a 0.1 nm grid scan of the null | a scan, not arithmetic; the report states it is not a `results.json` value |
| 2.9×, 13.7, 12.3, 7.5, 2.3 | §5, §6 | ratios and offsets of the Fig 4d bootstrap bounds; §6.1 says so explicitly | each combines four stored bounds, or a stored bound with the 1560 nm design wavelength, which is a code constant |
| 14.7 nm | §3 | the dispersion displacement used in the ruling-out argument | the difference of two code constants, `DC_LAMBDA_3DB` and `LAMBDA0`, neither of them a model output |
| 0.032 rad | §3 | linear interpolation between the 0.02 and 0.05 noise-sweep rows | an interpolation to a crossing, over four stored values and a threshold, not a difference of two |
| 0.42 dB | §6 | the percentile scan's RMS column rounded to a common value | a statement about a whole column; the per-row values are annotated |
| 0.008 | §3 | the largest of the three arm-length-sign changes | a maximum over three differences, not one of them |
| 142/150, 71/75, 140/150, 70/75, 42/45, 28/30 | §3 | the fractions the paper's percentages equal | the paper's values, as in §1 |
| ~1e-15 | §5 | an order-of-magnitude summary of the solver validation | a summary of two stored RMS values, written with a `~` and to no decimal place |

The two-value derivations, each stored by `scripts/run_all.py` and annotated where the
report writes it:

| Value | Section | Path it now carries |
|---|---|---|
| 7.18 dB | §3 | `switching.leak_mechanism_check.cross_ideal_coupler_improvement_db` |
| 0.05, 0.45, 1.19 dB | §3 | `switching.onchip_il_gap_nearest_db`, `onchip_il_gap_least_lossy_db`, `onchip_il_gap_most_lossy_db` |
| 3.6 nm | §5, §6 | `fig4d_mesh_fit.lambda0_minus_proxy_nm` |
| 0.4837 dB | §6 | `cross_check.fig4e_rms_improvement_at_fitted_spread_db` |
| 0.0104 dB | §6 | `cross_check.fig4d_rms_penalty_at_fitted_spread_db` |
| 67 | §3 | `ppuf.uniqueness_over_reliability` |
| 10 points | §3, §5 | `iris.unitary_minus_identity_full_acc`, with `\|pct` |
| 0.046 points | §3 | `ppuf_recirc.wiring_uniqueness_gap`, with `\|pct` |
| 4.1% | §4 | `coupler.demo_slope_offset_frac` |
| 0.002 | §4 | `coupler.demo_kappa0_abs_error` |

Two of them are written to a precision the prose had rounded past: the λ₀ gap is the
difference of the two fitted wavelengths rather than of the two rounded ones the report
displays, and the wiring gap is written rounded rather than truncated.

## 5. Values computed outside `results.json`

| Value | Section | Where it comes from |
|---|---|---|
| 1e-32 | §2 | a test assertion in `tests/test_reproduction.py`; the report says so in the row |
| −14.1 dB at 1549.0 nm | §3, §5 | read directly from `data/fig4d_T20_digitized.csv`; the report says so |
| 1574.5–1588.3, 1589.0, 1.5 nm grid | §6 | the legend-box occlusion read off the figure during digitization |
| 105, 15, 25, twelve | §6 | matching counts from `lightin/wiring_search.py`, not written to `results.json` |
| 1540, 1600, 0.1 nm | §6 | the diagnostic grid bounds of the null scan |
| 1550–1590, 0 to −25 dB | §6 | the Fig 4e axis limits, read off the panel |
| 32×32, 64×64 | §6 | the scaling projection the missing PDK sub-values would drive |

## 6. Superseded values, quoted as history

The pre-correction PUF metrics in §3: uniqueness **0.4901**, uniformity **0.5012**,
reliability **0.00719**, and the phase mean **+0.7604** rad. `results.json` holds only the
corrected values, which are annotated beside them. Keeping the old numbers unannotated is
what makes the sentence readable as a before-and-after.

## 7. Scale and sign — covered by modifiers

Nothing is listed here. A value the document writes on a different scale from the one
`results.json` stores it on, or whose sign the document carries in a word rather than a
character, is annotated with a modifier after a pipe and is checked like any other number:

* `|pct` multiplies the stored value by 100. It carries the differences the report writes
  in percentage *points* — the Iris full-set and held-out paired means and standard
  deviations, what the programmable unitary adds over the identity control, the
  recirculating-minus-feed-forward uniqueness difference, the gap between the two wirings'
  population uniqueness means, and the seed spread those two are judged against. A value that already carries a `%` sign must not also carry
  `|pct`; the test fails if both appear, so the scale can never be applied twice.
* `|abs` compares magnitudes. It carries the one value whose sign lives in a word: the
  0.0006 dB by which the bar model is *worse* than a constant, stored negative as
  `fig4e_fit.shape_check.rms_advantage_db`.

## 8. Structure, not measurement

Mesh and sweep dimensions that describe how a computation was set up: 4×4, 3×3, N = 4, 2×2,
8 ports, 40 cells, 25 vertices, 5×5, 20 orbits, 20 bits, 40 dies, 64 challenges, 20 dies,
32 challenges, 100 dies, 10 GBaud, 70/30, 15 parameters, 6/10/16 DOF where the DOF values
are annotated and the surrounding N-formulae are not, and the percentile labels 50th, 75th,
90th, 95th, 99th, 99.9th that name the rows of the §6.1 scan whose values are annotated.

---

Sections 1–8 above cover §2 to §6. §1 and §7 carry no `results.json` values: §1 is
definitional and §7 is the open-items list. The two runtimes quoted where the test suite
is described are measurements of this machine rather than pipeline outputs.

---

# `README.md`

The headline table's reproduction column is annotated and checked, and the chip geometry
the parameter list restates -- the two indices, the waveguide width, the coupler length and
gap, the mesh side, the arm length and the assumed split spread -- carries a square-bracket
comment and is checked against the module by `tests/test_constants_documented.py`, which
reads this file's two documents rather than the report alone. What is left:

| Value | Where | Why not checked |
|---|---|---|
| 94.67%, 93.33%, ~60 ps, −45 to <−20 dB, 50.15%, 1.875 pJ/MAC, 1.92 TOPS, σ=0.0269 → 6.22 bit | the "Paper" column | the paper's values, as in §1 above |
| 17.10 / 17.83 dB, 7.17–8.08 | the not-reproduced note | the paper's eye-diagram measurements |
| 3 V, 100 Ω, 96 ops, 2 dir, 10 GBaud | energy and throughput rows | Supplementary Note 3, which the rows say cannot be checked against the main article |
| 0.96 TMAC·s⁻¹ | energy row | `throughput_energy.mac_rate` holds 9.6e11 MAC·s⁻¹; the README writes the same quantity in TMAC·s⁻¹, and the markup carries no unit conversion |
| err ≤ 1e-32 | unitarity row | a test assertion, computed outside `results.json` |
| 1e-15 | solver row | an order-of-magnitude summary, written with a `~` in the prose |
| ~0.56 | architecture prose | the single-θ Haar fidelity, written as an approximation |
| 1560, 1549–1565, 1530–1549, 1550–1574 nm | crosstalk and loss rows | wavelength bounds of the stated comparisons |
| 8 paths, 8 modelled paths, 4×4, 40 PUCs, 10 seeds | throughout | structure, as in §8 above |
| 22 minutes, 50 seconds, 4 minutes | quick start | measured on this machine, not pipeline outputs |
| 60 checks | quick start | the size of the test suite |
| 6.22/5.47 bit, 60 ps, 1.92 TOPS, 1.875 pJ/MAC in the module-reference table and the tier list | module reference, Scope | restatements of the paper's values, identifying what a module covers |
| 0.0182 and the `0.0152-0.0707` range printed in the "How to run" block | how-to-run | inside a fenced code block, where an HTML comment would render as literal text |
