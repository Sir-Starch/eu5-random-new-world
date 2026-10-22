"""The commands that do what the window does with the worlds of the library, for scripts and for
players who do not use the window (ADR 0010, D).

Every action of the window on a world has a command here (list, show, rename, reveal, add to the
game, remove, delete, copy the mod, save a map, search the atlas, the settings), beside the ones
in ``rnw.cli`` that make, check, move and reroll worlds.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Final

import typer

from rnw import atlas, landmask, worldname
from rnw.app import (
    candidates as continent_candidates,
)
from rnw.app import (
    discovery,
    exchange,
    library,
    logs,
    paths,
    preferences,
    service,
)
from rnw.app.discovery import GameInstall, Profile
from rnw.app.install import InstallError
from rnw.app.worldcode import decode, encode, new_code, with_new_seed
from rnw.png import COLOR_RGB, encode_png
from rnw.progress import Cancelled, Progress

if TYPE_CHECKING:
    from rnw.app.library import World

FAILURES: Final[tuple[type[Exception], ...]] = (
    Cancelled,
    exchange.ExchangeError,
    InstallError,
    OSError,
    ValueError,
)
DataDirOption = Annotated[
    Path | None, typer.Option(file_okay=False, help="Default: the application's folder.")
]
GameDirOption = Annotated[
    Path | None, typer.Option(exists=True, file_okay=False, help="Default: search Steam.")
]


def _data(data_dir: Path | None) -> Path:
    data = data_dir or paths.data_directory()
    logs.start(data)
    return data


def _world(data: Path, identifier: str) -> World:
    default = preferences.load(data).show_new_world
    for item in library.migrate_visibility(data, default=default):
        if identifier in {item.id, item.code, item.folder}:
            return item
    message = f"No world {identifier!r} in the library at {data}"
    raise typer.BadParameter(message)


def _game(game_dir: Path | None) -> GameInstall:
    games = discovery.find_games()
    if game_dir is not None:
        return discovery.game_beside(game_dir) or GameInstall(game_dir, None, "")
    if not games:
        message = "No EU5 installation found; pass --game-dir"
        raise typer.BadParameter(message)
    return games[0]


def _profile() -> discovery.Profile:
    profiles = discovery.find_profiles(games=discovery.find_games())
    if not profiles:
        message = "No EU5 profile found, so nothing can be added to or removed from the game"
        raise typer.BadParameter(message)
    return profiles[0]


def _fail(error: Exception) -> typer.Exit:
    typer.echo(f"Error: {error}", err=True)
    return typer.Exit(code=2)


def _row(data: Path, world: World, profile: Path | None) -> dict[str, object]:
    return {
        "id": world.id,
        "name": worldname.display_name(world.preset, worldname.tag_of(world.id), world.name),
        "title": worldname.label(world.preset, worldname.tag_of(world.id), world.name).title,
        "tag": worldname.tag_of(world.id),
        "code": world.code,
        "preset": world.preset,
        "seed": world.seed,
        "generator": world.generator,
        "game_build": world.game_build,
        "place": library.placement(data, profile, world).value,
        "revealed": world.revealed,
        "show_new_world": library.world_shown(world, default=preferences.load(data).show_new_world),
        "notes": world.notes,
        "starred": world.starred,
        "user_tag": world.user_tag,
        "parent": world.parent or None,
        "part": world.part or None,
        "has_record": world.record is not None,
        "has_atlas": library.atlas(data, world) is not None,
    }


def worlds(*, data_dir: DataDirOption = None) -> None:
    """List the worlds of the library, newest continents first, with where each one is."""
    data = _data(data_dir)
    profiles = discovery.find_profiles(games=discovery.find_games())
    profile = profiles[0].directory if profiles else None
    rows = [_row(data, world, profile) for world, _depth in library.grouped(library.load(data))]
    typer.echo(json.dumps(rows, indent=2))


def show_world(
    world_id: Annotated[str, typer.Argument(help="The id, folder or code of a world.")],
    *,
    data_dir: DataDirOption = None,
) -> None:
    """Show one world: its facts and, if its maps are revealed, what its atlas counts."""
    data = _data(data_dir)
    world = _world(data, world_id)
    profiles = discovery.find_profiles(games=discovery.find_games())
    row = _row(data, world, profiles[0].directory if profiles else None)
    found = library.atlas(data, world)
    shown = world.revealed or library.world_shown(
        world, default=preferences.load(data).show_new_world
    )
    row["atlas"] = atlas.totals(found) if found is not None and shown else None
    typer.echo(json.dumps(row, indent=2))


def rename_world(
    world_id: Annotated[str, typer.Argument(help="The id, folder or code of a world.")],
    name: Annotated[str, typer.Argument(help="The new name; blank for the default.")],
    *,
    data_dir: DataDirOption = None,
) -> None:
    """Name a world, in the library and in its mod's title in the game's list."""
    data = _data(data_dir)
    world = _world(data, world_id)
    profiles = discovery.find_profiles(games=discovery.find_games())
    renamed = library.rename(data, world, name)
    mods = (
        library.installed(profiles[0].directory if profiles else None, renamed),
        library.kept(data, renamed),
    )
    held = [mod for mod in mods if mod is not None and not library.retitle(renamed, mod)]
    typer.echo(
        json.dumps(
            {
                "name": worldname.display_name(
                    renamed.preset, worldname.tag_of(renamed.id), renamed.name
                ),
                "in_game_list_updated": not held,
            },
            indent=2,
        )
    )


def reveal_world(
    world_id: Annotated[str, typer.Argument(help="The id, folder or code of a world.")],
    *,
    cover: Annotated[bool, typer.Option(help="Cover the world again instead.")] = False,
    data_dir: DataDirOption = None,
) -> None:
    """Show a world's maps in the generator (or cover it again). The game is not touched."""
    data = _data(data_dir)
    changed = library.reveal(data, _world(data, world_id), revealed=not cover)
    typer.echo(json.dumps({"id": changed.id, "revealed": changed.revealed}))


