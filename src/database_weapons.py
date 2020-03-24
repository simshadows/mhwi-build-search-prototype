# -*- coding: ascii -*-

"""
Filename: database_weapons.py
Author:   contact@simshadows.com

This file provides the MHWI build optimizer script's weapons database.
"""

import json
from abc import ABC, abstractmethod
from collections import namedtuple
from itertools import accumulate, product
from enum import Enum, auto
from copy import copy

from .database_skills import SetBonus

from .utils import json_read


# Corresponds to each level from red through to purple, in increasing-modifier order.
SHARPNESS_LEVEL_NAMES   = ("Red", "Orange", "Yellow", "Green", "Blue", "White", "Purple")
RAW_SHARPNESS_MODIFIERS = (0.5,   0.75,     1.0,      1.05,    1.2,    1.32,    1.39    )


WEAPONS_DATA_FILENAME = "data/database_weapons.json"


# These work by first representing the full bar at maximum Handicraft in terms of number of
# points in each colour, then you subtract 10 points per Handicraft level missing.
MaximumSharpness = namedtuple("MaximumSharpness", ["red", "orange", "yellow", "green", "blue", "white", "purple"])


WeaponAugmentsContribution = namedtuple(
    "WeaponAugmentsContribution",
    [
        "added_attack_power",
        "added_raw_affinity",
        "extra_decoration_slot_level",
    ],
)
class WeaponAugmentTracker(ABC):

    @classmethod
    def get_instance(cls, weapon):
        #assert isinstance(weapon, namedtuple) # TODO: Make a proper assertion.
        if weapon.augmentation_scheme is WeaponAugmentationScheme.ICEBORNE:
            return IBWeaponAugmentTracker(weapon.rarity)
        elif weapon.augmentation_scheme is WeaponAugmentationScheme.NONE:
            return NoWeaponAugments()
        else:
            raise RuntimeError(f"Augmentation scheme {weapon.augmentation_scheme} not supported.")

    @classmethod
    def get_maximized_trackers(cls, weapon, *, health_regen_minimum):
        trackers = []

        bare_tracker = cls.get_instance(weapon)
        for config_obj in bare_tracker.get_maximized_configs(health_regen_minimum=health_regen_minimum):
            tracker = cls.get_instance(weapon)
            tracker.update_with_config(config_obj)
            trackers.append(tracker)

        return trackers

    # TODO: Use something better, like the __copy__() method.
    @abstractmethod
    def copy(self):
        raise NotImplementedError

    # Outputs some arbitrary structure.
    #
    # This function is only really intended for diagnostic purposes for now, but will be given more important roles
    # later. I'll properly define the structure then.
    @abstractmethod
    def get_config(self):
        raise NotImplementedError

    # Similar to get_config(), but this returns an arbitrary string that the class can read to restore to the same augments.
    @abstractmethod
    def get_serialized_config(self):
        raise NotImplementedError

    # Gives back a WeaponAugmentsContribution namedtuple with all the values the current
    # set of augments contributes to the build.
    @abstractmethod
    def calculate_contribution(self):
        raise NotImplementedError

    # Gives back a list of arbitrary things describing all the possible maximum configurations.
    # You can pass one of these things to update_with_config.
    #
    # health_regen_minimum is the minimum level we need it to be.
    @abstractmethod
    def get_maximized_configs(self, health_regen_minimum=0):
        raise NotImplementedError

    # Set the config to the selected config.
    @abstractmethod
    def update_with_config(self, selected_config):
        raise NotImplementedError

    # Similar to update_with_config(), but you get a string returned by get_serialized_config().
    @abstractmethod
    def update_with_serialized_config(self, serialized_config):
        raise NotImplementedError


class NoWeaponAugments(WeaponAugmentTracker):

    MAGIC_WORD = "NoWeaponAugments"

    def copy(self):
        return self # It shouldn't matter at all

    def get_config(self):
        return []

    def get_serialized_config(self):
        return self.MAGIC_WORD

    def calculate_contribution(self):
        ret = WeaponAugmentsContribution (
                added_attack_power = 0,
                added_raw_affinity = 0,
                extra_decoration_slot_level = 0,
            )
        return ret

    def get_maximized_configs(self, health_regen_minimum=0):
        if health_regen_minimum > 0:
            return []
        else:
            return None # Not possible to add health regen.

    def update_with_config(self, selected_config):
        raise RuntimeError("Can't update the augments of a weapon that can't be augmented.")

    def update_with_serialized_config(self, serialized_config):
        assert serialized_config == self.MAGIC_WORD
        return


class IBWeaponAugmentType(Enum):
    AUGMENT_LEVEL             = auto() # This one's not really an augment.

    ATTACK_INCREASE           = auto()
    AFFINITY_INCREASE         = auto()
    #DEFENSE_INCREASE         = auto() # I'm just gonna pretend these don't exist yet...
    SLOT_UPGRADE              = auto()
    HEALTH_REGEN              = auto()
    #ELEMENT_STATUS_EFFECT_UP = auto()

