"""Original C486 physical contact and single-intermediary exchange calculation."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from rnw.history_model import Action

if TYPE_CHECKING:
    from rnw.history_context import Context


def unoptimized_contacts(self: Context) -> None:
    self.near = defaultdict(dict)
    self.land_near = defaultdict(set)
    self.sea_near = defaultdict(set)
    for number, route in enumerate(self.history.geography.routes):
        if number % 128 == 0:
            self.checkpoint()
        first, second = self.index.owner.get(route.first), self.index.owner.get(route.second)
        if (
            first
            and second
            and first != second
            and route.sea_steps <= (self.history.geography.rules.max_sea_steps)
        ):
            for one, other in ((first, second), (second, first)):
                self.near[one][other] = min(route.cost, self.near[one].get(other, route.cost))
                (self.sea_near if route.sea_steps else self.land_near)[one].add(other)
    self.reach = {key: dict(near) for key, near in self.near.items()}
    # Exchange supplies one intermediary, over verified physical contacts, not sea labels.
    for bond in self.state.bonds:
        if bond.kind is Action.EXCHANGE:
            for one, hub in ((bond.first, bond.second), (bond.second, bond.first)):
                if hub not in self.near.get(one, {}):
                    continue
                for other, cost in self.near.get(hub, {}).items():
                    if other != one:
                        distance = cost + self.near[one][hub]
                        current = self.reach.setdefault(one, {}).get(other, distance)
                        self.reach[one][other] = min(current, distance)
                        reverse = self.reach.setdefault(other, {}).get(one, distance)
                        self.reach[other][one] = min(reverse, distance)
