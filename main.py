"""This module sets up initial rogue basin game."""

import shelve

import roguelike as rl
import tcod as libtcod
from tcod import libtcodpy


def check_level_up() -> None:
    """See if the player's experience is enough to level-up."""
    level_up_xp = rl.constants.LEVEL_UP_BASE + rl.variables.player.level * rl.constants.LEVEL_UP_FACTOR
    if rl.variables.player.fighter.xp >= level_up_xp:
        # it is! level up
        rl.variables.player.level += 1
        rl.variables.player.fighter.xp -= level_up_xp
        rl.common.message(
            f"Your battle skills grow stronger! You reached level {str(rl.variables.player.level)}!", rl.Colors.YELLOW
        )

        choice = None
        while choice is None:  # keep asking until a choice is made
            choice = menu(
                "Level up! Choose a stat to raise:\n",
                [
                    f"Constitution (+20 HP, from {str(rl.variables.player.fighter.max_hp)})",
                    f"Strength (+1 attack, from {str(rl.variables.player.fighter.base_power)})",
                    f"Agility (+1 defense, from {str(rl.variables.player.fighter.base_defense)})",
                ],
                rl.constants.LEVEL_SCREEN_WIDTH,
            )

        if choice == 0:
            rl.variables.player.fighter.base_max_hp += 20
            rl.variables.player.fighter.hp += 20
        elif choice == 1:
            rl.variables.player.fighter.base_power += 1
        elif choice == 2:
            rl.variables.player.fighter.base_defense += 1


def cast_heal():
    """Heal the player."""
    if rl.variables.player.fighter.hp == rl.variables.player.fighter.max_hp:
        rl.common.message("You are already at full health.", rl.Colors.RED)
        return "cancelled"

    rl.common.message("Your wounds start to feel better!", rl.Colors.LIGHT_VIOLET)
    rl.variables.player.fighter.heal(rl.constants.HEAL_AMOUNT)


def cast_lightning():
    """Find closest enemy (inside a maximum range) and damage it."""
    monster = closest_monster(rl.constants.LIGHTNING_RANGE)
    if monster is None:  # no enemy found within maximum range
        rl.common.message("No enemy is close enough to strike.", rl.Colors.RED)
        return "cancelled"

    # zap it!
    rl.common.message(
        f"A lightning bolt strikes the {monster.name} with a loud thunder! "
        f"The damage is {str(rl.constants.LIGHTNING_DAMAGE)} hit points.",
        color=rl.Colors.LIGHT_BLUE,
    )
    monster.fighter.take_damage(rl.constants.LIGHTNING_DAMAGE)


def cast_confuse():
    """Ask the player for a target to confuse."""
    rl.common.message("Left-click an enemy to confuse it, or right-click to cancel.", rl.Colors.LIGHT_CYAN)
    monster = target_monster(rl.constants.CONFUSE_RANGE)
    if monster is None:
        return "cancelled"

    # replace the monster's AI with a "confused" one; after some turns it will restore the old AI
    old_ai = monster.ai
    monster.ai = rl.ConfusedMonster(old_ai)
    monster.ai.owner = monster  # tell the new component who owns it
    rl.common.message(f"The eyes of the {monster.name} look vacant, as he starts to stumble around!", rl.Colors.LIGHT_GREEN)


def cast_fireball():
    """Ask the player for a target tile to throw a fireball at."""
    rl.common.message("Left-click a target tile for the fireball, or right-click to cancel.", rl.Colors.LIGHT_CYAN)
    (x, y) = target_tile()
    if x is None:
        return "cancelled"
    rl.common.message(
        f"The fireball explodes, burning everything within {str(rl.constants.FIREBALL_RADIUS)} tiles!", rl.Colors.ORANGE
    )

    for obj in rl.variables.game_objects:  # damage every fighter in range, including the player
        if obj.distance(x, y) <= rl.constants.FIREBALL_RADIUS and obj.fighter:
            rl.common.message(
                f"The {obj.name} gets burned for {str(rl.constants.FIREBALL_DAMAGE)} hit points.", rl.Colors.ORANGE
            )
            obj.fighter.take_damage(rl.constants.FIREBALL_DAMAGE)


def closest_monster(max_range: int):
    """Find closest enemy, up to a maximum range, and in the player's FOV."""
    if rl.variables.fov_map is None or rl.variables.player is None:
        return
    closest_enemy = None
    closest_dist = max_range + 1  # start with (slightly more than) maximum range

    for g_object in rl.variables.game_objects:
        if (
            g_object.fighter
            and g_object != rl.variables.player
            and libtcodpy.map_is_in_fov(rl.variables.fov_map, g_object.x, g_object.y)
        ):
            # calculate distance between this object and the player
            dist = rl.variables.player.distance_to(g_object)
            if dist < closest_dist:  # it's closer, so remember it
                closest_enemy = g_object
                closest_dist = dist
    return closest_enemy


