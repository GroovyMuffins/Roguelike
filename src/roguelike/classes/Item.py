"""Item class."""

from dataclasses import dataclass
from typing import Any

from ..support import variables as var
from ..support.colors import Colors
from ..support.common import get_equipped_in_slot, message


@dataclass
class Item:
    """Class containing item objects."""

    use_function: Any = None

    def use(self) -> None:
        """Just call the "use_function" if it is defined.

        special case: if the object has the Equipment component,
        the "use" action is to equip/dequip
        """
        if self.owner.equipment:
            self.owner.equipment.toggle_equip()
            return

        if self.use_function is None:
            message("The " + self.owner.name + " cannot be used.")
        elif self.use_function() != "cancelled":
            # destroy after use, unless it was cancelled for some reason
            var.inventory.remove(self.owner)

    def pick_up(self) -> None:
        """Add to the player's inventory and remove from the map."""
        max_inventory = 26
        if len(var.inventory) >= max_inventory:
            message("Your inventory is full, cannot pick up " + self.owner.name + ".", Colors.RED)
        else:
            var.inventory.append(self.owner)
            var.game_objects.remove(self.owner)
            message("You picked up a " + self.owner.name + "!", Colors.GREEN)

        # special case: automatically equip, if the corresponding equipment slot is unused
        equipment = self.owner.equipment
        if equipment and get_equipped_in_slot(equipment.slot) is None:
            equipment.equip()

    def drop(self) -> None:
        """Add to the map and remove from the player's inventory. Also, place it at the player's coordinates."""
        var.game_objects.append(self.owner)
        var.inventory.remove(self.owner)
        self.owner.x = var.player.x
        self.owner.y = var.player.y
        message("You dropped a " + self.owner.name + ".", Colors.YELLOW)

        # special case: if the object has the Equipment component, dequip it before dropping
        if self.owner.equipment:
            self.owner.equipment.dequip()
