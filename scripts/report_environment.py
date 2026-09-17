"""
Print the installed library versions and the seed-0 Iris accuracies as one line of JSON.

The point is to be run somewhere that is not this machine. The CI jobs install with
`pip install -e .[dev]`, which resolves against the lower bounds in `pyproject.toml`
rather than `requirements-lock.txt`, so each job is a second, unpinned stack. Running
this there and reading the line out of the job log measures how far the reported
accuracies move when the library versions move, which `requirements-lock.txt` pins away
on the machine that produced `results.json`.

It calls the pipeline's own functions at seed 0 and changes nothing: `nn_iris.train`
with its default restarts for the photonic layer, and `nn_iris.identity_control` and
`nn_iris.logistic_baseline` restricted to the single seed. The keys are the ones
`results.json` stores under `environment.seed0_reference`.

Run directly:  python scripts/report_environment.py
"""

import lightin._threads  # noqa: F401  (sets thread counts before numpy loads)

import json
import platform
from importlib.metadata import version

from lightin import nn_iris

PACKAGES = ("numpy", "scipy", "scikit-learn", "matplotlib")


def report():
    """The versions and the four seed-0 accuracies, as a plain dict."""
    trained = nn_iris.train(seed=0)
    identity = nn_iris.identity_control(seeds=[0])
    logistic = nn_iris.logistic_baseline(seeds=[0])
    out = {"python": platform.python_version()}
    out.update({pkg.replace("-", "_"): version(pkg) for pkg in PACKAGES})
    out["iris_full_acc"] = trained["full_acc"]
    out["iris_test_acc"] = trained["test_acc"]
    out["identity_full_acc"] = identity["full_acc_per_seed"][0]
    out["logistic_full_acc"] = logistic["full_acc_per_seed"][0]
    return out


def machine():
    """What the run landed on, which `report()` deliberately leaves out.

    The accuracies are a property of the code and the library versions; the processor is
    not, and `results.json` records one machine rather than every machine. It is printed
    beside them because a hosted runner does not promise the same processor twice, and the
    kernels numpy and OpenBLAS select depend on which one it is.
    """
    return {"processor": platform.processor() or "unknown",
            "machine": platform.machine(),
            "system": platform.system()}


if __name__ == "__main__":
    print(json.dumps({**report(), **machine()}))
