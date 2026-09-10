Superseded: the paper and supplementary have been obtained; see docs/REPRODUCTION_REPORT_v2.md.
# Document search list — LightIN reproduction

Produced by auditing every assumed/approximate parameter in the package.
Each entry states: what to search for, where to look, what to extract,
which module and parameter it fixes, and the priority.

The ⚠ items in the parameter audit are the targets. Items already marked
✓ exact (n_g=4.0, waveguide length 4.5 mm) need no document.

There is also one genuine code bug flagged at the end (n_eff vs n_g).

---

## TIER 1 — The paper itself  (single highest-priority item)

### DOC-1 · Primary paper + supplementary / supporting information

**What to search:**
```
"LightIN" silicon photonic FPGA reconfigurable 2026 Light Science Applications
```
Or if you have the DOI already:
```
DOI: 10.1038/s41377-026-XXXXX   [fill from your copy]
```
Also search for "Supplementary Information" / "Supporting Data" linked from the
same page — Light: Science & Applications usually publishes these as a separate PDF.

**What to extract from the paper:**

| Figure / Section | What to read out | Fixes |
|---|---|---|
| Fig 4d | Through-port transmission (dB) vs wavelength (nm), all-cross state, all 4 output ports | `switching.py` slope + kappa0 via `fit_dc_dispersion()` |
| Fig 4e | Same for all-bar state | `switching.py` kappa_b scatter |
| Fig 3c | Monitoring signal vs heater voltage (or bias current); exact voltage at lock point | `mrm.py` r, bias range |
| Fig 3d–f | Eye SNR (dB) and Q factor values stated in caption or text | `mrm.py` SNR/Q annotation |
| Methods — MRM | Ring radius or perimeter (μm), through-coupling κ or r², round-trip loss, FSR, Q | `mrm.py` r, a |
| Methods — PUC/heater | Heater resistance (Ω), V_π (V), power for 2π phase (mW) | `throughput.py` heater_power_w |
| Methods — mesh | Number of active heaters per matrix operation; total static power stated | `throughput.py` n_active_heaters, 1.875 pJ/MAC check |
| Methods — waveguide | n_eff and/or n_g stated; propagation loss α (dB/cm) | `coupler.py` n_eff (fixes bug), loss_db_cm |
| Methods — grating coupler | Peak insertion loss (dB), centre wavelength (nm), 1-dB or 1.5-dB bandwidth | `coupler.py` grating params |
| Fig 5 caption / text | σ_phase used in 100-die simulation (stated as a fraction of π or in radians) | `ppuf.py` sigma_phase |
| Fig 5 / text | Exact 2-die experimental uniqueness/uniformity/reliability numbers | `ppuf.py` validation target |
| Fig 1 or Methods — topology | Wiring diagram of 40-PUC square recirculating mesh; segment lengths | `recirculating.py` topology |
| Abstract / Results | Op-count convention for 1.92 TOPS (is it real, complex, or bidirectional?) | `throughput.py` comment |
| Supplementary | Any tabulated raw data for Figs 3–5 | All of the above |

**Impact:** Fixes or confirms 14 of the 21 open parameters. The highest-leverage
single document in the list.

---

## TIER 2 — Chip-specific device references  (cited in the paper's Methods)

These are papers the LightIN authors cite for their specific DC, MRM, and grating
coupler designs. Check the paper's reference list for these.

### DOC-2 · Directional coupler design reference

The paper will cite either its own prior DC characterisation or a foundry DC.
Look for a reference in Methods near "directional coupler", "coupling length",
or "3-dB coupler".

**What to search (generic fallback):**
```
silicon photonics 220 nm SOI directional coupler coupling ratio wavelength dependence
measurement 1550 nm Journal of Lightwave Technology OR Optics Express OR Optics Letters
```

**What to extract:**
- Coupling length L_c (μm) and gap g (μm) for the 3-dB point
- Measured κ(λ): cross-coupling ratio at several wavelengths across 1520–1580 nm
- Any stated excess loss per coupler

**Fixes in code:**
```python
# coupler.py  line ~31
slope = MEASURED_VALUE   # rad/nm; replaces 0.004
kappa0 = MEASURED_VALUE  # replaces 0.5 if not exactly 50:50 at 1550 nm
excess_loss_db = MEASURED_VALUE  # replaces 0.1
```
Then run:
```python
from lightin.coupler import fit_dc_dispersion
k0, slope, rms = fit_dc_dispersion(lam_data, kappa_data)
```
to get the fitted parameters directly from the measured data.

**Impact:** Converts the CMT coupler from literature-typical to chip-specific.
Enables quantitative fit of Fig 4d/e once those curve points are digitised.

---

### DOC-3 · Micro-ring modulator (MRM) characterisation reference

Look in the LightIN Methods for the MRM reference: ring radius, modulation
bandwidth, V_π, bias voltage, measured extinction ratio.