class IBWeaponAugmentTracker(WeaponAugmentTracker):

    __slots__ = [
            "auto_maximize",
            "_rarity",
            "_aug_level",
            "_augments",
        ]

    IB_AUGMENTATION_SLOTS = {
            10: [5, 7, 9],
            11: [4, 5, 6],
            12: [3, 4, 5],
        }

    IB_SLOT_CONSUMPTIONS = {
            IBWeaponAugmentType.ATTACK_INCREASE           : [3, 2, 2, 2],
            IBWeaponAugmentType.AFFINITY_INCREASE         : [2, 2, 2, 2],
            #IBWeaponAugmentType.DEFENSE_INCREASE         : [1, 1, 1, 2],
            IBWeaponAugmentType.SLOT_UPGRADE              : [3, 3, 1, 1],
            IBWeaponAugmentType.HEALTH_REGEN              : [3, 2, 2, 2],
            #IBWeaponAugmentType.ELEMENT_STATUS_EFFECT_UP : [1, 2, 2, 2],
        }

    IB_ATTACK_AUGMENT_VALUES               = (0, 5,  5, 5, 5)
    IB_AFFINITY_AUGMENT_VALUES_PERCENTAGES = (0, 10, 5, 5, 5)
    #                                level =  0  1   2  3  4

    IB_SLOT_CONSUMPTIONS_CUMULATIVE = {k: list(accumulate(v)) for (k, v) in IB_SLOT_CONSUMPTIONS.items()}

    IB_ATTACK_AUGMENT_CUMULATIVE               = tuple(accumulate(IB_ATTACK_AUGMENT_VALUES))
    IB_AFFINITY_AUGMENT_PERCENTAGES_CUMULATIVE = tuple(accumulate(IB_AFFINITY_AUGMENT_VALUES_PERCENTAGES))

    # {rarity: [config]}
    _MAXIMIZED_CONFIGS_NOHEALTHREGEN = { # TODO: Consider automating this definition.
            10: [
                # Start without slots
                [
                    (IBWeaponAugmentType.ATTACK_INCREASE, 4),
                ],
                [
                    (IBWeaponAugmentType.ATTACK_INCREASE  , 3),
                    (IBWeaponAugmentType.AFFINITY_INCREASE, 1),
                ],
                [
                    (IBWeaponAugmentType.ATTACK_INCREASE  , 2),
                    (IBWeaponAugmentType.AFFINITY_INCREASE, 2),
                ],
                [
                    (IBWeaponAugmentType.ATTACK_INCREASE  , 1),
                    (IBWeaponAugmentType.AFFINITY_INCREASE, 3),
                ],
                [
                    (IBWeaponAugmentType.AFFINITY_INCREASE, 4),
                ],
                # Add one slot upgrade
                [
                    (IBWeaponAugmentType.ATTACK_INCREASE,   2),
                    (IBWeaponAugmentType.SLOT_UPGRADE,      1),
                ],
                [
                    (IBWeaponAugmentType.ATTACK_INCREASE,   1),
                    (IBWeaponAugmentType.AFFINITY_INCREASE, 1),
                    (IBWeaponAugmentType.SLOT_UPGRADE,      1),
                ],
                [
                    (IBWeaponAugmentType.AFFINITY_INCREASE, 3),
                    (IBWeaponAugmentType.SLOT_UPGRADE,      1),
                ],
                # Add two or three slot upgrades
                [
                    (IBWeaponAugmentType.ATTACK_INCREASE,   1),
                    (IBWeaponAugmentType.SLOT_UPGRADE,      2),
                ],
                [
                    (IBWeaponAugmentType.AFFINITY_INCREASE, 1),
                    (IBWeaponAugmentType.SLOT_UPGRADE,      3),
                ],
                # All slot upgrades
                [
                    (IBWeaponAugmentType.SLOT_UPGRADE,      4),
                ],
            ],
            11: [
                # Start without slots
                [
                    (IBWeaponAugmentType.ATTACK_INCREASE,   2),
                ],
                [
                    (IBWeaponAugmentType.ATTACK_INCREASE  , 1),
                    (IBWeaponAugmentType.AFFINITY_INCREASE, 1),
                ],
                [
                    (IBWeaponAugmentType.AFFINITY_INCREASE, 3),
                ],
                # Add one slot upgrade
                [
                    (IBWeaponAugmentType.ATTACK_INCREASE,   1),
                    (IBWeaponAugmentType.SLOT_UPGRADE,      1),
                ],
                [
                    (IBWeaponAugmentType.AFFINITY_INCREASE, 1),
                    (IBWeaponAugmentType.SLOT_UPGRADE,      1),
                ],
                # All slot upgrades
                [
                    (IBWeaponAugmentType.SLOT_UPGRADE,      2),
                ],
            ],
            12: [
                # Start without slots
                [
                    (IBWeaponAugmentType.ATTACK_INCREASE, 2),
                ],
                [
                    (IBWeaponAugmentType.ATTACK_INCREASE  , 1),
                    (IBWeaponAugmentType.AFFINITY_INCREASE, 1),
                ],
                [
                    (IBWeaponAugmentType.AFFINITY_INCREASE, 2),
                ],
                # Add one slot upgrade
                [
                    (IBWeaponAugmentType.AFFINITY_INCREASE, 1),
                    (IBWeaponAugmentType.SLOT_UPGRADE,      1),
                ],
                # That's about all you can do.
            ],
        }

    _MAXIMIZED_CONFIGS_WITHHEALTHREGEN = { # TODO: Consider automating this definition.
            10: [
                # Start without slots
                [
                    (IBWeaponAugmentType.HEALTH_REGEN,      1),
                    (IBWeaponAugmentType.ATTACK_INCREASE,   2),
                ],
                [
                    (IBWeaponAugmentType.HEALTH_REGEN,      1),
                    (IBWeaponAugmentType.ATTACK_INCREASE,   1),
                    (IBWeaponAugmentType.AFFINITY_INCREASE, 1),
                ],
                [
                    (IBWeaponAugmentType.HEALTH_REGEN,      1),
                    (IBWeaponAugmentType.AFFINITY_INCREASE, 3),
                ],
                # Add one slot upgrade
                [
                    (IBWeaponAugmentType.HEALTH_REGEN,      1),
                    (IBWeaponAugmentType.SLOT_UPGRADE,      1),
                    (IBWeaponAugmentType.ATTACK_INCREASE,   1),
                ],
                [
                    (IBWeaponAugmentType.HEALTH_REGEN,      1),
                    (IBWeaponAugmentType.SLOT_UPGRADE,      1),
                    (IBWeaponAugmentType.AFFINITY_INCREASE, 1),
                ],
                # Max out slot upgrade
                [
                    (IBWeaponAugmentType.HEALTH_REGEN,      1),
                    (IBWeaponAugmentType.SLOT_UPGRADE,      2),
                ],
            ],
            11: [
                # Start without slots
                [
                    (IBWeaponAugmentType.HEALTH_REGEN,      1),
                    (IBWeaponAugmentType.ATTACK_INCREASE,   1),
                ],
                [
                    (IBWeaponAugmentType.HEALTH_REGEN,      1),
                    (IBWeaponAugmentType.AFFINITY_INCREASE, 1),
                ],
                # Add a slot upgrade
                [
                    (IBWeaponAugmentType.HEALTH_REGEN,      1),
                    (IBWeaponAugmentType.SLOT_UPGRADE,      1),
                ],
                # Can't add more slot upgrades.
            ],
            12: [
                # There's literally nothing else you can do
                [
                    (IBWeaponAugmentType.HEALTH_REGEN,      1),
                    (IBWeaponAugmentType.AFFINITY_INCREASE, 1),
                ],
            ],
        }

    def __init__(self, rarity, auto_maximize=True):
        assert isinstance(rarity, int)
        assert isinstance(auto_maximize, bool)

        if auto_maximize == False:
            raise NotImplementedError("Only works with auto-maximize on for now.")
            # To implement auto_maximize==False, we'd need to actually allow lower augment levels.

        self._auto_maximize = auto_maximize

        self._rarity    = rarity
        self._aug_level = 2
        self._augments  = {} # {IBWeaponAugmentType: int}

        assert self._state_is_valid()
        return

    def copy(self):
        new = copy(self)
        new._augments = copy(self._augments)
        assert new._state_is_valid()
        return new

    def get_config(self):
        return list(self._augments.items())

    def get_serialized_config(self):
        augments = {k.name: v for (k, v) in self._augments.items()}

        data = {
                "rarity": self._rarity,
                "aug_level": self._aug_level,
                "augments": augments,
            }
        serialized_data = json.dumps(data)
        assert isinstance(serialized_data, str)
        return serialized_data

    def calculate_contribution(self):
        attack_level = self._augments.get(IBWeaponAugmentType.ATTACK_INCREASE, 0)
        affinity_level = self._augments.get(IBWeaponAugmentType.AFFINITY_INCREASE, 0)
        decoration_slot_level = self._augments.get(IBWeaponAugmentType.SLOT_UPGRADE, 0)

        ret = WeaponAugmentsContribution (
                added_attack_power = \
                        self.IB_ATTACK_AUGMENT_CUMULATIVE[attack_level],
                added_raw_affinity = \
                        self.IB_AFFINITY_AUGMENT_PERCENTAGES_CUMULATIVE[affinity_level],
                extra_decoration_slot_level = \
                        decoration_slot_level,
            )
        return ret

    def get_maximized_configs(self, health_regen_minimum=0):
        if health_regen_minimum == 0:
            return self._MAXIMIZED_CONFIGS_NOHEALTHREGEN[self._rarity]
        elif health_regen_minimum == 1:
            return self._MAXIMIZED_CONFIGS_WITHHEALTHREGEN[self._rarity]
        else:
            raise NotImplementedError("Other levels are not implemented yet.")

    def update_with_config(self, selected_config):
        assert isinstance(selected_config, list) # May accept dicts later.
        #assert (selected_config in self.get_maximized_configs()) or (len(selected_config) == 0) # Fails if our config isn't maximized
        assert all((level >= 0) and (level <= 4) for (augment, level) in selected_config)

        self._augments = {augment: level for (augment, level) in selected_config}

        assert len(self._augments) == len(selected_config) # Quick check if we have any duplicates.
        assert self._state_is_valid() # If our config breaks anything, it should be caught here
        return

    def update_with_serialized_config(self, serialized_config):
        assert isinstance(serialized_config, str)

        data = json.loads(serialized_config)
        
        # We check that we're updating the right tracker.
        assert self._rarity == data["rarity"]
        assert self._aug_level == data["aug_level"]

        self._augments = {IBWeaponAugmentType[k]: v for (k, v) in data["augments"].items()}
        
        assert self._state_is_valid()
        return

    def _state_is_valid(self):
        aug_maximum = self.IB_AUGMENTATION_SLOTS[self._rarity][self._aug_level]

        aug_used = 0
        for (augment, level) in self._augments.items():
            if level > 0:
                aug_used += self.IB_SLOT_CONSUMPTIONS_CUMULATIVE[augment][level - 1]
                # IMPORTANT: Need to remember that the slot consumptions list starts at level 1.

        ret = all(isinstance(k, IBWeaponAugmentType) and isinstance(v, int) for (k, v) in self._augments.items()) \
                and all((v >= 0) and (v <= 4) for (k, v) in self._augments.items()) \
                and (IBWeaponAugmentType.AUGMENT_LEVEL not in self._augments.items()) \
                and (aug_used <= aug_maximum)
        return ret



