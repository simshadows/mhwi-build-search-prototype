#!/usr/bin/env python3
# -*- coding: ascii -*-

"""
Filename: run.py
Author:   contact@simshadows.com
"""


import sys

from database_weapons import WeaponClass, weapon_db
from database_misc import *


BLUE_SHARPNESS_MODIFIER = 1.2

BASE_RAW_CRITICAL_MULTIPLIER = 1.25
RAW_BLUNDER_MULTIPLIER       = 0.75


def calculate_efr(**kwargs):
    weapon_type            = kwargs["weapon_type"]

    bloat                  = weapon_type.value.bloat
    weapon_true_raw        = kwargs["weapon_attack_power"] / bloat
    total_true_raw         = weapon_true_raw + kwargs["additional_attack_power"]
    raw_sharpness_modifier = kwargs["raw_sharpness_modifier"]
    raw_crit_multiplier    = kwargs["raw_crit_multiplier"]
    raw_crit_chance        = min(kwargs["affinity_percentage"], 100) / 100

    if raw_crit_chance < 0:
        # Negative Affinity
        raw_blunder_chance = -raw_crit_chance
        raw_crit_modifier = (RAW_BLUNDER_MULTIPLIER * raw_blunder_chance) + (1 - raw_blunder_chance)
    else:
        # Positive Affinity
        raw_crit_modifier = (raw_crit_multiplier * raw_crit_chance) + (1 - raw_crit_chance)

    efr = total_true_raw * raw_sharpness_modifier * raw_crit_modifier

    print(f"Weapon Type = {weapon_type.value.name}")
    print(f"Bloat Value = {bloat}")
    print()

    print(f"Raw Crit Multiplier = {raw_crit_multiplier}")
    print( "Affinity            = " + str(raw_crit_chance * 100))
    print(f"Raw Crit Modifier   = {raw_crit_modifier}")
    print()

    print(f"Raw Sharpness Modifier = {raw_sharpness_modifier}")
    print()

    print(f"Weapon True Raw = {weapon_true_raw}")
    print(f"Total True Raw  = {total_true_raw}")
    print()

    return efr


def search():
    raise NotImplementedError("search feature not yet implemented")


def lookup(weapon_name):
    w = weapon_db[weapon_name]

    kwargs = {}
    kwargs["weapon_attack_power"]     = w.attack
    kwargs["weapon_type"]             = w.type
    kwargs["additional_attack_power"] = POWERCHARM_ATTACK_POWER + POWERTALON_ATTACK_POWER
    kwargs["raw_sharpness_modifier"]  = BLUE_SHARPNESS_MODIFIER
    kwargs["raw_crit_multiplier"]     = BASE_RAW_CRITICAL_MULTIPLIER
    kwargs["affinity_percentage"]     = w.affinity

    efr = calculate_efr(**kwargs)
    print("EFR = " + str(efr))
    return


def run():
    # Determine whether to run in search or lookup mode.
    if len(sys.argv) > 1:
        weapon_name = sys.argv[1]
        lookup(weapon_name)
    else:
        search()
    return 0


if __name__ == '__main__':
    sys.exit(run())

