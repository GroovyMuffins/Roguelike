#! /usr/bin/python2.7
"""This module sets up initial rogue basin game."""
from classes.BasicMonster import BasicMonster
from classes.ConfusedMonster import ConfusedMonster
from classes.Equipment import Equipment
from classes.Fighter import Fighter
from classes.Item import Item
from classes.Object import Object
from classes.Rect import Rect
from classes.Tile import Tile
import libtcodpy as libtcod
import shelve
from support.common import is_blocked, message
import support.variables as var

def check_level_up():
    """see if the player's experience is enough to level-up"""
    level_up_xp = var.LEVEL_UP_BASE + var.player.level * var.LEVEL_UP_FACTOR
    if var.player.fighter.xp >= level_up_xp:
        #it is! level up
        var.player.level += 1
        var.player.fighter.xp -= level_up_xp
        message('Your battle skills grow stronger! You reached level ' +\
            str(var.player.level) + '!', libtcod.yellow)

        choice = None
        while choice is None: #keep asking until a choice is made
            choice = menu('Level up! Choose a stat to raise:\n',\
                ['Constitution (+20 HP, from ' + str(var.player.fighter.max_hp) + ')',\
                'Strength (+1 attack, from ' + str(var.player.fighter.base_power) + ')',\
                'Agility (+1 defense, from ' + str(var.player.fighter.base_defense) + ')'],\
                var.LEVEL_SCREEN_WIDTH)

        if choice == 0:
            var.player.fighter.max_hp += 20
            var.player.fighter.hp += 20
        elif choice == 1:
            var.player.fighter.base_power += 1
        elif choice == 2:
            var.player.fighter.base_defense += 1

def cast_heal():
    """heal the player"""
    if var.player.fighter.hp == var.player.fighter.max_hp:
        message('You are already at full health.', libtcod.red)
        return 'cancelled'

    message('Your wounds start to feel better!', libtcod.light_violet)
    var.player.fighter.heal(var.HEAL_AMOUNT)

def cast_lightning():
    """find closest enemy (inside a maximum range) and damage it"""
    monster = closest_monster(var.LIGHTNING_RANGE)
    if monster is None: #no enemy found within maximum range
        message('No enemy is close enough to strike.', libtcod.red)
        return 'cancelled'

    #zap it!
    message('A lightning bolt strikes the ' + monster.name + ' with a loud thunder! The damage is '\
        + str(var.LIGHTNING_DAMAGE) + ' hit points.', color=libtcod.light_blue)
    monster.fighter.take_damage(var.LIGHTNING_DAMAGE)

def cast_confuse():
    """ask the player for a target to confuse"""
    message('Left-click an enemy to confuse it, or right-click to cancel.', libtcod.light_cyan)
    monster = target_monster(var.CONFUSE_RANGE)
    if monster is None:
        return 'cancelled'

    #replace the monster's AI with a "confused" one; after some turns it will restore the old AI
    old_ai = monster.ai
    monster.ai = ConfusedMonster(old_ai)
    monster.ai.owner = monster #tell the new component who owns it
    message('The eyes of the ' + monster.name + ' look vacant, as he starts to stumble around!',\
        libtcod.light_green)

def cast_fireball():
    """ask the player for a target tile to throw a fireball at"""
    message('Left-click a target tile for the fireball, or right-click to cancel.',\
        libtcod.light_cyan)
    (x, y) = target_tile()
    if x is None:
        return 'cancelled'
    message('The fireball explodes, burning everything within ' + str(var.FIREBALL_RADIUS) +\
        ' tiles!', libtcod.orange)

    for obj in var.game_objects: #damage every fighter in range, including the player
        if obj.distance(x, y) <= var.FIREBALL_RADIUS and obj.fighter:
            message('The ' + obj.name + ' gets burned for ' + str(var.FIREBALL_DAMAGE) +\
                ' hit points.', libtcod.orange)
            obj.fighter.take_damage(var.FIREBALL_DAMAGE)

