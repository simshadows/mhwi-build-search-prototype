# -*- coding: ascii -*-

"""
Filename: query_weapons.py
Author:   contact@simshadows.com

This file provides the MHWI build optimizer script's weapon database queries.
"""

import json
from abc import ABC, abstractmethod
from collections import namedtuple
from itertools import accumulate, product, zip_longest
from enum import Enum, auto
from copy import copy

from .utils import ENCODING, ensure_directory, prune_by_superceding

from .database_skills import SetBonus

from .database_weapons import (SHARPNESS_LEVEL_NAMES,
                              MaximumSharpness,
                              WeaponAugmentationScheme,
                              WeaponUpgradeScheme,
                              weapon_db)


DEBUGGING_WEAPON_PRUNING_DUMP_FILENAME = "debugging_dumps/weapon_pruning_dump.txt"


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

    # Returns a one-line string that represents the state of the tracker.
    # Mostly targeted for debugging purposes.
    @abstractmethod
    def to_str_debugging(self):
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

    def to_str_debugging(self):
        return "Cannot augment this weapon."


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
            10: [5, 7, 9, 10],
            11: [4, 5, 6, 8 ],
            12: [3, 4, 5, 6 ],
            #    0  1  2  3 = slot level
        }

    IB_SLOT_CONSUMPTIONS = {
            IBWeaponAugmentType.ATTACK_INCREASE           : [3, 2, 2, 2],
            IBWeaponAugmentType.AFFINITY_INCREASE         : [2, 2, 2, 2],
            #IBWeaponAugmentType.DEFENSE_INCREASE         : [1, 1, 1, 2],
            IBWeaponAugmentType.SLOT_UPGRADE              : [3, 3, 1, 1],
            IBWeaponAugmentType.HEALTH_REGEN              : [3, 2, 2, 2],
            #IBWeaponAugmentType.ELEMENT_STATUS_EFFECT_UP : [1, 2, 2, 2],
        }

    _IB_MAX_SLOT_LEVEL = 3 # This determines the maximum slot level, i.e. length of each IB_AUGMENTATION_SLOTS list.
    _IB_AUGMENT_MAX_LEVEL = 4 # This determines the maximum level of each of the IBWeaponAugmentTypes.

    IB_ATTACK_AUGMENT_VALUES               = (0, 5,  5, 5, 5)
    IB_AFFINITY_AUGMENT_VALUES_PERCENTAGES = (0, 10, 5, 5, 5)
    #                                level =  0  1   2  3  4

    IB_SLOT_CONSUMPTIONS_CUMULATIVE = {k: list(accumulate(v)) for (k, v) in IB_SLOT_CONSUMPTIONS.items()}

    IB_ATTACK_AUGMENT_CUMULATIVE               = tuple(accumulate(IB_ATTACK_AUGMENT_VALUES))
    IB_AFFINITY_AUGMENT_PERCENTAGES_CUMULATIVE = tuple(accumulate(IB_AFFINITY_AUGMENT_VALUES_PERCENTAGES))

    def __init__(self, rarity, auto_maximize=True):
        assert isinstance(rarity, int)
        assert isinstance(auto_maximize, bool)

        if auto_maximize == False:
            raise NotImplementedError("Only works with auto-maximize on for now.")
            # To implement auto_maximize==False, we'd need to actually allow lower augment levels.

        self._auto_maximize = auto_maximize

        self._rarity    = rarity
        self._aug_level = self._IB_MAX_SLOT_LEVEL
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
        maximized_configs = []
        
        efr_augments = {
                IBWeaponAugmentType.ATTACK_INCREASE,
                IBWeaponAugmentType.AFFINITY_INCREASE,
                IBWeaponAugmentType.SLOT_UPGRADE,
            }

        picks = [[(aug, x) for x in range(self._IB_AUGMENT_MAX_LEVEL + 1)] for aug in efr_augments]
        # range() will go from 0 to 4. 0 will mean no augment, and 1-4 will be each level.

        for augs in product(*picks):
            config = [(aug, level) for (aug, level) in augs if (level > 0)]

            assert IBWeaponAugmentType.HEALTH_REGEN not in set(x for (x, _) in config) # Assume it's not in yet.
            if health_regen_minimum > 0:
                config.append((IBWeaponAugmentType.HEALTH_REGEN, health_regen_minimum))

            if self._is_valid_configuration(config, self._rarity, self._aug_level):
                maximized_configs.append(config)

        return maximized_configs

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

    def to_str_debugging(self):
        return f"[Augmentation Level: {self._aug_level}] " + ",".join(f"{k.name}_{v}" for (k, v) in self._augments.items())

    def _state_is_valid(self):
        config_list = list(self._augments.items())

        ret = all(isinstance(k, IBWeaponAugmentType) and isinstance(v, int) for (k, v) in self._augments.items()) \
                and all((v >= 0) and (v <= 4) for (k, v) in self._augments.items()) \
                and (IBWeaponAugmentType.AUGMENT_LEVEL not in self._augments.items()) \
                and self._is_valid_configuration(config_list, self._rarity, self._aug_level)
        return ret

    @classmethod
    def _is_valid_configuration(cls, config_list, rarity, aug_level):
        assert isinstance(config_list, list)
        assert all(isinstance(aug, IBWeaponAugmentType) and isinstance(level, int) for (aug, level) in config_list)
        assert all((level >= 0) and (level <= cls._IB_AUGMENT_MAX_LEVEL) for (_, level) in config_list)
        assert len(config_list) == len(set(x for (x, _) in config_list))

        slots_maximum = cls.IB_AUGMENTATION_SLOTS[rarity][aug_level]

        slots_used = 0
        for (aug, level) in config_list:
            if level > 0:
                slots_used += cls.IB_SLOT_CONSUMPTIONS_CUMULATIVE[aug][level - 1]
                # IMPORTANT: Need to remember that the slot consumptions list starts at level 1.
        if slots_used <= slots_maximum:
            return True
        else:
            return False


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

    # Similar to WeaponAugmentTracker
    @abstractmethod
    def to_str_debugging(self):
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

    def to_str_debugging(self):
        return "Cannot upgrade this weapon."


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

    def to_str_debugging(self):
        return ",".join(x.name for x in self._upgrades)

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

    def to_str_debugging(self):
        return ",".join(f"{k.name}_{v}" for (k, v) in self._config)

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

    slots = weapon.slots \
                + ((a_contrib.extra_decoration_slot_level,) if (a_contrib.extra_decoration_slot_level > 0) else tuple()) \
                + ((u_contrib.extra_decoration_slot_level,) if (u_contrib.extra_decoration_slot_level > 0) else tuple())
    assert all((x in {1,2,3,4}) for x in slots)

    if u_contrib.new_max_sharpness_values is not None:
        maximum_sharpness = u_contrib.new_max_sharpness_values
    else:
        maximum_sharpness = weapon.maximum_sharpness

    tup = WeaponFinalValues(
            original_weapon = weapon,

            true_raw  = weapon_true_raw + a_contrib.added_attack_power + u_contrib.added_attack_power,
            affinity  = weapon.affinity + a_contrib.added_raw_affinity + u_contrib.added_raw_affinity,
            slots     = slots,
            set_bonus = u_contrib.set_bonus,
            is_raw    = weapon.is_raw,

            maximum_sharpness = maximum_sharpness,
        )
    return tup


