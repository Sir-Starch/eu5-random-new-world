"""World codes: a seed, a preset and any changed settings as one short text to copy and paste.

``RNW1-`` and groups of five characters of Crockford base32. The payload is binary: a
format byte, the preset, the 64-bit seed, the generator version and, only when the player
changed settings, the changes; then three bytes of SHA-256 as a check. A default world is
17 bytes, 28 characters. Format 2 writes each change as the number of its field in
``CHANGE_FIELDS`` and its value as an unsigned LEB128, two or three bytes a change; format
1 (zlib-packed canonical JSON) stays readable and carries changes outside that list.
Reading is forgiving about case, spaces, dashes and the letters Crockford folds together
(O is 0, I and L are 1).
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import secrets
import struct
import zlib
from dataclasses import dataclass
from typing import Final, cast

from rnw import __version__
from rnw.epoch import CURRENT, epoch_of
from rnw.layers import PARTS, rolls_of
from rnw.messages import say
from rnw.rng import check_seed
from rnw.settings import PRESETS, SettingsError, build_settings

PREFIX: Final[str] = "RNW1"
FORMAT: Final[int] = 1
COMPACT: Final[int] = 2
# The fields a compact code can change, by number. Append only: a number, once given, names
# its field for good, or older codes would change their world.
CHANGE_FIELDS: Final[tuple[str, ...]] = (
    "new_world.land_permille",
    "new_world.feature_px",
    "new_world.octaves",
    "new_world.persistence_permille",
    "new_world.coast_margin_px",
    "new_world.min_island_px",
    "new_world.min_lake_px",
    "new_world.max_lake_px",
    "new_world.location_px",
    "new_world.sea_zone_px",
    "new_world.min_cell_px",
    "new_world.min_sea_cell_px",
    "new_world.wasteland_permille",
    "new_world.province_size",
    "new_world.ocean_band_px",
    "new_world.precious_permille",
    "natives.population_permille",
    "natives.hearths_per_10k",
    "natives.hearth_reach_steps",
    "natives.state_share_permille",
    "natives.state_locations",
    "natives.culture_locations",
    "natives.religion_locations",
    "natives.tribe_locations",
    "natives.organized_permille",
    "natives.state_spread_permille",
    "natives.empire_permille",
    "rolls.resources",
    "rolls.peoples",
    "mask.id",
)
FIELD_NUMBERS: Final[dict[str, int]] = {name: number for number, name in enumerate(CHANGE_FIELDS)}
ALPHABET: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
FOLDED: Final[dict[str, str]] = {"O": "0", "I": "1", "L": "1"}
GROUP: Final[int] = 5
CHECK_BYTES: Final[int] = 3
HAS_CHANGES: Final[int] = 1
PRESET_IDS: Final[dict[str, int]] = {
    "continents": 1,
    "archipelago": 2,
    "supercontinent": 3,
    "small_continents": 4,
    "islands": 5,
}
HEAD: Final[struct.Struct] = struct.Struct(">BBQBBBB")
SEPARATORS: Final[re.Pattern[str]] = re.compile(r"[\s\-_]+")


class WorldCodeError(ValueError):
    """Text that is not a world code, or one this generator cannot read."""


@dataclass(frozen=True, slots=True)
class WorldCode:
    """What reproduces a world: the preset, the seed, changed settings and the generator."""

    preset: str
    seed: int
    generator: str
    changes: dict[str, object] | None = None

    def settings(self):  # noqa: ANN201 - Settings is imported lazily by callers that need it
        """The settings this code stands for (the preset with its changes applied)."""
        return build_settings(self.preset, dict(self.changes) if self.changes else None)


def random_seed() -> int:
    """A fresh 64-bit seed from the system's secure source."""
    return secrets.randbits(64)