def closest_monster(max_range):
    """find closest enemy, up to a maximum range, and in the player's FOV"""
    closest_enemy = None
    closest_dist = max_range + 1 #start with (slightly more than) maximum range

    for g_object in var.game_objects:
        if g_object.fighter and g_object != var.player and\
            libtcod.map_is_in_fov(var.fov_map, g_object.x, g_object.y):
            #calculate distance between this object and the player
            dist = var.player.distance_to(g_object)
            if dist < closest_dist: #it's closer, so remember it
                closest_enemy = g_object
                closest_dist = dist
    return closest_enemy

def target_tile(max_range=None):
    """return the position of a tile left-clicked in player's FOV (optionally in a range),
    or (None,None) if right-clicked."""
    global key, mouse
    while True:
        #render the screen. this erases the inventory
        #and shows the names of objects under the mouse.
        libtcod.console_flush()
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE, key, mouse)
        render_all()

        (x, y) = (mouse.cx, mouse.cy)

        if mouse.rbutton_pressed or key.vk == libtcod.KEY_ESCAPE:
            return (None, None) #cancel if the player right-clicked or pressed Escape

        if mouse.lbutton_pressed and libtcod.map_is_in_fov(var.fov_map, x, y) and\
            (max_range is None or var.player.distance(x, y) <= max_range):
            return (x, y)

def target_monster(max_range=None):
    """returns a clicked monster inside FOV up to a range, or None if right-clicked"""
    while True:
        (x, y) = target_tile(max_range)
        if x is None: #player cancelled
            return None

        #return the first clicked monster, otherwise continue looping
        for obj in var.game_objects:
            if obj.x == x and obj.y == y and obj.fighter and obj != var.player:
                return obj

def player_death(player):
    """the game ended!"""
    message('You died!', libtcod.red)
    var.game_state = 'dead'

    #for added effect, transform the player into a corpse!
    player.char = '%'
    player.color = libtcod.dark_red

def monster_death(monster):
    """transform it into a nasty corpse! it doesn't block, can't be attacked and doesn't move"""
    message('The ' + monster.name + ' is dead! You gain ' + str(monster.fighter.xp) +\
        ' experience points.', libtcod.orange)
    monster.char = '%'
    monster.color = libtcod.dark_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'remains of ' + monster.name
    monster.send_to_back()

def create_room(room):
    """create room"""
    #go through the tiles in the rectangle and make them passable
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            var.game_map[x][y].blocked = False
            var.game_map[x][y].block_sight = False

def create_h_tunnel(x1: int, x2: int, y: int):
    """create horizontal tunnel"""
    #min() and max() are used in case x1>x2
    for x in range(min(x1, x2), max(x1, x2) + 1):
        var.game_map[x][y].blocked = False
        var.game_map[x][y].block_sight = False

def create_v_tunnel(y1: int, y2: int, x: int):
    """create vertical tunnel"""
    for y in range(min(y1, y2), max(y1, y2) + 1):
        var.game_map[x][y].blocked = False
        var.game_map[x][y].block_sight = False

def make_map():
    """fill map with "unblocked" tiles"""
    #the list of objects with just the player
    var.game_objects = [var.player]

    var.game_map = [[Tile(True)\
        for y in range(var.MAP_HEIGHT)]\
        for x in range(var.MAP_WIDTH)]

    rooms = []
    num_rooms = 0
    for _ in range(var.MAX_ROOMS):
        #random width and height
        width = libtcod.random_get_int(0, var.ROOM_MIN_SIZE, var.ROOM_MAX_SIZE)
        height = libtcod.random_get_int(0, var.ROOM_MIN_SIZE, var.ROOM_MAX_SIZE)

        #random position without going out of the boundaries of the map
        x = libtcod.random_get_int(0, 0, var.MAP_WIDTH - width - 1)
        y = libtcod.random_get_int(0, 0, var.MAP_HEIGHT - height - 1)

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
            new_x = int(new_x)
            new_y = int(new_y)

            if num_rooms == 0:
                #this is the first room, where the player starts at
                var.player.x = new_x
                var.player.y = new_y
            else:
                #all rooms after the first:
                #connect it to the previous room with a tunnel

                #center coordinates of the previous room
                (prev_x, prev_y) = rooms[num_rooms - 1].center()
                prev_x = int(prev_x)
                prev_y = int(prev_y)

                #draw a coin (random number that is either 0 or 1)
                if libtcod.random_get_int(0, 0, 1) == 1:
                    #first move horizontally, then vertically
                    create_h_tunnel(prev_x, new_x, prev_y)
                    create_v_tunnel(prev_y, new_y, new_x)
                else:
                    #first move vertically, then horizontally
                    create_v_tunnel(prev_y, new_y, prev_x)
                    create_h_tunnel(prev_x, new_x, new_y)

            #add some contents to this room, such as monsters
            place_objects(new_room)

            #finally, append the new room to the list
            rooms.append(new_room)
            num_rooms += 1

    #create stairs at the center of the last room
    var.stairs = Object(new_x, new_y, var.STAIRSDOWN_TILE, 'stairs', libtcod.white, always_visible=True)
    var.game_objects.append(var.stairs)
    var.stairs.send_to_back() #so it's drawn below the monsters

