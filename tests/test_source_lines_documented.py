"""
The file:line citations in the §6.3 parameter table must still point at their parameter.

Run directly:  PYTHONPATH=. python3 tests/test_source_lines_documented.py
Or with pytest: PYTHONPATH=. pytest -q

`tests/test_constants_documented.py` checks the thirteen rows whose value is a module-level
constant, by importing it. The other nineteen rows document a default argument or an inline
literal, which has no name to import, and all thirty-two rows carry a "Used in" cell naming
the file and line where the parameter lives. Nothing checked those line numbers, so they
drifted: every citation into `recirculating.py` pointed into the solver, and `FIG4D_FLOOR_DB`
pointed at `SIGMA_SPLIT`.

A cited line passes if it names the row's parameter or carries the row's documented value.
The parameter names are the backticked identifiers in the Parameter column. A name shorter
than three characters -- `N`, `r`, `a` -- would match almost any line, so those rows are
checked by their value instead.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC = "docs/REPRODUCTION_REPORT_v10.md"
PACKAGES = ("lightin", "scripts")

# `name.py:12` or `name.py:12,34,56`
CITATION = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*\.py):(\d+(?:,\d+)*)`")
IDENTIFIER = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`")
NUMBER = re.compile(r"[-−+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
MIN_NAME_LEN = 3


def _strip_comments(cell):
    return re.sub(r"<!--.*?-->", "", cell)


def parameter_rows():
    """Every §6.3 table row that cites a file and line.

    Yields (doc line, parameter names, written value, [(file, line), ...]).
    """
    text = (ROOT / DOC).read_text(encoding="utf-8")
    rows = []
    for number, line in enumerate(text.split("\n"), start=1):
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 5:
            continue
        used_in = cells[3]
        citations = [(m.group(1), int(n))
                     for m in CITATION.finditer(used_in)
                     for n in m.group(2).split(",")]
        if not citations:
            continue
        names = IDENTIFIER.findall(_strip_comments(cells[1]))
        value = NUMBER.search(_strip_comments(cells[2]))
        rows.append((number, names, value.group(0) if value else None, citations))
    return rows


def source_lines(filename):
    """The lines of a documented module, or None if no package holds it."""
    for package in PACKAGES:
        path = ROOT / package / filename
        if path.exists():
            return path.read_text(encoding="utf-8").split("\n")
    return None


def mentions(source_line, names, value):
    """Does this line name the parameter, or carry its value?

    A name is matched on word boundaries so that `detune` does not match inside an
    unrelated word. A short name is not matched at all -- `a` would pass on any line of
    English -- so those rows fall through to the value.
    """
    for name in names:
        if len(name) >= MIN_NAME_LEN and re.search(rf"\b{re.escape(name)}\b", source_line):
            return True
    if value is not None:
        token = value.replace("−", "-").lstrip("+")
        for written in {token, token.lstrip("-")}:
            if re.search(rf"(?<![\d.]){re.escape(written)}(?![\d.])", source_line):
                return True
    return False


def test_documented_source_lines_point_at_their_parameter():
    """Every line cited in §6.3 names its parameter or carries its value."""
    rows = parameter_rows()
    assert rows, "no file:line citations found -- has the §6.3 table moved?"

    bad = []
    for doc_line, names, value, citations in rows:
        subject = names[0] if names else (value or "?")
        for filename, number in citations:
            source = source_lines(filename)
            if source is None:
                bad.append((doc_line, subject, f"{filename}:{number}", "no such module"))
            elif not 0 < number <= len(source):
                bad.append((doc_line, subject, f"{filename}:{number}", "past end of file"))
            elif not mentions(source[number - 1], names, value):
                bad.append((doc_line, subject, f"{filename}:{number}",
                            source[number - 1].strip()[:60] or "<blank line>"))

    if bad:
        subject_width = max(len(row[1]) for row in bad)
        cite_width = max(len(row[2]) for row in bad)
        table = "\n".join(
            f"  {DOC}:{doc_line:<5} {subject:<{subject_width}}  cites {cite:<{cite_width}}"
            f"  which reads: {found}"
            for doc_line, subject, cite, found in bad
        )
        pytest.fail(
            f"{len(bad)} of {sum(len(r[3]) for r in rows)} cited source lines no longer "
            f"hold their parameter.\nCorrect the \"Used in\" cell in §6.3 -- never the "
            f"module.\n{table}"
        )


def test_every_cited_module_exists():
    """A renamed or deleted module fails here by filename."""
    missing = sorted({filename
                      for _, _, _, citations in parameter_rows()
                      for filename, _ in citations
                      if source_lines(filename) is None})
    if missing:
        rows = "\n".join(f"  {name}" for name in missing)
        pytest.fail(f"{len(missing)} cited modules do not exist:\n{rows}")


if __name__ == "__main__":
    rows = parameter_rows()
    total = sum(len(row[3]) for row in rows)
    failures = []
    for doc_line, names, value, citations in rows:
        for filename, number in citations:
            source = source_lines(filename)
            if (source is None or not 0 < number <= len(source)
                    or not mentions(source[number - 1], names, value)):
                failures.append((doc_line, names[0] if names else value,
                                 f"{filename}:{number}"))
    for doc_line, subject, cite in failures:
        print(f"{DOC}:{doc_line} {subject} cites {cite}")
    print(f"{total - len(failures)} of {total} cited source lines hold their parameter")
