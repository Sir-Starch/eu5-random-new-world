"""World files are hostile input: each way a file can lie is refused, and a good one round-trips."""

from __future__ import annotations

import io
import json
import stat
import warnings
import zipfile
from typing import TYPE_CHECKING

import pytest

from rnw import atlas, worldfile
from rnw.worldfile import WorldFileError
from tests.fakes import synthetic_atlas

if TYPE_CHECKING:
    from pathlib import Path

RECORD = {"schema": 1, "id": "abcdefghij", "code": "RNW1-X", "note": "ünïcode"}


def _atlas_files() -> tuple[bytes, bytes]:
    return atlas.to_files(synthetic_atlas())


def _archive(path: Path, members: dict[str, bytes], listing: dict[str, str] | None = None) -> Path:
    """A world file made by hand, with a listing that is right unless ``listing`` says otherwise."""
    kind = "world"
    files = listing if listing is not None else {n: worldfile.sha256(d) for n, d in members.items()}
    meta = {"format": 1, "kind": kind, "exported_by": "test", "files": files}
    with warnings.catch_warnings(), zipfile.ZipFile(path, "w") as archive:
        warnings.simplefilter("ignore")
        archive.writestr("rnworld.json", json.dumps(meta))
        for name, data in members.items():
            archive.writestr(name, data)
    return path


def _good() -> dict[str, bytes]:
    document, labels = _atlas_files()
    return {
        "world.json": json.dumps(RECORD).encode(),
        "atlas.json": document,
        "atlas_labels.png": labels,
    }


def test_a_world_file_round_trips_with_and_without_an_atlas(tmp_path: Path) -> None:
    """The record and the atlas come back as they went; the listing names what is inside."""
    document, labels = _atlas_files()
    path = worldfile.write(tmp_path / "w.rnworld", RECORD, (document, labels))
    found = worldfile.read(path)
    assert found.kind == "world"
    assert found.record == RECORD
    assert found.atlas == (document, labels)
    assert set(found.files) == {"world.json", "atlas.json", "atlas_labels.png"}
    assert found.exported_by
    bare = worldfile.read(worldfile.write(tmp_path / "b.rnworld", RECORD, None))
    assert bare.atlas is None
    assert worldfile.is_world_file(tmp_path / "X.RNWORLD")
    assert worldfile.is_world_file(tmp_path / "x.rnworld-mod")
    assert not worldfile.is_world_file(tmp_path / "x.zip")


@pytest.mark.parametrize(
    "name",
    [
        "",
        "/etc/passwd",
        "../x",
        "a/../../x",
        "a\\b",
        "C:x",
        "a//b",
        "./x",
        "a/",
        "x\x00y",
        "é" * 200,
    ],
)
def test_a_name_that_is_not_a_plain_relative_path_is_refused(name: str) -> None:
    """Absolute paths, parent steps, backslashes, drives, empty parts and controls."""
    with pytest.raises(WorldFileError):
        _ = worldfile.check_name(name)


def test_a_plain_name_is_kept() -> None:
    """A normal nested name passes unchanged."""
    assert (
        worldfile.check_name("mod/in_game/map_data/locations.png")
        == "mod/in_game/map_data/locations.png"
    )


def test_a_file_that_is_not_a_world_file_is_refused(tmp_path: Path) -> None:
    """Not a zip, no header, a header of another format or kind, no world, half an atlas."""
    junk = tmp_path / "junk.rnworld"
    _ = junk.write_bytes(b"this is not a zip")
    with pytest.raises(WorldFileError, match=r"not a world file"):
        _ = worldfile.read(junk)
    with zipfile.ZipFile(tmp_path / "empty.rnworld", "w") as archive:
        archive.writestr("world.json", "{}")
    with pytest.raises(WorldFileError, match=r"no rnworld\.json"):
        _ = worldfile.read(tmp_path / "empty.rnworld")
    cases: list[tuple[dict[str, object], str]] = [
        ({"format": 9, "kind": "world", "files": {}}, "format 9"),
        ({"format": 1, "kind": "banana", "files": {}}, "readable format"),
        ({"format": 1, "kind": "world"}, "lists no files"),
        ({"format": 1, "kind": "world", "files": {"a": 1}}, "names and hashes"),
    ]
    for meta, match in cases:
        path = tmp_path / "meta.rnworld"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("rnworld.json", json.dumps(meta))
        with pytest.raises(WorldFileError, match=match):
            _ = worldfile.read(path)
    members = _good()
    no_world = {k: v for k, v in members.items() if k != "world.json"}
    with pytest.raises(WorldFileError, match=r"no world\.json"):
        _ = worldfile.read(_archive(tmp_path / "a.rnworld", no_world))
    half = {k: v for k, v in members.items() if k != "atlas_labels.png"}
    with pytest.raises(WorldFileError, match="half there"):
        _ = worldfile.read(_archive(tmp_path / "b.rnworld", half))


