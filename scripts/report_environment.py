"""
Print the installed library versions, a block of stable physics probes and the seed-0
Iris accuracies, as one line of JSON followed by the probe table.

The point is to be run somewhere that is not this machine. The CI jobs install with
`pip install -e .[dev]`, which resolves against the lower bounds in `pyproject.toml`
rather than `requirements-lock.txt`, so each job is a second, unpinned stack. Running
this there and reading the output out of the job log measures how far the reported
numbers move when the library versions move, which `requirements-lock.txt` pins away
on the machine that produced `results.json`.

The probes are the drift signal. Each is a deterministic function of fixed inputs --
a closed form, a single least-squares fit to a fixed 25-point file, an analytic
resonator solve -- so a library that changed the arithmetic would move it, and nothing
else in the run can. Each is printed beside the value `results.json` stores and the
absolute difference between them.

The seed-0 Iris accuracies are printed for information and are not part of that signal.
The fit keeps the lowest-objective restart of a non-convex problem whose optima lie
within a thousandth of each other, so a last-bit difference changes which restart wins
and moves the accuracy by more than a point. It answers the question "which optimum did
this machine select", not "did the libraries change the physics".

It calls the pipeline's own functions and changes nothing: `nn_iris.train` at seed 0
with its default restarts for the photonic layer, `nn_iris.identity_control` and
`nn_iris.logistic_baseline` restricted to the single seed, and for the probes the same
entry points `scripts/run_all.py` calls to write the values they are compared against.
The accuracy keys are the ones `results.json` stores under
`environment.seed0_reference`.

Run directly:  python scripts/report_environment.py
"""

import os
import sys

# Python puts scripts/ on sys.path when this file is run as a script, not the repository
# root, so `lightin` resolves only when the package itself has been installed. Adding the
# root keeps `pip install -r requirements.txt` -- which installs the dependencies and not
# this package -- a working alternative to `pip install -e .`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lightin._threads  # noqa: F401  (sets thread counts before numpy loads)

import json
import platform
from importlib.metadata import version

from lightin import coupler, expressivity, nn_iris, recirculating
from lightin.metrics import enob, propagation_latency

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fit_fig4                       # noqa: E402  (sibling script)

PACKAGES = ("numpy", "scipy", "scikit-learn", "matplotlib")

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "..", "results.json")

# The two effective-bit sigmas and the propagation length the pipeline quotes. `run_all.py`
# writes them as literals at its own call sites, so these are second copies. The ENOB pair
# guards itself: `results.json` names the key after the sigma, so a sigma that stopped
# matching would fail the lookup here by name rather than compare a different quantity. The
# path length has no such guard, and a change to it would show as a large probe difference
# rather than as an equal value, which is the difference this script exists to print.
ENOB_SIGMAS = (0.0269, 0.0453)
ENOB_SECTIONS = ("unitary", "nonunitary")
PATH_LENGTH_M = 4.5e-3


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


def probes():
    """The stable probes, as an ordered {name: (value, key path in `results.json`)}.

    Stable means a deterministic function of inputs that do not move: closed forms over
    fixed constants, one least-squares fit to a fixed 25-point CSV, an analytic resonator
    solve against its own closed-form transfer function, and a best-fit recovery of a
    unitary the mesh generated itself. None of them selects among near-degenerate optima,
    so none can move by a visible amount for an arithmetic reason, and a library that did
    change the arithmetic would show up here at the last bits.

    Each is computed by the entry point `scripts/run_all.py` calls to write the stored
    value, so the two sides of the comparison are the same code on the same inputs. The
    paths are key tuples rather than dotted strings because two of the keys contain a dot
    of their own.

    The seed-0 Iris accuracy is deliberately not here. It is reported by `report()` for
    information: the fit selects among optima that lie within a thousandth of each other
    in objective, so it moves by more than a point for arithmetic reasons and cannot
    separate a library change from a change of machine.
    """
    cp = coupler.run(verbose=False)
    rc = recirculating.run(verbose=False)
    mesh = fit_fig4.fit_mesh()
    out = {}
    for sigma, section in zip(ENOB_SIGMAS, ENOB_SECTIONS):
        key = f"enob_at_sigma_{sigma}"
        out[f"{section}_{key}"] = (enob(sigma), (section, key))
    out["latency_on_chip_ps"] = (propagation_latency(PATH_LENGTH_M) * 1e12,
                                 ("latency_on_chip_ps",))
    out["coupler_extinction_at_1560_db"] = (float(cp["extinction_at_1560_db"]),
                                            ("coupler", "extinction_at_1560_db"))
    out["fig4d_mesh_lambda0_nm"] = (mesh["lambda0"], ("fig4d_mesh_fit", "lambda0_nm"))
    out["fig4d_mesh_slope"] = (mesh["slope"], ("fig4d_mesh_fit", "slope"))
    out["recirc_ring_rms"] = (float(rc["ring_rms"]), ("recirculating", "ring_rms"))
    out["recirc_add_drop_rms"] = (float(rc["add_drop_rms"]),
                                  ("recirculating", "add_drop_rms"))
    out["realizable_unitary_fidelity"] = (
        float(expressivity.realizable_unitary_reachability()),
        ("expressivity", "realizable_unitary_fidelity"))
    return out


