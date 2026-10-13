"""The standalone validation kit uses synthetic data and no game installation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from typer.testing import CliRunner

from rnw.cli import app

if TYPE_CHECKING:
    from pathlib import Path


def test_prepared_mod_has_matching_identity_and_beta_version(tmp_path: Path) -> None:
    """The generated folder and metadata identity match for the loading experiment."""
    output = tmp_path / "rnw_exp_001_metadata"
    result = CliRunner().invoke(app, ["prepare-mod", str(output)])
    assert result.exit_code == 0, result.output
    metadata = cast(
        "dict[str, object]",
        json.loads((output / ".metadata/metadata.json").read_text(encoding="utf-8-sig")),
    )
    assert metadata["id"] == output.name
    assert metadata["supported_game_version"] == "1.4.*"


def test_logdiff_reports_only_new_messages(tmp_path: Path) -> None:
    """Timestamp changes are ignored, while genuinely added errors are counted."""
    baseline = tmp_path / "baseline.log"
    current = tmp_path / "current.log"
    _ = baseline.write_text("[10:00:00][foo.cpp:1]: Existing error\n", encoding="utf-8")
    _ = current.write_text(
        "[10:01:00][foo.cpp:1]: Existing error\n[10:01:01][bar.cpp:2]: New error\n",
        encoding="utf-8",
    )
    result = CliRunner().invoke(app, ["logdiff", str(baseline), str(current)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["new_lines"] == 1