def target_tile(max_range: int | None = None):
    """Return the position of a tile left-clicked in player's FOV (optionally in a range), or (None,None) if right-clicked."""
    if rl.variables.fov_map is None or rl.variables.player is None:
        return
    global key, mouse
    while True:
        # render the screen. this erases the inventory
        # and shows the names of objects under the mouse.
        libtcodpy.console_flush()
        libtcodpy.sys_check_for_event(libtcodpy.EVENT_KEY_PRESS | libtcodpy.EVENT_MOUSE, key, mouse)
        render_all()

        (x, y) = (mouse.cx, mouse.cy)

        if mouse.rbutton_pressed or key.vk == libtcodpy.KEY_ESCAPE:
            return (None, None)  # cancel if the player right-clicked or pressed Escape

        if (
            mouse.lbutton_pressed
            and libtcodpy.map_is_in_fov(rl.variables.fov_map, x, y)
            and (max_range is None or rl.variables.player.distance(x, y) <= max_range)
        ):
            return (x, y)


def target_monster(max_range=None):
    """Returns a clicked monster inside FOV up to a range, or None if right-clicked."""
    while True:
        (x, y) = target_tile(max_range)
        if x is None:  # player cancelled
            return None

        # return the first clicked monster, otherwise continue looping
        for obj in rl.variables.game_objects:
            if obj.x == x and obj.y == y and obj.fighter and obj != rl.variables.player:
                return obj


def player_death(player):
    """The game ended!"""
    rl.common.message("You died!", rl.Colors.RED)
    rl.variables.game_state = "dead"

    # for added effect, transform the player into a corpse!
    player.char = "%"
    player.color = rl.Colors.DARK_RED


def monster_death(monster):
    """Transform it into a nasty corpse! it doesn't block, can't be attacked and doesn't move."""
    rl.common.message(f"The {monster.name} is dead! You gain {str(monster.fighter.xp)} experience points.", rl.Colors.ORANGE)
    monster.char = "%"
    monster.color = rl.Colors.DARK_RED
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = "remains of " + monster.name
    monster.send_to_back()


def create_room(room):
    """Create room."""
    # go through the tiles in the rectangle and make them passable
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            rl.variables.game_map[x][y].blocked = False
            rl.variables.game_map[x][y].block_sight = False


def create_h_tunnel(x1: int, x2: int, y: int):
    """Create horizontal tunnel."""
    # min() and max() are used in case x1>x2
    for x in range(min(x1, x2), max(x1, x2) + 1):
        rl.variables.game_map[x][y].blocked = False
        rl.variables.game_map[x][y].block_sight = False


def create_v_tunnel(y1: int, y2: int, x: int):
    """Create vertical tunnel."""
    for y in range(min(y1, y2), max(y1, y2) + 1):
        rl.variables.game_map[x][y].blocked = False
        rl.variables.game_map[x][y].block_sight = False


def make_map():
    """Fill map with "unblocked" tiles."""
    # the list of objects with just the player
    rl.variables.game_objects = [rl.variables.player]

    rl.variables.game_map = [[rl.Tile(True) for y in range(rl.constants.MAP_HEIGHT)] for x in range(rl.constants.MAP_WIDTH)]

    rooms = []
    num_rooms = 0
    for _ in range(rl.constants.MAX_ROOMS):
        # random width and height
        width = libtcodpy.random_get_int(0, rl.constants.ROOM_MIN_SIZE, rl.constants.ROOM_MAX_SIZE)
        height = libtcodpy.random_get_int(0, rl.constants.ROOM_MIN_SIZE, rl.constants.ROOM_MAX_SIZE)

        # random position without going out of the boundaries of the map
        x = libtcodpy.random_get_int(0, 0, rl.constants.MAP_WIDTH - width - 1)
        y = libtcodpy.random_get_int(0, 0, rl.constants.MAP_HEIGHT - height - 1)

        # "Rect" class makes rectangles easier to work with
        new_room = rl.Rect(x, y, width, height)

        # run through the other rooms and see if they intersect with this one
        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break

        if not failed:
            # this means there are no intersections, so this room is valid

            # "paint" it to the map's tiles
            create_room(new_room)

            # center coordinates of new room, will be useful later
            (new_x, new_y) = new_room.center()
            new_x = int(new_x)
            new_y = int(new_y)

            if num_rooms == 0:
                # this is the first room, where the player starts at
                rl.variables.player.x = new_x
                rl.variables.player.y = new_y
            else:
                # all rooms after the first:
                # connect it to the previous room with a tunnel

                # center coordinates of the previous room
                (prev_x, prev_y) = rooms[num_rooms - 1].center()
                prev_x = int(prev_x)
                prev_y = int(prev_y)

                # draw a coin (random number that is either 0 or 1)
                if libtcodpy.random_get_int(0, 0, 1) == 1:
                    # first move horizontally, then vertically
                    create_h_tunnel(prev_x, new_x, prev_y)
                    create_v_tunnel(prev_y, new_y, new_x)
                else:
                    # first move vertically, then horizontally
                    create_v_tunnel(prev_y, new_y, prev_x)
                    create_h_tunnel(prev_x, new_x, new_y)

            # add some contents to this room, such as monsters
            place_objects(new_room)

            # finally, append the new room to the list
            rooms.append(new_room)
            num_rooms += 1

    # create stairs at the center of the last room
    rl.variables.stairs = rl.Object(new_x, new_y, rl.constants.STAIRSDOWN_TILE, "stairs", rl.Colors.WHITE, always_visible=True)
    rl.variables.game_objects.append(rl.variables.stairs)
    rl.variables.stairs.send_to_back()  # so it's drawn below the monsters


