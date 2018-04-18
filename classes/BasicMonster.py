"""Class for basic monster"""
import libtcodpy as libtcod
import support.variables as var

class BasicMonster:
    """AI for a basic monster."""
    def take_turn(self):
        """a basic monster takes its turn. If you can see it, it can see you"""
        monster = self.owner
        if libtcod.map_is_in_fov(var.fov_map, monster.x, monster.y):

            #move towards player if far away
            if monster.distance_to(var.player) >= 2:
                monster.move_towards(var.player.x, var.player.y)

            #close enough, attack! (if the player is still alive.)
            elif var.player.fighter.hp > 0:
                monster.fighter.attack(var.player)
