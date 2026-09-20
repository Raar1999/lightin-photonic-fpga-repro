"""
The stable probes must be stable: same process, same inputs, bit-identical values.

Run directly:  PYTHONPATH=. python3 tests/test_probe_stability.py
Or with pytest: PYTHONPATH=. pytest -q

`scripts/report_environment.py` prints a block of probes in every CI job so that a library
upgrade that changed the arithmetic would show as a difference from `results.json`. That
reading only works if the probes are functions of their inputs and nothing else. A probe
that carried hidden state, consumed a shared random stream, or selected among near-equal
optima the way the Iris fit does would move on its own and be read as drift.

Calling the block twice in one process is the cheapest arrangement that catches that: the
libraries, the interpreter and the processor are all held fixed, so any difference between
the two calls is the probe's own. Catching it here rather than in CI matters because in CI
the same difference is indistinguishable from the drift the probes exist to detect.
"""

import json
from math import isfinite
from pathlib import Path

import pytest

from scripts import report_environment as env

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def two_runs():
    """The probe block, computed twice in this process, in that order."""
    return env.probes(), env.probes()


def test_the_two_runs_carry_the_same_probes(two_runs):
    """A probe that appears in one run and not the other is not comparable at all."""
    first, second = two_runs
    assert list(first) == list(second)
    assert first, "the probe block is empty"


def test_every_probe_is_identical_on_a_second_call(two_runs):
    """Exact equality, not a tolerance: the two calls differ in nothing.

    A tolerance here would pass a probe that drifts by less than it and leave the CI table
    reporting that drift as a library difference. `repr` is compared as well as the value
    so that a sign difference on zero, which `==` accepts, is still caught.
    """
    first, second = two_runs
    moved = [
        (name, first[name][0], second[name][0])
        for name in first
        if repr(first[name][0]) != repr(second[name][0])
    ]
    if moved:
        rows = "\n".join(f"  {name}: {a!r} then {b!r}" for name, a, b in moved)
        pytest.fail(
            f"{len(moved)} of {len(first)} probes moved between two calls in one "
            f"process, so they cannot measure library drift:\n{rows}"
        )


def test_every_probe_is_a_finite_number(two_runs):
    """A NaN probe compares equal to nothing and would read as permanent drift."""
    first, _ = two_runs
    bad = sorted(name for name, (value, _) in first.items()
                 if not isinstance(value, float) or not isfinite(value))
    assert not bad, f"probes that are not finite floats: {bad}"


def test_every_probe_path_resolves_in_results_json(two_runs):
    """The stored side of the comparison exists, so the CI table is a comparison.

    Without this a renamed `results.json` key would print as "missing" in every job and
    the probe would quietly stop being checked while the table still looked full.
    """
    first, _ = two_runs
    with (ROOT / "results.json").open(encoding="utf-8") as fh:
        results = json.load(fh)
    unresolved = sorted(
        (name, ".".join(keys)) for name, (_, keys) in first.items()
        if not isinstance(env._walk(results, keys), (int, float))
    )
    if unresolved:
        rows = "\n".join(f"  {name} -> {path}" for name, path in unresolved)
        pytest.fail(f"{len(unresolved)} probe paths do not resolve to a number "
                    f"in results.json:\n{rows}")


if __name__ == "__main__":
    first = env.probes()
    env.print_probe_table(env.probe_rows(computed=first))
    second = env.probes()
    moved = [name for name in first
             if repr(first[name][0]) != repr(second[name][0])]
    print(f"{len(first) - len(moved)} of {len(first)} probes identical on a second call")
    for name in moved:
        print(f"  moved: {name}: {first[name][0]!r} then {second[name][0]!r}")
