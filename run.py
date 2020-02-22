#!/usr/bin/env python3
# -*- coding: ascii -*-

"""
Filename: run.py
Author:   contact@simshadows.com
"""

import sys


# Core Constants

GS_BLOAT = 4.8

BLUE_SHARPNESS_MODIFIER = 1.2
BASE_RAW_CRITICAL_MULTIPLIER = 1.25


# Component Values

POWERCHARM_ATTACK_POWER = 6
POWERTALON_ATTACK_POWER = 9

ACID_SHREDDER_II_ATTACK_POWER = 1392
ACID_SHREDDER_II_AFFINITY     = 0


def calculate_efr(**kwargs):
    true_raw               = (kwargs["weapon_attack_power"] / GS_BLOAT) + kwargs["additional_attack_power"]
    raw_sharpness_modifier = kwargs["raw_sharpness_modifier"]
    raw_crit_multiplier    = kwargs["raw_crit_multiplier"]
    raw_crit_chance        = min(kwargs["affinity_percentage"], 100) / 100

    if raw_crit_chance < 0:
        raise RuntimeError("negative affinity is not yet implemented")

    raw_crit_modifier = (raw_crit_multiplier * raw_crit_chance) + (1 - raw_crit_chance)
    return true_raw * raw_sharpness_modifier * raw_crit_modifier


def run():
    kwargs = {}
    kwargs["weapon_attack_power"]     = ACID_SHREDDER_II_ATTACK_POWER
    kwargs["additional_attack_power"] = POWERCHARM_ATTACK_POWER + POWERTALON_ATTACK_POWER
    kwargs["raw_sharpness_modifier"]  = BLUE_SHARPNESS_MODIFIER
    kwargs["raw_crit_multiplier"]     = BASE_RAW_CRITICAL_MULTIPLIER
    kwargs["affinity_percentage"]     = ACID_SHREDDER_II_AFFINITY + 10 # given an affinity augment for testing

    efr = calculate_efr(**kwargs)
    print("EFR = " + str(efr))

    return 0


if __name__ == '__main__':
    sys.exit(run())

