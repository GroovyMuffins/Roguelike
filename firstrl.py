#!/c/Python27/python
"""This module sets up initial rogue basin game."""
import libtcodpy as libtcod
import math

#actual size of the window
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

#size of the map
MAP_WIDTH = 80
MAP_HEIGHT = 45

#parameters for dungeon generator
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30
MAX_ROOM_MONSTERS = 3

FOV_ALGO = 0 #default FOV algorithm
FOV_LIGHT_WALLS = True #light walls or not
TORCH_RADIUS = 10

LIMIT_FPS = 20 #20 frames-per-second maximum

COLOR_DARK_WALL = libtcod.Color(0, 0, 100)
COLOR_LIGHT_WALL = libtcod.Color(130, 110, 50)
COLOR_DARK_GROUND = libtcod.Color(50, 50, 150)
COLOR_LIGHT_GROUND = libtcod.Color(200, 180, 50)


class Tile:
    """A tile of the map and its properties"""
    def __init__(self, blocked, block_sight=None):
        self.blocked = blocked

        #all tiles start unexplored
        self.explored = False

        #by default, if a tile is blocked, it also blocks sight
        if block_sight is None:
            block_sight = blocked
        self.block_sight = block_sight

class Rect:
    """a rectangle on the map. used to characterize a room."""
    def __init__(self, x, y, width, height):
        self.x1 = x
        self.y1 = y
        self.x2 = x + width
        self.y2 = y + height

    def center(self):
        """return center coordinates of the room"""
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        return (center_x, center_y)

    def intersect(self, other):
        """returns true if this rectangle intersects wth another one"""
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)

class Object:
    """This is generic object: the player, a monster, an tiem, the stairs...
    it's always represented by a character on screen."""
    def __init__(self, x, y, char, name, color, blocks=False, fighter=None, ai=None):
        self.x = x
        self.y = y
        self.name = name
        self.char = char
        self.color = color
        self.blocks = blocks

        self.fighter = fighter
        if self.fighter: #let the fighter component know who owns it
            self.fighter.owner = self
        
        self.ai = ai
        if self.ai: #let the AI component know who owns it
            self.ai.owner = self

    def move(self, dx, dy):
        """move by the given amount, if the destination is not blocked"""
        if not is_blocked(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy

    def move_towards(self, target_x, target_y):
        #vector from this object to the target, and distance
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)

        #normalize it to length 1 (preserving direction), then round it and
        #convert to integer so the movement is restricted to the map grid
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))
        self.move(dx, dy)

    def distance_to(self, other):
        #return the distance to another object
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)

    def send_to_back(self):
        #make this object be drawn first, so all others appear above it if they're in the same tile.
        global GAME_OBJECTS
        GAME_OBJECTS.remove(self)
        GAME_OBJECTS.insert(0, self)

    def draw(self):
        """set the color and then draw the character that represents this object at its position"""
        #only show if it's visible to the player
        if libtcod.map_is_in_fov(fov_map, self.x, self.y):
            libtcod.console_set_default_foreground(CON, self.color)
            libtcod.console_put_char(CON, self.x, self.y, self.char, libtcod.BKGND_NONE)

    def clear(self):
        """erase the character that represents this object"""
        libtcod.console_put_char(CON, self.x, self.y, ' ', libtcod.BKGND_NONE)

class Fighter:
    #combat-related properties and methods (monster, player, NPC)
    def __init__(self, hp, defense, power, death_function=None):
        self.max_hp = hp
        self.hp = hp
        self.defense = defense
        self.power = power
        self.death_function = death_function
    
    def take_damage(self, damage):
        #apply damage if possible
        if damage > 0:
            self.hp -= damage
        
        #check for death. if there's a death function, call it
        if self.hp <= 0:
            function = self.death_function
            if function is not None:
                function(self.owner)
    
    def attack(self, target):
        #a simple formula for attack damage
        damage = self.power + target.fighter.defense

        if damage > 0:
            #make the target take some damage
            print self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points.'
            target.fighter.take_damage(damage)
        else:
            print self.owner.name.capitalize() + ' attacks ' + target.name + ' but it has no effect!'

