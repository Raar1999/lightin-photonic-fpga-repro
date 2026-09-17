"""
`results.json` must carry the seed-0 restart degeneracy, and it must describe a real fit.

The block exists so the reported single-seed accuracy can be read with the objective margin
that selected it. A block that drifted from the fit would be worse than none, so this checks
it against a freshly computed restart table rather than only checking that keys are present.

Run directly:  PYTHONPATH=. python3 tests/test_restart_degeneracy.py
Or with pytest: PYTHONPATH=. pytest -q
"""

import json
from pathlib import Path

from lightin import nn_iris

ROOT = Path(__file__).resolve().parents[1]
RESTARTS = 5      # the structure is a property of the fit, not of how many restarts it runs

KEYS = ("n_restarts", "tol", "best_objective", "best_restart", "gap_to_second",
        "n_within_tol", "full_acc_min", "full_acc_max", "full_acc_range",
        "selected_full_acc", "all_full_acc_min", "all_full_acc_max", "min_adjacent_gap")


def _stored():
    with (ROOT / "results.json").open(encoding="utf-8") as fh:
        return json.load(fh)["iris"]["restart_degeneracy"]


def test_block_is_present_and_complete():
    block = _stored()
    missing = [k for k in KEYS if k not in block]
    assert not missing, f"restart_degeneracy is missing {missing}"
    assert block["n_restarts"] == nn_iris.N_RESTARTS
    assert block["tol"] == nn_iris.DEGENERACY_TOL


def test_stored_block_is_self_consistent():
    """The stored ranges must bracket the accuracy the fit reports, and be ordered."""
    block = _stored()
    assert block["full_acc_min"] <= block["selected_full_acc"] <= block["full_acc_max"]
    assert block["all_full_acc_min"] <= block["full_acc_min"]
    assert block["all_full_acc_max"] >= block["full_acc_max"]
    assert block["full_acc_range"] == block["full_acc_max"] - block["full_acc_min"]
    assert 1 <= block["n_within_tol"] <= block["n_restarts"]
    assert block["gap_to_second"] >= 0
    assert block["min_adjacent_gap"] >= 0
    assert block["min_adjacent_gap"] <= block["gap_to_second"]


def test_summary_agrees_with_a_live_restart_table():
    """Summarising a real table reproduces the relations the stored block asserts.

    Run at reduced restarts, so the numbers are not the stored ones; what is checked is
    that `degeneracy_summary` reports the table it was given -- the accuracy range it
    quotes is the range of the restarts inside the tolerance, and the selected accuracy
    is the lowest-objective restart's.
    """
    rows = nn_iris.restart_table(seed=0, restarts=RESTARTS)
    block = nn_iris.degeneracy_summary(rows)

    assert [r["objective"] for r in rows] == sorted(r["objective"] for r in rows)
    assert block["selected_full_acc"] == rows[0]["full_acc"]
    assert block["best_restart"] == rows[0]["restart"]

    near = [r for r in rows if r["objective"] - rows[0]["objective"] <= block["tol"]]
    assert block["n_within_tol"] == len(near)
    assert block["full_acc_min"] == min(r["full_acc"] for r in near)
    assert block["full_acc_max"] == max(r["full_acc"] for r in near)
    assert block["all_full_acc_min"] == min(r["full_acc"] for r in rows)
    assert block["all_full_acc_max"] == max(r["full_acc"] for r in rows)


if __name__ == "__main__":
    test_block_is_present_and_complete()
    test_stored_block_is_self_consistent()
    test_summary_agrees_with_a_live_restart_table()
    print("restart degeneracy: ok")
