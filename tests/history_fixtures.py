"""Synthetic history geographies; scripted choices still use every production prerequisite."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rnw.history_engine import create, simulate
from rnw.history_model import (
    Action,
    Authority,
    Cohort,
    District,
    Founding,
    Geography,
    History,
    Partition,
    Proposal,
    Route,
    Tenure,
)

if TYPE_CHECKING:
    from rnw.history_actions import Context


def valley() -> History:
    places = tuple(
        District(
            key,
            "valley",
            Tenure.LAND,
            (Cohort("valley_people", "river_faith", amount, amount // 2),),
            sacred=key == "d1",
        )
        for key, amount in (
            ("u0", 1000),
            ("u1", 1000),
            ("m0", 1000),
            ("m1", 1000),
            ("d0", 8000),
            ("d1", 1000),
        )
    )
    geography = Geography(
        places,
        tuple(
            Route(first, second)
            for first, second in (
                ("u0", "u1"),
                ("u1", "m0"),
                ("m0", "m1"),
                ("m1", "d0"),
                ("d0", "d1"),
                ("u1", "d0"),
            )
        ),
    )
    foundings = (
        Founding("upstream", Tenure.LAND, ("u0", "u1"), "u0", Authority.CUSTOMARY),
        Founding("middle", Tenure.LAND, ("m0", "m1"), "m0", Authority.SACRED),
        Founding("downstream", Tenure.LAND, ("d0", "d1"), "d0", Authority.RULER),
    )
    return create(geography, foundings, seed=42)


def valley_policy(context: Context) -> tuple[Proposal, ...]:  # noqa: PLR0911 - dated fixture choices
    year = context.state.year
    if year == 1037:
        return tuple(
            Proposal(Action.CONTACT, one, other)
            for one, other in (
                ("upstream", "middle"),
                ("middle", "downstream"),
                ("upstream", "downstream"),
            )
        )
    if year in (1042, 1057, 1072):
        return tuple(
            Proposal(Action.EXCHANGE, one, other)
            for one, other in (
                ("upstream", "middle"),
                ("middle", "downstream"),
                ("upstream", "downstream"),
            )
        )
    if year == 1087:
        return (Proposal(Action.UNION, "upstream", "middle"),)
    living = [actor for actor in context.state.actors if actor.living]
    if year in (1102, 1112):
        union = next(actor.key for actor in living if actor.parents)
        return (Proposal(Action.EXCHANGE if year == 1102 else Action.UNION, union, "downstream"),)
    if year == 1227:
        return (
            Proposal(
                Action.SEPARATION,
                living[0].key,
                partitions=(
                    Partition(("u0", "u1"), "u0", Authority.CUSTOMARY),
                    Partition(("m0", "m1"), "m0", Authority.SACRED),
                    Partition(("d0", "d1"), "d0", Authority.RULER),
                ),
            ),
        )
    by_seat = {actor.seat: actor.key for actor in living}
    if year == 1282:
        return (Proposal(Action.CONFLICT, by_seat["d0"], by_seat["u0"], ("u1",)),)
    if year == 1317:
        return (Proposal(Action.ACCESS, by_seat["m0"], by_seat["d0"], ("d1",)),)
    return ()


def divided_valley() -> History:
    return simulate(valley(), policy=valley_policy)