def place_objects(room):
    """Choose random number of monsters."""
    # maximum number of monsters per room
    max_monsters = from_dungeon_level([[2, 1], [3, 4], [5, 6]])
    num_monsters = libtcodpy.random_get_int(0, 0, max_monsters)

    # chance of each monster
    monster_chances = {}
    monster_chances["orc"] = 80  # orc always shows up, even if all other monsters have 0 chance
    monster_chances["troll"] = from_dungeon_level([[15, 3], [30, 5], [60, 7]])
    monster_chances["feral orc"] = from_dungeon_level([[15, 8], [30, 10], [60, 12]])
    monster_chances["feral troll"] = from_dungeon_level([[15, 10], [30, 12], [60, 14]])
    monster_chances["dragon"] = from_dungeon_level([[15, 12], [20, 15]])

    # maximum number of items per room
    max_items = from_dungeon_level([[1, 1], [2, 4]])
    num_items = libtcodpy.random_get_int(0, 0, max_items)

    # chance of each item (by default they have a chance of 0 at level 1, which then goes up)
    item_chances = {}
    item_chances["heal"] = 35  # healing potion always shows up, even if all other items have 0 chance
    item_chances["lightning"] = from_dungeon_level([[25, 4]])
    item_chances["fireball"] = from_dungeon_level([[25, 6]])
    item_chances["confuse"] = from_dungeon_level([[10, 2]])
    item_chances["sword"] = from_dungeon_level([[5, 4]])
    item_chances["sword of awesomeness"] = from_dungeon_level([[5, 10]])
    item_chances["shield"] = from_dungeon_level([[15, 8]])
    item_chances["shield of awesomeness"] = from_dungeon_level([[5, 10]])

    for _ in range(num_monsters):
        # choose random spot for this monster
        x = libtcodpy.random_get_int(0, room.x1 + 1, room.x2 - 1)
        y = libtcodpy.random_get_int(0, room.y1 + 1, room.y2 - 1)

        # only place it if the tile is not blocked
        if not rl.common.is_blocked(x, y):
            choice = random_choice(monster_chances)
            if choice == "orc":
                # create an orc
                fighter_component = rl.Fighter(hp=20, defense=0, power=4, xp=35, death_function=monster_death)
                ai_component = rl.BasicMonster()

                monster = rl.Object(
                    x,
                    y,
                    rl.constants.ORC_TILE,
                    "orc",
                    rl.Colors.DESATURATED_GREEN,
                    blocks=True,
                    fighter=fighter_component,
                    ai=ai_component,
                )
            elif choice == "troll":
                # create a troll
                fighter_component = rl.Fighter(hp=30, defense=2, power=8, xp=100, death_function=monster_death)
                ai_component = rl.BasicMonster()

                monster = rl.Object(
                    x,
                    y,
                    rl.constants.TROLL_TILE,
                    "troll",
                    rl.Colors.DARKER_GREEN,
                    blocks=True,
                    fighter=fighter_component,
                    ai=ai_component,
                )
            elif choice == "feral orc":
                # create a feral orc
                fighter_component = rl.Fighter(hp=25, defense=1, power=6, xp=65, death_function=monster_death)
                ai_component = rl.BasicMonster()

                monster = rl.Object(
                    x,
                    y,
                    rl.constants.ORC_TILE,
                    "feral orc",
                    rl.Colors.CRIMSON,
                    blocks=True,
                    fighter=fighter_component,
                    ai=ai_component,
                )
            elif choice == "feral troll":
                # create a feral troll
                fighter_component = rl.Fighter(hp=40, defense=3, power=10, xp=150, death_function=monster_death)
                ai_component = rl.BasicMonster()

                monster = rl.Object(
                    x,
                    y,
                    rl.constants.TROLL_TILE,
                    "feral troll",
                    rl.Colors.CRIMSON,
                    blocks=True,
                    fighter=fighter_component,
                    ai=ai_component,
                )
            elif choice == "dragon":
                # create a dragon
                fighter_component = rl.Fighter(hp=100, defense=4, power=15, xp=500, death_function=monster_death)
                ai_component = rl.BasicMonster()

                monster = rl.Object(
                    x, y, "$", "dragon", rl.Colors.DARK_RED, blocks=True, fighter=fighter_component, ai=ai_component
                )

            rl.variables.game_objects.append(monster)

    for _ in range(num_items):
        # choose random spot for this item
        x = libtcodpy.random_get_int(0, room.x1 + 1, room.x2 - 1)
        y = libtcodpy.random_get_int(0, room.y1 + 1, room.y2 - 1)

        # only place it if the tile is not blocked
        if not rl.common.is_blocked(x, y):
            choice = random_choice(item_chances)
            if choice == "heal":
                # create a healing potion (70% chance)
                item_component = rl.Item(use_function=cast_heal)

                item = rl.Object(
                    x,
                    y,
                    rl.constants.HEALINGPOTION_TILE,
                    "healing potion",
                    rl.Colors.VIOLET,
                    item=item_component,
                    always_visible=True,
                )
            elif choice == "lightning":
                # create a lightning bolt scroll (10% chance)
                item_component = rl.Item(use_function=cast_lightning)

                item = rl.Object(
                    x, y, "#", "scroll of lightning bolt", rl.Colors.LIGHT_YELLOW, item=item_component, always_visible=True
                )
            elif choice == "fireball":
                # create a fireball scroll (10% chance)
                item_component = rl.Item(use_function=cast_fireball)

                item = rl.Object(
                    x, y, "#", "scroll of fireball", rl.Colors.LIGHT_YELLOW, item=item_component, always_visible=True
                )
            elif choice == "confuse":
                # create a confuse scroll (10% chance)
                item_component = rl.Item(use_function=cast_confuse)

                item = rl.Object(
                    x, y, "#", "scroll of confusion", rl.Colors.LIGHT_YELLOW, item=item_component, always_visible=True
                )
            elif choice == "sword":
                # create a sword
                equipment_component = rl.Equipment(slot="right hand", power_bonus=3)
                item = rl.Object(x, y, rl.constants.SWORD_TILE, "sword", rl.Colors.SKY, equipment=equipment_component)
            elif choice == "shield":
                # create a shield
                equipment_component = rl.Equipment(slot="left hand", defense_bonus=1)
                item = rl.Object(
                    x, y, rl.constants.SHIELD_TILE, "shield", rl.Colors.DARK_ORANGE, equipment=equipment_component
                )
            elif choice == "sword of awesomeness":
                # create a sword of awesomeness
                equipment_component = rl.Equipment(slot="right hand", power_bonus=10)
                item = rl.Object(
                    x, y, rl.constants.SWORD_TILE, "sword of awesomeness", rl.Colors.DARK_SKY, equipment=equipment_component
                )
            elif choice == "shield of awesomeness":
                # create a shield of awesomeness
                equipment_component = rl.Equipment(slot="left hand", defense_bonus=5)
                item = rl.Object(
                    x,
                    y,
                    rl.constants.SHIELD_TILE,
                    "shield of awesomeness",
                    rl.Colors.DARK_AMBER,
                    equipment=equipment_component,
                )

            rl.variables.game_objects.append(item)
            item.send_to_back()  # items appear below other objects
            item.always_visible = True  # items are visible even out-of-FOV, if in an explored area