def place_objects(room):
    """choose random number of monsters"""

    # maximum number of monsters per room
    max_monsters = from_dungeon_level([[2, 1], [3, 4], [5, 6]])
    num_monsters = libtcod.random_get_int(0, 0, max_monsters)

    # chance of each monster
    monster_chances = {}
    monster_chances['orc'] = 80 # orc always shows up, even if all other monsters have 0 chance
    monster_chances['troll'] = from_dungeon_level([[15, 3], [30, 5], [60, 7]])

    # maximum number of items per room
    max_items = from_dungeon_level([[1, 1], [2, 4]])
    num_items = libtcod.random_get_int(0, 0, max_items)

    # chance of each item (by default they have a chance of 0 at level 1, which then goes up)
    item_chances = {}
    item_chances['heal'] = 35 # healing potion always shows up, even if all other items have 0 chance
    item_chances['lightning'] = from_dungeon_level([[25, 4]])
    item_chances['fireball'] = from_dungeon_level([[25, 6]])
    item_chances['confuse'] = from_dungeon_level([[10, 2]])
    item_chances['sword'] = from_dungeon_level([[5, 4]])
    item_chances['shield'] = from_dungeon_level([[15, 8]])

    for _ in range(num_monsters):
        #choose random spot for this monster
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)

        #only place it if the tile is not blocked
        if not is_blocked(x, y):
            choice = random_choice(monster_chances)
            if choice == 'orc':
                #create an orc
                fighter_component = Fighter(\
                    hp=20, defense=0, power=4, xp=35, death_function=monster_death)
                ai_component = BasicMonster()

                monster = Object(x, y, var.ORC_TILE, 'orc', libtcod.desaturated_green,\
                    blocks=True, fighter=fighter_component, ai=ai_component)
            elif choice == 'troll':
                #create a troll
                fighter_component = Fighter(\
                    hp=30, defense=2, power=8, xp=100, death_function=monster_death)
                ai_component = BasicMonster()

                monster = Object(x, y, var.TROLL_TILE, 'troll', libtcod.darker_green,\
                    blocks=True, fighter=fighter_component, ai=ai_component)

            var.game_objects.append(monster)

    for _ in range(num_items):
        #choose random spot for this item
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)

        #only place it if the tile is not blocked
        if not is_blocked(x, y):
            choice = random_choice(item_chances)
            if choice == 'heal':
                #create a healing potion (70% chance)
                item_component = Item(use_function=cast_heal)

                item = Object(x, y, var.HEALINGPOTION_TILE, 'healing potion', libtcod.violet,\
                    item=item_component, always_visible=True)
            elif choice == 'lightning':
                #create a lightning bolt scroll (10% chance)
                item_component = Item(use_function=cast_lightning)

                item = Object(x, y, '#', 'scroll of lightning bolt', libtcod.light_yellow,\
                    item=item_component, always_visible=True)
            elif choice == 'fireball':
                #create a fireball scroll (10% chance)
                item_component = Item(use_function=cast_fireball)

                item = Object(x, y, '#', 'scroll of fireball', libtcod.light_yellow,\
                    item=item_component, always_visible=True)
            elif choice == 'confuse':
                #create a confuse scroll (10% chance)
                item_component = Item(use_function=cast_confuse)

                item = Object(x, y, '#', 'scroll of confusion', libtcod.light_yellow,\
                    item=item_component, always_visible=True)
            elif choice == 'sword':
                # create a sword
                equipment_component = Equipment(slot='right hand', power_bonus=3)
                item = Object(x, y, var.SWORD_TILE, 'sword', libtcod.sky, equipment=equipment_component)
            elif choice == 'shield':
                # create a shield
                equipment_component = Equipment(slot='left hand', defense_bonus=1)
                item = Object(x, y, var.SHIELD_TILE, 'shield', libtcod.dark_orange,\
                    equipment=equipment_component)

            var.game_objects.append(item)
            item.send_to_back() #items appear below other objects
            item.always_visible = True # items are visible even out-of-FOV, if in an explored area

