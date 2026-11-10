"""The epochs a world can still be made by (the experimental features, ADR 0013)."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from rnw import __version__, epoch
from rnw.app.worldcode import new_code, reproduces
from rnw.eu5_nw_export import (
    NewWorldExportError,
    _require_algorithm,  # pyright: ignore[reportPrivateUsage]
)
from rnw.settings import build_settings, run_spec, spec_digest


def test_the_selectable_epochs_run_from_the_oldest_kept_to_the_current_one() -> None:
    assert epoch.selectable() == tuple(range(epoch.OLDEST_SELECTABLE, epoch.CURRENT + 1))
    assert epoch.available(experimental=False) == (epoch.CURRENT,)
    assert epoch.available(experimental=True) == epoch.selectable()


def test_every_selectable_epoch_but_the_current_has_its_frozen_reference_world() -> None:
    """The rule of ADR 0013: an epoch that stays selectable keeps the reference world that proves
    the old path still makes its bytes. A new epoch therefore needs the one before it frozen."""
    tests = Path(__file__).parent
    for number in epoch.selectable()[:-1]:
        document = cast(
            "dict[str, object]",
            json.loads((tests / f"golden_world_epoch{number}.json").read_text(encoding="utf-8")),
        )
        assert document["epoch"] == number
    current = cast(
        "dict[str, object]",
        json.loads((tests / "golden_world.json").read_text(encoding="utf-8")),
    )
    assert current["epoch"] == epoch.CURRENT


def test_a_switch_lies_inside_the_window_it_still_has_to_serve() -> None:
    """A switch at or below the oldest selectable epoch is dead code; one above the current is
    not yet true. Each epoch of a switch is also an epoch of the table."""
    for name, number in epoch.SWITCHES.items():
        assert epoch.OLDEST_SELECTABLE < number <= epoch.CURRENT, name
        assert epoch.epoch_of(epoch.first_release(number)) == number


def test_a_selectable_epoch_is_stamped_with_the_release_that_made_it() -> None:
    assert epoch.first_release(62) == "1.2.1"
    assert epoch.first_release(61) == "1.2.0"
    assert epoch.stamp_of(epoch.CURRENT) == __version__
    for number in epoch.selectable():
        assert epoch.epoch_of(epoch.stamp_of(number)) == number


@pytest.mark.parametrize("number", [0, epoch.OLDEST_SELECTABLE - 1, epoch.CURRENT + 1])
def test_an_epoch_outside_the_window_is_refused(number: int) -> None:
    with pytest.raises(epoch.EpochError):
        _ = epoch.require_selectable(number)
    with pytest.raises(epoch.EpochError):
        _ = epoch.stamp_of(number)


def test_an_epoch_that_does_not_exist_has_no_first_release() -> None:
    with pytest.raises(epoch.EpochError):
        _ = epoch.first_release(0)
    with pytest.raises(epoch.EpochError):
        _ = epoch.first_release(len(epoch.ALGORITHM_SINCE) + 1)


def test_a_code_of_an_older_epoch_is_reproduced_only_by_the_epochs_asked_to_make_it() -> None:
    older = replace(new_code("continents", 7), generator=epoch.stamp_of(epoch.OLDEST_SELECTABLE))
    assert not reproduces(older)
    assert not reproduces(older, (epoch.CURRENT,))
    assert reproduces(older, epoch.selectable())
    assert reproduces(new_code("continents", 7))
    before_epochs = replace(new_code("continents", 7), generator="0.1.0")
    assert not reproduces(before_epochs, epoch.selectable())


@pytest.mark.parametrize("number", [0, epoch.OLDEST_SELECTABLE - 1, epoch.CURRENT + 1])
def test_the_export_refuses_an_epoch_it_cannot_make_before_it_does_anything(number: int) -> None:
    settings = replace(build_settings("continents"), algorithm=number)
    with pytest.raises(NewWorldExportError, match="cannot be chosen"):
        _require_algorithm(settings)
    for allowed in epoch.selectable():
        _require_algorithm(replace(settings, algorithm=allowed))


def test_the_algorithm_is_no_setting_of_the_world() -> None:
    """A world made by an older epoch has the settings document, and so the digest of the
    settings, of any other; only the run specification names the epoch."""
    settings = build_settings("continents")
    older = replace(settings, algorithm=epoch.OLDEST_SELECTABLE)
    assert older.to_json_data() == settings.to_json_data()
    assert "algorithm" not in settings.to_json_data()
    assert run_spec(1, older)["algorithm"] == epoch.OLDEST_SELECTABLE
    assert run_spec(1, settings)["algorithm"] == epoch.CURRENT
    assert spec_digest(run_spec(1, older)) != spec_digest(run_spec(1, settings))
