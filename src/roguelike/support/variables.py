"""Global variables for the game."""

from tcod import console, map

from ..classes import Object, Tile

game_map: list[list[Tile.Tile]] = []
game_objects: list[Object.Object] = []
player: Object.Object | None = None
stairs: Object.Object | None = None
inventory: list[Object.Object] = []
game_msgs: list[tuple[str, tuple[int, int, int]]] = []
game_state: str | None = None
dungeon_level: int | None = None

fov_map: map.Map | None = None
fov_recompute: bool = True

CON: console.Console | None = None
panel: console.Console | None = None
