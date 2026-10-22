"""Names inside a world's folder in the library, shared by the export and the viewer.

The export writes a world's bundle (its mod, pictures, atlas, record and lists) into a folder; the
library and the viewer read it. These are the names both sides must agree on, kept apart from the
code that reads the game so that the viewer does not need that code to know them.
"""

from __future__ import annotations

from typing import Final

# The copy, beside the mod, of the files that cover the New World at country selection.
COVER_COPY: Final[str] = "selection_cover"