def stored_results(path=RESULTS):
    """`results.json`, or None where it is not beside the script."""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except OSError:
        return None


def _walk(data, keys):
    node = data
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def probe_rows(computed=None, results=None):
    """One row per probe: (name, dotted path, computed, stored, absolute difference).

    `stored` and the difference are None where `results.json` is absent or does not hold
    the path, so a missing file reports as missing rather than as agreement.
    """
    computed = probes() if computed is None else computed
    results = stored_results() if results is None else results
    rows = []
    for name, (value, keys) in computed.items():
        stored = None if results is None else _walk(results, keys)
        diff = None if not isinstance(stored, (int, float)) else abs(value - float(stored))
        rows.append((name, ".".join(keys), value, stored, diff))
    return rows


def print_probe_table(rows):
    """The probe table, one line per probe, widest column sized to the names present."""
    width = max(len(name) for name, *_ in rows)
    print(f"{'probe':<{width}}  {'computed':>24}  {'results.json':>24}  {'abs diff':>10}")
    for name, _, value, stored, diff in rows:
        shown = "missing" if stored is None else f"{float(stored):.17g}"
        gap = "n/a" if diff is None else f"{diff:.3e}"
        print(f"{name:<{width}}  {value:>24.17g}  {shown:>24}  {gap:>10}")
    worst = [d for *_, d in rows if d is not None]
    if worst:
        print(f"largest absolute probe difference: {max(worst):.3e} "
              f"over {len(worst)} of {len(rows)} probes")


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


def _avx512():
    """Whether the processor offers AVX-512, and whether numpy is dispatching to it.

    Two different statements, and the CI job needs both. `__cpu_features__` is numpy's
    detection of what the processor supports, so its AVX-512 entries say whether this
    runner is one of the generations that offers the instruction set at all.
    `NPY_DISABLE_CPU_FEATURES` does not change those entries: from numpy 2.3 the
    dispatch targets are the x86-64 level groups, and the SIMD extensions block of
    `numpy.show_config` is where a disabled group moves from "found" to "not found".
    Printing both is what lets the log distinguish a runner with no AVX-512 from a
    runner whose AVX-512 was disabled, which the accuracies alone cannot separate.

    The dict is read from `numpy._core` where that exists and from `numpy.core`
    otherwise; the latter is the pre-2.0 spelling and warns on newer versions.
    """
    out = {}
    feats = None
    for mod in ("numpy._core._multiarray_umath", "numpy.core._multiarray_umath"):
        try:
            feats = __import__(mod, fromlist=["__cpu_features__"]).__cpu_features__
            break
        except Exception:
            continue
    if feats is None:
        out["avx512_features"] = "unavailable"
    else:
        out["avx512_features"] = {k: bool(v) for k, v in feats.items() if "AVX512" in k}
        out["avx512_any"] = any(out["avx512_features"].values())
    try:
        import numpy as np
        simd = np.show_config(mode="dicts").get("SIMD Extensions", {})
        out["simd_baseline"] = simd.get("baseline")
        out["simd_found"] = simd.get("found")
        out["simd_not_found"] = simd.get("not found")
    except Exception:
        out["simd_baseline"] = out["simd_found"] = out["simd_not_found"] = None
    out["npy_disable_cpu_features_env"] = os.environ.get("NPY_DISABLE_CPU_FEATURES")
    return out


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
    out.update(_avx512())
    return out


if __name__ == "__main__":
    rows = probe_rows()
    print(json.dumps({**report(), **machine(),
                      "probes": {name: value for name, _, value, _, _ in rows},
                      "probe_diffs": {name: diff for name, _, _, _, diff in rows}}))
    print_probe_table(rows)