def settings(
    show_new_world: Annotated[
        bool | None,
        typer.Option(
            "--show-new-world/--hide-new-world",
            help="Set the default visibility for newly made worlds.",
        ),
    ] = None,
    *,
    data_dir: DataDirOption = None,
) -> None:
    """Print the generator's settings, or change one."""
    data = _data(data_dir)
    current = preferences.load(data)
    if show_new_world is not None:
        _ = library.migrate_visibility(data, default=current.show_new_world)
        current = replace(current, show_new_world=show_new_world)
        preferences.save(data, current)
    typer.echo(json.dumps({"show_new_world": current.show_new_world}))


def world_visibility(
    world_id: Annotated[str, typer.Argument(help="The id, folder or code of a world.")],
    *,
    show_new_world: Annotated[
        bool, typer.Option("--show-new-world/--hide-new-world", help="Show this world's New World.")
    ],
    data_dir: DataDirOption = None,
) -> None:
    """Change one world's game-list picture and country-selection cover."""
    data = _data(data_dir)
    world = _world(data, world_id)
    changed = replace(world, show_new_world=show_new_world)
    selected_profile = preferences.load(data).profile_dir
    saved_directory = Path(selected_profile) if selected_profile else None
    if saved_directory is not None and saved_directory.is_dir():
        profile = Profile(saved_directory, "chosen", (saved_directory / "mod").is_dir())
    else:
        profile = next(iter(discovery.find_profiles(games=discovery.find_games())), None)
    mods = (
        library.installed(profile.directory if profile is not None else None, world),
        library.kept(data, world),
    )
    try:
        for mod in mods:
            if mod is not None:
                library.show(data, changed, mod, shown=show_new_world)
        library.save(data, changed)
    except (OSError, ValueError) as error:
        raise _fail(error) from error
    typer.echo(json.dumps({"id": changed.id, "show_new_world": show_new_world}))


def add_world(
    world_id: Annotated[str, typer.Argument(help="The id, folder or code of a world.")],
    *,
    game_dir: GameDirOption = None,
    data_dir: DataDirOption = None,
) -> None:
    """Add a world to the game: its kept mod, or the world made again from its code."""
    data = _data(data_dir)
    world = _world(data, world_id)
    try:
        result = service.add_to_game(
            world,
            game=_game(game_dir),
            data=data,
            profile=_profile(),
            progress=Progress(),
            show_new_world=world.show_new_world,
        )
    except FAILURES as error:
        raise _fail(error) from error
    typer.echo(json.dumps({"world": result.world.id, "installed": str(result.installed)}))


