#!/c/Python27/python
"""This module sets up initial rogue basin game."""
import libtcodpy as libtcod
import math
import textwrap

#actual size of the window
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

#size of the map
MAP_WIDTH = 80
MAP_HEIGHT = 43

#sizes and coordinates relevant for the GUI
BAR_WIDTH = 20
PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT
MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1
INVENTORY_WIDTH = 50

#parameters for dungeon generator
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30
MAX_ROOM_MONSTERS = 3
MAX_ROOM_ITEMS = 2

#spell values
HEAL_AMOUNT = 4
LIGHTNING_RANGE = 5
LIGHTNING_DAMAGE = 20


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
    def __init__(self, x, y, char, name, color, blocks=False, fighter=None, ai=None, item=None):
        self.x = x
        self.y = y
        self.char = char
        self.name = name
        self.color = color
        self.blocks = blocks

        self.fighter = fighter
        if self.fighter: #let the fighter component know who owns it
            self.fighter.owner = self
        
        self.ai = ai
        if self.ai: #let the AI component know who owns it
            self.ai.owner = self

        self.item = item
        if self.item: #let the Item component know who owns it
            self.item.owner = self

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
        
    def attack(self, target):
        #a simple formula for attack damage
        damage = self.power - target.fighter.defense

        if damage > 0:
            #make the target take some damage
            message(self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points.')
            target.fighter.take_damage(damage)
        else:
            message(self.owner.name.capitalize() + ' attacks ' + target.name + ' but it has no effect!')

    def take_damage(self, damage):
        #apply damage if possible
        if damage > 0:
            self.hp -= damage
        
            #check for death. if there's a death function, call it
            if self.hp <= 0:
                function = self.death_function
                if function is not None:
                    function(self.owner)
    
    def heal(self, amount):
        #heal by the given amount, without going over the maximum
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp

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

class Item:
    def __init__(self, use_function=None):
        self.use_function = use_function

    def use(self):
        #just call the "use_function" if it is defined
        if self.use_function is None:
            message('The '+ self.owner.name + ' cannot be used.')
        else:
            if self.use_function() != 'cancelled':
                inventory.remove(self.owner) #destroy after use, unless it was cancelled for some reason

    #an item that can be picked up and used.
    def pick_up(self):
        #add to the player's inventory and remove from the map
        if len(inventory) >= 26:
            message('Your inventory is full, cannot pick up ' + self.owner.name + '.', libtcod.red)
        else:
            inventory.append(self.owner)
            GAME_OBJECTS.remove(self.owner)
            message('You picked up a ' + self.owner.name + '!', libtcod.green)

def cast_heal():
    #heal the player
    if PLAYER.fighter.hp == PLAYER.fighter.max_hp:
        message('You are already at full health.', libtcod.red)
        return 'cancelled'
    
    message('Your wounds start to feel better!', libtcod.light_violet)
    PLAYER.fighter.heal(HEAL_AMOUNT)

def cast_lightning():
    #find closest enemy (inside a maximum range) and damage it
    monster = closest_monster(LIGHTNING_RANGE)
    if monster is None: #no enemy found within maximum range
        message('No enemy is close enough to strike.', libtcod.red)
        return 'cancelled'
    
    #zap it!
    message('A lightning bolt strikes the ' + monster.name + ' with a loud thunder! The damage is '
        + str(LIGHTNING_DAMAGE) + ' hit points.', color = libtcod.light_blue)
    monster.fighter.take_damage(LIGHTNING_DAMAGE)

def closest_monster(max_range):
    #find closest enemy, up to a maximum range, and in the player's FOV
    closest_enemy = None
    closest_dist = max_range + 1 #start with (slightly more than) maximum range

    for g_object in GAME_OBJECTS:
        if g_object.fighter and not g_object == PLAYER and libtcod.map_is_in_fov(fov_map, g_object.x, g_object.y):
            #calculate distance between this object and the player
            dist = PLAYER.distance_to(g_object)
            if dist < closest_dist: #it's closer, so remember it
                closest_enemy = g_object
                closest_dist = dist
    return closest_enemy

def player_death(PLAYER):
    #the game ended!
    global game_state
    message('You died!', libtcod.red)
    game_state = 'dead'

    #for added effect, transform the player into a corpse!
    PLAYER.char = '%'
    PLAYER.color = libtcod.dark_red

def monster_death(monster):
    #transform it into a nasty corpse! it doesn't block, can't be
    # attacked and doesn't move
    message(monster.name.capitalize() + ' is dead!', libtcod.orange)
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
    global GAME_MAP, GAME_OBJECTS

    #the list of objects with just the player
    GAME_OBJECTS = [PLAYER]

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
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)

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
    
    #choose random number of items
    num_items = libtcod.random_get_int(0, 0, MAX_ROOM_ITEMS)

    for i in range(num_items):
        #choose random spot for this item
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)

        #only place it if the tile is not blocked
        if not is_blocked(x, y):
            dice = libtcod.random_get_int(0, 0, 100)
            if dice < 70:
                #create a healing potion (70% chance)
                item_component = Item(use_function=cast_heal)

                item = Object(x, y, '!', 'healing potion', libtcod.violet, item=item_component)
            else:
                #create a lightning bolt scroll (30% chance)
                item_component = Item(use_function=cast_lightning)

                item = Object(x, y, '#', 'scroll of lightning bolt', libtcod.light_yellow, item=item_component)

            GAME_OBJECTS.append(item)
            item.send_to_back() #items appear below other objects

