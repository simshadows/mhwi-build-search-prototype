#!/usr/bin/env python3
# -*- coding: ascii -*-

"""
Filename: run.py
Author:   contact@simshadows.com

The entrypoint for my Monster Hunter World Iceborne build optimization tool!

In this version, we assume each level under maximum Handicraft will subtract sharpness by 10 points.
"""

import sys

#from math import floor
from collections import namedtuple

from skills           import Skill, clipped_skills_defaultdict
from database_weapons import WeaponClass, weapon_db
from database_misc    import *


# Corresponds to each level from red through to purple, in increasing-modifier order.
SHARPNESS_LEVEL_NAMES   = ("Red", "Orange", "Yellow", "Green", "Blue", "White", "Purple")
RAW_SHARPNESS_MODIFIERS = (0.5,   0.75,     1.0,      1.05,    1.2,    1.32,    1.39    )

RAW_BLUNDER_MULTIPLIER = 0.75 # If you have negative affinity, this is the multiplier instead.
CRITICAL_BOOST_RAW_CRIT_MULTIPLIERS = (1.25, 1.30, 1.35, 1.40)
#                             level =  0     1     2     3

CRITICAL_EYE_ADDED_AFFINITY_PERCENTAGE = (0, 5, 10, 15, 20, 25, 30, 40)
#                                level =  0  1  2   3   4   5   6   7

def print_debugging_statistics():
    print("=== Application Statistics ===")
    print()
    print("Number of skills: " + str(len(list(Skill))))
    print("Total number of weapons: " + str(len(weapon_db)))
    print("\n==============================\n")
    return


def calculate_highest_sharpness_modifier(weapon_maximum_sharpness, handicraft_level):
    assert (handicraft_level >= 0) and (handicraft_level <= 5)
    assert (len(weapon_maximum_sharpness) == 7) and (len(RAW_SHARPNESS_MODIFIERS) == 7)

    # We traverse the weapon sharpness bar in reverse, then
    # keep subtracting missing handicraft levels until we stop.
    points_to_subtract = (5 - handicraft_level) * 10
    for (level, points) in reversed(list(enumerate(weapon_maximum_sharpness))):
        points_to_subtract -= weapon_maximum_sharpness[level]
        if points_to_subtract < 0:
            break

    #print(f"Points of sharpness until next level = {-points_to_subtract}")
    #print()
    
    maximum_sharpness_level = level
    return RAW_SHARPNESS_MODIFIERS[maximum_sharpness_level]


SkillsContribution = namedtuple(
    "SkillsContribution",
    [
        "highest_sharpness_modifier",
        "raw_critical_multiplier",
        "added_raw_affinity_percentage",
    ],
)
def calculate_skills_contribution(skills_dict, maximum_sharpness_values):
    skills_dict = clipped_skills_defaultdict(skills_dict)

    ret = SkillsContribution(
            highest_sharpness_modifier = \
                calculate_highest_sharpness_modifier(maximum_sharpness_values, skills_dict[Skill.HANDICRAFT]),
            raw_critical_multiplier = \
                CRITICAL_BOOST_RAW_CRIT_MULTIPLIERS[skills_dict[Skill.CRITICAL_BOOST]],
            added_raw_affinity_percentage = \
                CRITICAL_EYE_ADDED_AFFINITY_PERCENTAGE[skills_dict[Skill.CRITICAL_EYE]],
        )
    return ret


def calculate_efr(**kwargs):
    weapon_type = kwargs["weapon_type"]
    bloat       = weapon_type.value.bloat

    weapon_true_raw            = kwargs["weapon_attack_power"] / bloat
    weapon_affinity_percentage = kwargs["weapon_affinity_percentage"]

    added_attack_power        = kwargs["added_attack_power"]
    added_affinity_percentage = kwargs["added_affinity_percentage"]

    true_raw        = weapon_true_raw + added_attack_power
    raw_crit_chance = min(weapon_affinity_percentage + added_affinity_percentage, 100) / 100

    raw_sharpness_modifier = kwargs["raw_sharpness_modifier"]
    raw_crit_multiplier    = kwargs["raw_crit_multiplier"]

    if raw_crit_chance < 0:
        # Negative Affinity
        raw_blunder_chance = -raw_crit_chance
        raw_crit_modifier = (RAW_BLUNDER_MULTIPLIER * raw_blunder_chance) + (1 - raw_blunder_chance)
    else:
        # Positive Affinity
        raw_crit_modifier = (raw_crit_multiplier * raw_crit_chance) + (1 - raw_crit_chance)

    efr = true_raw * raw_sharpness_modifier * raw_crit_modifier

    #print(f"Weapon Type = {weapon_type.value.name}")
    #print(f"Bloat Value = {bloat}")
    #print()

    #print(f"Raw Crit Multiplier = {raw_crit_multiplier}")
    #print( "Affinity            = " + str(raw_crit_chance * 100))
    #print(f"Raw Crit Modifier   = {raw_crit_modifier}")
    #print()

    #print(f"Raw Sharpness Modifier = {raw_sharpness_modifier}")
    #print()

    #print(f"Weapon True Raw = {weapon_true_raw}")
    #print(f"Total True Raw  = {true_raw}")
    #print()

    return efr