# Decides if w1 supercedes w2.
def _weapon_combo_supercedes(w1, w2):
    assert isinstance(w1, WeaponFinalValues)
    assert isinstance(w2, WeaponFinalValues)

    # STAGE 1: We first decide if w1 has any values less than w2.

    if w1.true_raw < w2.true_raw:
        return False
    if w1.affinity < w2.affinity:
        return False
    
    # The logic of this slots thing is a little complex. Here's are some examples of how it works!
    # Let's assume left is w1 and right is w2.
    #   [3,3] [1]     --> continue since w1 is clearly better.
    #   [1] [3,3]     --> return False since (1 < 3) for the first element evaluates True.
    #   [4,1,1] [3,3] --> return False since (1 < 3) for the second element evaluates True.
    # To explain that last example, we can't guarantee that the [3,3] jewels can be fit into [4,1,1],
    # hence we cannot prune away w2.
    w1_slots = sorted(list(w1.slots), reverse=True)
    w2_slots = sorted(list(w2.slots), reverse=True)
    assert w1_slots[0] >= w1_slots[-1] # Sanity check that it's in descending order.
    assert w2_slots[0] >= w2_slots[-1] # Sanity check that it's in descending order.
    if any((w1_slot < w2_slot) for (w1_slot, w2_slot) in zip_longest(w1_slots, w2_slots, fillvalue=0)):
        return False

    # We can explain this through truth tables:
    #                | w2=None  | w2=setbonusA | w2=setbonusB
    #   -------------|----------|--------------|--------------
    #   w1=None      | continue | return False | return False
    #   w1=setbonusA | continue | continue     | return False
    #   w1=setbonusB | continue | return False | continue
    #   -------------|----------|--------------|--------------
    # So, we only continue if w2 is None, or the set bonuses are the same.
    if not ((w2.set_bonus is None) or (w1.set_bonus is w1.set_bonus)):
        return False

    # For now, we just group everything by whether they are raw or not.
    # Any pair where one is raw and one isn't cannot supercede each other.
    if w1.is_raw != w2.is_raw:
        return False

    # We just return if any sharpness level in w1 has fewer hits than in w2.
    assert len(w1.maximum_sharpness) == len(w2.maximum_sharpness)
    if any((s1 < s2) for (s1, s2) in zip(w1.maximum_sharpness, w2.maximum_sharpness)):
        return False

    # STAGE 2: We now decide if w1 has anything better than w2.

    if w1.true_raw > w2.true_raw:
        return True
    if w1.affinity > w2.affinity:
        return True

    # The same as in stage 1, but the other way around!
    if any((w1_slot > w2_slot) for (w1_slot, w2_slot) in zip_longest(w1_slots, w2_slots, fillvalue=0)):
        return True

    # For set bonuses, let's have a look at the remaining options:
    #                | w2=None     | w2=setbonusA | w2=setbonusB
    #   -------------|-------------|--------------|--------------
    #   w1=None      | continue    |              | 
    #   w1=setbonusA | return True | continue     | 
    #   w1=setbonusB | return True |              | continue
    #   -------------|-------------|--------------|--------------
    # So, we will only continue now only if both weapons have the same set bonus.
    if w1.set_bonus is not w2.set_bonus:
        return True

    # We don't deal with is_raw. That has already been dealt with for us.

    # This one is also similar to stage 1, but the other way around :)
    if any((s1 > s2) for (s1, s2) in zip(w1.maximum_sharpness, w2.maximum_sharpness)):
        return True

    # STAGE 3: The two weapons are effectively the same.
    
    return None


