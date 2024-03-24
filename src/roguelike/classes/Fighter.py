"""Fighter class."""

from collections.abc import Callable

from ..support import variables as var
from ..support.common import get_all_equipped, message


class Fighter:
    """combat-related properties and methods (monster, player, NPC)."""

    def __init__(self, hp: int, defense: int, power: int, xp: int, death_function: Callable | None = None):
        self.base_max_hp: int = hp
        self.hp: int = hp
        self.base_defense: int = defense
        self.base_power: int = power
        self.xp: int = xp
        self.death_function: Callable | None = death_function

    @property
    def power(self) -> int:
        """Return actual power, by summing up the bonuses from all equipped items."""
        bonus = sum(equipment.power_bonus for equipment in get_all_equipped(self.owner))
        return self.base_power + bonus

    @property
    def defense(self) -> int:
        """Return actual defense, by summing up the bonuses from all equipped items."""
        bonus = sum(equipment.defense_bonus for equipment in get_all_equipped(self.owner))
        return self.base_defense + bonus

    @property
    def max_hp(self) -> int:
        """Return actual max_hp, by summing up the bonuses from all equipped items."""
        bonus = sum(equipment.max_hp_bonus for equipment in get_all_equipped(self.owner))
        return self.base_max_hp + bonus

    def attack(self, target) -> None:
        """A simple formula for attack damage."""
        damage = self.power - target.fighter.defense

        if damage > 0:
            # make the target take some damage
            message(self.owner.name.capitalize() + " attacks " + target.name + " for " + str(damage) + " hit points.")
            target.fighter.take_damage(damage)
        else:
            message(self.owner.name.capitalize() + " attacks " + target.name + " but it has no effect!")

    def take_damage(self, damage: int) -> None:
        """Apply damage if possible."""
        if damage > 0:
            self.hp -= damage

            # check for death. if there's a death function, call it
            if self.hp <= 0:
                function = self.death_function
                if function is not None:
                    function(self.owner)
                if self.owner != var.player:  # yield experience to the player
                    var.player.fighter.xp += self.xp

    def heal(self, amount: int) -> None:
        """Heal by the given amount, without going over the maximum."""
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp
