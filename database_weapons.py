"""
Filename: database_weapons.py
Author:   contact@simshadows.com

This file provides the MHWI build optimizer script's weapons database.
"""

from abc import ABC, abstractmethod
from collections import namedtuple
from itertools import accumulate
from enum import Enum, auto
from copy import copy

from utils import json_read


WEAPONS_DATA_FILENAME = "database_weapons.json"


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

    # TODO: Use something better, like the __copy__() method.
    @abstractmethod
    def copy(self):
        raise NotImplementedError

    # Not used yet.
    ## Sets the tracker to automatically maximize the augments where possible.
    ## Basically, anything that can be used 100% of the time without negatively affecting
    ## a build will be done automatically.
    ##
    ## If you want to turn this behaviour off, set value=False.
    #@abstractmethod
    #def set_auto_maximize(self, value=True):
    #    raise NotImplementedError

    # Gives back the sequence of get_options() "options", in order, that were used to arrive
    # to the current augments.
    @abstractmethod
    def get_current_selections_sequence(self):
        raise NotImplementedError

    # Gives back a dictionary that describes the augments in a more convenient manner than
    # get_current_selections_sequence(). The keys may not necessarily correspond to the references
    # found in the get_current_selections_sequence() list.
    @abstractmethod
    def get_current_selections_dict(self):
        raise NotImplementedError

    # Gives back a WeaponAugmentsContribution namedtuple with all the values the current
    # set of augments contributes to the build.
    @abstractmethod
    def calculate_contribution(self):
        raise NotImplementedError

    # Gives back a list of arbitrary things describing all the possible things you can add
    # to the build.
    # This function is guaranteed to only give back "options" that add to the build, never
    # undoing anything done.
    @abstractmethod
    def get_options(self):
        raise NotImplementedError

    # This function takes one of the things from the list returned by get_options() to update
    # the build.
    # This function will only accept references available from the get_options() list.
    @abstractmethod
    def update_with_option(self, selected_option):
        raise NotImplementedError

    # A convenience function that returns a list of updated copies of this instance, where
    # each copy corresponds to each reference from the get_options() list.
    def do_all_options(self):
        return [self.copy().update_with_option(option) for option in self.get_options()]


class NoWeaponAugments(WeaponAugmentTracker):

    def copy(self):
        return self # It shouldn't doesn't matter at all

    def get_current_selections_sequence(self):
        return []

    def get_current_selections_dict(self):
        return {}

    def calculate_contribution(self):
        ret = WeaponAugmentsContribution (
                added_attack_power = 0,
                added_raw_affinity = 0,
                extra_decoration_slot_level = 0,
            )
        return ret

    def get_options(self):
        return []

    def update_with_option(self, selected_option):
        raise RuntimeError("Can't update the augments of a weapon that can't be augmented.")


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

    ib_slot_consumptions_cumulative = {k: list(accumulate(v)) for (k, v) in IB_SLOT_CONSUMPTIONS.items()}

    ib_attack_augment_cumulative               = tuple(accumulate(IB_ATTACK_AUGMENT_VALUES))
    ib_affinity_augment_percentages_cumulative = tuple(accumulate(IB_AFFINITY_AUGMENT_VALUES_PERCENTAGES))

    def __init__(self, rarity, auto_maximize=True):
        assert isinstance(rarity, int)
        assert isinstance(auto_maximize, bool)

        if auto_maximize == False:
            raise NotImplementedError("Only works with auto-maximize on for now.")
            # To implement auto_maximize==False, we'd need to actually allow lower augment levels.

        self._auto_maximize = auto_maximize
        self._selections = []

        self._rarity    = rarity
        self._aug_level = 2
        self._augments  = {} # {IBWeaponAugmentType: int}

        assert self._state_is_valid()
        return

    def copy(self):
        new = copy(self)
        new._selections = copy(self._selections)
        new._augments = copy(self._augments)
        assert self._state_is_valid()
        assert new._state_is_valid()
        return new

    def get_current_selections_sequence(self):
        return copy(self._selections)

    def get_current_selections_dict(self):
        ret = copy(self._augments)
        assert IBWeaponAugmentType.AUGMENT_LEVEL not in ret
        ret[IBWeaponAugmentType.AUGMENT_LEVEL] = self._aug_level
        return ret

    def calculate_contribution(self):
        attack_level = self._augments.get(IBWeaponAugmentType.ATTACK_INCREASE, 0)
        affinity_level = self._augments.get(IBWeaponAugmentType.AFFINITY_INCREASE, 0)
        decoration_slot_level = self._augments.get(IBWeaponAugmentType.SLOT_UPGRADE, 0)

        ret = WeaponAugmentsContribution (
                added_attack_power = \
                        self.ib_attack_augment_cumulative[attack_level],
                added_raw_affinity = \
                        self.ib_affinity_augment_percentages_cumulative[affinity_level],
                extra_decoration_slot_level = \
                        decoration_slot_level,
            )
        return ret

    def get_options(self):
        slots_maximum = self.IB_AUGMENTATION_SLOTS[self._rarity][self._aug_level]

        slots_used = 0
        for (augment, _) in self.IB_SLOT_CONSUMPTIONS.items():
            level = self._augments.get(augment, 0)

            # Add to slots_used
            if (level > 0) and (level <= 4):
                slots_used +=  self.ib_slot_consumptions_cumulative[augment][level - 1]
                # IMPORTANT: Need to remember that the slot consumptions list starts at level 1.

        # Now that we know how many slots we used, we take out the augments we can't appli
        slots_unused = slots_maximum - slots_used
        possible_augments = []
        assert (slots_unused >= 0) and (slots_used >= 0)
        if slots_unused > 0:
            for (augment, slot_consumptions) in self.IB_SLOT_CONSUMPTIONS.items():
                next_level = self._augments.get(augment, 0) + 1
                # IMPORTANT: For this next line, need to remember that the slot consumptions list starts at level 1.
                if (next_level > 0) and (next_level <= 4) and (slot_consumptions[next_level - 1] <= slots_unused):
                    possible_augments.append((augment, next_level))
                    
        #else:
            #possible_augments = [] # This path should run by default.

        #print()
        #print(f"max {slots_maximum}")
        #print(f"used {slots_used}")
        #print(self._augments)
        #print()

        return possible_augments

    def update_with_option(self, selected_option):
        assert isinstance(selected_option, tuple)
        #print()
        #print(f"Selected: {selected_option}")
        #print(f"Available:\n{self.get_options()}")
        #print()
        assert selected_option in self.get_options()

        augment, next_level = selected_option
        assert ((augment not in self._augments) and (next_level == 1)) or (self._augments[augment] == (next_level - 1))
        assert (next_level > 0) and (next_level <= 4)

        self._augments[augment] = next_level
        self._state_is_valid()
        return

    def _state_is_valid(self):
        aug_maximum = self.IB_AUGMENTATION_SLOTS[self._rarity][self._aug_level]

        aug_used = 0
        for (augment, level) in self._augments.items():
            if level > 0:
                aug_used += self.ib_slot_consumptions_cumulative[augment][level - 1]
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


# If None is used instead of this Enum, then the weapon cannot be upgraded.
class WeaponUpgradeScheme(Enum):
    NONE = auto()
    ICEBORNE_COMMON = auto()
    #SAFI = auto() # To be implemented later!


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
    "name",
    "id",
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