# Returns a list of tuples (weapon, augments_tracker, upgrades_tracker)
def get_pruned_weapon_combos(weapon_class, health_regen_minimum):

    weapon_combinations = []

    for (_, weapon) in weapon_db.items():

        if weapon.type is not weapon_class:
            continue # We ignore weapons that don't match our desired weapon class.

        for augments_tracker in WeaponAugmentTracker.get_maximized_trackers(weapon, health_regen_minimum=health_regen_minimum):
            for upgrades_tracker in WeaponUpgradeTracker.get_maximized_trackers_pruned(weapon):
                precalculated_values = calculate_final_weapon_values(weapon, augments_tracker, upgrades_tracker)
                weapon_combinations.append(((weapon, augments_tracker, upgrades_tracker), precalculated_values))

    # Now, we prune!

    def left_supercedes_right(weapon1, weapon2):
        return _weapon_combo_supercedes(weapon1[1], weapon2[1])

    if __debug__:
        before = weapon_combinations

    weapon_combinations = prune_by_superceding(weapon_combinations, left_supercedes_right)

    if __debug__:
        after = weapon_combinations
        diff = [x for x in before if (x not in after)]
        buf = []
        assert len(diff) > 0
        for x in diff:
            superceding_set = None
            effectively_equivalent = None
            for y in after:
                result = left_supercedes_right(y, x)
                if result is True:
                    superceding_set = y
                    break
                elif result is None:
                    effectively_equivalent = y
            assert (superceding_set is not None) or (effectively_equivalent is not None)
            buf.append(x[0][0].name)
            buf.append(x[0][1].to_str_debugging())
            buf.append(x[0][2].to_str_debugging())
            if effectively_equivalent:
                buf.append("<IS EQUIVALENT TO>")
            else:
                buf.append("<IS SUPERCEDED BY>")
            buf.append(y[0][0].name)
            buf.append(y[0][1].to_str_debugging())
            buf.append(y[0][2].to_str_debugging())
            buf.append("\n")
        ensure_directory(DEBUGGING_WEAPON_PRUNING_DUMP_FILENAME)
        with open(DEBUGGING_WEAPON_PRUNING_DUMP_FILENAME, encoding=ENCODING, mode="w") as f:
            f.write("\n".join(buf))
    
    weapon_combinations = [x[0] for x in weapon_combinations]
    return weapon_combinations


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