def remove_world(
    world_id: Annotated[str, typer.Argument(help="The id, folder or code of a world.")],
    *,
    data_dir: DataDirOption = None,
) -> None:
    """Take a world's mod out of the game; the world stays in the library as its code."""
    data = _data(data_dir)
    world = _world(data, world_id)
    try:
        service.remove_from_game(world.folder, _profile())
    except FAILURES as error:
        raise _fail(error) from error
    typer.echo(json.dumps({"removed": world.id}))


def delete_world(
    world_id: Annotated[str, typer.Argument(help="The id, folder or code of a world.")],
    *,
    data_dir: DataDirOption = None,
) -> None:
    """Take a world out of the game if it is there and forget it, its kept mod included."""
    data = _data(data_dir)
    world = _world(data, world_id)
    profiles = discovery.find_profiles(games=discovery.find_games())
    try:
        service.delete(world, data, profiles[0] if profiles else None)
    except FAILURES as error:
        raise _fail(error) from error
    typer.echo(json.dumps({"deleted": world.id}))


def copy_mod(
    world_id: Annotated[str, typer.Argument(help="The id, folder or code of a world.")],
    destination: Annotated[Path, typer.Argument(file_okay=False, help="An existing folder.")],
    *,
    data_dir: DataDirOption = None,
) -> None:
    """Copy a world's mod into a folder of your choice; nothing there is replaced."""
    data = _data(data_dir)
    world = _world(data, world_id)
    profiles = discovery.find_profiles(games=discovery.find_games())
    mod = library.installed(profiles[0].directory if profiles else None, world) or library.kept(
        data, world
    )
    if mod is None:
        typer.echo("Error: the world has no mod here (in the game or kept) to copy", err=True)
        raise typer.Exit(code=2)
    try:
        copied = exchange.copy_mod(mod, destination)
    except FAILURES as error:
        raise _fail(error) from error
    typer.echo(f"Copied to {copied}")


def draw_map(
    world_id: Annotated[str, typer.Argument(help="The id, folder or code of a world.")],
    layer: Annotated[str, typer.Argument(help=f"One of: {', '.join(atlas.LAYERS)}.")],
    output: Annotated[Path, typer.Argument(dir_okay=False, help="The PNG to write.")],
    *,
    reveal: Annotated[
        bool, typer.Option(help="Draw it although the world is covered (a spoiler).")
    ] = False,
    data_dir: DataDirOption = None,
) -> None:
    """Draw a layer of a world's atlas as a PNG; a covered world needs ``--reveal``."""
    data = _data(data_dir)
    world = _world(data, world_id)
    found = library.atlas(data, world)
    if found is None:
        typer.echo("Error: this world has no atlas", err=True)
        raise typer.Exit(code=2)
    if not (
        reveal
        or world.revealed
        or library.world_shown(world, default=preferences.load(data).show_new_world)
    ):
        typer.echo("Error: this world is covered; pass --reveal to see it", err=True)
        raise typer.Exit(code=2)
    try:
        picture = atlas.render(found, layer)
        output.parent.mkdir(parents=True, exist_ok=True)
        _ = output.write_bytes(encode_png(picture, color_type=COLOR_RGB, compression="zlib"))
    except (atlas.AtlasError, OSError) as error:
        raise _fail(error) from error
    typer.echo(f"Wrote {output}")


def search_atlas(
    world_id: Annotated[str, typer.Argument(help="The id, folder or code of a world.")],
    query: Annotated[str, typer.Argument(help="A name, or part of one.")],
    *,
    reveal: Annotated[bool, typer.Option(help="Search although the world is covered.")] = False,
    data_dir: DataDirOption = None,
) -> None:
    """Find a country, culture, religion, resource or place in a world's atlas."""
    data = _data(data_dir)
    world = _world(data, world_id)
    found = library.atlas(data, world)
    if found is None:
        typer.echo("Error: this world has no atlas", err=True)
        raise typer.Exit(code=2)
    if not (
        reveal
        or world.revealed
        or library.world_shown(world, default=preferences.load(data).show_new_world)
    ):
        typer.echo("Error: this world is covered; pass --reveal to search it", err=True)
        raise typer.Exit(code=2)
    rows = [
        {"kind": match.kind, "name": match.label, "locations": len(match.cells)}
        for match in atlas.find(found, query)
    ]
    typer.echo(json.dumps(rows, indent=2))


