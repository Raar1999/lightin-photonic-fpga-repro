"""
The seed-0 Iris fit must give the same answer twice.

The fit keeps the best of several random restarts of a non-convex optimisation. Its local
optima lie within about a thousandth of each other in objective and carry accuracies two
points apart, so anything that perturbs the last bits can change which restart wins and move
the reported accuracy. `lightin._threads` pins the BLAS and OpenMP thread counts to one to
remove one such source; this test is what would notice if the fit stopped being repeatable
anyway.

Run directly:  PYTHONPATH=. python3 tests/test_iris_fit_deterministic.py
Or with pytest: PYTHONPATH=. pytest -q
"""

import os

from lightin import _threads, nn_iris

RESTARTS = 5      # the property does not depend on the count; five keeps the suite quick


def test_thread_counts_pinned_before_numpy():
    """The pinning is only effective if it ran before numpy loaded its BLAS.

    Setting the variables afterwards leaves the libraries on the thread count they already
    chose, and the fit would be unpinned while every other check stayed green.
    """
    assert _threads.SET_BEFORE_NUMPY, (
        "numpy was imported before lightin._threads, so the thread counts were already "
        "read and the pinning had no effect"
    )
    for var in _threads.THREAD_VARS:
        assert os.environ.get(var) == "1", f"{var} is {os.environ.get(var)!r}, expected '1'"


def test_seed0_fit_repeats_within_a_process():
    """Two runs of the same fit in one process agree on both accuracies."""
    first = nn_iris.train(restarts=RESTARTS, seed=0)
    second = nn_iris.train(restarts=RESTARTS, seed=0)
    assert first["full_acc"] == second["full_acc"]
    assert first["test_acc"] == second["test_acc"]


if __name__ == "__main__":
    test_thread_counts_pinned_before_numpy()
    test_seed0_fit_repeats_within_a_process()
    print("iris fit determinism: ok")