def _generator_parts(version: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if match is None or any(int(part) > 255 for part in match.groups()):  # noqa: PLR2004 - a byte
        message = f"The generator version {version!r} does not fit a world code"
        raise WorldCodeError(message)
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def new_code(
    preset: str, seed: int | None = None, changes: dict[str, object] | None = None
) -> WorldCode:
    """A code for this generator: a random seed unless one is given; presets are checked."""
    if preset not in PRESETS or preset not in PRESET_IDS:
        message = f"Unknown preset {preset!r}; choose one of {', '.join(sorted(PRESET_IDS))}"
        raise WorldCodeError(message)
    try:
        chosen = random_seed() if seed is None else check_seed(seed)
        if changes:
            _ = build_settings(preset, dict(changes))
    except (ValueError, SettingsError) as error:
        raise WorldCodeError(str(error)) from error
    return WorldCode(preset, chosen, __version__, dict(changes) if changes else None)


def rolled(code: WorldCode, part: str) -> WorldCode:
    """The code of the same world with ``part`` (``rnw.layers``) made again: its roll one higher.

    The land, and every other part, stay as they are; the generator is the one running now.
    """
    if part not in PARTS:
        message = f"Unknown part {part!r}; choose one of {', '.join(PARTS)}"
        raise WorldCodeError(message)
    changes = copy.deepcopy(code.changes) if code.changes else {}
    section = cast("dict[str, object]", changes.setdefault("rolls", {}))
    section[part] = rolls_of(code.settings())[part] + 1
    return _checked(code.preset, code.seed, changes)


def with_new_seed(code: WorldCode, seed: int | None = None) -> WorldCode:
    """The same settings on a new land: a new seed (random unless given), every roll back to 0."""
    changes = copy.deepcopy(code.changes) if code.changes else {}
    _ = changes.pop("rolls", None)
    return _checked(code.preset, random_seed() if seed is None else check_seed(seed), changes)


def _checked(preset: str, seed: int, changes: dict[str, object]) -> WorldCode:
    try:
        _ = build_settings(preset, changes)
    except (ValueError, SettingsError) as error:
        raise WorldCodeError(str(error)) from error
    return WorldCode(preset, seed, __version__, changes or None)


def encode(code: WorldCode) -> str:
    """The text of a code, with its prefix and groups."""
    preset = PRESET_IDS.get(code.preset)
    if preset is None:
        message = f"Unknown preset {code.preset!r}"
        raise WorldCodeError(message)
    major, minor, patch = _generator_parts(code.generator)
    flags = HAS_CHANGES if code.changes else 0
    compact = _compact(code.changes) if code.changes else None
    version = COMPACT if compact is not None else FORMAT
    body = HEAD.pack(version, preset, code.seed, major, minor, patch, flags)
    if compact is not None:
        body += compact
    elif code.changes:
        packed = zlib.compress(
            json.dumps(code.changes, sort_keys=True, separators=(",", ":")).encode(), 9
        )
        body += struct.pack(">H", len(packed)) + packed
    body += hashlib.sha256(body).digest()[:CHECK_BYTES]
    digits = _to_base32(body)
    groups = [digits[at : at + GROUP] for at in range(0, len(digits), GROUP)]
    return "-".join([PREFIX, *groups])


def decode(text: str) -> WorldCode:
    """The code in ``text``; raises ``WorldCodeError`` with the reason if it is not one."""
    cleaned = "".join(FOLDED.get(char, char) for char in SEPARATORS.sub("", text).upper())
    if not cleaned.startswith(PREFIX):
        message = say("code.prefix", prefix=PREFIX)
        raise WorldCodeError(message)
    body = _from_base32(cleaned[len(PREFIX) :])
    if len(body) < HEAD.size + CHECK_BYTES:
        message = say("code.short")
        raise WorldCodeError(message)
    payload, check = body[:-CHECK_BYTES], body[-CHECK_BYTES:]
    if hashlib.sha256(payload).digest()[:CHECK_BYTES] != check:
        message = say("code.typo")
        raise WorldCodeError(message)
    version, preset, seed, major, minor, patch, flags = cast(
        "tuple[int, int, int, int, int, int, int]", HEAD.unpack_from(payload)
    )
    names = {number: name for name, number in PRESET_IDS.items()}
    if version not in {FORMAT, COMPACT} or preset not in names:
        message = say("code.format")
        raise WorldCodeError(message)
    changes: dict[str, object] | None = None
    rest = payload[HEAD.size :]
    if flags & HAS_CHANGES and version == COMPACT:
        changes = _expand(rest)
    elif flags & HAS_CHANGES:
        try:
            (length,) = struct.unpack_from(">H", rest)
            raw = zlib.decompress(rest[2 : 2 + length])
            parsed = cast("object", json.loads(raw))
        except (struct.error, zlib.error, ValueError) as error:
            message = say("code.damaged")
            raise WorldCodeError(message) from error
        if not isinstance(parsed, dict):
            message = say("code.damaged")
            raise WorldCodeError(message)
        changes = cast("dict[str, object]", parsed)
    elif rest:
        message = say("code.extra")
        raise WorldCodeError(message)
    return WorldCode(names[preset], seed, f"{major}.{minor}.{patch}", changes)


def _leb128(value: int) -> bytes:
    out = bytearray()
    while True:
        byte, value = value & 0x7F, value >> 7
        out.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(out)


def _compact(changes: dict[str, object]) -> bytes | None:
    """Format 2 changes, or None when one of them has no number or no small integer."""
    items: list[tuple[int, int]] = []
    for section, fields in changes.items():
        if not isinstance(fields, dict):
            return None
        for field, value in cast("dict[str, object]", fields).items():
            number = FIELD_NUMBERS.get(f"{section}.{field}")
            if number is None or isinstance(value, bool) or not isinstance(value, int) or value < 0:
                return None
            items.append((number, value))
    if not items or len(items) > 255:  # noqa: PLR2004 - the count is one byte
        return None
    return bytes([len(items)]) + b"".join(
        bytes([number]) + _leb128(value) for number, value in sorted(items)
    )


def _expand(rest: bytes) -> dict[str, object]:
    """The changes of a format 2 code."""
    damaged = "The changed settings in the world code are damaged"
    if not rest:
        raise WorldCodeError(damaged)
    count, at = rest[0], 1
    document: dict[str, dict[str, int]] = {}
    for _ in range(count):
        if at >= len(rest) or rest[at] >= len(CHANGE_FIELDS):
            raise WorldCodeError(damaged)
        section, field = CHANGE_FIELDS[rest[at]].split(".", 1)
        at += 1
        value, shift = 0, 0
        while True:
            if at >= len(rest) or shift > 63:  # noqa: PLR2004 - a 64-bit value at most
                raise WorldCodeError(damaged)
            byte = rest[at]
            at += 1
            value |= (byte & 0x7F) << shift
            shift += 7
            if not byte & 0x80:
                break
        document.setdefault(section, {})[field] = value
    if at != len(rest):
        message = say("code.extra")
        raise WorldCodeError(message)
    return cast("dict[str, object]", document)


def format_of(text: str) -> int:
    """The format number of a world code (1: JSON changes, 2: compact), read without checks."""
    cleaned = "".join(FOLDED.get(char, char) for char in SEPARATORS.sub("", text).upper())
    body = _from_base32(cleaned.removeprefix(PREFIX))
    if not body:
        message = say("code.short")
        raise WorldCodeError(message)
    return body[0]


def reproduces(code: WorldCode) -> bool:
    """Whether this generator makes the world of ``code``: the release that made it and this one
    are of the same algorithm epoch (``rnw.epoch``); before the first epoch nothing is promised."""
    made = epoch_of(code.generator)
    return made != 0 and made == CURRENT


def _to_base32(data: bytes) -> str:
    number = int.from_bytes(data, "big")
    bits = len(data) * 8
    digits = -(-bits // 5)
    number <<= digits * 5 - bits
    return "".join(ALPHABET[(number >> (5 * place)) & 31] for place in range(digits - 1, -1, -1))


def _from_base32(digits: str) -> bytes:
    if not digits or any(char not in ALPHABET for char in digits):
        message = say("code.characters")
        raise WorldCodeError(message)
    bits = len(digits) * 5
    number = 0
    for char in digits:
        number = (number << 5) | ALPHABET.index(char)
    size = bits // 8
    number >>= bits - size * 8
    return number.to_bytes(size, "big")