def land_template(
    output: Annotated[Path, typer.Argument(dir_okay=False, help="The PNG to write.")],
    *,
    game_dir: GameDirOption = None,
) -> None:
    """Write a picture of the area the New World can fill, to draw your own land on.

    Paint land in white over the dark area (any program), then make the world with the picture:
    ``rnw world-code --land-image FILE`` and ``rnw world CODE --land-image FILE``. The template
    is cut from your installed game's map and is for your own use.
    """
    try:
        width, height = service.land_template(_game(game_dir), output)
    except FAILURES as error:
        raise _fail(error) from error
    typer.echo(json.dumps({"written": str(output), "width": width, "height": height}))


def land_image(
    file: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="A picture of land.")],
) -> None:
    """Check a picture of land and sea (white is land): its size, share of land and id."""
    try:
        found = landmask.read(file)
    except landmask.LandMaskError as error:
        raise _fail(error) from error
    height, width = found.size
    typer.echo(
        json.dumps({"id": found.id, "width": width, "height": height, "land_permille": found.share})
    )


def annotate_world(
    world_id: Annotated[str, typer.Argument()],
    *,
    notes: Annotated[str, typer.Option()] = "",
    tag: Annotated[str, typer.Option()] = "",
    starred: Annotated[bool, typer.Option()] = False,
    data_dir: DataDirOption = None,
) -> None:
    data = _data(data_dir)
    found = _world(data, world_id)
    library.save(data, replace(found, notes=notes[:16384], user_tag=tag[:64], starred=starred))
    typer.echo(found.id)


def undo_roll(
    world_id: Annotated[str, typer.Argument()],
    *,
    game_dir: GameDirOption = None,
    data_dir: DataDirOption = None,
) -> None:
    data = _data(data_dir)
    world = _world(data, world_id)
    if not world.parent:
        message = "This world has no previous roll"
        raise typer.BadParameter(message)
    parent = _world(data, world.parent)
    try:
        profiles = discovery.find_profiles(games=discovery.find_games())
        profile = profiles[0] if profiles else None
        if profile is not None and library.installed(profile.directory, world) is not None:
            _ = service.undo_roll(
                world,
                parent,
                game=_game(game_dir),
                profile=profile,
                data=data,
                show_new_world=library.world_shown(
                    _world(data, world.parent), default=preferences.load(data).show_new_world
                ),
            )
    except FAILURES as error:
        raise _fail(error) from error
    typer.echo(parent.id)


def candidates(
    output: Annotated[Path, typer.Argument(dir_okay=False, help="Contact sheet PNG to write.")],
    *,
    code: Annotated[str | None, typer.Option(help="Settings of this code; fresh seeds.")] = None,
    count: Annotated[int, typer.Option(min=1, max=12)] = 6,
    game_dir: GameDirOption = None,
) -> None:
    try:
        base = decode(code) if code else new_code("continents", 0)
        found = continent_candidates.sketch(
            _game(game_dir).directory, base.settings(), continent_candidates.roll(count)
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        _ = output.write_bytes(
            encode_png(
                continent_candidates.contact_sheet(found), color_type=COLOR_RGB, compression="zlib"
            )
        )
    except FAILURES as error:
        raise _fail(error) from error
    typer.echo(
        json.dumps(
            [
                {
                    "number": number,
                    "seed": item.seed,
                    "code": encode(with_new_seed(base, item.seed)),
                }
                for number, item in enumerate(found, start=1)
            ],
            indent=2,
        )
    )


def generate_queue(
    codes_file: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    *,
    game_dir: GameDirOption = None,
    data_dir: DataDirOption = None,
) -> None:
    try:
        codes = [
            decode(line)
            for line in codes_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        game, data = _game(game_dir), _data(data_dir)
        for code in codes:
            result = service.generate(
                service.Request(
                    game=game,
                    code=code,
                    data=data,
                    install=False,
                    show_new_world=preferences.load(data).show_new_world,
                )
            )
            typer.echo(result.world.id)
    except FAILURES as error:
        raise _fail(error) from error


def register(app: typer.Typer) -> None:
    """Add these commands to the application."""
    for function in (
        worlds,
        show_world,
        rename_world,
        reveal_world,
        settings,
        world_visibility,
        add_world,
        remove_world,
        delete_world,
        copy_mod,
        draw_map,
        search_atlas,
        land_template,
        land_image,
        annotate_world,
        candidates,
        generate_queue,
        undo_roll,
    ):
        _ = app.command()(function)
