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

    IB_AUGMENTATION_SLOT_CONSUMPTIONS = {
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
        aug_maximum = self.IB_AUGMENTATION_SLOTS[self._rarity][self._aug_level]

        aug_used = 0
        possible_augments = []
        for (augment, slot_consumptions) in self.IB_AUGMENTATION_SLOT_CONSUMPTIONS.items():
            level = self._augments.get(augment, 0)
            next_level = level + 1
            if level > 0:
                aug_used += sum(self.IB_AUGMENTATION_SLOT_CONSUMPTIONS[augment][i] for i in range(level - 2))
            if (next_level <= 4) and (self.IB_AUGMENTATION_SLOT_CONSUMPTIONS[augment][next_level] <= aug_maximum - aug_used):
                possible_augments.append((augment, next_level))

        assert (0 <= aug_used) and (aug_used <= aug_maximum)

        return possible_augments

    def update_with_option(self, selected_option):
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
                aug_used += sum(self.IB_AUGMENTATION_SLOT_CONSUMPTIONS[i] for i in range(level - 2))

        ret = all(isinstance(k, IBWeaponAugmentType) and isinstance(v, int) for (k, v) in self._augments.items()) \
                and all((v >= 0) and (v <= 4) for (k, v) in self._augments.items()) \
                and (IBWeaponAugmentType.AUGMENT_LEVEL not in self._augments.items()) \
                and (aug_used <= aug_maximum)
        return ret



# If None is used instead of this Enum, then the weapon cannot be augmented.
# Values of this enum are the WeaponAugmentTracker implementations.
class WeaponAugmentationScheme(Enum):
    NONE       = NoWeaponAugments
    #BASE_GAME = auto() # Not used yet.
    ICEBORNE   = IBWeaponAugmentTracker


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
    "rarity",
    "attack",
    "affinity",
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

_Greatsword     = namedtuple("_Greatsword",     _bm_fields, defaults=_common_defaults+[WeaponClass.GREATSWORD])
_Longsword      = namedtuple("_Longsword",      _bm_fields, defaults=_common_defaults+[WeaponClass.LONGSWORD])
_SwordAndShield = namedtuple("_SwordAndShield", _bm_fields, defaults=_common_defaults+[WeaponClass.SWORD_AND_SHIELD])
_DualBlades     = namedtuple("_DualBlades",     _bm_fields, defaults=_common_defaults+[WeaponClass.DUAL_BLADES])
_Hammer         = namedtuple("_Hammer",         _bm_fields, defaults=_common_defaults+[WeaponClass.HAMMER])
_HuntingHorn    = namedtuple("_HuntingHorn",    _bm_fields, defaults=_common_defaults+[WeaponClass.HUNTING_HORN])
_Lance          = namedtuple("_Lance",          _bm_fields, defaults=_common_defaults+[WeaponClass.LANCE])
_Gunlance       = namedtuple("_Gunlance",       _bm_fields, defaults=_common_defaults+[WeaponClass.GUNLANCE])
_Switchaxe      = namedtuple("_Switchaxe",      _bm_fields, defaults=_common_defaults+[WeaponClass.SWITCHAXE])
_ChargeBlade    = namedtuple("_ChargeBlade",    _bm_fields, defaults=_common_defaults+[WeaponClass.CHARGE_BLADE])
_InsectGlaive   = namedtuple("_InsectGlaive",   _bm_fields, defaults=_common_defaults+[WeaponClass.INSECT_GLAIVE])
_Bow            = namedtuple("_Bow",            _g_fields,  defaults=_common_defaults+[WeaponClass.BOW])
_HeavyBowgun    = namedtuple("_HeavyBowgun",    _g_fields,  defaults=_common_defaults+[WeaponClass.HEAVY_BOWGUN])
_LightBowgun    = namedtuple("_LightBowgun",    _g_fields,  defaults=_common_defaults+[WeaponClass.LIGHT_BOWGUN])


weapon_db = {

    # Weapons are indexed by their full name.

    "Jagras Deathclaw II" : _Greatsword(
        rarity   = 10,
        attack   = 1248,
        affinity = 0,
        is_raw   = True, # Temporary oversimplification.

        maximum_sharpness = MaximumSharpness(110, 80, 30, 30, 80, 70, 0),

        augmentation_scheme = WeaponAugmentationScheme.ICEBORNE,
        upgrade_scheme      = WeaponUpgradeScheme.ICEBORNE_COMMON,
    ),

    "Acid Shredder II" : _Greatsword(
        rarity   = 11,
        attack   = 1392,
        affinity = 0,
        is_raw   = True, # Temporary oversimplification.

        maximum_sharpness = MaximumSharpness(60, 50, 110, 90, 60, 20, 10),

        augmentation_scheme = WeaponAugmentationScheme.ICEBORNE,
        upgrade_scheme      = WeaponUpgradeScheme.ICEBORNE_COMMON,
    ),

    "Immovable Dharma" : _Greatsword(
        rarity   = 12,
        attack   = 1344,
        affinity = 0,
        is_raw   = True, # Temporary oversimplification.

        maximum_sharpness = MaximumSharpness(170, 30, 30, 60, 50, 30, 30),

        augmentation_scheme = WeaponAugmentationScheme.ICEBORNE,
        upgrade_scheme      = WeaponUpgradeScheme.NONE,
    ),

    "Great Demon Rod" : _Greatsword(
        rarity   = 12,
        attack   = 1488,
        affinity = -15,
        is_raw   = False, # Temporary oversimplification.

        maximum_sharpness = MaximumSharpness(100, 100, 40, 50, 60, 50, 0),

        augmentation_scheme = WeaponAugmentationScheme.ICEBORNE,
        upgrade_scheme      = WeaponUpgradeScheme.NONE,
    ),

    "Royal Venus Blade" : _Greatsword(
        rarity   = 12,
        attack   = 1296,
        affinity = 15,
        is_raw   = True, # Temporary oversimplification.

        maximum_sharpness = MaximumSharpness(200, 30, 30, 50, 50, 30, 50),

        augmentation_scheme = WeaponAugmentationScheme.ICEBORNE,
        upgrade_scheme      = WeaponUpgradeScheme.NONE,
    ),

    "Lunatic Rose" : _SwordAndShield(
        rarity   = 12,
        attack   = 406,
        affinity = 10,
        is_raw   = False, # Temporary oversimplification.

        maximum_sharpness = MaximumSharpness(60, 80, 30, 30, 80, 120, 0),

        augmentation_scheme = WeaponAugmentationScheme.ICEBORNE,
        upgrade_scheme      = WeaponUpgradeScheme.NONE,
    ),

}


def _weapon_db_integrity_check():
    type_associations = {
        _Greatsword     : WeaponClass.GREATSWORD,
        _Longsword      : WeaponClass.LONGSWORD,
        _SwordAndShield : WeaponClass.SWORD_AND_SHIELD,
        _DualBlades     : WeaponClass.DUAL_BLADES,
        _Hammer         : WeaponClass.HAMMER,
        _HuntingHorn    : WeaponClass.HUNTING_HORN,
        _Lance          : WeaponClass.LANCE,
        _Gunlance       : WeaponClass.GUNLANCE,
        _Switchaxe      : WeaponClass.SWITCHAXE,
        _ChargeBlade    : WeaponClass.CHARGE_BLADE,
        _InsectGlaive   : WeaponClass.INSECT_GLAIVE,
        _Bow            : WeaponClass.BOW,
        _HeavyBowgun    : WeaponClass.HEAVY_BOWGUN,
        _LightBowgun    : WeaponClass.LIGHT_BOWGUN,
    }

    for (name, data) in weapon_db.items():

        if (data.rarity > 12) or (data.rarity < 1):
            raise ValueError(str(name) + ": Rarity value out of bounds.")

        elif (data.attack > 10000):
            raise ValueError(str(name) + ": Attack value is probably wrong. Please check!")
        elif (data.attack < 0):
            raise ValueError(str(name) + ": Attack value out of bounds.")

        elif (data.affinity > 100) or (data.affinity < -100):
            raise ValueError(str(name) + ": Affinity value out of bounds.")

        elif (data.type != type_associations[type(data)]):
            raise ValueError(str(name) + ": Wrong value in the type field. (Did you accidentally overwrite it?)")

        elif any(((x < 0) or (x > 800) or (x % 10 != 0)) for x in data.maximum_sharpness):
            raise ValueError(str(name) + ": Strange sharpness numbers.")

        elif (not isinstance(data.augmentation_scheme, WeaponAugmentationScheme)):
            raise ValueError(str(name) + ": Augmentation scheme is wrong type.")

        elif (not isinstance(data.upgrade_scheme, WeaponUpgradeScheme)):
            raise ValueError(str(name) + ": Upgrade scheme is wrong type.")

        # Not going to bother validating is_raw. It's a temporary flag anyway.

    return True

_weapon_db_integrity_check()

