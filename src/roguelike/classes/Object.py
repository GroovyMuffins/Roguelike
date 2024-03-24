"""Object class."""

import math
from dataclasses import dataclass
from typing import Any

import tcod as libtcod
from tcod import libtcodpy

from ..support import variables as var
from ..support.common import is_blocked
from . import Item


@dataclass
class Object:
    """This is generic object: the player, a monster, an item, the stairs... It's always represented by a character on screen."""

    x: int
    y: int
    char: int
    name: str
    color: libtcodpy.Color
    blocks: bool = False
    always_visible: bool = False
    fighter: Any | None = None
    ai: Any | None = None
    item: Any | None = None
    equipment: Any | None = None
    level: int | None = None

    def __post_init__(self):
        if self.fighter:  # let the fighter component know who owns it
            self.fighter.owner = self

        if self.ai:  # let the AI component know who owns it
            self.ai.owner = self

        if self.item:  # let the Item component know who owns it
            self.item.owner = self

        if self.equipment:  # let the Equipment component know who owns it
            self.equipment.owner = self

            # there must be an Item component for the Equipment component to work properly
            self.item = Item()
            self.item.owner = self

    def move(self, dx: int, dy: int) -> None:
        """Move by the given amount, if the destination is not blocked."""
        if not is_blocked(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy

    def move_towards(self, target_x: int, target_y: int) -> None:
        """Vector from this object to the target, and distance."""
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx**2 + dy**2)

        # normalize it to length 1 (preserving direction), then round it and
        # convert to integer so the movement is restricted to the map grid
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))
        self.move(dx, dy)

    def distance_to(self, other: type["Object"]) -> float:
        """Return the distance to another object."""
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx**2 + dy**2)

    def distance(self, x: int, y: int) -> float:
        """Return the distance to some coordinates."""
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)

    def send_to_back(self) -> None:
        """Make this object be drawn first, so all others appear above it if they're in the same tile."""
        var.game_objects.remove(self)
        var.game_objects.insert(0, self)

    def draw(self) -> None:
        """Set the color and then draw the character that represents this object at its position."""
        if var.fov_map is None or var.CON is None:
            return
        # only show if it's visible to the player;
        # or it's set to "always visible" and on an explored tile
        if libtcod.map_is_in_fov(var.fov_map, self.x, self.y) or (
            self.always_visible and var.game_map[self.x][self.y].explored
        ):
            var.CON.default_fg = self.color
            libtcod.console_put_char(var.CON, self.x, self.y, self.char, libtcod.BKGND_NONE)

    def clear(self) -> None:
        """Erase the character that represents this object."""
        if var.CON is None:
            return
        libtcod.console_put_char(var.CON, self.x, self.y, " ", libtcod.BKGND_NONE)
