"""The standalone validation kit uses synthetic data and no game installation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import pytest
from typer.testing import CliRunner

from rnw import epoch, parallel
from rnw.app import library, service
from rnw.app.worldcode import encode, new_code
from rnw.cli import app
from rnw.record import FORMAT, GameRecord, Record, Verdict
from rnw.settings import build_settings

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


def test_newworld_refuses_to_start_without_the_memory_it_needs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With too little free memory the command stops before any work and says why."""
    monkeypatch.delenv("RNW_MEMORY", raising=False)
    monkeypatch.setattr(parallel, "available_memory", lambda: 2 * parallel.GIB)
    game = tmp_path / "game"
    game.mkdir()
    output = tmp_path / "generated" / "rnw_exp_low_memory"
    result = CliRunner().invoke(
        app, ["newworld", "--game-dir", str(game), "--output", str(output), "--seed", "1"]
    )
    assert result.exit_code == 2
    assert "needs about 7.5 GiB of free memory" in result.output
    assert "2.0 GiB free" in result.output
    assert not output.exists()


def test_world_codes_round_trip_through_the_command() -> None:
    """The command prints a code for a seed and reads it back to the same world."""
    runner = CliRunner()
    made = runner.invoke(app, ["world-code", "--preset", "archipelago", "--seed", "99"])
    assert made.exit_code == 0, made.output
    printed = cast("dict[str, object]", json.loads(made.output))
    assert printed["seed"] == 99
    assert printed["preset"] == "archipelago"
    assert printed["reproduced_by_this_generator"] is True
    assert printed["algorithm"] == epoch.CURRENT
    read = runner.invoke(app, ["world-code", str(printed["code"]).lower()])
    assert read.exit_code == 0, read.output
    assert cast("dict[str, object]", json.loads(read.output))["seed"] == 99
    broken = runner.invoke(app, ["world-code", "RNW1-00000-00000"])
    assert broken.exit_code == 2
    assert "Error:" in broken.output


def test_find_game_reports_the_variables_it_was_given(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The search lists an explicit game folder and profile folder first."""
    game = tmp_path / "game"
    (game / "game" / "in_game" / "map_data").mkdir(parents=True)
    profile = tmp_path / "profile"
    profile.mkdir()
    monkeypatch.setenv("EU5_GAME_DIR", str(game))
    monkeypatch.setenv("EU5_USER_DIR", str(profile))
    result = CliRunner().invoke(app, ["find-game"])
    assert result.exit_code == 0, result.output
    found = cast("dict[str, list[dict[str, object]]]", json.loads(result.output))
    assert found["games"][0]["directory"] == str(game)
    assert found["profiles"][0]["kind"] == "chosen"


def _recorded_world(data: Path) -> library.World:
    """A world in a library at ``data``, with a record, as the export leaves it."""
    code = encode(new_code("continents", 5))
    world = library.World(
        id=library.world_id(code, "1"),
        code=code,
        preset="continents",
        seed=5,
        generator="0.9.22",
        game_build="1",
        created=1,
        seconds=1.0,
        record=Record(
            format=FORMAT,
            algorithm=epoch.CURRENT,
            release="0.9.22",
            code=code,
            preset="continents",
            seed=5,
            settings=build_settings("continents").to_json_data(),
            game=GameRecord("EU5 test", "f" * 64, "1.4.*", "e" * 64, 3),
            output_sha256="d" * 64,
            output_count=2,
        ),
    )
    library.save(data, world)
    return world


@pytest.mark.parametrize(("reproduced", "exit_code"), [(True, 0), (False, 1)])
def test_verify_world_says_whether_a_world_comes_out_the_same(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, reproduced: bool, exit_code: int
) -> None:
    """The exit code is 0 only for a reproduced world; the answer is printed as JSON."""
    world = _recorded_world(tmp_path / "data")
    (tmp_path / "game").mkdir()

    def fake_check(found: library.World, **_: object) -> service.Check:
        assert found.id == world.id
        return service.Check(
            Verdict.IDENTICAL if reproduced else Verdict.OTHER_INPUTS,
            reproduced,
            [],
            [] if reproduced else ["seed.txt"],
            2.0,
        )

    monkeypatch.setattr(service, "check", fake_check)
    arguments = [
        "verify-world",
        world.code,
        "--game-dir",
        str(tmp_path / "game"),
        "--data-dir",
        str(tmp_path / "data"),
    ]
    result = CliRunner().invoke(app, arguments)
    assert result.exit_code == exit_code, result.output
    answer = cast("dict[str, object]", json.loads(result.output[result.output.index("{") :]))
    assert answer["world"] == world.id
    assert answer["reproduced"] is reproduced
    missing = CliRunner().invoke(app, ["verify-world", "nothing", *arguments[2:]])
    assert missing.exit_code != 0


def test_a_world_file_goes_out_and_in_through_the_commands(tmp_path: Path) -> None:
    """Export writes it; import takes it into another library; a bad file is an error."""
    world = _recorded_world(tmp_path / "one")
    runner = CliRunner()
    output = tmp_path / "w.rnworld"
    made = runner.invoke(
        app, ["export-world", world.id, str(output), "--data-dir", str(tmp_path / "one")]
    )
    assert made.exit_code == 0, made.output
    taken = runner.invoke(app, ["import-world", str(output), "--data-dir", str(tmp_path / "two")])
    assert taken.exit_code == 0, taken.output
    answer = cast("dict[str, object]", json.loads(taken.output[taken.output.index("{") :]))
    assert answer["world"] == world.id
    assert answer["new"] is True
    again = runner.invoke(app, ["import-world", str(output), "--data-dir", str(tmp_path / "two")])
    assert json.loads(again.output[again.output.index("{") :])["new"] is False
    junk = tmp_path / "junk.rnworld"
    _ = junk.write_bytes(b"nope")
    bad = runner.invoke(app, ["import-world", str(junk), "--data-dir", str(tmp_path / "two")])
    assert bad.exit_code == 2
    missing = runner.invoke(
        app, ["export-world", "nothing", str(output), "--data-dir", str(tmp_path / "one")]
    )
    assert missing.exit_code != 0
    none = runner.invoke(
        app,
        [
            "transfer-out",
            world.id,
            str(tmp_path / "m.rnworld-mod"),
            "--data-dir",
            str(tmp_path / "one"),
        ],
    )
    assert none.exit_code == 2
    assert "no mod" in none.output