def random_choice_index(chances):
    """Choose one option from the list of chances, returning its index."""
    # the dice will land on some number between 1 and the sum of the chances
    dice = libtcodpy.random_get_int(0, 1, sum(chances))

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
    """Choose one option from dictionary of chances, returning its key."""
    chances = list(chances_dict.values())
    strings = list(chances_dict.keys())
    return strings[random_choice_index(chances)]


def from_dungeon_level(table):
    """Returns a value that depends on level. The table specifies what value occurs after each level, default is 0."""
    for value, level in reversed(table):
        if rl.variables.dungeon_level >= level:
            return value
    return 0


def render_bar(x, y, total_width, name, value, maximum):
    """Render a bar (HP, experience, etc). first calculate the widt o the bar."""
    if rl.variables.panel is None:
        return
    load_customfont()

    bar_width = int(float(value) / maximum * total_width)

    if bar_width > 0:
        rl.variables.panel.draw_rect(x, y, bar_width, 1, 0, rl.Colors.LIGHT_RED, rl.Colors.DARK_RED, libtcodpy.BKGND_SCREEN)

    # finally, some centered text with the values
    rl.variables.panel.print(
        int(x + total_width / 2),
        y,
        f"{name}: {str(value)}/{str(maximum)}",
        rl.Colors.WHITE,
        rl.Colors.LIGHT_RED,
        libtcodpy.BKGND_NONE,
        libtcodpy.CENTER,
    )


