"""Support file with common help functions"""
import support.variables as var

def is_blocked(x, y):
    """first test the map tile"""
    if var.game_map[x][y].blocked:
        return True

    #now check for any blocking objects
    for g_object in var.game_objects:
        if g_object.blocks and g_object.x == x and g_object.y == y:
            return True

    return False
