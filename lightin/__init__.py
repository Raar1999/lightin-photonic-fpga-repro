"""The thread pinning has to happen before numpy loads, so it is the package's first import."""

from . import _threads  # noqa: F401