# If None is used instead of this Enum, then the weapon cannot be augmented.
# Values of this enum are the WeaponAugmentTracker implementations.
class WeaponAugmentationScheme(Enum):
    NONE       = auto()
    #BASE_GAME = auto() # Not used yet.
    ICEBORNE   = auto()


WeaponUpgradesContribution = namedtuple(
    "WeaponUpgradesContribution",
    [
        "added_attack_power",
        "added_raw_affinity",
        "extra_decoration_slot_level",
        "new_max_sharpness_values",
        "set_bonus",
    ],
)
class WeaponUpgradeTracker(ABC):

    @classmethod
    def get_instance(cls, weapon):
        #assert isinstance(weapon, namedtuple) # TODO: Make a proper assertion.
        if weapon.upgrade_scheme is WeaponUpgradeScheme.ICEBORNE_COMMON:
            return IBCWeaponUpgradeTracker()
        elif weapon.upgrade_scheme is WeaponUpgradeScheme.SAFI_STANDARD:
            return SafiWeaponUpgrades()
        elif weapon.upgrade_scheme is WeaponUpgradeScheme.NONE:
            return NoWeaponUpgrades()
        else:
            raise RuntimeError(f"Upgrade scheme {weapon.upgrade_scheme} not supported.")

    # TODO: Consider pruning configurations that are clearly inferior, rather than just pruning
    #       configurations that have unique contributions.
    @classmethod
    def get_maximized_trackers_pruned(cls, weapon):
        trackers = []
        seen_tracker_contributions = set()

        bare_tracker = cls.get_instance(weapon)
        for config_obj in bare_tracker.get_maximized_configs():
            tracker = cls.get_instance(weapon)
            tracker.update_with_config(config_obj)

            contribution = tracker.calculate_contribution()
            if contribution not in seen_tracker_contributions:
                seen_tracker_contributions.add(contribution)
                trackers.append(tracker)

        return trackers

    # TODO: Use something better, like the __copy__() method.
    @abstractmethod
    def copy(self):
        raise NotImplementedError

    # Similar to WeaponAugmentTracker
    @abstractmethod
    def get_config(self):
        raise NotImplementedError

    # Similar to WeaponAugmentTracker
    @abstractmethod
    def get_serialized_config(self):
        raise NotImplementedError

    # Similar to WeaponAugmentTracker
    @abstractmethod
    def calculate_contribution(self):
        raise NotImplementedError

    # Similar to WeaponAugmentTracker
    @abstractmethod
    def get_maximized_configs(self):
        raise NotImplementedError

    # Similar to WeaponAugmentTracker
    @abstractmethod
    def update_with_config(self, selected_config):
        raise NotImplementedError

    # Similar to WeaponAugmentTracker
    @abstractmethod
    def update_with_serialized_config(self, serialized_config):
        raise NotImplementedError