PerformanceValues = namedtuple(
    "PerformanceValues",
    [
        "efr",
    ],
)
def lookup(weapon_name, skills_dict):
    assert isinstance(weapon_name, str)
    assert isinstance(skills_dict, dict)

    weapon = weapon_db[weapon_name]

    maximum_sharpness_values = weapon.maximum_sharpness
    skills_contribution = calculate_skills_contribution(skills_dict, maximum_sharpness_values)

    kwargs = {}
    kwargs["weapon_attack_power"]        = weapon.attack
    kwargs["weapon_type"]                = weapon.type
    kwargs["weapon_affinity_percentage"] = weapon.affinity
    kwargs["added_attack_power"]         = POWERCHARM_ATTACK_POWER + POWERTALON_ATTACK_POWER
    kwargs["added_affinity_percentage"]  = skills_contribution.added_raw_affinity_percentage
    kwargs["raw_sharpness_modifier"]     = skills_contribution.highest_sharpness_modifier
    kwargs["raw_crit_multiplier"]        = skills_contribution.raw_critical_multiplier

    ret = PerformanceValues(
            efr = calculate_efr(**kwargs),
        )
    return ret


def search_command():
    raise NotImplementedError("search feature not yet implemented")


def lookup_command(weapon_name):
    skills_dict = {
            Skill.HANDICRAFT: 5,
            Skill.CRITICAL_EYE: 1,
            Skill.CRITICAL_BOOST: 3,
        }

    print("\n".join(f"{skill}: {level}" for (skill, level) in clipped_skills_defaultdict(skills_dict).items()))
    print()

    p = lookup(weapon_name, skills_dict)

    print("EFR = " + str(p.efr))
    return


# Super-simple unit testing. Will probably switch to a testing framework if I have complex needs.
def tests_passed():
    print("Running unit tests.\n")

    skills_dict = {} # Start with no skills
    weapon = "Acid Shredder II"

    # This function will leave skills_dict with the skill at max_level.
    def test_with_incrementing_skill(skill, max_level, expected_efrs):
        assert len(expected_efrs) == (max_level + 1)
        for level in range(max_level + 1):
            skills_dict[skill] = level
            vals = lookup(weapon, skills_dict)
            if round(vals.efr) != round(expected_efrs[level]):
                raise ValueError(f"Failed for skill level {level}.")
        return

    print("Incrementing Handicraft.")
    test_with_incrementing_skill(Skill.HANDICRAFT, 5, [366.00, 366.00, 366.00, 402.60, 402.60, 423.95])
    print("Incrementing Critical Boost with zero Affinity.")
    test_with_incrementing_skill(Skill.CRITICAL_BOOST, 3, [423.95, 423.95, 423.95, 423.95])

    weapon = "Royal Venus Blade"

    print("Incrementing Critical Boost with non-zero Affinity.")
    test_with_incrementing_skill(Skill.CRITICAL_BOOST, 3, [411.01, 413.98, 416.95, 419.92])
    print("Incrementing Critical Eye.")
    test_with_incrementing_skill(Skill.CRITICAL_EYE, 7, [419.92, 427.84, 435.77, 443.69, 451.61, 459.53, 467.46, 483.30])

    #weapon = "Jagras Deathclaw II"

    #print("Incrementing Critical Eye again.")
    #test_with_incrementing_skill(Skill.CRITICAL_EYE, 7, [363.00, 370.26, 377.52, 384.78, 392.04, 399.30, 406.56, 421.08])

    print("\nUnit tests are all passed.")
    print("\n==============================\n")
    return True


def run():
    print_debugging_statistics()
    assert tests_passed()

    # Determine whether to run in search or lookup mode.
    if len(sys.argv) > 1:
        weapon_name = sys.argv[1]
        lookup_command(weapon_name)
    else:
        search()
    return 0


if __name__ == '__main__':
    sys.exit(run())

