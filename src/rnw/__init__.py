"""Random New World: a generated New World for Europa Universalis V."""

import os
from importlib.metadata import version

# numpy asks the kernel for huge pages (``madvise``) for every large array. Where the kernel's
# defrag setting is ``madvise``, the usual one, the thread that allocates then reclaims and
# compacts memory itself, and a whole export stalled every task of the machine for 1.2 s
# (198 000 pages reclaimed, 1 800 compaction stalls); without the request the stall was 2 ms
# and the run as fast (ADR 0006). numpy reads the variable when it is imported, so it is set
# here, before anything imports numpy; a value the user has set stays.
_ = os.environ.setdefault("NUMPY_MADVISE_HUGEPAGE", "0")

# The one product version (ADR 0003), read from pyproject.toml. It is the Steam
# Workshop version of the mod and versions generated output for reproducibility.
__version__: str = version("eu5-random-new-world")