class NoWeaponUpgrades(WeaponUpgradeTracker):

    MAGIC_WORD = "NoWeaponUpgrades"

    def copy(self):
        return self # It shouldn't matter at all

    def get_config(self):
        return []

    def get_serialized_config(self):
        return self.MAGIC_WORD

    def calculate_contribution(self):
        ret = WeaponUpgradesContribution (
                added_attack_power = 0,
                added_raw_affinity = 0,
                extra_decoration_slot_level = 0,
                new_max_sharpness_values = None,
                set_bonus = None,
            )
        return ret

    def get_maximized_configs(self):
        return [None]

    def update_with_config(self, selected_config):
        if selected_config is not None:
            raise RuntimeError("Can't update the upgrades of a weapon that can't be upgraded.")
        return

    def update_with_serialized_config(self, serialized_config):
        assert serialized_config == self.MAGIC_WORD


class IBCWeaponUpgradeType(Enum):
    ATTACK            = auto()
    AFFINITY          = auto()
    #ELEMENTAL_STATUS = auto() # I'm just gonna pretend these don't exist yet...
    #DEFENSE          = auto()


class IBCWeaponUpgradeTracker(WeaponUpgradeTracker):

    __slots__ = [
            "_upgrades",
        ]

    _IB_ATTACK_UPGRADE_VALUES   = (1, 1, 1, 1, 1, 1   )
    _IB_AFFINITY_UPGRADE_VALUES = (1, 1, 1, 1, 1, None)
    #                     level =  1  2  3  4  5  6

    # {rarity: [config]}
    _MAXIMIZED_CONFIGS = [ # TODO: Consider automating this definition.
            [IBCWeaponUpgradeType.ATTACK] * 6,
            ([IBCWeaponUpgradeType.AFFINITY] * 1) + ([IBCWeaponUpgradeType.ATTACK] * 5),
            ([IBCWeaponUpgradeType.AFFINITY] * 2) + ([IBCWeaponUpgradeType.ATTACK] * 4),
            ([IBCWeaponUpgradeType.AFFINITY] * 3) + ([IBCWeaponUpgradeType.ATTACK] * 3),
            ([IBCWeaponUpgradeType.AFFINITY] * 4) + ([IBCWeaponUpgradeType.ATTACK] * 2),
            ([IBCWeaponUpgradeType.AFFINITY] * 5) + ([IBCWeaponUpgradeType.ATTACK] * 1),
        ]

    def __init__(self):
        self._upgrades = []
        assert self._state_is_valid()
        return

    def copy(self):
        new = copy(self)
        new._upgrades = copy(self._upgrades)
        assert new._state_is_valid()
        return new

    def get_config(self):
        return copy(self._upgrades)

    def get_serialized_config(self):
        upgrades_strs = [(x.name if (x is not None) else None) for x in self._upgrades]

        serialized_data = json.dumps(upgrades_strs)
        assert isinstance(serialized_data, str)
        return serialized_data

    def calculate_contribution(self):
        # IMPORTANT: We're actually mostly just relying on this function for debugging.
        #            If this function doesn't raise an exception, then we're good.
        added_attack_power = 0
        added_raw_affinity = 0
        for (i, upgrade) in enumerate(self._upgrades):
            assert i < len(self._IB_ATTACK_UPGRADE_VALUES)
            if upgrade is IBCWeaponUpgradeType.ATTACK:
                added_attack_power += self._IB_ATTACK_UPGRADE_VALUES[i]
            elif upgrade is IBCWeaponUpgradeType.AFFINITY:
                added_raw_affinity += self._IB_AFFINITY_UPGRADE_VALUES[i]
            else:
                raise RuntimeError("Unsupported upgrade type found: " + str(type(upgrade)))

        ret = WeaponUpgradesContribution (
                added_attack_power          = added_attack_power,
                added_raw_affinity          = added_raw_affinity,
                extra_decoration_slot_level = 0,
                new_max_sharpness_values    = None,
                set_bonus                   = None,
            )
        return ret

    def get_maximized_configs(self):
        return self._MAXIMIZED_CONFIGS

    def update_with_config(self, selected_config):
        if selected_config is None:
            self._upgrades = []
        else:
            assert isinstance(selected_config, list)
            self._upgrades = selected_config
        assert self._state_is_valid()
        return

    def update_with_serialized_config(self, serialized_config):
        assert isinstance(serialized_config, str)

        upgrades_strs = json.loads(serialized_config)
        
        assert isinstance(upgrades_strs, list)

        self._upgrades = [(IBCWeaponUpgradeType[x] if (x is not None) else None) for x in upgrades_strs]
        
        assert self._state_is_valid()
        return

    def _state_is_valid(self):
        # We generally just rely on calculate_contribution() to raise exceptions when something's wrong.
        return (len(self._upgrades) <= 7)


