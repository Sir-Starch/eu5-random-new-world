"""What goes into the application folder and what stays out (read by ``rnw.spec``)."""

from __future__ import annotations

from typing import Final

NAME: Final[str] = "RandomNewWorld"
# Libraries of the build machine's desktop (GTK and what it pulls in) that Qt's platform-theme
# plugin links against: the player's own desktop supplies its theme, and a copy of GTK in the
# folder would fight the system's.
HOST_DESKTOP: Final[tuple[str, ...]] = (
    "libgtk-",
    "libgdk-",
    "libgdk_pixbuf",
    "libglycin",
    "libpango",
    "libcairo",
    "libatk",
    "libatspi",
    "libepoxy",
    "libharfbuzz",
    "libfribidi",
    "libthai",
    "libdatrie",
    "libwayland-cursor",
)
# Qt modules the window does not import; their libraries and plugins stay out of the folder.
EXCLUDED_MODULES: Final[tuple[str, ...]] = (
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtNetwork",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "PySide6.QtDBus",
    "PySide6.QtConcurrent",
    "PySide6.QtXml",
    "PySide6.QtHelp",
    "PySide6.QtDesigner",
    "PySide6.QtUiTools",
    "tkinter",
    "pytest",
    "ruff",
    "basedpyright",
)
# Plugins of the platform theme integrate with GTK or the desktop portal; Qt falls back to its
# own style without them.
EXCLUDED_PLUGINS: Final[tuple[str, ...]] = ("platformthemes",)


def wanted(destination: str) -> bool:
    """Whether a binary or data file bound for ``destination`` belongs in the folder."""
    name = destination.rsplit("/", 1)[-1]
    if any(plugin in destination for plugin in EXCLUDED_PLUGINS):
        return False
    return not name.startswith(HOST_DESKTOP)
