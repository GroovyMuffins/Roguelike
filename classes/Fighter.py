"""Fighter class"""
import support.variables as var
from support.common import message, get_all_equipped

class Fighter:
    """combat-related properties and methods (monster, player, NPC)"""
    def __init__(self, hp, defense, power, xp, death_function=None):
        self.base_max_hp = hp
        self.hp = hp
        self.base_defense = defense
        self.base_power = power
        self.xp = xp
        self.death_function = death_function

    @property
    def power(self):
        """Return actual power, by summing up the bonuses from all equipped items"""
        bonus = sum(equipment.power_bonus for equipment in get_all_equipped(self.owner))
        return self.base_power + bonus

    @property
    def defense(self):
        """Return actual defense, by summing up the bonuses from all equipped items"""
        bonus = sum(equipment.defense_bonus for equipment in get_all_equipped(self.owner))
        return self.base_defense + bonus

    @property
    def max_hp(self):
        """Return actual max_hp, by summing up the bonuses from all equipped items"""
        bonus = sum(equipment.max_hp_bonus for equipment in get_all_equipped(self.owner))
        return self.base_max_hp + bonus

    def attack(self, target):
        """a simple formula for attack damage"""
        damage = self.power - target.fighter.defense

        if damage > 0:
            #make the target take some damage
            message(self.owner.name.capitalize() + ' attacks ' + target.name\
                + ' for ' + str(damage) + ' hit points.')
            target.fighter.take_damage(damage)
        else:
            message(self.owner.name.capitalize() + ' attacks ' + target.name\
                + ' but it has no effect!')

    def take_damage(self, damage):
        """apply damage if possible"""
        if damage > 0:
            self.hp -= damage

            #check for death. if there's a death function, call it
            if self.hp <= 0:
                function = self.death_function
                if function is not None:
                    function(self.owner)
                if self.owner != var.player: # yield experience to the player
                    var.player.fighter.xp += self.xp

    def heal(self, amount):
        """heal by the given amount, without going over the maximum"""
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp
