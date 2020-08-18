"""Support file with common help functions"""
import tcod as libtcod
import support.variables as var
import textwrap

def get_equipped_in_slot(slot):
    """Returns the equipment in a slot, or None if it's empty"""
    for obj in var.inventory:
        if obj.equipment and obj.equipment.slot == slot and obj.equipment.is_equipped:
            return obj.equipment
    return None

def message(new_msg, color=libtcod.white):
    """split the message if necessary, among multiple lines"""
    new_msg_lines = textwrap.wrap(new_msg, var.MSG_WIDTH)

    for line in new_msg_lines:
        #if the buffer is full, remove the first line to make room for the new one
        if len(var.game_msgs) == var.MSG_HEIGHT:
            del var.game_msgs[0]

        # add the new line as a tuple, with the tex and the color
        var.game_msgs.append((line, color))

def get_all_equipped(obj):
    """Returns a list of equipped items"""
    if obj == var.player:
        equipped_list = []
        for item in var.inventory:
            if item.equipment and item.equipment.is_equipped:
                equipped_list.append(item.equipment)
        return equipped_list
    else:
        return [] # other objects have no equipment

def is_blocked(x, y):
    """first test the map tile"""
    if var.game_map[x][y].blocked:
        return True

    #now check for any blocking objects
    for g_object in var.game_objects:
        if g_object.blocks and g_object.x == x and g_object.y == y:
            return True

    return False