class SafiWeaponStandardUpgradeType(Enum):
    ATTACK    = auto()
    AFFINITY  = auto()
    #STATUS   = auto() # Will implement later.
    #ELEMENT  = auto() # Will implement later.
    #DEFENSE  = auto() # Will implement later.
    SLOT      = auto()
    SHARPNESS = auto()

SafiWeaponSetBonusUpgradeTypeInfo = namedtuple("SafiWeaponSetBonusUpgradeTypeInfo", ["upgrade_name", "set_bonus_name"])
class SafiWeaponSetBonusUpgradeType(Enum):
    TEOSTRA_ESSENCE  = SafiWeaponSetBonusUpgradeTypeInfo("Teostra Essence",  "TEOSTRA_TECHNIQUE")
    TIGREX_ESSENCE   = SafiWeaponSetBonusUpgradeTypeInfo("Tigrex Essence",   "TIGREX_ESSENCE")
    VELKHANA_ESSENCE = SafiWeaponSetBonusUpgradeTypeInfo("Velkhana Essence", "VELKHANA_DIVINITY")
    # I'll add the others as I fill the database!

class SafiWeaponUpgrades(WeaponUpgradeTracker):

    __slots__ = [
            "_config",
        ]

    # TODO: These values are true for GS according to honeyhunterworld.com. What about other weapons?
    #           level =  1     2     3     4   5   6
    _ATTACK_VALUES    = (None, None, None, 7,  9,  14) # Raw added to the weapon raw. Other levels not yet implemented.
    _AFFINITY_VALUES  = (None, None, None, 8,  10, 15) # Added affinity percentage. Other levels not yet implemented.
    _SLOT_VALUES      = (None, None, 1,    2,  3,  4 ) # The level of the slot. Slot I and II don't exist.
    _SHARPNESS_VALUES = (None, None, None, 40, 50, 70) # Sharpness value added. Other levels not yet implemented.

    _WHITE_MAX = 120 # Maximum white sharpness value before we overflow into purple sharpness.
    _BASE_SHARPNESS = MaximumSharpness(100, 50, 50, 50, 50, 90, 0) # All Safi weapons start at this sharpness.

    _MAXIMIZED_CONFIG_REGULAR_PICKS = [ # TODO: Consider automating this definition.
            (SafiWeaponStandardUpgradeType.ATTACK,    5),
            (SafiWeaponStandardUpgradeType.AFFINITY,  5),
            (SafiWeaponStandardUpgradeType.SHARPNESS, 5),
            (SafiWeaponStandardUpgradeType.SLOT,      5),
        ]

    _MAXIMIZED_CONFIG_LEVEL_6_PICKS = [ # TODO: Consider automating this definition.
            (SafiWeaponStandardUpgradeType.ATTACK,    6),
            (SafiWeaponStandardUpgradeType.AFFINITY,  6),
            (SafiWeaponStandardUpgradeType.SHARPNESS, 6),
            (SafiWeaponStandardUpgradeType.SLOT,      6),
        ]

    _MAXIMIZED_CONFIG_SET_BONUS_PICKS = [(x, 1) for x in SafiWeaponSetBonusUpgradeType]

    def __init__(self):
        self._config = []
        assert self._state_is_valid()
        return

    def copy(self):
        new = copy(self)
        new._config = copy(self._config)
        assert new._state_is_valid()
        return new

    def get_config(self):
        return copy(self._config)

    def get_serialized_config(self):
        assert self._state_is_valid()
        json_serializable = [(upgrade_type.name, level) for (upgrade_type, level) in self._config]
        return json.dumps(json_serializable)

    def calculate_contribution(self):
        assert self._state_is_valid() # We rely on these assumptions. E.g. only one set bonus upgrade.

        added_attack_power          = 0
        added_raw_affinity          = 0
        extra_decoration_slot_level = 0
        added_sharpness_value       = 0 # We turn this into new_max_sharpness_values once we have it.
        set_bonus                   = None

        for (upgrade_type, level) in self._config:
            if upgrade_type is SafiWeaponStandardUpgradeType.ATTACK:
                added_attack_power += self._ATTACK_VALUES[level - 1]
            elif upgrade_type is SafiWeaponStandardUpgradeType.AFFINITY:
                added_raw_affinity += self._AFFINITY_VALUES[level - 1]
            elif upgrade_type is SafiWeaponStandardUpgradeType.SLOT:
                extra_decoration_slot_level += self._SLOT_VALUES[level - 1]
            elif upgrade_type is SafiWeaponStandardUpgradeType.SHARPNESS:
                added_sharpness_value += self._SHARPNESS_VALUES[level - 1]
            elif isinstance(upgrade_type, SafiWeaponSetBonusUpgradeType):
                assert set_bonus is None
                set_bonus = SetBonus[upgrade_type.value.set_bonus_name]
            else:
                raise RuntimeError("Not a valid Safi upgrade type.")
            
        # Now, we calculate sharpness

        assert SHARPNESS_LEVEL_NAMES[5] == "White"
        assert SHARPNESS_LEVEL_NAMES[6] == "Purple"
        assert len(SHARPNESS_LEVEL_NAMES) == 7
        white_value = self._BASE_SHARPNESS[5] + added_sharpness_value
        purple_value = 0
        if white_value > self._WHITE_MAX:
            purple_value = white_value - self._WHITE_MAX
            white_value = self._WHITE_MAX

        new_max_sharpness_values = MaximumSharpness(
                self._BASE_SHARPNESS[0],
                self._BASE_SHARPNESS[1],
                self._BASE_SHARPNESS[2],
                self._BASE_SHARPNESS[3],
                self._BASE_SHARPNESS[4],
                white_value,
                purple_value,
            )

        # We've calculated everything, so now we return.

        ret = WeaponUpgradesContribution (
                added_attack_power          = added_attack_power,
                added_raw_affinity          = added_raw_affinity,
                extra_decoration_slot_level = extra_decoration_slot_level,
                new_max_sharpness_values    = new_max_sharpness_values,
                set_bonus                   = set_bonus,
            )
        return ret

    def get_maximized_configs(self):
        maximized_configs = []

        it = product(
                self._MAXIMIZED_CONFIG_LEVEL_6_PICKS,
                self._MAXIMIZED_CONFIG_REGULAR_PICKS,
                self._MAXIMIZED_CONFIG_REGULAR_PICKS,
                self._MAXIMIZED_CONFIG_REGULAR_PICKS,
                self._MAXIMIZED_CONFIG_REGULAR_PICKS + self._MAXIMIZED_CONFIG_SET_BONUS_PICKS,
            )
        for tup in it:
            config = list(tup)
            if self._is_valid_configuration(config):
                maximized_configs.append(config)

        return maximized_configs

    def update_with_config(self, selected_config):
        self._config = copy(selected_config)
        assert self._state_is_valid()
        return

    def update_with_serialized_config(self, serialized_config):
        json_parsed_config = json.loads(serialized_config)

        self._config = []
        for (upgrade_type_str, level) in json_parsed_config:
            if upgrade_type_str in SafiWeaponStandardUpgradeType.__members__:
                upgrade_type = SafiWeaponStandardUpgradeType[upgrade_type_str]
            elif upgrade_type_str in SafiWeaponSetBonusUpgradeType.__members__:
                upgrade_type = SafiWeaponSetBonusUpgradeType[upgrade_type_str]
            else:
                raise RuntimeError("Unknown Safi upgrade type.")
            self._config.append((upgrade_type, level))

        assert self._state_is_valid() # We test for config validity here.
        return

    def _state_is_valid(self):
        if len(self._config) > 5 or (not self._is_valid_configuration(self._config)):
            return False

        for (upgrade_type, level) in self._config:
            if not (isinstance(upgrade_type, SafiWeaponStandardUpgradeType)
                            or isinstance(upgrade_type, SafiWeaponSetBonusUpgradeType)):
                return False
        return True

    @classmethod
    def _is_valid_configuration(cls, config_list):
        assert len(config_list) <= 5

        has_slot = False
        has_set_bonus = False
        has_level_6 = False

        for (upgrade_type, level) in config_list:
            if upgrade_type is SafiWeaponStandardUpgradeType.SLOT:
                if has_slot:
                    return False
                has_slot = True
            elif isinstance(upgrade_type, SafiWeaponSetBonusUpgradeType):
                if has_set_bonus:
                    return False
                has_set_bonus = True
            elif (level > 6) or (level < 1):
                return False
            elif level == 6:
                if has_level_6:
                    return False
                has_level_6 = True
        return True


