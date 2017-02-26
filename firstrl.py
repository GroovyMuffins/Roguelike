#!/c/Python27/python
"""This module sets up initial rogue basin game."""
import libtcodpy as libtcod

#actual size of the window
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

LIMIT_FPS = 20 #20 frames-per-second maximum


def handle_keys():
    """Handle keyboard movement."""
    global PLAYERX, PLAYERY

    key = libtcod.console_check_for_keypress() #real-time
    # key = libtcod.console_wait_for_keypress(true) #turn-based

    if key.vk == libtcod.KEY_ENTER and key.lalt:
        #Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    elif key.vk == libtcod.KEY_ESCAPE:
        return True #exit game

    #movement keys
    if libtcod.console_is_key_pressed(libtcod.KEY_UP):
        PLAYERY -= 1

    elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN):
        PLAYERY += 1

    elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT):
        PLAYERX -= 1

    elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT):
        PLAYERX += 1


#############################################
# Initialization & Main Loop
#############################################

libtcod.console_set_custom_font('arial10x10.png', \
    libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python/libtcod tutorial', False)
libtcod.sys_set_fps(LIMIT_FPS)

PLAYERX = SCREEN_WIDTH/2
PLAYERY = SCREEN_HEIGHT/2

while not libtcod.console_is_window_closed():
    libtcod.console_set_default_foreground(0, libtcod.white)
    libtcod.console_put_char(0, PLAYERX, PLAYERY, '@', libtcod.BKGND_NONE)

    libtcod.console_flush()

    libtcod.console_put_char(0, PLAYERX, PLAYERY, ' ', libtcod.BKGND_NONE)

    #handle keys and exit game if needed
    EXIT = handle_keys()
    if EXIT:
        break
