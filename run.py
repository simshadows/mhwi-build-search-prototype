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

ATTACK_BOOST_ATTACK_POWER        = (0, 3, 6, 9, 12, 15, 18, 21)
ATTACK_BOOST_AFFINITY_PERCENTAGE = (0, 0, 0, 0, 5,  5,  5,  5 )
#                          level =  0  1  2  3  4   5   6   7

CRITICAL_EYE_AFFINITY_PERCENTAGE = (0, 5, 10, 15, 20, 25, 30, 40)
#                          level =  0  1  2   3   4   5   6   7

RAW_BLUNDER_MULTIPLIER = 0.75 # If you have negative affinity, this is the multiplier instead.
CRITICAL_BOOST_RAW_CRIT_MULTIPLIERS = (1.25, 1.30, 1.35, 1.40)
#                             level =  0     1     2     3

WEAKNESS_EXPLOIT_WEAKPOINT_AFFINITY_PERCENTAGE     = (0, 10, 15, 30)
WEAKNESS_EXPLOIT_WOUNDED_EXTRA_AFFINITY_PERCENTAGE = (0, 5,  15, 20)
#                                            level =  0  1   2   3

def print_debugging_statistics():
    print("=== Application Statistics ===")
    print()
    print("Number of skills: " + str(len(list(Skill))))
    print("Total number of weapons: " + str(len(weapon_db)))
    print("\n==============================\n")
    return


# Returns both the values of the new sharpness bar, and the highest sharpness level.
# The new sharpness bar corresponds to the indices in RAW_SHARPNESS_LEVEL_MODIFIERS and SHARPNESS_LEVEL_NAMES.
# The highest sharpness level also corresponds to the same indices.
def actual_sharpness_level_values(weapon_maximum_sharpness, handicraft_level):
    assert (handicraft_level >= 0) and (handicraft_level <= 5)
    assert (len(weapon_maximum_sharpness) == 7) and (len(RAW_SHARPNESS_MODIFIERS) == 7)

    # We traverse the weapon sharpness bar in reverse, subtracting based on missing handicraft levels.
    points_to_subtract = (5 - handicraft_level) * 10
    stop_level = 7
    actual_values = []
    for (level, points) in reversed(list(enumerate(weapon_maximum_sharpness))):
        if points > points_to_subtract:
            points_to_subtract = 0
            actual_values.insert(0, points - points_to_subtract)
        else:
            stop_level = level
            points_to_subtract -= points
            actual_values.insert(0, 0)

    assert len(actual_values) == 7
    return (tuple(actual_values), stop_level - 1)

# This will be useful in the future for algorithm performance optimization.
#def calculate_highest_sharpness_modifier(weapon_maximum_sharpness, handicraft_level):
#    assert (handicraft_level >= 0) and (handicraft_level <= 5)
#    assert (len(weapon_maximum_sharpness) == 7) and (len(RAW_SHARPNESS_MODIFIERS) == 7)
#
#    # We traverse the weapon sharpness bar in reverse, then
#    # keep subtracting missing handicraft levels until we stop.
#    points_to_subtract = (5 - handicraft_level) * 10
#    for (level, points) in reversed(list(enumerate(weapon_maximum_sharpness))):
#        points_to_subtract -= weapon_maximum_sharpness[level]
#        if points_to_subtract < 0:
#            break
#
#    #print(f"Points of sharpness until next level = {-points_to_subtract}")
#    #print()
#    
#    maximum_sharpness_level = level
#    return RAW_SHARPNESS_MODIFIERS[maximum_sharpness_level]


