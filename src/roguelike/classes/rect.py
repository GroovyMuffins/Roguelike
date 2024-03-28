"""Rect class."""

from dataclasses import dataclass


@dataclass
class Rect:
    """a rectangle on the map. used to characterize a room."""

    x1: int
    y1: int
    w: int
    h: int

    def __post_init__(self):
        """Set properties after initializaion."""
        self.x2 = self.x1 + self.w
        self.y2 = self.y1 + self.h

    def center(self):
        """Return center coordinates of the room."""
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        return (center_x, center_y)

    def intersect(self, other):
        """Returns true if this rectangle intersects wth another one."""
        return self.x1 <= other.x2 and self.x2 >= other.x1 and self.y1 <= other.y2 and self.y2 >= other.y1