class BasicMonster:
    #AI for a basic monster.
    def take_turn(self):
        #a basic monster takes its turn. If you can see it, it can see you
        monster = self.owner
        if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):

            #move towards player if far away
            if monster.distance_to(PLAYER) >= 2:
                monster.move_towards(PLAYER.x, PLAYER.y)

            #close enough, attack! (if the player is still alive.)
            elif PLAYER.fighter.hp > 0:
                monster.fighter.attack(PLAYER)

def player_death(PLAYER):
    #the game ended!
    global game_state
    print 'You died!'
    game_state = 'dead'

    #for added effect, transform the player into a corpse!
    PLAYER.char = '%'
    PLAYER.color = libtcod.dark_red

def monster_death(monster):
    #transform it into a nasty corpse! it doesn't block, can't be
    # attacked and doesn't move
    print monster.name.capitalize() + ' is dead!'
    monster.char = '%'
    monster.color = libtcod.dark_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'remains of ' + monster.name
    monster.send_to_back()

def is_blocked(x, y):
    #first test the map tile
    if GAME_MAP[x][y].blocked:
        return True
    
    #now check for any blocking objects
    for g_object in GAME_OBJECTS:
        if g_object.blocks and g_object.x == x and g_object.y == y:
            return True
    
    return False

def create_room(room):
    """create room"""
    global GAME_MAP
    #go through the tiles in the rectangle and make them passable
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            GAME_MAP[x][y].blocked = False
            GAME_MAP[x][y].block_sight = False

def create_h_tunnel(x1, x2, y):
    """create horizontal tunnel"""
    global GAME_MAP
    #min() and max() are used in case x1>x2
    for x in range(min(x1, x2), max(x1, x2) + 1):
        GAME_MAP[x][y].blocked = False
        GAME_MAP[x][y].block_sight = False

def create_v_tunnel(y1, y2, x):
    """create vertical tunnel"""
    global GAME_MAP
    for y in range(min(y1, y2), max(y1, y2) + 1):
        GAME_MAP[x][y].blocked = False
        GAME_MAP[x][y].block_sight = False

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
        x = libtcod.random_get_int(0, 0, MAP_WIDTH - width - 1)
        y = libtcod.random_get_int(0, 0, MAP_HEIGHT - height - 1)

        #"Rect" class makes rectangles easier to work with
        new_room = Rect(x, y, width, height)

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
                PLAYER.x = new_x
                PLAYER.y = new_y

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
            
            #add some contents to this room, such as monsters
            place_objects(new_room)

            #finally, append the new room to the list
            rooms.append(new_room)
            num_rooms += 1

def place_objects(room):
    #choose random number of monsters
    num_monsters = libtcod.random_get_int(0, 0, MAX_ROOM_MONSTERS)

    for i in range(num_monsters):
        #choose random spot for this monster
        x = libtcod.random_get_int(0, room.x1, room.x2)
        y = libtcod.random_get_int(0, room.y1, room.y2)

        #only place it if the tile is not blocked
        if not is_blocked(x, y):
            if libtcod.random_get_int(0, 0, 100) < 80: #80% chance of getting an orc
                #create an orc
                fighter_component = Fighter(hp=10, defense=0, power=3, death_function=monster_death)
                ai_component = BasicMonster()

                monster = Object(x, y, 'o', 'orc', libtcod.desaturated_green,
                    blocks=True, fighter=fighter_component, ai=ai_component)
            else:
                #create a troll
                fighter_component = Fighter(hp=16, defense=1, power=4, death_function=monster_death)
                ai_component = BasicMonster()
                
                monster = Object(x, y, 'T', 'troll', libtcod.darker_green,
                    blocks=True, fighter=fighter_component, ai=ai_component)
            
            GAME_OBJECTS.append(monster)