def random_choice_index(chances):
    """Choose one option from the list of chances, returning its index"""
    # the dice will land on some number between 1 and the sum of the chances
    dice = libtcod.random_get_int(0, 1, sum(chances))

    # go through all chances, keeping the sum so far
    running_sum = 0
    choice = 0
    for w in chances:
        running_sum += w

        # see if the dice landed in the part that corresponds to this choice
        if dice <= running_sum:
            return choice
        choice += 1

def random_choice(chances_dict):
    """Choose one option from dictionary of chances, returning its key"""
    chances = list(chances_dict.values())
    strings = list(chances_dict.keys())
    return strings[random_choice_index(chances)]

def from_dungeon_level(table):
    """Returns a value that depends on level.
    The table specifies what value occurs after each level, default is 0."""
    for (value, level) in reversed(table):
        if var.dungeon_level >= level:
            return value
    return 0

def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
    """render a bar (HP, experience, etc). first calculate the widt o the bar"""
    load_customfont()

    bar_width = int(float(value) / maximum * total_width)

    #render the background first
    libtcod.console_set_default_background(var.panel, back_color)
    libtcod.console_rect(var.panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)

    #now render the bar on top
    libtcod.console_set_default_background(var.panel, bar_color)
    if bar_width > 0:
        libtcod.console_rect(var.panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)

    #finally, some centered text with the values
    libtcod.console_set_default_foreground(var.panel, libtcod.white)
    libtcod.console_print_ex(var.panel, int(x + total_width / 2), y, libtcod.BKGND_NONE, libtcod.CENTER,\
        name + ': ' + str(value) + '/' + str(maximum))

def render_all():
    """Draw all objects in the list"""
    if var.fov_recompute:
        #recompute FOV if needed (the player moved or something)
        var.fov_recompute = False
        libtcod.map_compute_fov(\
            var.fov_map, var.player.x, var.player.y, var.TORCH_RADIUS, var.FOV_LIGHT_WALLS, var.FOV_ALGO)

    #go through all tiles, and set their background color
    for y in range(var.MAP_HEIGHT):
        for x in range(var.MAP_WIDTH):
            visible = libtcod.map_is_in_fov(var.fov_map, x, y)
            wall = var.game_map[x][y].block_sight
            if not visible:
                #if it's not visible right now, the player can only see it if it's explored
                if var.game_map[x][y].explored:
                    if wall:
                        libtcod.console_put_char_ex(\
                            var.CON, x, y, var.WALL_TILE, libtcod.grey, libtcod.black)
                    else:
                        libtcod.console_put_char_ex(\
                            var.CON, x, y, var.FLOOR_TILE, libtcod.grey, libtcod.black)
            else:
                #it's visible
                if wall:
                    libtcod.console_put_char_ex(var.CON, x, y, var.WALL_TILE, libtcod.white, libtcod.black)
                else:
                    libtcod.console_put_char_ex(var.CON, x, y, var.FLOOR_TILE, libtcod.white, libtcod.black)
                #since it's visible, explore it
                var.game_map[x][y].explored = True

    #draw all objects in the list, except the player. we want it to
    #always appear over all other objects! so it's drawn later.
    for g_object in var.game_objects:
        if g_object != var.player:
            g_object.draw()
    var.player.draw()

    #blit the contents of "con" to the root console
    libtcod.console_blit(var.CON, 0, 0, var.SCREEN_WIDTH, var.SCREEN_HEIGHT, 0, 0, 0)

    #prepare to render the GUI panel
    libtcod.console_set_default_background(var.panel, libtcod.black)
    libtcod.console_clear(var.panel)

    #print the game messages, one line at a time
    y = 1
    for (line, color) in var.game_msgs:
        libtcod.console_set_default_foreground(var.panel, color)
        libtcod.console_print_ex(var.panel, int(var.MSG_X), y, libtcod.BKGND_NONE, libtcod.LEFT, line)
        y += 1

    #show the player's stats
    render_bar(1, 1, var.BAR_WIDTH, 'HP', var.player.fighter.hp, var.player.fighter.max_hp,\
        libtcod.light_red, libtcod.darker_red)

    libtcod.console_print_ex(\
        var.panel, 1, 3, libtcod.BKGND_NONE, libtcod.LEFT, 'Dungeon level ' + str(var.dungeon_level))

    #display names of objects under the mouse
    libtcod.console_set_default_foreground(var.panel, libtcod.light_gray)
    libtcod.console_print_ex(var.panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse())

    #blit the contents of "panel" to the root console
    libtcod.console_blit(var.panel, 0, 0, var.SCREEN_WIDTH, var.PANEL_HEIGHT, 0, 0, var.PANEL_Y)

