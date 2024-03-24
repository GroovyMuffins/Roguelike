"""Tile class"""

from dataclasses import dataclass


@dataclass
class Tile:
    """A tile of the map and its properties"""

    blocked: bool
    block_sight: bool | None = None
    explored: bool = False

    def __post_init__(self):
        self.block_sight = self.blocked if self.block_sight is None else self.block_sight
