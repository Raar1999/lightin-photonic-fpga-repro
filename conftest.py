"""Pytest imports this before the test modules, which is where the thread pinning has to
happen: the variables in `lightin._threads` are read when numpy loads its BLAS."""

import lightin._threads  # noqa: F401
