# Open-items loop

One row per iteration. This file records what the loop did; it is not a changelog for any
other document, and nothing else in the repository refers to it.

The checked total is the number of annotated values `tests/test_report_consistency.py`
resolves across `docs/REPRODUCTION_REPORT_v10.md` and `README.md`. The test count is the
whole suite. The loop began at checked total 642 and 60 tests, commit `2446452`.

| # | Item | What changed | Checked | Tests | Commit |
|---|---|---|---|---|---|
| 1 | Priority 1-2 audit, then §6.3 source-line citations | Audited every derived value `REPORT_UNCHECKED.md` §4 calls uncheckable and every file:line citation in the report. The derived values all reproduce; twenty of the thirty-three citations pointed at the wrong line, including every citation into `recirculating.py` and `FIG4D_FLOOR_DB` pointing at `SIGMA_SPLIT`. Corrected all twenty and added `tests/test_source_lines_documented.py`, which requires each of the 53 cited lines to name its parameter or carry its value. | 642 | 62 | `84d356f` |
| 2 | Priority 1-2 audit of §5, then transcribed constants | Reproduced the wiring-search counts (105, 15, 25, twelve) and the digitized −14.12 dB at 1549.0 nm; all hold. Bound fourteen occurrences of thirteen module-level constants the documents write but nothing checked: the eight §6 geometry values taken from the paper's Methods, the two design wavelengths, the preprint's grating pitch and waveguide length, and `switching.ZERO_TOL`. Documented constants 15 to 29. | 642 | 62 | `708950b` |
| 3 | §7.3 promoting the inline literals of §6.3 to named constants | Gave a module-level name to the nineteen §6.3 rows that were default arguments or inline literals, across `coupler`, `switching`, `ppuf`, `mrm`, `recirculating` and `nn_iris`, and pointed every default and call site at it. Rewrote those rows to name both the argument and the constant, bound each to the constants test, and re-cited every line the promotion moved. `run_all.py` reproduced `results.json` byte for byte: no key added or removed, no value moved. Documented constants 29 to 48; cited lines 53 to 71. Item resolved and removed from §7.3. | 642 | 62 | `ca63c83` |
| 4 | §7.3 extending the consistency test to what it still misses | `tests/test_constants_documented.py` read only the report, so the chip geometry the README restates in its own words -- the two indices, the waveguide width, the coupler length and gap, the mesh side, the arm length and the assumed split spread -- was checked nowhere. Extended the test to read both documents and bound those eight values. Documented constants 48 to 56. | 642 | 62 | `f80e32c` |