def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
    #render a bar (HP, experience, etc). first calculate the widt o the bar
    bar_width = int(float(value) / maximum * total_width)

    #render the background first
    libtcod.console_set_default_background(panel, back_color)
    libtcod.console_rect(panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)

    #now render the bar on top
    libtcod.console_set_default_background(panel, bar_color)
    if bar_width > 0:
        libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)
    
    #finally, some centered text with the values
    libtcod.console_set_default_foreground(panel, libtcod.white)
    libtcod.console_print_ex(panel, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER,
        name + ': ' + str(value) + '/' + str(maximum))

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
    
    #prepare to render the GUI panel
    libtcod.console_set_default_background(panel, libtcod.black)
    libtcod.console_clear(panel)

    #print the game messages, one line at a time
    y = 1
    for (line, color) in game_msgs:
        libtcod.console_set_default_foreground(panel, color)
        libtcod.console_print_ex(panel, MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
        y += 1

    #show the player's stats
    render_bar(1, 1, BAR_WIDTH, 'HP', PLAYER.fighter.hp, PLAYER.fighter.max_hp,
        libtcod.light_red, libtcod.darker_red)

    #display names of objects under the mouse
    libtcod.console_set_default_foreground(panel, libtcod.light_gray)
    libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse())

    #blit the contents of "panel" to the root console
    libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)
    

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

def message(new_msg, color = libtcod.white):
    #split the message if necessary, among multiple lines
    new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)

    for line in new_msg_lines:
        #if the buffer is full, remove the first line to make room for the new one
        if len(game_msgs) == MSG_HEIGHT:
            del game_msgs[0]
        
        # add the new line as a tuple, with the tex and the color
        game_msgs.append( (line, color) )

def handle_keys():
    """Handle keyboard movement."""
    global fov_recompute, key
    # key = libtcod.console_check_for_keypress() #real-time
    # key = libtcod.console_wait_for_keypress(True) #turn-based

    if key.vk == libtcod.KEY_ENTER and key.lalt:
        #Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    elif key.vk == libtcod.KEY_ESCAPE:
        return 'exit' #exit game

    if game_state == 'playing':
        #movement keys
        if key.vk == libtcod.KEY_UP:
            player_move_or_attack(0, -1)

        elif key.vk == libtcod.KEY_DOWN:
            player_move_or_attack(0, 1)

        elif key.vk == libtcod.KEY_LEFT:
            player_move_or_attack(-1, 0)

        elif key.vk == libtcod.KEY_RIGHT:
            player_move_or_attack(1, 0)

        else:
            #test for other keys
            key_char = chr(key.c)

            if key_char == 'g':
                #pick up an item
                for g_object in GAME_OBJECTS: #look for an item in the player's tile
                    if g_object.x == PLAYER.x and g_object.y == PLAYER.y and g_object.item:
                        g_object.item.pick_up()
                        break
            if key_char == 'i':
                #show the inventory; if an item is selected, use it
                chosen_item = inventory_menu('Press the key next to an item to use it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.use()

            return 'didnt-take-turn'

def get_names_under_mouse():
    global mouse

    #return a string with the names of all objects under the mouse
    (x, y) = (mouse.cx, mouse.cy)

    #create a list with the names of all objects at the mouse's coordinates
    names = [g_object.name for g_object in GAME_OBJECTS
        if g_object.x == x and g_object.y == y and libtcod.map_is_in_fov(fov_map, g_object.x, g_object.y)]
    names = ', '.join(names) # join the names, separated by commas
    return names.capitalize()

def menu(header, options, width):
    if len(options) > 26: raise ValueError('Cannot have a menu with more than 26 options.')

    #calculate total height for the header (after auto-wrap) and one line per option
    header_height = libtcod.console_get_height_rect(CON, 0, 0, width, SCREEN_HEIGHT, header)
    if header == '':
        header_height = 0
    height = len(options) + header_height

    #create an off-screen console that represents the menu's window
    window = libtcod.console_new(width, height)

    #print the header, with auto-wrap
    libtcod.console_set_default_foreground(window, libtcod.white)
    libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)

    #print all the options
    y = header_height
    letter_index = ord('a')
    for option_text in options:
        text = '(' + chr(letter_index) + ')' + option_text
        libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
        y += 1
        letter_index += 1

    #blit the contents of "window" to the root console
    x = SCREEN_WIDTH/2 - width/2
    y = SCREEN_HEIGHT/2 - height/2
    libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)

    #present the root console to the player and wait for a key-press
    libtcod.console_flush()
    key = libtcod.console_wait_for_keypress(True)
    if key.vk == libtcod.KEY_ENTER and key.lalt: #(special case) Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    #convert the ASCII code to an index; if it corresponds to an option, return it
    index = key.c - ord('a')
    if index >= 0 and index < len(options): return index
    return None

