"""World codes: a seed, a preset and any changed settings as one short text to copy and paste.

``RNW1-`` and groups of five characters of Crockford base32. The payload is binary: a
format byte, the preset, the 64-bit seed, the generator version and, only when the player
changed settings, the changes (zlib-packed canonical JSON); then three bytes of SHA-256
as a check. A default world is 17 bytes, 28 characters. Reading is forgiving about case,
spaces, dashes and the letters Crockford folds together (O is 0, I and L are 1).
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import struct
import zlib
from dataclasses import dataclass
from typing import Final, cast

from rnw import __version__
from rnw.rng import check_seed
from rnw.settings import PRESETS, SettingsError, build_settings

PREFIX: Final[str] = "RNW1"
FORMAT: Final[int] = 1
ALPHABET: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
FOLDED: Final[dict[str, str]] = {"O": "0", "I": "1", "L": "1"}
GROUP: Final[int] = 5
CHECK_BYTES: Final[int] = 3
HAS_CHANGES: Final[int] = 1
PRESET_IDS: Final[dict[str, int]] = {"continents": 1, "archipelago": 2}
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


def encode(code: WorldCode) -> str:
    """The text of a code, with its prefix and groups."""
    preset = PRESET_IDS.get(code.preset)
    if preset is None:
        message = f"Unknown preset {code.preset!r}"
        raise WorldCodeError(message)
    major, minor, patch = _generator_parts(code.generator)
    flags = HAS_CHANGES if code.changes else 0
    body = HEAD.pack(FORMAT, preset, code.seed, major, minor, patch, flags)
    if code.changes:
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
        message = f"A world code starts with {PREFIX}"
        raise WorldCodeError(message)
    body = _from_base32(cleaned[len(PREFIX) :])
    if len(body) < HEAD.size + CHECK_BYTES:
        message = "The world code is too short"
        raise WorldCodeError(message)
    payload, check = body[:-CHECK_BYTES], body[-CHECK_BYTES:]
    if hashlib.sha256(payload).digest()[:CHECK_BYTES] != check:
        message = "The world code has a typing mistake (its check does not match)"
        raise WorldCodeError(message)
    version, preset, seed, major, minor, patch, flags = cast(
        "tuple[int, int, int, int, int, int, int]", HEAD.unpack_from(payload)
    )
    names = {number: name for name, number in PRESET_IDS.items()}
    if version != FORMAT or preset not in names:
        message = "This world code is from a newer or different generator format"
        raise WorldCodeError(message)
    changes: dict[str, object] | None = None
    rest = payload[HEAD.size :]
    if flags & HAS_CHANGES:
        try:
            (length,) = struct.unpack_from(">H", rest)
            raw = zlib.decompress(rest[2 : 2 + length])
            parsed = cast("object", json.loads(raw))
        except (struct.error, zlib.error, ValueError) as error:
            message = "The changed settings in the world code are damaged"
            raise WorldCodeError(message) from error
        if not isinstance(parsed, dict):
            message = "The changed settings in the world code are damaged"
            raise WorldCodeError(message)
        changes = cast("dict[str, object]", parsed)
    elif rest:
        message = "The world code has extra data"
        raise WorldCodeError(message)
    return WorldCode(names[preset], seed, f"{major}.{minor}.{patch}", changes)


def reproduces(code: WorldCode) -> bool:
    """Whether this generator makes the world of ``code`` (only the same version promises it)."""
    return code.generator == __version__


def _to_base32(data: bytes) -> str:
    number = int.from_bytes(data, "big")
    bits = len(data) * 8
    digits = -(-bits // 5)
    number <<= digits * 5 - bits
    return "".join(ALPHABET[(number >> (5 * place)) & 31] for place in range(digits - 1, -1, -1))


def _from_base32(digits: str) -> bytes:
    if not digits or any(char not in ALPHABET for char in digits):
        message = "The world code has characters that cannot be part of one"
        raise WorldCodeError(message)
    bits = len(digits) * 5
    number = 0
    for char in digits:
        number = (number << 5) | ALPHABET.index(char)
    size = bits // 8
    number >>= bits - size * 8
    return number.to_bytes(size, "big")