# If None is used instead of this Enum, then the weapon cannot be upgraded.
class WeaponUpgradeScheme(Enum):
    NONE = auto()
    ICEBORNE_COMMON = auto()
    SAFI_STANDARD = auto()


WeaponFinalValues = namedtuple(
    "WeaponFinalValues",
    [
        "original_weapon", # The original weapon object

        "true_raw",
        "affinity",
        "slots",
        "set_bonus",
        "is_raw",

        "maximum_sharpness",
    ],
)
# Calculates a weapon's final values based on all selected augments and upgrades.
def calculate_final_weapon_values(weapon, weapon_augments_tracker, weapon_upgrades_tracker):
    assert isinstance(weapon, tuple) # TODO: Make a more specific type assertion.
    assert isinstance(weapon_augments_tracker, WeaponAugmentTracker)
    assert isinstance(weapon_upgrades_tracker, WeaponUpgradeTracker)

    a_contrib = weapon_augments_tracker.calculate_contribution()
    u_contrib = weapon_upgrades_tracker.calculate_contribution()

    bloat_value = weapon.type.value.bloat
    weapon_true_raw = weapon.attack / bloat_value

    if u_contrib.new_max_sharpness_values is not None:
        maximum_sharpness = u_contrib.new_max_sharpness_values
    else:
        maximum_sharpness = weapon.maximum_sharpness

    tup = WeaponFinalValues(
            original_weapon = weapon,

            true_raw  = weapon_true_raw + a_contrib.added_attack_power + u_contrib.added_attack_power,
            affinity  = weapon.affinity + a_contrib.added_raw_affinity + u_contrib.added_raw_affinity,
            slots     = weapon.slots + (a_contrib.extra_decoration_slot_level,) + (u_contrib.extra_decoration_slot_level,),
            set_bonus = u_contrib.set_bonus,
            is_raw    = weapon.is_raw,

            maximum_sharpness = maximum_sharpness,
        )
    return tup