def test_a_file_that_lies_about_its_contents_is_refused(tmp_path: Path) -> None:
    """A hash that does not match, a member the layout does not have, a broken JSON record."""
    members = _good()
    wrong = {n: worldfile.sha256(d) for n, d in members.items()}
    wrong["world.json"] = "0" * 64
    with pytest.raises(WorldFileError, match="damaged"):
        _ = worldfile.read(_archive(tmp_path / "h.rnworld", members, wrong))
    with pytest.raises(WorldFileError, match="does not"):
        _ = worldfile.read(_archive(tmp_path / "s.rnworld", {**members, "evil.exe": b"MZ"}))
    broken = {**members, "world.json": b"{"}
    with pytest.raises(WorldFileError, match="not valid JSON"):
        _ = worldfile.read(_archive(tmp_path / "j.rnworld", broken))
    listed = {**members, "world.json": b"[1, 2]"}
    with pytest.raises(WorldFileError, match="not an object"):
        _ = worldfile.read(_archive(tmp_path / "l.rnworld", listed))


def test_unsafe_members_are_refused_whatever_they_are_named_for(tmp_path: Path) -> None:
    """Traversal, folders, links, duplicates and encryption never reach the contents."""
    members = _good()
    with pytest.raises(WorldFileError, match="not allowed"):
        _ = worldfile.read(_archive(tmp_path / "t.rnworld", {**members, "../escape": b"x"}))
    with pytest.raises(WorldFileError, match="not allowed"):
        _ = worldfile.read(_archive(tmp_path / "d.rnworld", {**members, "/abs": b"x"}))
    folder = tmp_path / "f.rnworld"
    with zipfile.ZipFile(folder, "w") as archive:
        archive.writestr("rnworld.json", "{}")
        archive.writestr("sub/", b"")
    with pytest.raises(WorldFileError, match=r"not allowed|folder"):
        _ = worldfile.read(folder)
    link = tmp_path / "link.rnworld"
    with zipfile.ZipFile(link, "w") as archive:
        archive.writestr("rnworld.json", "{}")
        info = zipfile.ZipInfo("world.json")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "/etc/passwd")
    with pytest.raises(WorldFileError, match="link"):
        _ = worldfile.read(link)
    twice = tmp_path / "twice.rnworld"
    with warnings.catch_warnings(), zipfile.ZipFile(twice, "w") as archive:
        warnings.simplefilter("ignore")
        archive.writestr("rnworld.json", "{}")
        archive.writestr("world.json", "{}")
        archive.writestr("world.json", "{}")
    with pytest.raises(WorldFileError, match="twice"):
        _ = worldfile.read(twice)
    encrypted = zipfile.ZipInfo("world.json")
    encrypted.flag_bits |= 0x1
    with pytest.raises(WorldFileError, match="encrypted"):
        _ = worldfile.list_members([encrypted])


