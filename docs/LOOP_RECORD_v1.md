# Open-items loop

One row per iteration. This file records what the loop did; it is not a changelog for any
other document, and nothing else in the repository refers to it.

The checked total is the number of annotated values `tests/test_report_consistency.py`
resolves across `docs/REPRODUCTION_REPORT_v10.md` and `README.md`. The test count is the
whole suite. The loop began at checked total 642 and 60 tests, commit `2446452`.

| # | Item | What changed | Checked | Tests | Commit |
|---|---|---|---|---|---|
| 1 | Priority 1-2 audit, then §6.3 source-line citations | Audited every derived value `REPORT_UNCHECKED.md` §4 calls uncheckable and every file:line citation in the report. The derived values all reproduce; twenty of the thirty-three citations pointed at the wrong line, including every citation into `recirculating.py` and `FIG4D_FLOOR_DB` pointing at `SIGMA_SPLIT`. Corrected all twenty and added `tests/test_source_lines_documented.py`, which requires each of the 53 cited lines to name its parameter or carry its value. | 642 | 62 | `84d356f` |
