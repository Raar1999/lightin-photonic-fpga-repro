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
import os
import platform
from importlib.metadata import version

from lightin import nn_iris

PACKAGES = ("numpy", "scipy", "scikit-learn", "matplotlib")


def report():
    """The versions, the four seed-0 accuracies, and the two leading restarts.

    The objectives are here because the accuracy alone does not say why it is what it is:
    the fit keeps the lowest-objective restart, and the restarts below it reach different
    accuracies, so the objective and the index identify which optimum a machine selected.
    """
    trained = nn_iris.train(seed=0)
    identity = nn_iris.identity_control(seeds=[0])
    logistic = nn_iris.logistic_baseline(seeds=[0])
    rows = trained["restarts"]
    out = {"python": platform.python_version()}
    out.update({pkg.replace("-", "_"): version(pkg) for pkg in PACKAGES})
    out["iris_full_acc"] = trained["full_acc"]
    out["iris_test_acc"] = trained["test_acc"]
    out["identity_full_acc"] = identity["full_acc_per_seed"][0]
    out["logistic_full_acc"] = logistic["full_acc_per_seed"][0]
    out["best_restart"] = trained["best_restart"]
    out["best_objective"] = rows[0]["objective"]
    out["second_objective"] = rows[1]["objective"]
    return out


def _cpu_model():
    """The processor's model name.

    `platform.processor()` returns only "x86_64" on Linux, which does not say which
    generation of hardware ran the job, so on Linux the name is read out of
    /proc/cpuinfo instead. Elsewhere `platform.processor()` is informative and is used.
    """
    if platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except OSError:
            pass
    return platform.processor() or "unknown"


def _openblas_coretype():
    """Which OpenBLAS kernel is loaded, and how many threads it is allowed.

    OpenBLAS is built DYNAMIC_ARCH, so it picks a kernel from the processor it finds at
    load time; two runner generations therefore run different code for the same call.
    `threadpoolctl` reports the choice directly. Without it the build configuration in
    `numpy.show_config()` names the architecture the wheel was built against, which is
    the fallback and is not the same statement.
    """
    try:
        from threadpoolctl import threadpool_info
        for info in threadpool_info():
            if info.get("internal_api") == "openblas":
                return {"openblas_coretype": info.get("architecture", "unknown"),
                        "openblas_threads": info.get("num_threads"),
                        "openblas_source": "threadpoolctl"}
    except Exception:
        pass
    try:
        import numpy as np
        cfg = np.show_config(mode="dicts")
        blas = cfg.get("Build Dependencies", {}).get("blas", {})
        return {"openblas_coretype": blas.get("openblas configuration", "unknown"),
                "openblas_threads": None,
                "openblas_source": "numpy.show_config"}
    except Exception:
        return {"openblas_coretype": "unknown", "openblas_threads": None,
                "openblas_source": "unavailable"}


def machine():
    """What the run landed on, which `report()` deliberately leaves out.

    The accuracies are a property of the code and the library versions; the processor is
    not, and `results.json` records one machine rather than every machine. It is printed
    beside them because a hosted runner does not promise the same processor twice, and the
    kernel OpenBLAS selects depends on which one it is.
    """
    out = {"cpu_model": _cpu_model(),
           "cpu_count": os.cpu_count(),
           "machine": platform.machine(),
           "system": platform.system()}
    out.update(_openblas_coretype())
    out["openblas_coretype_env"] = os.environ.get("OPENBLAS_CORETYPE")
    return out


if __name__ == "__main__":
    print(json.dumps({**report(), **machine()}))
