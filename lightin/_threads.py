"""
Pin the BLAS and OpenMP thread counts to one, so the Iris fit is reproducible.

The thread count is an execution setting, not a model parameter: it decides the order in
which a parallel floating-point reduction accumulates, and so the last bits of the result.
The Iris fit keeps the best of several random restarts of a non-convex optimisation whose
local optima lie within a thousandth of each other in objective, so a last-bit difference
can change which restart wins and move the reported accuracy by more than a point. Pinning
the counts is done to make the fit reproducible, not to move any result toward any other.

The variables are read by OpenBLAS, MKL and OpenMP when their libraries load, which happens
on the first numpy import, so this module has to be imported before numpy. `lightin`'s own
`__init__` imports it, and the entry points that do not go through the package -- the two
scripts and the test suite's `conftest.py` -- import it as their first statement.
`SET_BEFORE_NUMPY` records whether that ordering actually held, so a caller that imported
numpy first fails the determinism test rather than silently getting the unpinned behaviour.
"""

import os
import sys

THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
               "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")

SET_BEFORE_NUMPY = "numpy" not in sys.modules

for _var in THREAD_VARS:
    os.environ[_var] = "1"
