# Scope note: digitizing Fig. 4e to constrain the bar state

This was the plan for the work, written before any of it was done. The work has since been
carried out: `data/fig4e_bar_digitized.csv` holds the digitized curve and `SIGMA_SPLIT` in
`lightin/switching.py` is fitted to it. What was actually found, including the two places
this plan guessed wrong, is in `docs/REPRODUCTION_REPORT_v8.md` §6.1. The plan is kept as
written, because its check 3 is the pre-registered criterion that rejected the first fit.

## Which panel carries the bar-state spectra

Figure 4 of the published article shows the 4×4 switch. Panel **4d** is the all-cross
configuration and panel **4e** is the all-bar configuration; report v5 §2 rows 17–19 cite
"Fig. 4d,e" for the crosstalk claims, and the superseded document search list already
identifies 4e as "same for all-bar state". Only 4d has been digitized
(`data/fig4d_T20_digitized.csv`, 25 points over 1549–1587 nm). Fig. 4e is therefore the
panel that carries the bar-state measurement, and it is untouched.

## Which curve to digitize

Each panel overlays four output-port curves against wavelength. For 4d only the T20 curve
was extracted, because "a precise per-point digitization of the other three overlapping
curves in each panel is noise-limited" (report §6.1). The same selection rule applies to
4e: take the single curve with the largest vertical separation from its neighbours over the
widest wavelength span, which is the one whose colour can be followed unambiguously where
the traces cross.

The curve that plays that role in 4e has not been identified, because the panel has not
been examined at the resolution needed to judge it. The analogous choice would be the
bar-state counterpart of T20 — the transmission from input 2 to output 0 with every cell in
the bar state — but that is an expectation from how 4d behaved, not an observation about
4e, and the first step of the work is to look at the panel and check it.

## What a fit to it would constrain

The bar-state crosstalk in this model is set by two parameters, both assumed, both with no
recorded source (report v5 §6.3):

| Parameter | Current assumed value | Where it lives |
|---|---|---|
| coupler-to-coupler power-split spread, σ | **0.02**, clipped to [0.3, 0.7] | `lightin/switching.py`, the two `rng.normal(0.5, 0.02, ...)` draws |
| arm phase error, σ | **0.02 rad** | `lightin/switching.py`, the `rng.normal(0, 0.02, ...)` draw |

Report v5 §3 shows these two are what set the bar state: with both at zero the bar state
nulls exactly, below the 1e-20 structural-zero threshold; with either one alone the cell
leaks about −32.8 dB; with both, −29.81 dB. Coupler dispersion is not involved — moving the
fitted 3-dB wavelength by 14.7 nm changes the bar-state values by hundredths of a dB.

A fit of the mesh model to a digitized 4e curve would replace both assumed spreads with
fitted values, in the same way the fit to 4d replaced the coupler's 3-dB wavelength and
dispersion slope with `DC_LAMBDA_3DB` = 1574.7 nm and `DC_SLOPE` = 0.0026 rad/nm. It would
turn row 17's bar-state entry from a statement about two assumed numbers into a statement
about the chip, and it would remove two of the 23 no-source parameters from §6.3.

Whether the two spreads are separately identifiable from one curve is itself an open
question. Both enter the bar-state leakage amplitude additively in quadrature at a single
cell, so a single curve may determine only their combination; the fit should report the
parameter correlation and, if the two are not separable, say so and fit the combination.

## What the fit would be checked against

Four checks, in the order they would be applied:

1. **Held-out wavelengths.** Fit on part of the digitized range and predict the rest, as a
   guard against a fit that only interpolates its own points.
2. **The bootstrap procedure already used for 4d.** A pairs bootstrap for the scatter of the
   points about the model and a parametric bootstrap at the digitization uncertainty
   (±2 dB, one standard deviation) for the reading error, with the parametric interval
   treated as the honest one — the same reasoning as §6.1.
3. **The cross state, unchanged.** The 4d fit fixes the coupler; a 4e fit must not move it.
   Refitting the bar-state spreads while holding `DC_LAMBDA_3DB` and `DC_SLOPE` at their 4d
   values, and confirming the cross-state predictions of rows 17–19 are unchanged, is what
   makes the two fits independent rather than one fit with more knobs.
4. **The paper's stated range.** The published article gives −45 to <−20 dB at 1560 nm
   across both panels. A fitted bar state that falls outside that range would indicate the
   digitization or the model, not the chip, and would have to be resolved before the
   fitted values were adopted.

A fit that failed check 3 or 4 would be reported as a failed fit and the assumed values
kept, rather than adopted with the disagreement absorbed.

## Cost and prerequisites

The work needs a copy of the published figure at usable resolution. The digitization itself
is the same manual colour-tracing used for 4d, producing a CSV with the same provenance
header and stated uncertainty; the fit reuses `scripts/fit_fig4.py`, which already carries
both bootstraps and the mesh model. The new part is a bar-state objective and the
identifiability analysis above.
