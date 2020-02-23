#!/usr/bin/env python3
# -*- coding: ascii -*-

"""
Filename: database_weapons.py
Author:   contact@simshadows.com

This file provides the MHWI build optimizer script's weapons database.
"""


from collections import namedtuple
from enum import Enum


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

    # You do not change this field. Keep it at the end. It gets a default value.
    "type",
]


# Each unique weapon is represented by a named tuple.
# The right-most field "type" carries the associated weapon class. DO NOT OVERWRITE THIS.
# (idk yet how to protect namedtuple fields from being overwritten. should figure this out.)

_Greatsword     = namedtuple("_Greatsword",     _common_fields, defaults=[WeaponClass.GREATSWORD])
_Longsword      = namedtuple("_Longsword",      _common_fields, defaults=[WeaponClass.LONGSWORD])
_SwordAndShield = namedtuple("_SwordAndShield", _common_fields, defaults=[WeaponClass.SWORD_AND_SHIELD])
_DualBlades     = namedtuple("_DualBlades",     _common_fields, defaults=[WeaponClass.DUAL_BLADES])
_Hammer         = namedtuple("_Hammer",         _common_fields, defaults=[WeaponClass.HAMMER])
_HuntingHorn    = namedtuple("_HuntingHorn",    _common_fields, defaults=[WeaponClass.HUNTING_HORN])
_Lance          = namedtuple("_Lance",          _common_fields, defaults=[WeaponClass.LANCE])
_Gunlance       = namedtuple("_Gunlance",       _common_fields, defaults=[WeaponClass.GUNLANCE])
_Switchaxe      = namedtuple("_Switchaxe",      _common_fields, defaults=[WeaponClass.SWITCHAXE])
_ChargeBlade    = namedtuple("_ChargeBlade",    _common_fields, defaults=[WeaponClass.CHARGE_BLADE])
_InsectGlaive   = namedtuple("_InsectGlaive",   _common_fields, defaults=[WeaponClass.INSECT_GLAIVE])
_Bow            = namedtuple("_Bow",            _common_fields, defaults=[WeaponClass.BOW])
_HeavyBowgun    = namedtuple("_HeavyBowgun",    _common_fields, defaults=[WeaponClass.HEAVY_BOWGUN])
_LightBowgun    = namedtuple("_LightBowgun",    _common_fields, defaults=[WeaponClass.LIGHT_BOWGUN])


weapon_db = {

    # Weapons are indexed by their full name.

    # For now, we will only have a subset of greatswords.
    # I'll add other weapons later!

    "Jagras Deathclaw II" : _Greatsword(
        rarity   = 10,
        attack   = 1248,
        affinity = 0,
    ),

    "Acid Shredder II" : _Greatsword(
        rarity   = 11,
        attack   = 1392,
        affinity = 0,
    ),

    "Immovable Dharma" : _Greatsword(
        rarity   = 12,
        attack   = 1344,
        affinity = 0,
    ),

    "Great Demon Rod" : _Greatsword(
        rarity   = 12,
        attack   = 1488,
        affinity = -15,
    ),

    "Royal Venus Blade" : _Greatsword(
        rarity   = 12,
        attack   = 1296,
        affinity = 15,
    ),

    "Lunatic Rose" : _SwordAndShield(
        rarity   = 12,
        attack   = 406,
        affinity = 10,
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

    return True

_weapon_db_integrity_check()

