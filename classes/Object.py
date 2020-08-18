"""Object class"""
import tcod as libtcod
import math
import support.variables as var
from classes.Item import Item
from support.common import is_blocked

class Object:
    """This is generic object: the player, a monster, an item, the stairs...
    it's always represented by a character on screen."""
    def __init__(self, x, y, char, name, color, blocks=False,\
        always_visible=False, fighter=None, ai=None, item=None, equipment=None):
        self.x = x
        self.y = y
        self.char = char
        self.name = name
        self.color = color
        self.blocks = blocks
        self.always_visible = always_visible

        self.fighter = fighter
        if self.fighter: #let the fighter component know who owns it
            self.fighter.owner = self

        self.ai = ai
        if self.ai: #let the AI component know who owns it
            self.ai.owner = self

        self.item = item
        if self.item: #let the Item component know who owns it
            self.item.owner = self

        self.equipment = equipment
        if self.equipment: # let the Equipment component know who owns it
            self.equipment.owner = self

            # there must be and Item component for the Equipment component to work properly
            self.item = Item()
            self.item.owner = self

    def move(self, dx, dy):
        """move by the given amount, if the destination is not blocked"""
        if not is_blocked(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy

    def move_towards(self, target_x, target_y):
        """vector from this object to the target, and distance"""
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)

        #normalize it to length 1 (preserving direction), then round it and
        #convert to integer so the movement is restricted to the map grid
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))
        self.move(dx, dy)

    def distance_to(self, other):
        """return the distance to another object"""
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)

    def distance(self, x, y):
        """return the distance to some coordinates"""
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)

    def send_to_back(self):
        """make this object be drawn first,
        so all others appear above it if they're in the same tile."""
        var.game_objects.remove(self)
        var.game_objects.insert(0, self)

    def draw(self):
        """set the color and then draw the character that represents this object at its position"""
        #only show if it's visible to the player;
        #or it's set to "always visible" and on an explored tile
        if libtcod.map_is_in_fov(var.fov_map, self.x, self.y) or\
            (self.always_visible and var.game_map[self.x][self.y].explored):
            libtcod.console_set_default_foreground(var.CON, self.color)
            libtcod.console_put_char(var.CON, self.x, self.y, self.char, libtcod.BKGND_NONE)

    def clear(self):
        """erase the character that represents this object"""
        libtcod.console_put_char(var.CON, self.x, self.y, ' ', libtcod.BKGND_NONE)
