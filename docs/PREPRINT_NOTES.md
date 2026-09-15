# Details taken from the preprint

Secondary source: Y. Zhu *et al.*, "Versatile silicon integrated photonic processor: a
reconfigurable solution for next-generation AI clusters", arXiv:2504.01463v2. This is an
earlier version of the published article that this repository reproduces (Zhu *et al.*,
*Light: Science & Applications* **15**, 165 (2026), doi:10.1038/s41377-026-02209-5). Some
of its numbers differ from the published ones. Where they differ, the published value is
the one this repository uses; the preprint value is recorded here only so the difference is
visible. Every line below cites the preprint section it comes from.

## Chip and mesh

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

## PUF design

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

## Where the preprint and the published article disagree

Published values are those already recorded in this repository, in `results.json` and in
report v5 §6. The published value is kept in every case.

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
stated at the top of this file.
