"""Enum with tcod colors."""

from dataclasses import dataclass


@dataclass
class Colors:
    """Enum with tcod colors."""

    BLACK = (0, 0, 0)
    RED = (255, 0, 0)
    DARKER_RED = (127, 0, 0)
    DARK_RED = (191, 0, 0)
    LIGHT_RED = (255, 63, 63)
    GREEN = (0, 255, 0)
    LIGHT_GREEN = (63, 255, 63)
    DARKER_GREEN = (0, 127, 0)
    ORANGE = (255, 127, 0)
    DARK_ORANGE = (191, 95, 0)
    GREY = (127, 127, 127)
    LIGHT_GREY = (159, 159, 159)
    WHITE = (255, 255, 255)
    SKY = (0, 191, 255)
    DARK_SKY = (0, 143, 191)
    DESATURATED_GREEN = (63, 127, 63)
    VIOLET = (127, 0, 255)
    LIGHT_VIOLET = (159, 63, 255)
    YELLOW = (255, 255, 0)
    LIGHT_YELLOW = (255, 255, 63)
    LIGHT_CYAN = (63, 255, 255)
    DARK_AMBER = (191, 143, 0)
    LIGHT_BLUE = (63, 63, 255)
    CRIMSON = (255, 0, 63)
