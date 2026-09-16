"""
Report-to-results consistency: every number the report quotes from `results.json` must
still equal what `results.json` holds.

Run directly:  PYTHONPATH=. python3 tests/test_report_consistency.py
Or with pytest: PYTHONPATH=. pytest -q

A checked number is written in the document as the value followed by an HTML comment
naming its `results.json` path, for example

    cross **-16.77<!--{switching.cross_worst_xtalk_fitrange_db}--> dB**

GitHub's renderer strips the comment, so the markup is invisible to a reader and visible to
this test. A path may carry one modifier after a pipe, which says how the written value was
derived from the stored one:

    `|pct`   the document writes a percentage or a percentage-point difference where
             `results.json` stores a fraction; the stored value is multiplied by 100
    `|abs`   the document writes a magnitude and carries the sign in words; the stored
             value is compared by absolute value

Numbers the report does not annotate are listed, with their provenance, in
`docs/REPORT_UNCHECKED.md`.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results.json"
DOCS = ["docs/REPRODUCTION_REPORT_v10.md", "README.md"]

# value, optional percent sign, then the target in an HTML comment. A leading minus may be
# written as a hyphen or as U+2212; a leading plus is allowed for signed differences. The
# en dash U+2013 is deliberately excluded: this document uses it as a range separator.
ANNOTATION = re.compile(
    r"([-−+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)(%?)<!--\{([^}]+)\}-->"
)

MODIFIERS = ("pct", "abs")

MISSING = object()


def _load_results():
    with RESULTS.open(encoding="utf-8") as fh:
        return json.load(fh)


def split_target(target):
    """`path` or `path|modifier` -> (path, modifier). The modifier may be unknown here."""
    path, pipe, modifier = target.partition("|")
    return path.strip(), (modifier.strip() if pipe else "")


def resolve(data, path):
    """Walk a dotted path, returning MISSING if any step does not exist.

    Three keys in `results.json` contain a dot of their own -- `enob_at_sigma_0.0269`,
    `enob_at_sigma_0.0453` and the percentile-scan row `p99.9` -- so the walk cannot just
    split on ".". At each level it takes the longest key that matches a prefix of what is
    left, ending at a "." or a "[". List indices are written `[0]`.
    """
    node, rest = data, path
    while rest:
        if rest.startswith("["):
            close = rest.find("]")
            if close < 0:
                return MISSING
            try:
                index = int(rest[1:close])
            except ValueError:
                return MISSING
            if not isinstance(node, list) or not -len(node) <= index < len(node):
                return MISSING
            node, rest = node[index], rest[close + 1:]
            continue
        if rest.startswith("."):
            rest = rest[1:]
            continue
        if not isinstance(node, dict):
            return MISSING
        best = None
        for key in node:
            if rest == key or (rest.startswith(key) and rest[len(key):len(key) + 1] in ".["):
                if best is None or len(key) > len(best):
                    best = key
        if best is None:
            return MISSING
        node, rest = node[best], rest[len(best):]
    return node


def _significant_figures(written):
    mantissa = re.split(r"[eE]", written)[0].lstrip("+-")
    digits = mantissa.replace(".", "").lstrip("0")
    return len(digits) or 1


def _round_to_significant(value, figures):
    if value == 0:
        return 0.0
    from math import floor, log10
    return round(value, -(int(floor(log10(abs(value)))) - (figures - 1)))


def agrees(written, percent, stored, modifier=""):
    """Does the written value equal the stored one at the precision it was written to?

    Decimal notation is compared at the number of decimal places written, so `-16.77`
    accepts -16.76775. Scientific notation is compared at the number of significant
    figures written, so `7.8e-16` accepts 7.7715e-16 and does not accept anything merely
    smaller than 0.05.

    A trailing `%` on the written value, or a `pct` modifier on the path, means the
    document writes a percentage where `results.json` stores a fraction, and the stored
    value is scaled by 100 first. The two are alternatives, never both: `%` is for a value
    the document calls a percentage, `pct` for one it calls a difference in points. An
    `abs` modifier compares magnitudes, for a value whose sign the document carries in
    words.
    """
    if not isinstance(stored, (int, float)) or isinstance(stored, bool):
        return False
    token = written.replace("−", "-").lstrip("+")
    value = float(token)
    actual = float(stored)
    if modifier == "abs":
        actual = abs(actual)
    if percent or modifier == "pct":
        actual *= 100.0
    if "e" in token or "E" in token:
        figures = _significant_figures(token)
        return _round_to_significant(actual, figures) == _round_to_significant(value, figures)
    places = len(token.split(".")[1]) if "." in token else 0
    return round(actual, places) == round(value, places)


def annotations(doc):
    """Every annotated number in one document.

    Yields (line number, written value, percent sign, path, modifier).
    """
    text = (ROOT / doc).read_text(encoding="utf-8")
    found = []
    for match in ANNOTATION.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        path, modifier = split_target(match.group(3))
        found.append((line, match.group(1), match.group(2), path, modifier))
    return found


def _all_annotations():
    return [(doc,) + item for doc in DOCS for item in annotations(doc)]


def test_report_numbers_match_results_json():
    """Every annotated number equals the `results.json` value its path names."""
    results = _load_results()
    checked = _all_annotations()
    assert checked, "no annotated numbers found -- has the markup been removed?"

    bad = []
    for doc, line, written, percent, path, modifier in checked:
        shown = written + percent + (f"|{modifier}" if modifier else "")
        if modifier and modifier not in MODIFIERS:
            bad.append((doc, line, path, shown,
                        f"unknown modifier {modifier!r}, expected one of {MODIFIERS}"))
            continue
        if percent and modifier == "pct":
            bad.append((doc, line, path, shown,
                        "written with a % sign and a pct modifier: the x100 scale would "
                        "be applied twice"))
            continue
        stored = resolve(results, path)
        if stored is MISSING:
            bad.append((doc, line, path, shown, "no such path"))
        elif not agrees(written, percent, stored, modifier):
            bad.append((doc, line, path, shown, repr(stored)))

    if bad:
        width = max(len(row[2]) for row in bad)
        rows = "\n".join(
            f"  {doc}:{line:<5} {path:<{width}}  written {written:<14} stored {stored}"
            for doc, line, path, written, stored in bad
        )
        pytest.fail(
            f"{len(bad)} of {len(checked)} annotated numbers disagree with results.json.\n"
            f"Regenerate the report from the current results, or correct the document -- "
            f"never the other way round.\n{rows}"
        )


def test_every_annotated_path_resolves():
    """A renamed or removed `results.json` key fails here by name."""
    results = _load_results()
    unresolved = sorted(
        {(doc, path) for doc, _, _, _, path, _ in _all_annotations()
         if resolve(results, path) is MISSING}
    )
    if unresolved:
        rows = "\n".join(f"  {doc}: {path}" for doc, path in unresolved)
        pytest.fail(f"{len(unresolved)} annotated paths do not resolve:\n{rows}")


def test_every_modifier_is_known():
    """A misspelled modifier fails by name rather than being ignored."""
    unknown = sorted(
        {(doc, path, modifier) for doc, _, _, _, path, modifier in _all_annotations()
         if modifier and modifier not in MODIFIERS}
    )
    if unknown:
        rows = "\n".join(f"  {doc}: {path}|{modifier}" for doc, path, modifier in unknown)
        pytest.fail(
            f"{len(unknown)} annotations carry an unknown modifier "
            f"(known: {', '.join(MODIFIERS)}):\n{rows}"
        )


def test_unchecked_inventory_exists():
    """The numbers outside the check are accounted for rather than simply absent."""
    inventory = ROOT / "docs" / "REPORT_UNCHECKED.md"
    assert inventory.exists(), "docs/REPORT_UNCHECKED.md is missing"
    assert inventory.read_text(encoding="utf-8").strip(), "docs/REPORT_UNCHECKED.md is empty"


if __name__ == "__main__":
    results = _load_results()
    checked = _all_annotations()
    failures = []
    for doc, line, written, percent, path, modifier in checked:
        if modifier and modifier not in MODIFIERS:
            failures.append((doc, line, path, written, f"unknown modifier {modifier!r}"))
        elif percent and modifier == "pct":
            failures.append((doc, line, path, written, "double x100 scale"))
        else:
            stored = resolve(results, path)
            if stored is MISSING or not agrees(written, percent, stored, modifier):
                failures.append((doc, line, path, written, stored))
    for doc, line, path, written, stored in failures:
        print(f"{doc}:{line} {path} written {written} stored {stored}")
    by_mod = {}
    for _, _, _, _, _, modifier in checked:
        by_mod[modifier or "(none)"] = by_mod.get(modifier or "(none)", 0) + 1
    print(f"{len(checked) - len(failures)} of {len(checked)} annotated numbers agree")
    print("  by modifier: " + ", ".join(f"{k} {v}" for k, v in sorted(by_mod.items())))