def render_all():
    """Draw all objects in the list"""
    global fov_map, COLOR_DARK_WALL, COLOR_LIGHT_WALL
    global COLOR_DARK_GROUND, COLOR_LIGHT_GROUND
    global fov_recompute

    if fov_recompute:
        #recompute FOV if needed (the player moved or something)
        fov_recompute = False
        libtcod.map_compute_fov(fov_map, PLAYER.x, PLAYER.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)

    #go through all tiles, and set their background color
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            visible = libtcod.map_is_in_fov(fov_map, x, y)
            wall = GAME_MAP[x][y].block_sight
            if not visible:
                #if it's not visible right now, the player can only see it if it's explored
                if GAME_MAP[x][y].explored:
                    if wall:
                        libtcod.console_set_char_background( \
                            CON, x, y, COLOR_DARK_WALL, libtcod.BKGND_SET)
                    else:
                        libtcod.console_set_char_background( \
                            CON, x, y, COLOR_DARK_GROUND, libtcod.BKGND_SET)
            else:
                #it's visible
                if wall:
                    libtcod.console_set_char_background( \
                        CON, x, y, COLOR_LIGHT_WALL, libtcod.BKGND_SET)
                else:
                    libtcod.console_set_char_background( \
                        CON, x, y, COLOR_LIGHT_GROUND, libtcod.BKGND_SET)
                #since it's visible, explore it
                GAME_MAP[x][y].explored = True

    #draw all objects in the list, except the player. we want it to
    #always appear over all other objects! so it's drawn later.
    for g_object in GAME_OBJECTS:
        if g_object != PLAYER:
            g_object.draw()
    PLAYER.draw()

    #blit the contents of "con" to the root console
    libtcod.console_blit(CON, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)
    
    #show the player's stats
    libtcod.console_set_default_foreground(CON, libtcod.white)
    libtcod.console_print_ex(CON, 1, SCREEN_HEIGHT - 2, libtcod.BKGND_NONE, libtcod.LEFT,
        'HP: ' + str(PLAYER.fighter.hp) + '/' + str(PLAYER.fighter.max_hp))

def player_move_or_attack(dx, dy):
    global fov_recompute

    #the coordinates the payer is moving to/attacking
    x = PLAYER.x + dx
    y = PLAYER.y + dy

    #try to find an attackable object there
    target = None
    for g_object in GAME_OBJECTS:
        if g_object.fighter and g_object.x == x and g_object.y == y:
            target = g_object
            break
    
    #attack if target found, move otherwise
    if target is not None:
        PLAYER.fighter.attack(target)
    else:
        PLAYER.move(dx, dy)
        fov_recompute = True

def handle_keys():
    """Handle keyboard movement."""
    global fov_recompute
    # key = libtcod.console_check_for_keypress() #real-time
    key = libtcod.console_wait_for_keypress(True) #turn-based

    if key.vk == libtcod.KEY_ENTER and key.lalt:
        #Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    elif key.vk == libtcod.KEY_ESCAPE:
        return 'exit' #exit game

    if game_state == 'playing':
        #movement keys
        if libtcod.console_is_key_pressed(libtcod.KEY_UP):
            player_move_or_attack(0, -1)

        elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN):
            player_move_or_attack(0, 1)

        elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT):
            player_move_or_attack(-1, 0)

        elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT):
            player_move_or_attack(1, 0)

        else:
            return 'didnt-take-turn'

    

#############################################
# Initialization & Main Loop
#############################################

libtcod.console_set_custom_font('arial10x10.png', \
    libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python/libtcod tutorial', False)
libtcod.sys_set_fps(LIMIT_FPS)
CON = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)

#create object representing the player
fighter_component = Fighter(hp=30, defense=2, power=5, death_function=player_death)
PLAYER = Object(0, 0, '@', 'player', libtcod.white, blocks=True, fighter=fighter_component)

#the list of objects starting with the player
GAME_OBJECTS = [PLAYER]

#generate map (at this point it's not drawn to the screen)
make_map()

fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
for y in range(MAP_HEIGHT):
    for x in range(MAP_WIDTH):
        libtcod.map_set_properties(fov_map, x, y, not GAME_MAP[x][y].block_sight, not GAME_MAP[x][y].blocked)

fov_recompute = True
game_state = 'playing'
player_action = None

while not libtcod.console_is_window_closed():

    #render the screen
    render_all()

    libtcod.console_flush()

    #erase all objects at their old locations, before they move
    for g_object in GAME_OBJECTS:
        g_object.clear()

    #handle keys and exit game if needed
    player_action = handle_keys()
    if player_action == 'exit':
        break
    
    #let monster take their turn
    if game_state == 'playing' and player_action != 'didnt-take-turn':
        for g_object in GAME_OBJECTS:
            if g_object.ai:
                g_object.ai.take_turn()
