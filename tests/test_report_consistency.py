"""
Report-to-results consistency: every number the report quotes from `results.json` must
still equal what `results.json` holds.

Run directly:  PYTHONPATH=. python3 tests/test_report_consistency.py
Or with pytest: PYTHONPATH=. pytest -q

A checked number is written in the document as the value followed by an HTML comment
naming its `results.json` path, for example

    cross **-16.77<!--{switching.cross_worst_xtalk_fitrange_db}--> dB**

GitHub's renderer strips the comment, so the markup is invisible to a reader and visible to
this test. Numbers the report does not annotate are listed, with their provenance, in
`docs/REPORT_UNCHECKED.md`.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results.json"
DOCS = ["docs/REPRODUCTION_REPORT_v10.md"]

# value, optional percent sign, then the path in an HTML comment. A leading minus may be
# written as a hyphen or as U+2212; a leading plus is allowed for signed differences. The
# en dash U+2013 is deliberately excluded: this document uses it as a range separator.
ANNOTATION = re.compile(
    r"([-−+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)(%?)<!--\{([^}]+)\}-->"
)

MISSING = object()


def _load_results():
    with RESULTS.open(encoding="utf-8") as fh:
        return json.load(fh)


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


def _as_float(written):
    """The written token as a float, with U+2212 normalised and a leading plus dropped."""
    return float(written.replace("−", "-").lstrip("+"))


def _significant_figures(written):
    mantissa = re.split(r"[eE]", written)[0].lstrip("+-")
    digits = mantissa.replace(".", "").lstrip("0")
    return len(digits) or 1


def _round_to_significant(value, figures):
    if value == 0:
        return 0.0
    from math import floor, log10
    return round(value, -(int(floor(log10(abs(value)))) - (figures - 1)))


def agrees(written, percent, stored):
    """Does the written value equal the stored one at the precision it was written to?

    Decimal notation is compared at the number of decimal places written, so `-16.77`
    accepts -16.76775. Scientific notation is compared at the number of significant
    figures written, so `7.8e-16` accepts 7.7715e-16 and does not accept anything merely
    smaller than 0.05. A trailing `%` means the document writes a percentage where
    `results.json` stores a fraction, and the stored value is scaled by 100 before the
    comparison; a percentage-point difference written without a `%` cannot be checked and
    is recorded in `docs/REPORT_UNCHECKED.md` instead.
    """
    if not isinstance(stored, (int, float)) or isinstance(stored, bool):
        return False
    token = written.replace("−", "-").lstrip("+")
    value = float(token)
    actual = stored * 100.0 if percent else float(stored)
    if "e" in token or "E" in token:
        figures = _significant_figures(token)
        return _round_to_significant(actual, figures) == _round_to_significant(value, figures)
    places = len(token.split(".")[1]) if "." in token else 0
    return round(actual, places) == round(value, places)


def annotations(doc):
    """Every annotated number in one document, as (line number, written, percent, path)."""
    text = (ROOT / doc).read_text(encoding="utf-8")
    found = []
    for match in ANNOTATION.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        found.append((line, match.group(1), match.group(2), match.group(3)))
    return found


def _all_annotations():
    return [(doc,) + item for doc in DOCS for item in annotations(doc)]


def test_report_numbers_match_results_json():
    """Every annotated number equals the `results.json` value its path names."""
    results = _load_results()
    checked = _all_annotations()
    assert checked, "no annotated numbers found -- has the markup been removed?"

    bad = []
    for doc, line, written, percent, path in checked:
        stored = resolve(results, path)
        if stored is MISSING:
            bad.append((doc, line, path, written + percent, "no such path"))
        elif not agrees(written, percent, stored):
            bad.append((doc, line, path, written + percent, repr(stored)))

    if bad:
        width = max(len(row[2]) for row in bad)
        rows = "\n".join(
            f"  {doc}:{line:<5} {path:<{width}}  written {written:<12} stored {stored}"
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
        {(doc, path) for doc, _, _, _, path in _all_annotations()
         if resolve(results, path) is MISSING}
    )
    if unresolved:
        rows = "\n".join(f"  {doc}: {path}" for doc, path in unresolved)
        pytest.fail(f"{len(unresolved)} annotated paths do not resolve:\n{rows}")


def test_unchecked_inventory_exists():
    """The numbers outside the check are accounted for rather than simply absent."""
    inventory = ROOT / "docs" / "REPORT_UNCHECKED.md"
    assert inventory.exists(), "docs/REPORT_UNCHECKED.md is missing"
    assert inventory.read_text(encoding="utf-8").strip(), "docs/REPORT_UNCHECKED.md is empty"


if __name__ == "__main__":
    results = _load_results()
    checked = _all_annotations()
    failures = [
        (doc, line, path, written + percent, resolve(results, path))
        for doc, line, written, percent, path in checked
        if resolve(results, path) is MISSING
        or not agrees(written, percent, resolve(results, path))
    ]
    for doc, line, path, written, stored in failures:
        print(f"{doc}:{line} {path} written {written} stored {stored}")
    print(f"{len(checked) - len(failures)} of {len(checked)} annotated numbers agree")
