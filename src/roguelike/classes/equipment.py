"""Equipment class."""

from dataclasses import dataclass
from typing import Any

from ..support.colors import Colors
from ..support.common import get_equipped_in_slot, message


@dataclass
class Equipment:
    """An object that can be equipped, yielding bonuses. Automatically adds the Item component."""

    slot: Any = None
    is_equipped: bool = False
    power_bonus: int = 0
    defense_bonus: int = 0
    max_hp_bonus: int = 0

    def toggle_equip(self) -> None:
        """Toggle equip/dequip status."""
        if self.is_equipped:
            self.dequip()
        else:
            self.equip()

    def equip(self) -> None:
        """Equip equipment."""
        # if the slot is already being used, dequip whatever is there first
        old_equipment = get_equipped_in_slot(self.slot)
        if old_equipment is not None:
            old_equipment.dequip()

        # equip object and show a message about it
        self.is_equipped = True
        message("Equipped " + self.owner.name + " on " + self.slot + ".", Colors.LIGHT_GREEN)

    def dequip(self) -> None:
        """Dequip object and show a mesage about it."""
        if not self.is_equipped:
            return
        self.is_equipped = False
        message("Dequipped " + self.owner.name + " from " + self.slot + ".", Colors.LIGHT_YELLOW)