def test_sizes_are_counted_by_what_is_read_not_by_what_an_archive_declares(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A member over its limit, and a whole over its total, are refused."""
    members = _good()
    path = _archive(tmp_path / "ok.rnworld", members)
    limits = {**worldfile.LIMITS, "atlas.json": 100}
    monkeypatch.setattr(worldfile, "LIMITS", limits)
    with pytest.raises(WorldFileError, match="larger than"):
        _ = worldfile.read(path)
    monkeypatch.undo()
    monkeypatch.setattr(worldfile, "WORLD_TOTAL", 1000)
    with pytest.raises(WorldFileError, match="larger than a world file"):
        _ = worldfile.read(path)
    monkeypatch.undo()


def test_a_corrupt_archive_is_a_world_file_error_and_not_a_crash(tmp_path: Path) -> None:
    """A flipped byte in the stored data fails the archive's own checks, and says so plainly."""
    path = _archive(tmp_path / "ok.rnworld", _good())
    raw = bytearray(path.read_bytes())
    with zipfile.ZipFile(path) as source:
        info = source.getinfo("atlas.json")
        start = info.header_offset + 30 + len(info.filename) + 8
    raw[start] ^= 0xFF
    broken = tmp_path / "broken.rnworld"
    _ = broken.write_bytes(bytes(raw))
    with pytest.raises(WorldFileError, match="damaged"):
        _ = worldfile.read(broken)
    assert io.BytesIO(b"").read() == b""


def _mod(root: Path) -> Path:
    mod = root / "rnw_exp_world_abcdefghij"
    for relative, content in (
        (".metadata/metadata.json", b"{}"),
        ("in_game/map_data/x.txt", b"x"),
        ("main_menu/localization/english/a_l_english.yml", "é".encode()),
    ):
        target = mod / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = target.write_bytes(content)
    return mod


def test_a_built_world_round_trips_and_every_file_is_checked_on_the_way_out(
    tmp_path: Path,
) -> None:
    """The mod comes out byte for byte; the compact reader sees its record without the mod."""
    mod = _mod(tmp_path / "src")
    bundle = {"manifest.json": b"{}", "inputs.json": b"{}"}
    path = worldfile.write_mod(tmp_path / "w.rnworld-mod", RECORD, _atlas_files(), bundle, mod)
    found = worldfile.read(path)
    assert found.kind == "mod"
    assert found.record == RECORD
    assert any(name.startswith("mod/") for name in found.files)
    assert worldfile.read_bundle(path) == bundle
    target = tmp_path / "out" / "rnw_exp_world_abcdefghij"
    again = worldfile.extract_mod(path, target)
    assert again.record == RECORD
    for relative in worldfile.mod_files(mod):
        assert (target / relative).read_bytes() == (mod / relative).read_bytes()
    with pytest.raises(WorldFileError, match="no mod"):
        _ = worldfile.extract_mod(
            worldfile.write(tmp_path / "c.rnworld", RECORD, None), tmp_path / "never"
        )


def test_a_mod_with_a_program_or_a_damaged_file_is_refused_and_leaves_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Executables are refused going out and coming in; a changed byte, a stray file, the limits."""
    mod = _mod(tmp_path / "src")
    bundle = {"manifest.json": b"{}", "inputs.json": b"{}"}
    _ = (mod / "tool.exe").write_bytes(b"MZ")
    with pytest.raises(WorldFileError, match="refuses"):
        _ = worldfile.write_mod(tmp_path / "x.rnworld-mod", RECORD, None, bundle, mod)
    (mod / "tool.exe").unlink()
    path = worldfile.write_mod(tmp_path / "w.rnworld-mod", RECORD, None, bundle, mod)

    def rewrite(change: dict[str, bytes | None], name: str) -> Path:
        out = tmp_path / name
        with zipfile.ZipFile(path) as source, zipfile.ZipFile(out, "w") as sink:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename in change:
                    replacement = change.pop(info.filename)
                    if replacement is None:
                        continue
                    data = replacement
                sink.writestr(info.filename, data)
            for extra, content in change.items():
                assert content is not None
                sink.writestr(extra, content)
        return out

    flipped = rewrite({"mod/in_game/map_data/x.txt": b"y"}, "flipped.rnworld-mod")
    target = tmp_path / "t1"
    with pytest.raises(WorldFileError, match="damaged"):
        _ = worldfile.extract_mod(flipped, target)
    assert not target.exists()
    program = rewrite({"mod/in_game/run.exe": b"MZ"}, "program.rnworld-mod")
    with pytest.raises(WorldFileError, match=r"does not|refuses|differ"):
        _ = worldfile.extract_mod(program, tmp_path / "t2")
    assert not (tmp_path / "t2").exists()
    missing = rewrite({"mod/in_game/map_data/x.txt": None}, "missing.rnworld-mod")
    with pytest.raises(WorldFileError, match="differ from the listing"):
        _ = worldfile.extract_mod(missing, tmp_path / "t3")
    monkeypatch.setattr(worldfile, "MOD_FILES", 1)
    with pytest.raises(WorldFileError, match="at most"):
        _ = worldfile.extract_mod(path, tmp_path / "t4")
    assert not (tmp_path / "t4").exists()
    monkeypatch.undo()
    monkeypatch.setattr(worldfile, "MOD_FILE_LIMIT", 1)
    with pytest.raises(WorldFileError, match=r"larger than|more than"):
        _ = worldfile.extract_mod(path, tmp_path / "t5")
    assert not (tmp_path / "t5").exists()
