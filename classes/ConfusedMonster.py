"""Confused monster class"""
import libtcodpy as libtcod
import support.variables as var
from support.common import message

class ConfusedMonster:
    """AI for a temporarily confused monster (reerts to previous AI after a while)."""
    def __init__(self, old_ai, num_turns=var.CONFUSE_NUM_TURNS):
        self.old_ai = old_ai
        self.num_turns = num_turns

    def take_turn(self):
        """AI for a confused monster."""
        if self.num_turns > 0: #still confused...
            #move in a random direction, and decrease the number of turns confused
            self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
            self.num_turns -= 1
        #restore the previous AI (this one will be deleted because it's not referenced anymore)
        else:
            self.owner.ai = self.old_ai
            message('The ' + self.owner.name + ' is no longer confused!', libtcod.red)
