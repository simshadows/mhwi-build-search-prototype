# -*- coding: ascii -*-

"""
Filename: database_weapons.py
Author:   contact@simshadows.com

This file provides the MHWI build optimizer script's weapon database data.
"""

from collections import namedtuple
from enum import Enum, auto

from .utils import json_read


WEAPONS_DATA_FILENAME = "data/database_weapons.json"


# Corresponds to each level from red through to purple, in increasing-modifier order.
SHARPNESS_LEVEL_NAMES   = ("Red", "Orange", "Yellow", "Green", "Blue", "White", "Purple")
RAW_SHARPNESS_MODIFIERS = (0.5,   0.75,     1.0,      1.05,    1.2,    1.32,    1.39    )


# These work by first representing the full bar at maximum Handicraft in terms of number of
# points in each colour, then you subtract 10 points per Handicraft level missing.
MaximumSharpness = namedtuple("MaximumSharpness", ["red", "orange", "yellow", "green", "blue", "white", "purple"])


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
    SAFI_STANDARD = auto()


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
    "constant_sharpness",
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
            kwargs["constant_sharpness"] = dat["constant_sharpness"]

            if any(x < 0 for x in kwargs["maximum_sharpness"]):
                validation_error("Weapon sharpness values must be zero or above.", weapon=weapon_id)
            elif not isinstance(kwargs["constant_sharpness"], bool):
                validation_error("Weapons must have a boolean constant_sharpness field..", weapon=weapon_id)

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