def player_move_or_attack(dx, dy):
    #the coordinates the payer is moving to/attacking
    x = var.player.x + dx
    y = var.player.y + dy

    #try to find an attackable object there
    target = None
    for g_object in var.game_objects:
        if g_object.fighter and g_object.x == x and g_object.y == y:
            target = g_object
            break

    #attack if target found, move otherwise
    if target is not None:
        var.player.fighter.attack(target)
    else:
        var.player.move(dx, dy)
        var.fov_recompute = True

def handle_keys():
    """Handle keyboard movement."""
    global key

    if key.vk == libtcod.KEY_ENTER and key.lalt:
        #Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    elif key.vk == libtcod.KEY_ESCAPE:
        return 'exit' #exit game

    if var.game_state == 'playing':
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
                for g_object in var.game_objects: #look for an item in the player's tile
                    if g_object.x == var.player.x and g_object.y == var.player.y and g_object.item:
                        g_object.item.pick_up()
                        break

            if key_char == 'i':
                #show the inventory; if an item is selected, use it
                chosen_item = inventory_menu(\
                    'Press the key next to an item to use it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.use()

            if key_char == 'd':
                #show the inventory; if an item is selected, drop it
                chosen_item = inventory_menu(\
                    'Press the key next to an item to drop it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.drop()

            if key_char == 'u':
                #go down stairs, if the player is on them
                if var.stairs.x == var.player.x and var.stairs.y == var.player.y:
                    next_level()

            if key_char == 'c':
                #show character information
                level_up_xp = var.LEVEL_UP_BASE + var.player.level * var.LEVEL_UP_FACTOR
                msgbox('Character Information\n\nLevel ' + str(var.player.level) +\
                    '\nExperience: ' + str(var.player.fighter.xp) +\
                    '\nExperience to level up: ' + str(level_up_xp) +\
                    '\n\nMaximum HP: ' + str(var.player.fighter.max_hp) +\
                    '\nAttack: ' + str(var.player.fighter.power) +\
                    '\nDefense: ' + str(var.player.fighter.defense), var.CHARACTER_SCREEN_WIDTH)

            return 'didnt-take-turn'

def next_level():
    """advance to the next level"""
    message('You take a moment to rest, and recover your strength.', libtcod.light_violet)
    var.player.fighter.heal(var.player.fighter.max_hp / 2) #heal the player by 50%

    var.dungeon_level += 1
    message('After a rare moment of peace, you descend deeper into the heart of the dungeon...',\
        libtcod.red)
    make_map() #create a fresh new level!
    initialize_fov()

def get_names_under_mouse():
    """return a string with the names of all objects under the mouse"""
    global mouse

    (x, y) = (mouse.cx, mouse.cy)

    #create a list with the names of all objects at the mouse's coordinates
    names = [g_object.name for g_object in var.game_objects\
        if g_object.x == x and g_object.y == y and\
        libtcod.map_is_in_fov(var.fov_map, g_object.x, g_object.y)]
    names = ', '.join(names) # join the names, separated by commas
    return names.capitalize()

def menu(header, options, width):
    """create a menu"""
    if len(options) > 26: raise ValueError('Cannot have a menu with more than 26 options.')

    #calculate total height for the header (after auto-wrap) and one line per option
    header_height = libtcod.console_get_height_rect(var.CON, 0, 0, width, var.SCREEN_HEIGHT, header)
    if header == '':
        header_height = 0
    height = len(options) + header_height

    #create an off-screen console that represents the menu's window
    window = libtcod.console_new(width, height)

    #print the header, with auto-wrap
    libtcod.console_set_default_foreground(window, libtcod.white)
    libtcod.console_print_rect_ex(\
        window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)

    #print all the options
    y = header_height
    letter_index = ord('a')
    for option_text in options:
        text = '(' + chr(letter_index) + ')' + option_text
        libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
        y += 1
        letter_index += 1

    #blit the contents of "window" to the root console
    x = var.SCREEN_WIDTH/2 - width/2
    y = var.SCREEN_HEIGHT/2 - height/2
    libtcod.console_blit(window, 0, 0, width, height, 0, int(x), int(y), 1.0, 0.7)

    #present the root console to the player and wait for a key-press
    libtcod.console_flush()
    key = libtcod.console_wait_for_keypress(True)
    if key.vk == libtcod.KEY_ENTER and key.lalt: #(special case) Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    #convert the ASCII code to an index; if it corresponds to an option, return it
    index = key.c - ord('a')
    if index >= 0 and index < len(options):
        return index
    return None

def inventory_menu(header):
    """show a menu with each item of the inventory as an option"""
    if len(var.inventory) == 0:
        options = ['Inventory is empty.']
    else:
        options = []
        for item in var.inventory:
            text = item.name
            # show additional information, in case it's equipped
            if item.equipment and item.equipment.is_equipped:
                text = text + ' (on ' + item.equipment.slot + ')'
            options.append(text)

    index = menu(header, options, var.INVENTORY_WIDTH)

    #if an item was chosen, return it
    if index is None or len(var.inventory) == 0:
        return None
    return var.inventory[index].item

def new_game():
    """create a new game"""
    #create object representing the player
    fighter_component = Fighter(hp=100, defense=1, power=2, xp=0, death_function=player_death)
    var.player = Object(0, 0, var.PLAYER_TILE, 'player', libtcod.white, blocks=True, fighter=fighter_component)

    var.player.level = 1

    #generate map (at this point it's not drawn to the screen)
    var.dungeon_level = 1
    make_map()
    initialize_fov()

    var.game_state = 'playing'
    var.inventory = []

    #create the list of game messages and their colors, starts empty
    var.game_msgs = []

    #a warm welcoming message!
    message('Welcome stranger! Prepare to perish in the Tombs of the Ancient Kings.', libtcod.red)

    # initial equipment: a dagger
    equipment_component = Equipment(slot='right hand', power_bonus=2)
    obj = Object(0, 0, var.DAGGER_TILE, 'dagger', libtcod.sky, equipment=equipment_component)
    var.inventory.append(obj)
    equipment_component.equip()
    obj.always_visible = True

def initialize_fov():
    """ initialize field of view"""
    #create the FOV map, according to the generated map
    var.fov_map = libtcod.map_new(var.MAP_WIDTH, var.MAP_HEIGHT)
    for y in range(var.MAP_HEIGHT):
        for x in range(var.MAP_WIDTH):
            libtcod.map_set_properties(\
                var.fov_map, x, y, not var.game_map[x][y].block_sight, not var.game_map[x][y].blocked)

    libtcod.console_clear(var.CON) #unexplored areas start black (which is the default background color)


def play_game():
    """play the game"""
    global key, mouse

    player_action = None

    mouse = libtcod.Mouse()
    key = libtcod.Key()
    while not libtcod.console_is_window_closed():
        #render the screen
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS | libtcod.EVENT_MOUSE, key, mouse)
        render_all()

        libtcod.console_flush()

        check_level_up()

        #erase all objects at their old locations, before they move
        for obj in var.game_objects:
            obj.clear()

        #handle keys and exit game if needed
        player_action = handle_keys()
        if player_action == 'exit':
            save_game()
            break

        #let monsters take their turn
        if var.game_state == 'playing' and player_action != 'didnt-take-turn':
            for obj in var.game_objects:
                if obj.ai:
                    obj.ai.take_turn()

def main_menu():
    """create a main menu"""
    img = libtcod.image_load('menu_background.png')

    while not libtcod.console_is_window_closed():
        #show the background image, at twice the regular console resolution
        libtcod.image_blit_2x(img, 0, 0, 0)

        #show the game's title, and some credits!
        libtcod.console_set_default_foreground(0, libtcod.yellow)
        libtcod.console_print_ex(\
            0, int(var.SCREEN_WIDTH/2), int(var.SCREEN_HEIGHT/2-4), libtcod.BKGND_NONE, libtcod.CENTER,
            'TOMBS OF THE ANCIENT KINGS')
        libtcod.console_print_ex(\
            0, int(var.SCREEN_WIDTH/2), int(var.SCREEN_HEIGHT-2), libtcod.BKGND_NONE, libtcod.CENTER,
            'By Alf')

        #show options and wait for the player's choice
        choice = menu('', ['Play a new game', 'Continue last game', 'Quit'], 24)

        if choice == 0: #new game
            new_game()
            play_game()
        if choice == 1: #load last game
            try:
                load_game()
            except:
                msgbox('\n No saved game to load.\n', 24)
                continue
            play_game()
        elif choice == 2: #quit
            break

def msgbox(text, width=50):
    """create a message box"""
    menu(text, [], width) #use menu() as a sort of "message box"

def save_game():
    """open a new empty shelve (possibly overwriting an old one) to write the game data"""
    file = shelve.open('savegame', 'n')
    file['game_map'] = var.game_map
    file['game_objects'] = var.game_objects
    file['player_index'] = var.game_objects.index(var.player) #index of player in objects lists
    file['stairs_index'] = var.game_objects.index(var.stairs)
    file['dungeon_level'] = var.dungeon_level
    file['inventory'] = var.inventory
    file['game_msgs'] = var.game_msgs
    file['game_state'] = var.game_state
    file.close()

def load_game():
    """open the previously saved shelve and load the game data"""
    file = shelve.open('savegame', 'r')
    var.game_map = file['game_map']
    var.game_objects = file['game_objects']
    var.player = var.game_objects[file['player_index']] #get index of player in objects list and access it
    var.stairs = var.game_objects[file['stairs_index']]
    var.dungeon_level = file['dungeon_level']
    var.inventory = file['inventory']
    var.game_msgs = file['game_msgs']
    var.game_state = file['game_state']
    file.close()

    initialize_fov()

def load_customfont():
    """The index of the first custom tile in the file"""
    a = 256

    # The "y" is the row index, here we load the sixth row in the font file.
    # Increase the "6" to load any new rows from the file.
    for y in range(5, 6):
        libtcod.console_map_ascii_codes_to_font(a, 32, 0, y)
        a += 32

#############################################
# Initialization & Main Loop
#############################################

# The font has 32 chars in a row, and there's a total of 10 rows.
# Increase the "10" when you add new rows to the sample font file.
libtcod.console_set_custom_font('TiledFont.png',\
    libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD, 32, 10)
libtcod.console_init_root(var.SCREEN_WIDTH, var.SCREEN_HEIGHT, 'python/libtcod tutorial', False)
libtcod.sys_set_fps(var.LIMIT_FPS)
var.CON = libtcod.console_new(var.MAP_WIDTH, var.MAP_HEIGHT)
var.panel = libtcod.console_new(var.SCREEN_WIDTH, var.PANEL_HEIGHT)

main_menu()