# Returns a list of tuples (weapon, augments_tracker, upgrades_tracker)
def get_pruned_weapon_combos(weapon_class, set_bonus_subset, health_regen_minimum):

    weapon_combinations = []

    for (_, weapon) in weapon_db.items():

        if weapon.type is not weapon_class:
            continue # We ignore weapons that don't match our desired weapon class.

        for augments_tracker in WeaponAugmentTracker.get_maximized_trackers(weapon, health_regen_minimum=health_regen_minimum):
            for upgrades_tracker in WeaponUpgradeTracker.get_maximized_trackers_pruned(weapon):
                precalculated_values = calculate_final_weapon_values(weapon, augments_tracker, upgrades_tracker)
                weapon_combinations.append(((weapon, augments_tracker, upgrades_tracker), precalculated_values))

    # TODO: Implement pruning!
    
    return [x[0] for x in weapon_combinations]


WeaponClassInfo = namedtuple("WeaponClassInfo", ["name", "bloat"])

class WeaponClass(Enum):
    GREATSWORD       = WeaponClassInfo(name="Greatsword",       bloat=4.8)
    LONGSWORD        = WeaponClassInfo(name="Longsword",        bloat=3.3)
    SWORD_AND_SHIELD = WeaponClassInfo(name="Sword and Shield", bloat=1.4)
    DUAL_BLADES      = WeaponClassInfo(name="Dual Blades",      bloat=1.4)
    HAMMER           = WeaponClassInfo(name="Hammer",           bloat=5.2)
    HUNTING_HORN     = WeaponClassInfo(name="Hunting Horn",     bloat=4.2)
    LANCE            = WeaponClassInfo(name="Lance",            bloat=2.3)
    GUNLANCE         = WeaponClassInfo(name="Gunlance",         bloat=2.3)
    SWITCHAXE        = WeaponClassInfo(name="Switchaxe",        bloat=3.5)
    CHARGE_BLADE     = WeaponClassInfo(name="Charge Blade",     bloat=3.6)
    INSECT_GLAIVE    = WeaponClassInfo(name="Insect Glaive",    bloat=4.1)
    BOW              = WeaponClassInfo(name="Bow",              bloat=1.2)
    HEAVY_BOWGUN     = WeaponClassInfo(name="Heavy Bowgun",     bloat=1.5)
    LIGHT_BOWGUN     = WeaponClassInfo(name="Light Bowgun",     bloat=1.3)


_common_fields = [
    "id",

    "name",
    "rarity",
    "attack",
    "affinity",
    "slots",
    "is_raw",

    # You do not change this field. Keep it at the end. It gets a default value.
    "augmentation_scheme",
    "upgrade_scheme",
    "type",
]
_blademaster_unique_fields = [
    "maximum_sharpness",
]
_bm_fields = _blademaster_unique_fields + _common_fields
_g_fields = _common_fields

_common_defaults = [WeaponAugmentationScheme.NONE, WeaponUpgradeScheme.NONE]


# Each unique weapon is represented by a named tuple.
# The right-most field "type" carries the associated weapon class. DO NOT OVERWRITE THIS.
# (idk yet how to protect namedtuple fields from being overwritten. should figure this out.)

GreatswordInfo     = namedtuple("GreatswordInfo",     _bm_fields)
LongswordInfo      = namedtuple("LongswordInfo",      _bm_fields) 
SwordAndShieldInfo = namedtuple("SwordAndShieldInfo", _bm_fields) 
DualBladesInfo     = namedtuple("DualBladesInfo",     _bm_fields) 
HammerInfo         = namedtuple("HammerInfo",         _bm_fields) 
HuntingHornInfo    = namedtuple("HuntingHornInfo",    _bm_fields) 
LanceInfo          = namedtuple("LanceInfo",          _bm_fields) 
GunlanceInfo       = namedtuple("GunlanceInfo",       _bm_fields) 
SwitchaxeInfo      = namedtuple("SwitchaxeInfo",      _bm_fields) 
ChargeBladeInfo    = namedtuple("ChargeBladeInfo",    _bm_fields) 
InsectGlaiveInfo   = namedtuple("InsectGlaiveInfo",   _bm_fields) 
BowInfo            = namedtuple("BowInfo",            _g_fields )  
HeavyBowgunInfo    = namedtuple("HeavyBowgunInfo",    _g_fields )  
LightBowgunInfo    = namedtuple("LightBowgunInfo",    _g_fields )  