def render_all():
    """Draw all objects in the list."""
    if rl.variables.panel is None or rl.variables.CON is None or rl.variables.fov_map is None:
        return

    if rl.variables.fov_recompute:
        # recompute FOV if needed (the player moved or something)
        rl.variables.fov_recompute = False
        libtcodpy.map_compute_fov(
            rl.variables.fov_map,
            rl.variables.player.x,
            rl.variables.player.y,
            rl.constants.TORCH_RADIUS,
            rl.constants.FOV_LIGHT_WALLS,
            rl.constants.FOV_ALGO,
        )

    # go through all tiles, and set their background color
    for y in range(rl.constants.MAP_HEIGHT):
        for x in range(rl.constants.MAP_WIDTH):
            visible = libtcodpy.map_is_in_fov(rl.variables.fov_map, x, y)
            wall = rl.variables.game_map[x][y].block_sight
            if not visible:
                # if it's not visible right now, the player can only see it if it's explored
                if rl.variables.game_map[x][y].explored:
                    if wall:
                        libtcodpy.console_put_char_ex(
                            rl.variables.CON, x, y, rl.constants.WALL_TILE, rl.Colors.GREY, rl.Colors.BLACK
                        )
                    else:
                        libtcodpy.console_put_char_ex(
                            rl.variables.CON, x, y, rl.constants.FLOOR_TILE, rl.Colors.GREY, rl.Colors.BLACK
                        )
            else:
                # it's visible
                if wall:
                    libtcodpy.console_put_char_ex(
                        rl.variables.CON, x, y, rl.constants.WALL_TILE, rl.Colors.WHITE, rl.Colors.BLACK
                    )
                else:
                    libtcodpy.console_put_char_ex(
                        rl.variables.CON, x, y, rl.constants.FLOOR_TILE, rl.Colors.WHITE, rl.Colors.BLACK
                    )
                # since it's visible, explore it
                rl.variables.game_map[x][y].explored = True

    # draw all objects in the list, except the player. we want it to
    # always appear over all other objects! so it's drawn later.
    for g_object in rl.variables.game_objects:
        if g_object != rl.variables.player:
            g_object.draw()
    rl.variables.player.draw()

    # blit the contents of "con" to the root console
    libtcodpy.console_blit(rl.variables.CON, 0, 0, rl.constants.SCREEN_WIDTH, rl.constants.SCREEN_HEIGHT, 0, 0, 0)

    # prepare to render the GUI panel
    libtcodpy.console_clear(rl.variables.panel)

    # print the game messages, one line at a time
    y = 1
    for line, color in rl.variables.game_msgs:
        rl.variables.panel.print(
            int(rl.constants.MSG_X), y, line, color, rl.Colors.BLACK, libtcodpy.BKGND_NONE, libtcodpy.LEFT
        )
        y += 1

    # show the player's stats
    render_bar(1, 1, rl.constants.BAR_WIDTH, "HP", rl.variables.player.fighter.hp, rl.variables.player.fighter.max_hp)

    rl.variables.panel.print_(1, 3, f"Dungeon level {str(rl.variables.dungeon_level)}", libtcodpy.BKGND_NONE, libtcodpy.LEFT)

    # display names of objects under the mouse
    rl.variables.panel.print(
        1, 0, get_names_under_mouse(), rl.Colors.LIGHT_GREY, rl.Colors.BLACK, libtcodpy.BKGND_NONE, libtcodpy.LEFT
    )

    # blit the contents of "panel" to the root console
    libtcodpy.console_blit(
        rl.variables.panel, 0, 0, rl.constants.SCREEN_WIDTH, rl.constants.PANEL_HEIGHT, 0, 0, rl.constants.PANEL_Y
    )


