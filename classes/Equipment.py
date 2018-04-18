"""Equipment class"""
import libtcodpy as libtcod
from support.common import get_equipped_in_slot, message

class Equipment:
    """An object that can be equipped, yielding bonuses.
    Automatically adds the Item component."""
    def __init__(self, slot, power_bonus=0, defense_bonus=0, max_hp_bonus=0):
        self.slot = slot
        self.is_equipped = False
        self.power_bonus = power_bonus
        self.defense_bonus = defense_bonus
        self.max_hp_bonus = max_hp_bonus

    def toggle_equip(self):
        """Toggle equip/dequip status"""
        if self.is_equipped:
            self.dequip()
        else:
            self.equip()

    def equip(self):
        """Equip equipment"""
        # if the slot is already being used, dequip whatever is there first
        old_equipment = get_equipped_in_slot(self.slot)
        if old_equipment is not None:
            old_equipment.dequip()

        # equip object and show a message about it
        self.is_equipped = True
        message('Equipped ' + self.owner.name + ' on ' + self.slot + '.',\
            libtcod.light_green)

    def dequip(self):
        """Dequip object and show a mesage about it"""
        if not self.is_equipped:
            return
        self.is_equipped = False
        message('Dequipped ' + self.owner.name + ' from ' + self.slot + '.',\
            libtcod.light_yellow)