**What to search (generic fallback):**
```
silicon micro-ring modulator 10 Gbaud NRZ extinction ratio Q factor 220 nm SOI
```

**What to extract:**
- Self-coupling coefficient r (or r², the through-port power fraction)
- Round-trip power transmission a² (= 1 − round-trip loss)
- FSR (nm) at 1550 nm → gives ring perimeter: L = λ²/(n_g · FSR)
- Through coupling κ = 1 − r²
- Half-wave voltage V_π (V) and operating bias

**Fixes in code:**
```python
# mrm.py  line ~60
r = np.sqrt(PAPER_VALUE)       # replaces 0.92
a = PAPER_VALUE                # replaces 0.90
# data_swing: convert V_swing/V_pi * pi to phase, then to detuning
```

**Impact:** Converts the MRM model from a qualitative shape to a quantitative
reproduction of Fig 3c (monitoring curve peak position and width).

---

### DOC-4 · Grating coupler characterisation reference

Look in the LightIN Methods for the GC reference. May be the same paper as
DOC-2 if the authors use a standard foundry GC.

**What to search (generic fallback):**
```
silicon grating coupler 1550 nm insertion loss bandwidth 220 nm SOI TE mode
```

**What to extract:**
- Peak insertion loss (dB) — we use 4.4 dB; verify
- Centre wavelength (nm) — we use 1545 nm; verify
- 1-dB bandwidth (nm) — we use ~38 nm; verify
- 3-dB or 1.5-dB bandwidth — we use 45 nm; verify

**Fixes in code:**
```python
# coupler.py  line ~73
def grating_coupler_db(lam, peak_loss_db=PAPER_VALUE,
                       lam_peak=PAPER_VALUE, bw_1p5db=PAPER_VALUE):
```

**Impact:** Corrects the fibre-to-fibre loss budget in `link_budget_db()`.
Currently ~10 dB total; actual value depends on GC loss and bandwidth.

---

## TIER 3 — Process / foundry reference  (fixes the n_eff bug + loss)

### DOC-5 · SOI foundry process design kit (PDK) note or characterisation paper

This is the most important fix for a genuine code bug: we use `n_eff = 4.0`
everywhere for phase propagation, but 4.0 is the *group* index n_g; the actual
*effective* (phase) index for a 220 × 500 nm SOI strip at 1550 nm TE is ~2.4.
This makes ring resonance positions and MZI fringe periods off by ~40%.

The paper's Methods will state the foundry (e.g. IME A*STAR, AMF Singapore,
IMEC iSiPP50G, CORNERSTONE Southampton, VTT Finland, or Tower Semiconductor).

**What to search:**
```
[FOUNDRY NAME] 220 nm SOI photonics process design kit waveguide effective index
group index propagation loss 1550 nm
```
Or generically:
```
220 nm silicon-on-insulator strip waveguide 500 nm effective index group index
1550 nm TE mode
```

**What to extract:**
- n_eff (phase index, TE mode, 220 × 500 nm strip, 1550 nm) — expect ~2.4–2.45
- n_g (group index, same geometry) — expect ~4.0–4.3; cross-check with paper's 60 ps
- α (propagation loss, dB/cm) — we use 2.0; typical range 1.5–3.0

**Fixes in code:**
```python
# recirculating.py  line ~46  AND  coupler.py
# The Circuit class uses n_eff for phase: 2π n_eff L / λ
# Replace n_eff=4.0 with n_eff≈2.4 (phase index)
# Keep n_g=4.0 only for latency = n_g L / c  (metrics.py is already correct)
Circuit(n_eff=2.40, ...)   # phase propagation
propagation_latency(L, group_index=4.0)   # latency stays 4.0
```

**Impact:** Fixes ring resonance positions and MZI fringe periods in
`recirculating.py` and `switching.py`. Does not affect crosstalk magnitude or
the matrix-multiply results (which are wavelength-independent).

---

## TIER 4 — Supporting literature  (validates our approximate baseline values)

These are the five papers I cited when setting the baseline parameters. Getting
them confirms or corrects the numbers we already use. Lower priority than
Tiers 1–3 because the values are already approximately right.

### DOC-6 · DC dispersion measurement (slope parameter)

**Search:**
```
arXiv 2302.13177
```
Or: `"directional coupler" "power coupling ratio" wavelength dependence silicon
photonics measurement 2023`

**Extract:** Table or figure of κ vs λ (nm) for a strip DC of similar geometry.
**Fixes:** `coupler.py` slope = 0.004 rad/nm (confirm or correct).

---

### DOC-7 · DC excess loss measurement

**Search:**
```
"directional coupler" "excess loss" silicon photonics Journal of Lightwave
Technology 2017 volume 35 issue 22
```
DOI region: JLT vol.35 no.22 (Nov. 2017)

**Extract:** Excess loss per DC (dB) for a 220 nm SOI strip DC.
**Fixes:** `coupler.py` excess_loss_db = 0.1 (confirm or correct).