def player_move_or_attack(dx: int, dy: int) -> None:
    """Move or attach with player."""
    # the coordinates the payer is moving to/attacking
    x = rl.variables.player.x + dx
    y = rl.variables.player.y + dy

    # try to find an attackable object there
    target = None
    for g_object in rl.variables.game_objects:
        if g_object.fighter and g_object.x == x and g_object.y == y:
            target = g_object
            break

    # attack if target found, move otherwise
    if target is not None:
        rl.variables.player.fighter.attack(target)
    else:
        rl.variables.player.move(dx, dy)
        rl.variables.fov_recompute = True


def handle_keys():
    """Handle keyboard movement."""
    global key

    if key.vk == libtcodpy.KEY_ENTER and key.lalt:
        # Alt+Enter: toggle fullscreen
        libtcodpy.console_set_fullscreen(not libtcod.console_is_fullscreen())

    elif key.vk == libtcodpy.KEY_ESCAPE:
        return "exit"  # exit game

    if rl.variables.game_state == "playing":
        # movement keys
        if key.vk == libtcodpy.KEY_UP:
            player_move_or_attack(0, -1)

        elif key.vk == libtcodpy.KEY_DOWN:
            player_move_or_attack(0, 1)

        elif key.vk == libtcodpy.KEY_LEFT:
            player_move_or_attack(-1, 0)

        elif key.vk == libtcodpy.KEY_RIGHT:
            player_move_or_attack(1, 0)

        else:
            # test for other keys
            key_char = chr(key.c)

            if key_char == "g":
                # pick up an item
                for g_object in rl.variables.game_objects:  # look for an item in the player's tile
                    if g_object.x == rl.variables.player.x and g_object.y == rl.variables.player.y and g_object.item:
                        g_object.item.pick_up()
                        break

            if key_char == "i":
                # show the inventory; if an item is selected, use it
                chosen_item = inventory_menu("Press the key next to an item to use it, or any other to cancel.\n")
                if chosen_item is not None:
                    chosen_item.use()

            if key_char == "d":
                # show the inventory; if an item is selected, drop it
                chosen_item = inventory_menu("Press the key next to an item to drop it, or any other to cancel.\n")
                if chosen_item is not None:
                    chosen_item.drop()

            if key_char == "u":
                # go down stairs, if the player is on them
                if rl.variables.stairs.x == rl.variables.player.x and rl.variables.stairs.y == rl.variables.player.y:
                    next_level()

            if key_char == "c":
                # show character information
                level_up_xp = rl.constants.LEVEL_UP_BASE + rl.variables.player.level * rl.constants.LEVEL_UP_FACTOR
                msgbox(
                    "Character Information\n\nLevel "
                    + str(rl.variables.player.level)
                    + "\nExperience: "
                    + str(rl.variables.player.fighter.xp)
                    + "\nExperience to level up: "
                    + str(level_up_xp)
                    + "\n\nMaximum HP: "
                    + str(rl.variables.player.fighter.max_hp)
                    + "\nAttack: "
                    + str(rl.variables.player.fighter.power)
                    + "\nDefense: "
                    + str(rl.variables.player.fighter.defense),
                    rl.constants.CHARACTER_SCREEN_WIDTH,
                )

            return "didnt-take-turn"


def next_level() -> None:
    """Advance to the next level."""
    rl.common.message("You take a moment to rest, and recover your strength.", rl.Colors.LIGHT_VIOLET)
    rl.variables.player.fighter.heal(rl.variables.player.fighter.max_hp / 2)  # heal the player by 50%

    rl.variables.dungeon_level += 1
    rl.common.message("After a rare moment of peace, you descend deeper into the heart of the dungeon...", rl.Colors.RED)
    make_map()  # create a fresh new level!
    initialize_fov()


def get_names_under_mouse() -> str:
    """Return a string with the names of all objects under the mouse."""
    if rl.variables.fov_map is None:
        return
    global mouse

    (x, y) = (mouse.cx, mouse.cy)

    # create a list with the names of all objects at the mouse's coordinates
    names = [
        g_object.name
        for g_object in rl.variables.game_objects
        if g_object.x == x and g_object.y == y and libtcodpy.map_is_in_fov(rl.variables.fov_map, g_object.x, g_object.y)
    ]
    names = ", ".join(names)  # join the names, separated by commas
    return names.capitalize()