SkillsContribution = namedtuple(
    "SkillsContribution",
    [
        "handicraft_level",
        "added_attack_power",
        "raw_critical_multiplier",
        "added_raw_affinity_base_percentage",
        "added_raw_affinity_weakpoint_percentage",
        "added_raw_affinity_wounded_percentage",
    ],
)
def calculate_skills_contribution(skills_dict, maximum_sharpness_values):
    skills_dict = clipped_skills_defaultdict(skills_dict)

    attack_boost_ap = ATTACK_BOOST_ATTACK_POWER[skills_dict[Skill.ATTACK_BOOST]]
    attack_boost_aff = ATTACK_BOOST_AFFINITY_PERCENTAGE[skills_dict[Skill.ATTACK_BOOST]]

    critical_eye_aff = CRITICAL_EYE_AFFINITY_PERCENTAGE[skills_dict[Skill.CRITICAL_EYE]]

    wex_weakpoint_affinity = WEAKNESS_EXPLOIT_WEAKPOINT_AFFINITY_PERCENTAGE[skills_dict[Skill.WEAKNESS_EXPLOIT]]
    wex_wounded_extra_affinity = WEAKNESS_EXPLOIT_WOUNDED_EXTRA_AFFINITY_PERCENTAGE[skills_dict[Skill.WEAKNESS_EXPLOIT]]

    added_attack_power = attack_boost_ap
    added_raw_affinity = critical_eye_aff + attack_boost_aff

    ret = SkillsContribution(
            handicraft_level                        = skills_dict[Skill.HANDICRAFT],
            added_attack_power                      = added_attack_power,
            raw_critical_multiplier                 = CRITICAL_BOOST_RAW_CRIT_MULTIPLIERS[skills_dict[Skill.CRITICAL_BOOST]],
            added_raw_affinity_base_percentage      = added_raw_affinity,
            added_raw_affinity_weakpoint_percentage = added_raw_affinity + wex_weakpoint_affinity,
            added_raw_affinity_wounded_percentage   = added_raw_affinity + wex_weakpoint_affinity + wex_wounded_extra_affinity,
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
        "efr_base",
        "efr_weakpoint",
        "efr_wounded",
        "sharpness_values",
    ],
)
def lookup(weapon_name, skills_dict):
    assert isinstance(weapon_name, str)
    assert isinstance(skills_dict, dict)

    weapon = weapon_db[weapon_name]

    maximum_sharpness_values = weapon.maximum_sharpness
    skills_contribution = calculate_skills_contribution(skills_dict, maximum_sharpness_values)

    handicraft_level = skills_contribution.handicraft_level
    sharpness_values, highest_sharpness_level = actual_sharpness_level_values(maximum_sharpness_values, handicraft_level)

    item_attack_power = POWERCHARM_ATTACK_POWER + POWERTALON_ATTACK_POWER

    kwargs = {}
    kwargs["weapon_attack_power"]        = weapon.attack
    kwargs["weapon_type"]                = weapon.type
    kwargs["weapon_affinity_percentage"] = weapon.affinity
    kwargs["added_attack_power"]         = skills_contribution.added_attack_power + item_attack_power
    kwargs["added_affinity_percentage"]  = skills_contribution.added_raw_affinity_base_percentage
    kwargs["raw_sharpness_modifier"]     = RAW_SHARPNESS_MODIFIERS[highest_sharpness_level]
    kwargs["raw_crit_multiplier"]        = skills_contribution.raw_critical_multiplier

    efr_base      = calculate_efr(**kwargs)
    kwargs["added_affinity_percentage"]  = skills_contribution.added_raw_affinity_weakpoint_percentage
    efr_weakpoint = calculate_efr(**kwargs)
    kwargs["added_affinity_percentage"]  = skills_contribution.added_raw_affinity_wounded_percentage
    efr_wounded   = calculate_efr(**kwargs)

    ret = PerformanceValues(
            efr_base           = efr_base,
            efr_weakpoint      = efr_weakpoint,
            efr_wounded        = efr_wounded,
            sharpness_values   = sharpness_values,
        )
    return ret


def search_command():
    raise NotImplementedError("search feature not yet implemented")


def lookup_command(weapon_name):
    skills_dict = {
            Skill.HANDICRAFT: 5,
            Skill.CRITICAL_EYE: 7,
            Skill.CRITICAL_BOOST: 3,
            Skill.ATTACK_BOOST: 7,
            Skill.WEAKNESS_EXPLOIT: 3,
        }

    print("Skills:")
    print("\n".join(f"   {skill.value.name} {level}" for (skill, level) in clipped_skills_defaultdict(skills_dict).items()))
    print()

    p = lookup(weapon_name, skills_dict)

    print("Sharpness values:")
    print(f"   Red:    {p.sharpness_values[0]} hits")
    print(f"   Orange: {p.sharpness_values[1]} hits")
    print(f"   Yellow: {p.sharpness_values[2]} hits")
    print(f"   Green:  {p.sharpness_values[3]} hits")
    print(f"   Blue:   {p.sharpness_values[4]} hits")
    print(f"   White:  {p.sharpness_values[5]} hits")
    print(f"   Purple: {p.sharpness_values[6]} hits")
    print()

    print("EFR (base)      = " + str(p.efr_base))
    print("EFR (weakpoint) = " + str(p.efr_weakpoint))
    print("EFR (wounded)   = " + str(p.efr_wounded))
    return


# Super-simple unit testing. Will probably switch to a testing framework if I have complex needs.
def tests_passed():
    print("Running unit tests.\n")

    skills_dict = {} # Start with no skills
    weapon = "Acid Shredder II"

    # This function will leave skills_dict with the skill at max_level.
    def test_with_incrementing_skill(skill, max_level, expected_base_efrs, *args):
        assert max_level == skill.value.limit
        assert len(expected_base_efrs) == (max_level + 1)
        expected_weakpoint_efrs = expected_base_efrs
        expected_wounded_efrs = expected_base_efrs
        if len(args) > 0:
            expected_weakpoint_efrs = args[0]
            if len(args) > 1:
                expected_wounded_efrs = args[1]
            assert len(args) <= 2

        for level in range(max_level + 1):
            skills_dict[skill] = level
            vals = lookup(weapon, skills_dict)
            if round(vals.efr_base) != round(expected_base_efrs[level]):
                raise ValueError(f"Failed base EFR for skill level {level}.")
            elif round(vals.efr_weakpoint) != round(expected_weakpoint_efrs[level]):
                raise ValueError(f"Failed base EFR for skill level {level}.")
            elif round(vals.efr_wounded) != round(expected_wounded_efrs[level]):
                raise ValueError(f"Failed base EFR for skill level {level}.")
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
    print("Incrementing Attack Boost.")
    test_with_incrementing_skill(Skill.ATTACK_BOOST, 7, [483.30, 488.39, 493.48, 498.57, 511.91, 517.08, 522.25, 527.42])
    print("Incrementing Weakness Exploit.")
    test_with_incrementing_skill(Skill.WEAKNESS_EXPLOIT, 3, [527.42, 527.42, 527.42, 527.42],
            [527.42, 544.44, 552.94, 578.46], [527.42, 552.94, 578.46, 595.48])

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