---

### DOC-8 · Propagation loss measurement

**Search:**
```
arXiv 2111.01792
```
Or: `silicon strip waveguide propagation loss 2.14 dB/cm 220 nm`

**Extract:** α in dB/cm for 220 × 500 nm strip TE mode at 1550 nm.
**Fixes:** `coupler.py` loss_db_cm = 2.0 (paper value was 2.14).

---

### DOC-9 · Grating coupler insertion loss and bandwidth

**Search:**
```
arXiv 1203.0767
```
Or: `grating coupler silicon 1550 nm insertion loss 4.4 dB bandwidth`

**Extract:** Peak IL (dB), peak λ (nm), 1.5-dB or 3-dB BW (nm).
**Fixes:** `coupler.py` grating_coupler_db() default parameters.

---

### DOC-10 · Grating coupler 1-dB bandwidth

**Search:**
```
PMC10576773
```
Or: `grating coupler 1 dB bandwidth 38 nm silicon photonics 2023`

**Extract:** 1-dB BW (nm) to complement the 1.5-dB BW from DOC-9.
**Fixes:** Cross-check for `coupler.py` bw_1p5db = 45 nm.

---

## Summary table

| Doc | Search term / ID | Fixes (module · parameter) | Priority |
|---|---|---|---|
| DOC-1 | LightIN paper + supplementary | 14 parameters across all modules | **CRITICAL** |
| DOC-2 | DC design ref (from paper's Methods) | coupler.py slope, kappa0, excess_loss | High |
| DOC-3 | MRM characterisation ref | mrm.py r, a, FSR, V_π | High |
| DOC-4 | GC characterisation ref | coupler.py grating params | Medium |
| DOC-5 | SOI foundry PDK / process note | recirculating.py n_eff bug fix | Medium |
| DOC-6 | arXiv:2302.13177 | coupler.py slope confirm | Low |
| DOC-7 | JLT-35-22 | coupler.py excess_loss confirm | Low |
| DOC-8 | arXiv:2111.01792 | coupler.py loss_db_cm confirm | Low |
| DOC-9 | arXiv:1203.0767 | coupler.py grating params confirm | Low |
| DOC-10 | PMC10576773 | coupler.py bw_1p5db confirm | Low |

---

## What happens in the code once you have each document

### After DOC-1 (paper):

```python
# 1. Digitise Fig 4d/e: (wavelength_nm, transmission_dB) for each port
#    Use WebPlotDigitizer (free, browser-based) or ImageJ
lam_data = np.array([1530, 1535, ...])          # nm, from figure x-axis
T_cross_dB = np.array([-45.1, -43.2, ...])     # dB, intended path
T_xtalk_dB = np.array([-30.1, -28.4, ...])     # dB, crosstalk port

# 2. Convert to power coupling
kappa_data = 1 - 10**(T_xtalk_dB / 10)         # approx from xtalk spectrum

# 3. Fit
from lightin.coupler import fit_dc_dispersion
k0, slope, rms = fit_dc_dispersion(lam_data, kappa_data)
print(f"Fitted: kappa0={k0:.3f}, slope={slope:.4f} rad/nm, RMS={rms:.4f}")

# 4. Plug back in to switching.py and re-run
```

```python
# MRM: from paper's MRM section
from lightin import mrm
mrm.LAMBDA0 = PAPER_PEAK_WAVELENGTH_NM
# Edit mrm.py: r = sqrt(PAPER_THROUGH_COUPLING), a = PAPER_ROUNDTRIP_AMP
```

```python
# PUF: from paper's sigma_phase in simulation description
from lightin import ppuf
result = ppuf.evaluate(sigma_phase=PAPER_SIGMA, n_dies=100)
# Should now match 49.97% / 50.15% exactly
```

### After DOC-5 (foundry PDK):

```python
# Fix n_eff bug in recirculating.py and coupler.py
# n_eff_phase ≈ 2.40 for 220×500 nm SOI TE at 1550 nm
# n_g        ≈ 4.00 (already correct in metrics.py latency calc)

from lightin.recirculating import Circuit, validate_ring
c = Circuit(n_eff=2.40, loss_db_cm=PAPER_ALPHA)
# Ring resonances will now be at correct wavelengths
```

---

## Notes on digitising Fig 4d/e

If you can get a clean PNG/PDF of Fig 4d/e:

1. **WebPlotDigitizer** (automeris.io/WebPlotDigitizer) — free, no install,
   runs in browser. Set axes, click points on each curve, export CSV.
2. Target: ~20–30 points per curve across the wavelength range shown.
3. Read out both the intended (high-transmission) path and at least one
   crosstalk port for each switch state (cross and bar).
4. `fit_dc_dispersion()` in `coupler.py` is already written and tested;
   it accepts numpy arrays directly.

The fit will take under 1 second once you have the data.

