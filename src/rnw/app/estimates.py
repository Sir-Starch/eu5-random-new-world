"""Bounded, local ETA training, separate from worlds and reproducibility records."""

from __future__ import annotations

import contextlib
import json
import math
import platform
import statistics
from typing import TYPE_CHECKING, Final, cast

from rnw import epoch
from rnw.app import logs
from rnw.eta import DEPENDENCIES
from rnw.parallel import stage_workers, thread_count

if TYPE_CHECKING:
    from pathlib import Path


FILE: Final[str] = "generation-times.json"
SAMPLES: Final[int] = 5
CONTEXTS: Final[int] = 16
# Change when the timing model or pipeline dependencies change, independently of world epochs.
SCHEMA: Final[int] = 1
MAX_SECONDS: Final[float] = 86400.0


def key(build: str, preset: str) -> str:
    """Avoid mixing presets, game inputs, platforms and parallelism limits."""
    return ":".join(
        str(value)
        for value in (
            SCHEMA,
            epoch.CURRENT,
            build,
            preset,
            platform.system(),
            platform.machine(),
            thread_count(),
            stage_workers(),
        )
    )


def _read(data: Path) -> dict[str, dict[str, list[float]]]:
    try:
        raw = cast("object", json.loads((data / FILE).read_text(encoding="utf-8")))
        if not isinstance(raw, dict):
            return {}
        result: dict[str, dict[str, list[float]]] = {}
        for context, stages in cast("dict[str, object]", raw).items():
            if not isinstance(stages, dict):
                continue
            valid: dict[str, list[float]] = {}
            for name, samples in cast("dict[str, object]", stages).items():
                if name not in DEPENDENCIES or not isinstance(samples, list):
                    continue
                values = [
                    float(value)
                    for value in cast("list[object]", samples)
                    if isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and 0 < float(value) < MAX_SECONDS
                    and math.isfinite(float(value))
                ]
                if values:
                    valid[name] = values[-SAMPLES:]
            result[context] = valid
        return dict(list(result.items())[-CONTEXTS:])
    except (OSError, ValueError):
        return {}


def load(data: Path, context: str) -> dict[str, float]:
    return {
        name: statistics.median(values) for name, values in _read(data).get(context, {}).items()
    }


def save(data: Path, context: str, costs: dict[str, float]) -> None:
    """Learn complete exports only. A cache hit must not teach that new terrain is free.

    Optional timing storage must never turn a successfully generated world into an error.
    The scratch file is replaced atomically, and lives only in the application's data.
    """
    if "write files" not in costs:
        return
    rows = _read(data)
    stages = rows.pop(context, {})
    for name, seconds in costs.items():
        if name == "generate world" and seconds < 1.0:
            continue
        stages[name] = [*stages.get(name, []), seconds][-SAMPLES:]
    rows[context] = stages
    scratch = data / f".{FILE}.new"
    try:
        data.mkdir(parents=True, exist_ok=True)
        _ = scratch.write_text(json.dumps(dict(list(rows.items())[-CONTEXTS:])), encoding="utf-8")
        _ = scratch.replace(data / FILE)
    except OSError as error:
        logs.get().warning("Could not save generation timings: %s", error)
    finally:
        with contextlib.suppress(OSError):
            scratch.unlink(missing_ok=True)
