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


def _fake_mod(root: Path, name: str, marker: str) -> Path:
    mod = root / name
    (mod / ".metadata").mkdir(parents=True)
    _ = (mod / ".metadata/metadata.json").write_text("{}", encoding="utf-8")
    _ = (mod / "marker.txt").write_text(marker, encoding="utf-8")
    return mod


def test_install_replace_swaps_only_rnw_mods(tmp_path: Path) -> None:
    """--replace swaps an installed rnw_exp_* mod in place; plain install refuses."""
    user = tmp_path / "user"
    (user / "mod").mkdir(parents=True)
    first = _fake_mod(tmp_path / "a", "rnw_exp_new_world", "one")
    second = _fake_mod(tmp_path / "b", "rnw_exp_new_world", "two")
    runner = CliRunner()
    assert runner.invoke(app, ["install-mod", str(first), str(user)]).exit_code == 0
    assert runner.invoke(app, ["install-mod", str(second), str(user)]).exit_code != 0
    result = runner.invoke(app, ["install-mod", "--replace", str(second), str(user)])
    assert result.exit_code == 0, result.output
    installed = user / "mod/rnw_exp_new_world/marker.txt"
    assert installed.read_text(encoding="utf-8") == "two"
    assert sorted(path.name for path in (user / "mod").iterdir()) == ["rnw_exp_new_world"]


def test_uninstall_removes_rnw_mods_and_refuses_others(tmp_path: Path) -> None:
    """Only rnw_exp_* folders with metadata can be removed."""
    user = tmp_path / "user"
    mods = user / "mod"
    _ = _fake_mod(mods, "rnw_exp_old", "x")
    _ = _fake_mod(mods, "someone_elses_mod", "y")
    runner = CliRunner()
    refused = runner.invoke(app, ["uninstall-mod", "someone_elses_mod", "--user-dir", str(user)])
    assert refused.exit_code != 0
    assert (mods / "someone_elses_mod").is_dir()
    done = runner.invoke(app, ["uninstall-mod", "rnw_exp_old", "--user-dir", str(user)])
    assert done.exit_code == 0, done.output
    assert not (mods / "rnw_exp_old").exists()
    assert (mods / "someone_elses_mod").is_dir()
