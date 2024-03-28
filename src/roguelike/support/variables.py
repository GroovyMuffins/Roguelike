"""Global variables for the game."""

from tcod import console, map

from ..classes.object import Object
from ..classes.tile import Tile

game_map: list[list[Tile]] = []
game_objects: list[Object] = []
player: Object | None = None
stairs: Object | None = None
inventory: list[Object] = []
game_msgs: list[tuple[str, tuple[int, int, int]]] = []
game_state: str | None = None
dungeon_level: int | None = None

fov_map: map.Map | None = None
fov_recompute: bool = True

CON: console.Console | None = None
panel: console.Console | None = None