def menu(header: str, options: list[str], width: int):
    """Create a menu."""
    max_options = 26
    if len(options) > max_options:
        raise ValueError(f"Cannot have a menu with more than {max_options} options.")

    # calculate total height for the header (after auto-wrap) and one line per option
    header_height = libtcodpy.console_get_height_rect(rl.variables.CON, 0, 0, width, rl.constants.SCREEN_HEIGHT, header)
    if header == "":
        header_height = 0
    height = len(options) + header_height

    # create an off-screen console that represents the menu's window
    window = libtcod.console.Console(width, height)

    # print the header, with auto-wrap
    window.default_fg = rl.Colors.WHITE
    window.print_rect(0, 0, width, height, header, libtcodpy.BKGND_NONE, libtcodpy.LEFT)

    # print all the options
    y = header_height
    letter_index = ord("a")
    for option_text in options:
        text = "(" + chr(letter_index) + ")" + option_text
        window.print_(0, y, text, libtcodpy.BKGND_NONE, libtcodpy.LEFT)
        y += 1
        letter_index += 1

    # blit the contents of "window" to the root console
    x = rl.constants.SCREEN_WIDTH / 2 - width / 2
    y = rl.constants.SCREEN_HEIGHT / 2 - height / 2
    libtcodpy.console_blit(window, 0, 0, width, height, 0, int(x), int(y), 1.0, 0.7)

    # present the root console to the player and wait for a key-press
    libtcodpy.console_flush()
    key = libtcodpy.console_wait_for_keypress(True)
    if key.vk == libtcodpy.KEY_ENTER and key.lalt:  # (special case) Alt+Enter: toggle fullscreen
        libtcodpy.console_set_fullscreen(not libtcod.console_is_fullscreen())

    # convert the ASCII code to an index; if it corresponds to an option, return it
    index = key.c - ord("a")
    if index >= 0 and index < len(options):
        return index
    return None


def inventory_menu(header: str) -> rl.Item | None:
    """Show a menu with each item of the inventory as an option."""
    if len(rl.variables.inventory) == 0:
        options = ["Inventory is empty."]
    else:
        options = []
        for item in rl.variables.inventory:
            text = item.name
            # show additional information, in case it's equipped
            if item.equipment and item.equipment.is_equipped:
                text = text + " (on " + item.equipment.slot + ")"
            options.append(text)

    index = menu(header, options, rl.constants.INVENTORY_WIDTH)

    # if an item was chosen, return it
    if index is None or len(rl.variables.inventory) == 0:
        return None
    return rl.variables.inventory[index].item


def new_game() -> None:
    """Create a new game."""
    # create object representing the player
    fighter_component = rl.Fighter(hp=100, defense=1, power=2, xp=0, death_function=player_death)
    rl.variables.player = rl.Object(
        0, 0, rl.constants.PLAYER_TILE, "player", rl.Colors.WHITE, blocks=True, fighter=fighter_component
    )

    rl.variables.player.level = 1

    # generate map (at this point it's not drawn to the screen)
    rl.variables.dungeon_level = 1
    make_map()
    initialize_fov()

    rl.variables.game_state = "playing"
    rl.variables.inventory = []

    # create the list of game messages and their colors, starts empty
    rl.variables.game_msgs = []

    # a warm welcoming message!
    rl.common.message("Welcome stranger! Prepare to perish in the Tombs of the Ancient Kings.", rl.Colors.RED)

    # initial equipment: a dagger
    equipment_component = rl.Equipment(slot="right hand", power_bonus=2)
    obj = rl.Object(0, 0, rl.constants.DAGGER_TILE, "dagger", rl.Colors.SKY, equipment=equipment_component)
    rl.variables.inventory.append(obj)
    equipment_component.equip()
    obj.always_visible = True


def initialize_fov() -> None:
    """Initialize field of view."""
    # create the FOV map, according to the generated map
    rl.variables.fov_map = libtcodpy.map_new(rl.constants.MAP_WIDTH, rl.constants.MAP_HEIGHT)
    for y in range(rl.constants.MAP_HEIGHT):
        for x in range(rl.constants.MAP_WIDTH):
            libtcodpy.map_set_properties(
                rl.variables.fov_map,
                x,
                y,
                not rl.variables.game_map[x][y].block_sight,
                not rl.variables.game_map[x][y].blocked,
            )

    if rl.variables.CON is not None:
        libtcodpy.console_clear(rl.variables.CON)  # unexplored areas start black (which is the default background color)
    rl.variables.fov_recompute = True