def _obtain_weapon_db():
    json_data = json_read(WEAPONS_DATA_FILENAME)

    def validation_error(info, weapon=None):
        if weapon is None:
            raise ValueError(f"{WEAPONS_DATA_FILENAME}: {info}")
        else:
            raise ValueError(f"{WEAPONS_DATA_FILENAME} {weapon}: {info}")

    weapons_intermediate = {}
    weapon_names = set()

    for (weapon_id, dat) in json_data.items():

        if not isinstance(weapon_id, str):
            validation_error("Weapon IDs must be strings. Instead, we have: " + str(weapon_id))
        elif len(weapon_id) == 0:
            validation_error("Weapon IDs must be strings of non-zero length.")
        elif weapon_id in weapons_intermediate:
            validation_error(f"Weapon IDs must be unique.", weapon=weapon_id)
        # TODO: Also put a condition that weapon IDs must be capitalized with underscores.

        blademaster_classes = {
            WeaponClass.GREATSWORD,
            WeaponClass.LONGSWORD,
            WeaponClass.SWORD_AND_SHIELD,
            WeaponClass.DUAL_BLADES,
            WeaponClass.HAMMER,
            WeaponClass.HUNTING_HORN,
            WeaponClass.LANCE,
            WeaponClass.GUNLANCE,
            WeaponClass.SWITCHAXE,
            WeaponClass.CHARGE_BLADE,
            WeaponClass.INSECT_GLAIVE,
        }

        # We first deal with common fields.

        kwargs = {
            "id"       : weapon_id,
            "name"     : dat["name"],
            "type"     : WeaponClass[str(dat["class"])],
            "rarity"   : dat["rarity"],
            "attack"   : dat["attack"],
            "affinity" : dat["affinity"],
            "slots"    : tuple(dat["slots"]),
            "is_raw"   : dat["is_raw"],

            "augmentation_scheme" : WeaponAugmentationScheme[str(dat.get("augmentation_scheme", "NONE"))],
            "upgrade_scheme"      : WeaponUpgradeScheme[str(dat.get("upgrade_scheme", "NONE"))],
        }

        if (not isinstance(kwargs["name"], str)) or (len(kwargs["name"]) == 0):
            validation_error("Weapon names must be non-empty strings.", weapon=weapon_id)
        elif kwargs["name"] in weapon_names:
            validation_error("Weapon names must be unique.", weapon=weapon_id)
        elif (not isinstance(kwargs["rarity"], int)) or (kwargs["rarity"] <= 0):
            validation_error("Weapon rarity levels must be ints above zero.", weapon=weapon_id)
        elif (not isinstance(kwargs["attack"], int)) or (kwargs["attack"] <= 0):
            validation_error("Weapon attack power must be an int above zero.", weapon=weapon_id)
        elif (not isinstance(kwargs["affinity"], int)) or (kwargs["affinity"] < -100) or (kwargs["affinity"] > 100):
            validation_error("Weapon affinity must be an int between -100 and 100.", weapon=weapon_id)
        elif (len(kwargs["slots"]) > 2) or any((not isinstance(x, int)) or (x < 1) or (x > 4) for x in kwargs["slots"]):
            validation_error("There must only be at most 2 weapon decoration slots, each slot " \
                                "represented by an int from 1 to 4.", weapon=weapon_id)
        elif not isinstance(kwargs["is_raw"], bool):
            validation_error("is_raw must be a boolean.", weapon=weapon_id)

        # Now we deal with unique fields.

        if kwargs["type"] in blademaster_classes:
            kwargs["maximum_sharpness"] = MaximumSharpness(*dat["maximum_sharpness"])

            if any(x < 0 for x in kwargs["maximum_sharpness"]):
                validation_error("Weapon sharpness values must be zero or above.", weapon=weapon_id)

        tup = None
        if kwargs["type"] is WeaponClass.GREATSWORD:
            tup = GreatswordInfo(**kwargs)
        elif kwargs["type"] is WeaponClass.LONGSWORD:
            tup = LongswordInfo(**kwargs)
        elif kwargs["type"] is WeaponClass.SWORD_AND_SHIELD:
            tup = SwordAndShieldInfo(**kwargs)
        elif kwargs["type"] is WeaponClass.DUAL_BLADES:
            tup = DualBladesInfo(**kwargs)
        elif kwargs["type"] is WeaponClass.HAMMER:
            tup = HammerInfo(**kwargs)
        elif kwargs["type"] is WeaponClass.HUNTING_HORN:
            tup = HuntingHornInfo(**kwargs)
        elif kwargs["type"] is WeaponClass.LANCE:
            tup = LanceInfo(**kwargs)
        elif kwargs["type"] is WeaponClass.GUNLANCE:
            tup = GunlanceInfo(**kwargs)
        elif kwargs["type"] is WeaponClass.SWITCHAXE:
            tup = SwitchaxeInfo(**kwargs)
        elif kwargs["type"] is WeaponClass.CHARGE_BLADE:
            tup = ChargeBladeInfo(**kwargs)
        elif kwargs["type"] is WeaponClass.INSECT_GLAIVE:
            tup = InsectGlaiveInfo(**kwargs)
        elif kwargs["type"] is WeaponClass.BOW:
            tup = BowInfo(**kwargs)
        elif kwargs["type"] is WeaponClass.HEAVY_BOWGUN:
            tup = HeavyBowgunInfo(**kwargs)
        elif kwargs["type"] is WeaponClass.LIGHT_BOWGUN:
            tup = LightBowgunInfo(**kwargs)
        else:
            raise RuntimeError("Unexpected weapon type.")

        weapon_names.add(tup.name)
        #weapons_intermediate[weapon_id] = tup # TODO: Consider using the weapon ID instead.
        weapons_intermediate[weapon_id] = tup

    return weapons_intermediate


weapon_db = _obtain_weapon_db()


def print_weapon_config(linebegin, weapon, weapon_augments_tracker, weapon_upgrades_tracker):
    print(linebegin + weapon.name)

    print()
    for (augment, level) in weapon_augments_tracker.get_config():
        print(f"{linebegin}{augment.name} {level}")
    # TODO: Let the tracker print itself.
    if isinstance(weapon_upgrades_tracker, IBCWeaponUpgradeTracker):
        for (stage, upgrade) in enumerate(weapon_upgrades_tracker.get_config()):
            print(f"{linebegin}Custom Upgrade: {upgrade.name} {stage+1}")
    elif isinstance(weapon_upgrades_tracker, SafiWeaponUpgrades):
        for (upgrade, level) in weapon_upgrades_tracker.get_config():
            print(f"{linebegin}Safi Awakening: {upgrade.name} {level}")
    return

