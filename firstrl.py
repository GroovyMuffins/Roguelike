#!/c/Python27/python
"""This module sets up initial rogue basin game."""
import libtcodpy as libtcod

#actual size of the window
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

#size of the map
MAP_WIDTH = 80
MAP_HEIGHT = 45
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30

LIMIT_FPS = 20 #20 frames-per-second maximum

COLOR_DARK_WALL = libtcod.Color(0, 0, 100)
COLOR_DARK_GROUND = libtcod.Color(50, 50, 150)


class Tile:
    """A tile of the map and its properties"""
    def __init__(self, blocked, block_sight=None):
        self.blocked = blocked

        #by default, if a tile is blocked, it also blocks sight
        if block_sight is None:
            block_sight = blocked
        self.block_sight = block_sight

class Rect:
    """a rectangle on the map. used to characterize a room."""
    def __init__(self, x_value, y_value, width, height):
        self.x_1 = x_value
        self.y_1 = y_value
        self.x_2 = x_value + width
        self.y_2 = y_value + height

    def center(self):
        """return center coordinates of the room"""
        center_x = (self.x_1 + self.x_2) / 2
        center_y = (self.y_1 + self.y_2) / 2
        return (center_x, center_y)

    def intersect(self, other):
        """returns true if this rectangle intersects wth another one"""
        return (self.x_1 <= other.x_2 and self.x_2 >= other.x_1 and
                self.y_1 <= other.y_2 and self.y_2 >= other.y_1)

class Object:
    """This is generic object: the player, a monster, an tiem, the stairs...
    it's always represented by a character on screen."""
    def __init__(self, x_value, y_value, char, color):
        self.x_value = x_value
        self.y_value = y_value
        self.char = char
        self.color = color

    def move(self, d_x, d_y):
        """move by the given amount, if the destination is not blocked"""
        if not GAME_MAP[self.x_value + d_x][self.y_value + d_y].blocked:
            self.x_value += d_x
            self.y_value += d_y

    def draw(self):
        """set the color and then draw the character that represents this object at its position"""
        libtcod.console_set_default_foreground(CON, self.color)
        libtcod.console_put_char(CON, self.x_value, self.y_value, self.char, libtcod.BKGND_NONE)

    def clear(self):
        """erase the character that represents this object"""
        libtcod.console_put_char(CON, self.x_value, self.y_value, ' ', libtcod.BKGND_NONE)


def create_room(room):
    """create room"""
    global GAME_MAP
    #go through the tiles in the rectangle and make them passable
    for x_value in range(room.x_1 + 1, room.x_2):
        for y_value in range(room.y_1 + 1, room.y_2):
            GAME_MAP[x_value][y_value].blocked = False
            GAME_MAP[x_value][y_value].block_sight = False

def create_h_tunnel(x_1, x_2, y_value):
    """create horizontal tunnel"""
    global GAME_MAP
    #min() and max() are used in case x1>x2
    for x_value in range(min(x_1, x_2), max(x_1, x_2) + 1):
        GAME_MAP[x_value][y_value].blocked = False
        GAME_MAP[x_value][y_value].block_sight = False

def create_v_tunnel(y_1, y_2, x_value):
    """create vertical tunnel"""
    global GAME_MAP
    for y_value in range(min(y_1, y_2), max(y_1, y_2) + 1):
        GAME_MAP[x_value][y_value].blocked = False
        GAME_MAP[x_value][y_value].block_sight = False

def make_map():
    """fill map with "unblocked" tiles"""
    global GAME_MAP, PLAYER

    GAME_MAP = [[Tile(True) for y in range(MAP_HEIGHT)] for x in range(MAP_WIDTH)]

    rooms = []
    num_rooms = 0
    for room in range(MAX_ROOMS):
        #random width and height
        width = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        height = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        #random position without going out of the boundaries of the map
        x_value = libtcod.random_get_int(0, 0, MAP_WIDTH - width - 1)
        y_value = libtcod.random_get_int(0, 0, MAP_HEIGHT - height - 1)

        #"Rect" class makes rectangles easier to work with
        new_room = Rect(x_value, y_value, width, height)

        #run through the other rooms and see if they intersect with this one
        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break
        
        if not failed:
            #this means there are no intersections, so this room is valid

            #"paint" it to the map's tiles
            create_room(new_room)

            #center coordinates of new room, will be useful later
            (new_x, new_y) = new_room.center()

            if num_rooms == 0:
                #this is the first room, where the player starts at
                PLAYER.x_value = new_x
                PLAYER.y_value = new_y

            else:
                #all rooms after the first:
                #connect it to the previous room with a tunnel

                #center coordinates of the previous room
                (prev_x, prev_y) = rooms[num_rooms - 1].center()

                #draw a coin (random number that is either 0 or 1)
                if libtcod.random_get_int(0, 0, 1) == 1:
                    #first move horizontally, then vertically
                    create_h_tunnel(prev_x, new_x, prev_y)
                    create_v_tunnel(prev_y, new_y, prev_x)
                else:
                    #first move vertically, then horizontally
                    create_v_tunnel(prev_y, new_y, prev_x)
                    create_h_tunnel(prev_x, new_x, prev_y)
            
            #finally, append the new room to the list
            rooms.append(new_room)
            num_rooms += 1

def render_all():
    """Draw all objects in the list"""
    global COLOR_DARK_WALL, COLOR_LIGHT_WALL
    global COLOR_DARK_GROUND, COLOR_LIGHT_GROUND

    #go through all tiles, and set their background color
    for y_value in range(MAP_HEIGHT):
        for x_value in range(MAP_WIDTH):
            wall = GAME_MAP[x_value][y_value].block_sight
            if wall:
                libtcod.console_set_char_background( \
                    CON, x_value, y_value, COLOR_DARK_WALL, libtcod.BKGND_SET)
            else:
                libtcod.console_set_char_background( \
                    CON, x_value, y_value, COLOR_DARK_GROUND, libtcod.BKGND_SET)

    #draw all objects in the list
    for g_object in GAME_OBJECTS:
        g_object.draw()

    #blit the contents of "con" to the root console
    libtcod.console_blit(CON, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)

def handle_keys():
    """Handle keyboard movement."""
    # key = libtcod.console_check_for_keypress() #real-time
    key = libtcod.console_wait_for_keypress(True) #turn-based

    if key.vk == libtcod.KEY_ENTER and key.lalt:
        #Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    elif key.vk == libtcod.KEY_ESCAPE:
        return True #exit game

    #movement keys
    if libtcod.console_is_key_pressed(libtcod.KEY_UP):
        PLAYER.move(0, -1)

    elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN):
        PLAYER.move(0, 1)

    elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT):
        PLAYER.move(-1, 0)

    elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT):
        PLAYER.move(1, 0)


#############################################
# Initialization & Main Loop
#############################################

libtcod.console_set_custom_font('arial10x10.png', \
    libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python/libtcod tutorial', False)
libtcod.sys_set_fps(LIMIT_FPS)
CON = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)

#create object representing player
PLAYER = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', libtcod.white)

#create an NPC
NPC = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', libtcod.yellow)

#the list of objects with those two
GAME_OBJECTS = [NPC, PLAYER]

#generate map (at this point it's not drawn to the screen)
make_map()

while not libtcod.console_is_window_closed():

    #render the screen
    render_all()

    libtcod.console_flush()

    #erase all objects at their old locations, before they move
    for g_object in GAME_OBJECTS:
        g_object.clear()

    #handle keys and exit game if needed
    EXIT = handle_keys()
    if EXIT:
        break
