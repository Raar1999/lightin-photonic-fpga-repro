"""
The §6.3 parameter table must still match the modules it documents.

Run directly:  PYTHONPATH=. python3 tests/test_constants_documented.py
Or with pytest: PYTHONPATH=. pytest -q

`results.json` cannot police this table: it records what the model produced, not the
constants the model was given. A row that documents a module-level constant therefore names
it in a square-bracket comment beside the documented value,

    | `SIGMA_SPLIT` | 0.02<!--[lightin.switching.SIGMA_SPLIT]--> | ... |

and this test imports the module and compares. A tuple constant is indexed, as in
`ARM_LOSS_DB[0]`. Rows that document a default argument or an inline literal rather than a
module-level constant carry no comment and are listed in `docs/REPORT_UNCHECKED.md`.

The numeric comparison is the one `test_report_consistency` uses, imported rather than
copied so the two files cannot drift apart on what "equal to the precision written" means.
"""

import importlib
import re
from pathlib import Path

import pytest

from test_report_consistency import agrees

ROOT = Path(__file__).resolve().parents[1]
DOC = "docs/REPRODUCTION_REPORT_v10.md"

# value, then module.attribute (optionally indexed) in a square-bracket HTML comment
CONSTANT = re.compile(
    r"([-−+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)<!--\[([^\]]+(?:\[\d+\])?)\]-->"
)

MISSING = object()


def split_target(target):
    """`lightin.mod.NAME` or `lightin.mod.NAME[0]` -> (module, attribute, index or None)."""
    index = None
    match = re.search(r"\[(\d+)\]$", target)
    if match:
        index = int(match.group(1))
        target = target[:match.start()]
    module, _, attribute = target.rpartition(".")
    return module, attribute, index


def lookup(module, attribute, index):
    """The live value, or MISSING if the module or the attribute is gone."""
    try:
        mod = importlib.import_module(module)
    except ImportError:
        return MISSING
    if not hasattr(mod, attribute):
        return MISSING
    value = getattr(mod, attribute)
    if index is not None:
        if not isinstance(value, (list, tuple)) or index >= len(value):
            return MISSING
        value = value[index]
    return value


def documented():
    """Every annotated constant in the report, as (line, written, module, attr, index)."""
    text = (ROOT / DOC).read_text(encoding="utf-8")
    found = []
    for match in CONSTANT.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        module, attribute, index = split_target(match.group(2))
        found.append((line, match.group(1), module, attribute, index))
    return found


def test_documented_constants_match_the_modules():
    """Every documented constant equals the value its module actually holds."""
    rows = documented()
    assert rows, "no documented constants found -- has the markup been removed?"

    bad = []
    for line, written, module, attribute, index in rows:
        name = attribute if index is None else f"{attribute}[{index}]"
        live = lookup(module, attribute, index)
        if live is MISSING:
            bad.append((line, module, name, written, "no such attribute"))
        elif not agrees(written, "", live):
            bad.append((line, module, name, written, repr(live)))

    if bad:
        mod_width = max(len(row[1]) for row in bad)
        name_width = max(len(row[2]) for row in bad)
        table = "\n".join(
            f"  {DOC}:{line:<5} {module:<{mod_width}}  {name:<{name_width}}  "
            f"documented {written:<12} live {live}"
            for line, module, name, written, live in bad
        )
        pytest.fail(
            f"{len(bad)} of {len(rows)} documented constants disagree with the modules.\n"
            f"Correct the table in §6.3 -- never the constant.\n{table}"
        )


def test_every_documented_constant_exists():
    """A renamed or deleted constant fails here by attribute name."""
    gone = sorted(
        {(module, attribute if index is None else f"{attribute}[{index}]")
         for _, _, module, attribute, index in documented()
         if lookup(module, attribute, index) is MISSING}
    )
    if gone:
        rows = "\n".join(f"  {module}.{name}" for module, name in gone)
        pytest.fail(f"{len(gone)} documented constants no longer exist:\n{rows}")


if __name__ == "__main__":
    rows = documented()
    failures = []
    for line, written, module, attribute, index in rows:
        name = attribute if index is None else f"{attribute}[{index}]"
        live = lookup(module, attribute, index)
        if live is MISSING or not agrees(written, "", live):
            failures.append((line, module, name, written, live))
    for line, module, name, written, live in failures:
        print(f"{DOC}:{line} {module}.{name} documented {written} live {live}")
    print(f"{len(rows) - len(failures)} of {len(rows)} documented constants match the modules")
