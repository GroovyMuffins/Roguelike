"""Confused monster class"""
from dataclasses import dataclass
import support.variables as var
from support.common import message
import tcod as libtcod
from typing import Any

@dataclass
class ConfusedMonster:
    """AI for a temporarily confused monster (reverts to previous AI after a while)."""
    old_ai: Any
    num_turns: int = var.CONFUSE_NUM_TURNS

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
