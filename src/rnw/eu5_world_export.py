"""The export of a world: generated geography, or the game's own with only its societies.

A world that keeps the real Americas (``new_world.keep_geography``, ADR 0012) and otherwise uses
the installed map is made by ``rnw.eu5_vanilla_export``. Worlds with any new geography use
``rnw.eu5_nw_export``. The application and the command line call this shared dispatcher.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rnw.eu5_nw_export import NewWorldExportError, export_new_world
from rnw.eu5_vanilla_export import export_vanilla_world

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from rnw.landmask import LandMask
    from rnw.progress import Progress
    from rnw.settings import Settings
    from rnw.worldname import Label


def export_world(  # noqa: PLR0913 - the CLI contract names each input.
    game_dir: Path,
    output: Path,
    *,
    seed: int,
    settings: Settings,
    accept_build: str | None = None,
    settings_file: str | None = None,
    replace: bool = False,
    check_memory: bool = True,
    progress: Progress | None = None,
    world_code: str | None = None,
    world_label: Label | None = None,
    land_mask: LandMask | None = None,
    regional_masks: Mapping[str, LandMask] | None = None,
    cache_dir: Path | None = None,
) -> dict[str, object]:
    """Generate, validate and stage one world's mod bundle; return its report."""
    keeps_america = settings.continents.america and bool(settings.new_world.keep_geography)
    if keeps_america and land_mask is not None:
        message = "A world that keeps the real Americas has no drawn land"
        raise NewWorldExportError(message)
    if keeps_america and not settings.continents.regions:
        return export_vanilla_world(
            game_dir,
            output,
            seed=seed,
            settings=settings,
            accept_build=accept_build,
            settings_file=settings_file,
            replace=replace,
            check_memory=check_memory,
            progress=progress,
            world_code=world_code,
            world_label=world_label,
            cache_dir=cache_dir,
        )
    return export_new_world(
        game_dir,
        output,
        seed=seed,
        settings=settings,
        accept_build=accept_build,
        settings_file=settings_file,
        replace=replace,
        check_memory=check_memory,
        progress=progress,
        world_code=world_code,
        world_label=world_label,
        land_mask=land_mask,
        regional_masks=regional_masks,
        cache_dir=cache_dir,
    )
