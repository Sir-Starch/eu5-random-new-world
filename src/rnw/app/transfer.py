"""Built worlds sent from one machine of the player's to another (ADR 0010, C, G3b).

``send_mod`` writes the mod's files with the world's record as a ``.rnworld-mod``. ``receive_mod``
takes one in as a mod kept beside the generator, and only if this game is the one the world was
made from, file by file, before it takes a single byte: a mod made for other files of the game
could be wrong in ways nothing would show. It reads the game (the map contract and the files the
world read), which is why it is not part of ``rnw.app.exchange``. The file holds rasters derived
from the game's map and is not for sharing (``docs/legal.md``).
"""

from __future__ import annotations

import json
import shutil
from dataclasses import replace
from typing import TYPE_CHECKING, cast

from rnw import inputs, worldfile
from rnw.app import exchange, install, library
from rnw.app.exchange import ExchangeError, Imported
from rnw.bundle import COVER_COPY
from rnw.contract import aggregate_digest, fingerprint
from rnw.parallel import cores
from rnw.record import Manifest

if TYPE_CHECKING:
    from pathlib import Path

    from rnw.app.discovery import GameInstall
    from rnw.app.library import World


def send_mod(data: Path, world: World, mod: Path, output: Path) -> Path:
    """Write the built world, its mod included, at ``output`` as a ``.rnworld-mod``; returns it.

    ``mod`` is the world's mod folder, in the game or beside the generator. The world's bundle
    (its list of files and of the game files it read) must still be in the library.
    """
    if not install.is_rnw_mod(mod):
        message = f"{mod} is not a mod of this project"
        raise ExchangeError(message)
    folder = library.folder(data, world)
    bundle: dict[str, bytes] = {}
    for name in worldfile.BUNDLE_FILES:
        source = folder / name
        if not source.is_file():
            message = f"The world's bundle no longer has {name}, so it cannot be transferred"
            raise ExchangeError(message)
        bundle[name] = source.read_bytes()
    cover = folder / COVER_COPY
    for source in sorted(cover.rglob("*")):
        if source.is_file():
            bundle[f"{COVER_COPY}/{source.relative_to(cover).as_posix()}"] = source.read_bytes()
    record = library.document(replace(world, revealed=False))
    image = folder / library.LAND_MASK
    drawn = image.read_bytes() if image.is_file() else None
    return worldfile.write_mod(
        output, record, exchange.atlas_files(data, world), bundle, mod, land_mask=drawn
    )


def receive_mod(data: Path, path: Path, game: GameInstall) -> Imported:
    """Take a transferred built world into the library as a mod kept beside the generator.

    Refused unless this game is the one the world was made from: the digest of the map contract
    and every game file the world read must be as the world recorded. Nothing is taken in before
    that is known; a file that fails any check leaves nothing behind.
    """
    found = worldfile.read(path)
    if found.kind != worldfile.KIND_MOD:
        message = "This file has no mod in it; open it as a world file"
        raise ExchangeError(message)
    world = exchange.checked_world(found.record)
    record = world.record
    if record is None:
        message = "The world was made before records were kept, so its game cannot be checked"
        raise ExchangeError(message)
    if found.atlas is not None:
        exchange.check_atlas(found.atlas)
    if found.land_mask is not None:
        exchange.check_land_mask(found.land_mask, world)
    bundle = worldfile.read_bundle(path)
    _same_game(game, record.game.fingerprint_sha256, bundle.get("inputs.json"))
    target = library.folder(data, world)
    final = target / world.folder
    if library.load_one(target) is not None or final.exists():
        message = "The library already has this world; delete it first to take this copy"
        raise ExchangeError(message)
    staged = target / f"{world.folder}.incoming"
    _ = worldfile.extract_mod(path, staged)
    if not install.is_rnw_mod(staged):
        shutil.rmtree(staged, ignore_errors=True)
        message = "The mod in the file is not a mod of this project"
        raise ExchangeError(message)
    _ = staged.rename(final)
    library.save(data, world)
    for name, content in bundle.items():
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        _ = destination.write_bytes(content)
    if found.atlas is not None:
        exchange.keep_atlas(target, found.atlas)
    if found.land_mask is not None:
        exchange.keep_land_mask(target, found.land_mask)
    exchange.draw_previews(target)
    return Imported(world, created=True)


def _same_game(game: GameInstall, fingerprint_sha256: str, listing: bytes | None) -> None:
    """Raise unless ``game`` is the one the world was made from."""
    local = aggregate_digest(fingerprint(game.directory))
    if local != fingerprint_sha256:
        message = (
            "This game is not the one the world was made from: the files of its map differ. "
            "Make the world again here from its code."
        )
        raise ExchangeError(message)
    if listing is None:
        message = "The file lists no game files, so this game cannot be checked against it"
        raise ExchangeError(message)
    manifest = Manifest.from_json(cast("object", json.loads(listing.decode("utf-8"))))
    found = inputs.compare(game.directory, manifest, workers=cores())
    if not found.same:
        names = [*found.missing, *found.changed][:5]
        message = (
            f"{len(found.missing) + len(found.changed)} game files the world read are not as "
            f"they were, for example {names}. Make the world again here from its code."
        )
        raise ExchangeError(message)
