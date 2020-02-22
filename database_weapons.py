#!/usr/bin/env python3
# -*- coding: ascii -*-

"""
Filename: database_weapons.py
Author:   contact@simshadows.com

This file provides the MHWI build optimizer script's weapons database.
"""


from collections import namedtuple
from enum import Enum


Weapon = namedtuple("Weapon",
    [
        "wclass",
        "rarity",
        "attack",
        "affinity",
    ]
)

# Weapon classes, and associated bloat values.
class WeaponClass(Enum):
    SWORD_AND_SHIELD = 1.4
    DUAL_BLADES      = 1.4
    GREATSWORD       = 4.8
    LONGSWORD        = 3.3
    HAMMER           = 5.2
    HUNTING_HORN     = 4.2
    LANCE            = 2.3
    GUNLANCE         = 2.3
    SWITCHAXE        = 3.5
    CHARGE_BLADE     = 3.6
    INSECT_GLAIVE    = 4.1
    BOW              = 1.2
    HEAVY_BOWGUN     = 1.5
    LIGHT_BOWGUN     = 1.3


weapon_db = {

    # Weapons are indexed by their full name.

    # For now, we will only have a subset of greatswords.
    # I'll add other weapons later!

    "Acid Shredder II": Weapon(
        wclass   = WeaponClass.GREATSWORD,
        rarity   = 11,
        attack   = 1392,
        affinity = 0,
    ),

    "Immovable Dharma": Weapon(
        wclass   = WeaponClass.GREATSWORD,
        rarity   = 12,
        attack   = 1344,
        affinity = 0,
    ),

}