def play_game() -> None:
    """Play the game."""
    global key, mouse

    player_action = None

    mouse = libtcodpy.Mouse()
    key = libtcodpy.Key()
    while not libtcodpy.console_is_window_closed():
        # render the screen
        libtcodpy.sys_check_for_event(libtcodpy.EVENT_KEY_PRESS | libtcodpy.EVENT_MOUSE, key, mouse)
        render_all()

        libtcodpy.console_flush()

        check_level_up()

        # erase all objects at their old locations, before they move
        for obj in rl.variables.game_objects:
            obj.clear()

        # handle keys and exit game if needed
        player_action = handle_keys()
        if player_action == "exit":
            save_game()
            break

        # let monsters take their turn
        if rl.variables.game_state == "playing" and player_action != "didnt-take-turn":
            for obj in rl.variables.game_objects:
                if obj.ai:
                    obj.ai.take_turn()


def main_menu() -> None:
    """Create a main menu."""
    img = libtcodpy.image_load("menu_background.png")

    while not libtcodpy.console_is_window_closed():
        # show the background image, at twice the regular console resolution
        libtcodpy.image_blit_2x(img, 0, 0, 0)

        # show the game's title, and some credits!
        libtcodpy.console_set_default_foreground(0, rl.Colors.YELLOW)
        libtcodpy.console_print_ex(
            0,
            int(rl.constants.SCREEN_WIDTH / 2),
            int(rl.constants.SCREEN_HEIGHT / 2 - 4),
            libtcodpy.BKGND_NONE,
            libtcodpy.CENTER,
            "TOMBS OF THE ANCIENT KINGS",
        )
        libtcodpy.console_print_ex(
            0,
            int(rl.constants.SCREEN_WIDTH / 2),
            int(rl.constants.SCREEN_HEIGHT - 2),
            libtcodpy.BKGND_NONE,
            libtcodpy.CENTER,
            "By Alf",
        )

        # show options and wait for the player's choice
        choice = menu("", ["Play a new game", "Continue last game", "Quit"], 24)

        if choice == 0:  # new game
            new_game()
            play_game()
        if choice == 1:  # load last game
            try:
                load_game()
            except:  # noqa: E722
                msgbox("\n No saved game to load.\n", 24)
                continue
            play_game()
        elif choice == 2:  # quit
            break


def msgbox(text: str, width: int = 50) -> None:
    """Create a message box."""
    menu(text, [], width)  # use menu() as a sort of "message box"


def save_game() -> None:
    """Open a new empty shelve (possibly overwriting an old one) to write the game data."""
    file = shelve.open("savegame", "n")
    file["game_map"] = rl.variables.game_map
    file["game_objects"] = rl.variables.game_objects
    file["player_index"] = rl.variables.game_objects.index(rl.variables.player)  # index of player in objects lists
    file["stairs_index"] = rl.variables.game_objects.index(rl.variables.stairs)
    file["dungeon_level"] = rl.variables.dungeon_level
    file["inventory"] = rl.variables.inventory
    file["game_msgs"] = rl.variables.game_msgs
    file["game_state"] = rl.variables.game_state
    file.close()


def load_game() -> None:
    """Open the previously saved shelve and load the game data."""
    file = shelve.open("savegame", "r")
    rl.variables.game_map = file["game_map"]
    rl.variables.game_objects = file["game_objects"]
    rl.variables.player = rl.variables.game_objects[file["player_index"]]  # get index of player in objects list and access it
    rl.variables.stairs = rl.variables.game_objects[file["stairs_index"]]
    rl.variables.dungeon_level = file["dungeon_level"]
    rl.variables.inventory = file["inventory"]
    rl.variables.game_msgs = file["game_msgs"]
    rl.variables.game_state = file["game_state"]
    file.close()

    initialize_fov()


def load_customfont() -> None:
    """The index of the first custom tile in the file."""
    a = 256

    # The "y" is the row index, here we load the sixth row in the font file.
    # Increase the "6" to load any new rows from the file.
    for y in range(5, 6):
        libtcodpy.console_map_ascii_codes_to_font(a, 32, 0, y)
        a += 32


#############################################
# Initialization & Main Loop
#############################################

# The font has 32 chars in a row, and there's a total of 10 rows.
# Increase the "10" when you add new rows to the sample font file.
libtcodpy.console_set_custom_font("TiledFont.png", libtcodpy.FONT_TYPE_GREYSCALE | libtcodpy.FONT_LAYOUT_TCOD, 32, 10)
libtcodpy.console_init_root(rl.constants.SCREEN_WIDTH, rl.constants.SCREEN_HEIGHT, "python/roguebasin_tombs", False)
libtcodpy.sys_set_fps(rl.constants.LIMIT_FPS)
rl.variables.CON = libtcod.console.Console(rl.constants.MAP_WIDTH, rl.constants.MAP_HEIGHT)
rl.variables.panel = libtcod.console.Console(rl.constants.SCREEN_WIDTH, rl.constants.PANEL_HEIGHT)

main_menu()