def inventory_menu(header):
    #show a menu with each item of the inventory as an option
    if len(inventory) == 0:
        options = ['Inventory is empty.']
    else:
        options = [item.name for item in inventory]
    
    index = menu(header, options, INVENTORY_WIDTH)

    #if an item was chosen, return it
    if index is None or len(inventory) == 0: return None
    return inventory[index].item

def new_game():
    global PLAYER, inventory, game_msgs, game_state

    #create object representing the player
    fighter_component = Fighter(hp=30, defense=2, power=5, death_function=player_death)
    PLAYER = Object(0, 0, '@', 'player', libtcod.white, blocks=True, fighter=fighter_component)

    #generate map (at this point it's not drawn to the screen)
    make_map()
    initialize_fov()

    game_state = 'playing'
    inventory = []

    #create the list of game messages and their colors, starts empty
    game_msgs = []

    #a warm welcoming message!
    message('Welcome stranger! Prepare to perish in the Tombs of the Ancient Kings.', libtcod.red)

def initialize_fov():
    global fov_recompute, fov_map
    fov_recompute = True

    #create the FOV map, according to the generated map
    fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            libtcod.map_set_properties(fov_map, x, y, not GAME_MAP[x][y].block_sight, not GAME_MAP[x][y].blocked)
            
    libtcod.console_clear(CON) #unexplored areas start black (which is the default background color)


def play_game():
    global key, mouse

    player_action = None

    mouse = libtcod.Mouse()
    key = libtcod.Key()
    while not libtcod.console_is_window_closed():
        #render the screen
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)
        render_all()

        libtcod.console_flush()

        #erase all objects at their old locations, before they move
        for obj in GAME_OBJECTS:
            obj.clear()
        
        #handle keys and exit game if needed
        player_action = handle_keys()
        if player_action == 'exit':
            break
        
        #let monsters take their turn
        if game_state == 'playing' and player_action != 'didnt-take-turn':
            for obj in GAME_OBJECTS:
                if obj.ai:
                    obj.ai.take_turn()

def main_menu():
    img = libtcod.image_load('menu_background.png')

    while not libtcod.console_is_window_closed():
        #show the background image, at twice the regular console resolution
        libtcod.image_blit_2x(img, 0, 0, 0)

        #show the game's title, and some credits!
        libtcod.console_set_default_foreground(0, libtcod.yellow)
        libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2-4, libtcod.BKGND_NONE, libtcod.CENTER,
            'TOMBS OF THE ANCIENT KINGS')
        libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT-2, libtcod.BKGND_NONE, libtcod.CENTER,
            'By Alf')

        #show options and wait for the player's choice
        choice = menu('', ['Play a new game', 'Continue last game', 'Quit'], 24)

        if choice == 0: #new game
            new_game()
            play_game()
        elif choice == 2: #quit
            break


#############################################
# Initialization & Main Loop
#############################################

libtcod.console_set_custom_font('arial10x10.png', \
    libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python/libtcod tutorial', False)
libtcod.sys_set_fps(LIMIT_FPS)
CON = libtcod.console_new(MAP_WIDTH, MAP_HEIGHT)
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)

main_menu()