"""Start the application: ``rnw-gui``, ``python -m rnw.gui`` or the packaged program.

The Tauri window opens; the classic Qt window opens instead when it is chosen or when the Tauri
window cannot open (``rnw.gui.start``). ``--self-test`` checks the classic window offscreen and,
when there is one, the Tauri window's shell and bridge; a package must carry the Tauri window.
The packaging jobs run it on the built folder.
"""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from rnw.app import paths
from rnw.gui import start

if TYPE_CHECKING:
    from collections.abc import Sequence

SELF_TEST = "--self-test"


def self_test(arguments: Sequence[str]) -> int:
    """Both windows' self-tests; the exit code is 0 when every one that must pass did."""
    from rnw.gui import classic  # noqa: PLC0415 - Qt only when it is needed

    code = classic.main(arguments)
    folder = paths.program_directory()
    window = start.find_window(folder)
    if window is None:
        if start.packaged(folder):
            print("The Tauri window is missing from this package", file=sys.stderr)
            return 1
        print("No Tauri window is built in this checkout; only the classic window was checked")
        return code
    with TemporaryDirectory(prefix="rnw-window-test-") as temporary:
        answer, output = start.self_test(window, Path(temporary))
    print(output)
    if answer != 0 or start.SELF_TEST_LINE not in output:
        print(f"The Tauri window's self-test failed (exit code {answer})", file=sys.stderr)
        return 1
    return code


def main(argv: Sequence[str] | None = None) -> int:
    """Open the Tauri window, or the classic one when it is chosen or the Tauri one cannot."""
    arguments = list(sys.argv if argv is None else argv)
    if SELF_TEST in arguments:
        return self_test(arguments)
    choice = start.choose(arguments)
    instead = choice.reason
    if choice.program is not None:
        forwarded = [argument for argument in arguments[1:] if argument != start.CLASSIC]
        outcome = start.run_window(choice.program, forwarded)
        if outcome.opened:
            return outcome.code
        instead = outcome.reason
        print(f"The classic window opens: {instead}", file=sys.stderr)
    try:
        from rnw.gui import classic  # noqa: PLC0415 - Qt only when it is needed
    except ImportError as error:
        print(f"The classic window needs PySide6 ({error})", file=sys.stderr)
        return 2
    kept = [argument for argument in arguments if argument != start.CLASSIC]
    return classic.main(kept, instead=instead)


if __name__ == "__main__":
    sys.exit(main())
