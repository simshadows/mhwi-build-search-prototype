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

AGITATOR_ATTACK_POWER        = (0, 4, 8, 12, 16, 20, 24, 28)
AGITATOR_AFFINITY_PERCENTAGE = (0, 5, 5, 7,  7,  10, 15, 20)
#                      level =  0  1  2  3   4   5   6   7

PEAK_PERFORMANCE_ATTACK_POWER = (0, 5, 10, 20)
#                       level =  0  1  2   3

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
        "added_raw_affinity_percentage",
    ],
)
def calculate_skills_contribution(skills_dict, skill_states_dict, maximum_sharpness_values):
    skills_dict = clipped_skills_defaultdict(skills_dict)

    added_attack_power = 0
    added_raw_affinity = 0

    # Attack Boost
    added_attack_power += ATTACK_BOOST_ATTACK_POWER[skills_dict[Skill.ATTACK_BOOST]]
    added_raw_affinity += ATTACK_BOOST_AFFINITY_PERCENTAGE[skills_dict[Skill.ATTACK_BOOST]]

    # Critical Eye
    added_raw_affinity += CRITICAL_EYE_AFFINITY_PERCENTAGE[skills_dict[Skill.CRITICAL_EYE]]

    # Weakness Exploit
    if skills_dict[Skill.WEAKNESS_EXPLOIT] > 0:
        assert Skill.WEAKNESS_EXPLOIT in skill_states_dict

        state = skill_states_dict[Skill.WEAKNESS_EXPLOIT]
        assert (state <= 2) and (state >= 0)
        if state >= 1:
            added_raw_affinity += WEAKNESS_EXPLOIT_WEAKPOINT_AFFINITY_PERCENTAGE[skills_dict[Skill.WEAKNESS_EXPLOIT]]
            if state == 2:
                added_raw_affinity += WEAKNESS_EXPLOIT_WOUNDED_EXTRA_AFFINITY_PERCENTAGE[skills_dict[Skill.WEAKNESS_EXPLOIT]]

    # Agitator
    if skills_dict[Skill.AGITATOR] > 0:
        assert Skill.AGITATOR in skill_states_dict

        state = skill_states_dict[Skill.AGITATOR]
        assert (state == 0) or (state == 1)
        if state == 1:
            added_attack_power += AGITATOR_ATTACK_POWER[skills_dict[Skill.AGITATOR]]
            added_raw_affinity += AGITATOR_AFFINITY_PERCENTAGE[skills_dict[Skill.AGITATOR]]

    # Peak Performance
    if skills_dict[Skill.PEAK_PERFORMANCE] > 0:
        assert Skill.PEAK_PERFORMANCE in skill_states_dict

        state = skill_states_dict[Skill.PEAK_PERFORMANCE]
        assert (state == 0) or (state == 1)
        if state == 1:
            added_attack_power += PEAK_PERFORMANCE_ATTACK_POWER[skills_dict[Skill.PEAK_PERFORMANCE]]

    ret = SkillsContribution(
            handicraft_level              = skills_dict[Skill.HANDICRAFT],
            added_attack_power            = added_attack_power,
            raw_critical_multiplier       = CRITICAL_BOOST_RAW_CRIT_MULTIPLIERS[skills_dict[Skill.CRITICAL_BOOST]],
            added_raw_affinity_percentage = added_raw_affinity,
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
        "sharpness_values",
    ],
)
# This function is recursive.
# For each condition missing from skill_conditions_dict,
# it will call itself again for each possible state of the skill.
def lookup(weapon_name, skills_dict, skill_states_dict):
    assert isinstance(weapon_name, str)
    assert isinstance(skills_dict, dict)
    assert isinstance(skill_states_dict, dict)

    ret = None

    skill_states_missing = any(
            (lvl > 0) and (s.value.states is not None) and (s not in skill_states_dict)
            for (s, lvl) in skills_dict.items()
        )

    if skill_states_missing:
        # We do recursion here.

        if __debug__:
            # Determine if skills_states_dict contains any skills not in skills_dict.
            skills_keys = set(k for (k, v) in skills_dict.items())
            skill_states_keys = set(k for (k, v) in skill_states_dict.items())
            diff = skill_states_keys - skills_keys
            if len(diff) > 0:
                skills_str = " ".join(diff)
                raise RuntimeError(f"skill_states_dict has sklls not in skills_dict. \
                        (Skills unique to skill_states_dict: {skills_str}.")

        # We first determine the missing skill name from skill_states_dict that is earliest in alphabetical order.

        skill_to_iterate = None

        for (skill, _) in skills_dict.items():
            if (skill.value.states is not None) and (skill not in skill_states_dict):
                if (skill_to_iterate is None) or (skill.value.name <= skill_to_iterate.value.name):
                    assert (skill_to_iterate is None) or (skill.value.name != skill_to_iterate.value.name)
                    skill_to_iterate = skill

        assert skill_to_iterate is not None

        ret = []
        total_states = len(skill_to_iterate.value.states)
        for level in range(total_states):
            new_skill_states_dict = skill_states_dict.copy()
            new_skill_states_dict[skill_to_iterate] = level
            ret.append(lookup(weapon_name, skills_dict, new_skill_states_dict))

    else:
        # We terminate recursion here.

        weapon = weapon_db[weapon_name]

        maximum_sharpness_values = weapon.maximum_sharpness
        skills_contribution = calculate_skills_contribution(skills_dict, skill_states_dict, maximum_sharpness_values)

        handicraft_level = skills_contribution.handicraft_level
        sharpness_values, highest_sharpness_level = actual_sharpness_level_values(maximum_sharpness_values, handicraft_level)

        item_attack_power = POWERCHARM_ATTACK_POWER + POWERTALON_ATTACK_POWER

        kwargs = {}
        kwargs["weapon_attack_power"]        = weapon.attack
        kwargs["weapon_type"]                = weapon.type
        kwargs["weapon_affinity_percentage"] = weapon.affinity
        kwargs["added_attack_power"]         = skills_contribution.added_attack_power + item_attack_power
        kwargs["added_affinity_percentage"]  = skills_contribution.added_raw_affinity_percentage
        kwargs["raw_sharpness_modifier"]     = RAW_SHARPNESS_MODIFIERS[highest_sharpness_level]
        kwargs["raw_crit_multiplier"]        = skills_contribution.raw_critical_multiplier

        ret = PerformanceValues(
                efr               = calculate_efr(**kwargs),
                sharpness_values  = sharpness_values,
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
            Skill.AGITATOR: 5,
            Skill.PEAK_PERFORMANCE: 3,
        }

    skill_states_dict = {
            #Skill.WEAKNESS_EXPLOIT: 2,
            #Skill.AGITATOR: 1,
            Skill.PEAK_PERFORMANCE: 1,
        }

    print("Skills:")
    print("\n".join(f"   {skill.value.name} {level}" for (skill, level) in clipped_skills_defaultdict(skills_dict).items()))
    print()

    results = lookup(weapon_name, skills_dict, skill_states_dict)
    sharpness_values = None
    efrs_strings = []

    iterated_skills = [
            skill for (skill, level) in skills_dict.items()
            if (level > 0) and (skill.value.states is not None) and (skill not in skill_states_dict)
        ]

    if isinstance(iterated_skills, list) and (len(iterated_skills) > 0):
        # We have an arbitrarily-deep list with nested lists of result tuples.

        # It should be in alphabetical order, so we sort first.
        iterated_skills.sort(key=lambda skill : skill.value.name)

        states_strings = []
        efrs = []
        sharpness_values = None
        def traverse_results_structure(states, subresults):
            nonlocal sharpness_values
            assert isinstance(states, list)

            next_index = len(states)
            if next_index >= len(iterated_skills):
                # Terminate recursion here.
                
                states_strings.append("; ".join(s.value.states[states[i]] for (i, s) in enumerate(iterated_skills)))
                efrs.append(subresults.efr)

                assert (sharpness_values is None) or (sharpness_values == subresults.sharpness_values)
                sharpness_values = subresults.sharpness_values

            else:
                # Do more recursion here!

                skill_to_iterate = iterated_skills[next_index]
                assert len(skill_to_iterate.value.states) > 1
                for state_value, _ in enumerate(skill_to_iterate.value.states):
                    traverse_results_structure(states + [state_value], subresults[state_value])
            return

        traverse_results_structure([], results)

        # Make state_strings look nicer
        states_strings = [s + ":" for s in states_strings]
        max_str_len = max(len(s) for s in states_strings)
        states_strings = [s.ljust(max_str_len, " ") for s in states_strings]

        efrs_strings.append("EFR values:")
        efrs_strings.extend(f"   {state_str} {efr}" for (state_str, efr) in zip(states_strings, efrs))

    else:
        # We have just a single result tuple.

        sharpness_values = results.sharpness_values
        efrs_strings.append(f"EFR: {results.efr}")

    print("Sharpness values:")
    print(f"   Red:    {sharpness_values[0]} hits")
    print(f"   Orange: {sharpness_values[1]} hits")
    print(f"   Yellow: {sharpness_values[2]} hits")
    print(f"   Green:  {sharpness_values[3]} hits")
    print(f"   Blue:   {sharpness_values[4]} hits")
    print(f"   White:  {sharpness_values[5]} hits")
    print(f"   Purple: {sharpness_values[6]} hits")
    print()

    print("\n".join(efrs_strings))
    return


# Super-simple unit testing. Will probably switch to a testing framework if I have complex needs.
def tests_passed():
    print("Running unit tests.\n")

    skills_dict = {} # Start with no skills
    skill_states_dict = {} # Start with no states
    weapon = "Acid Shredder II"

    # This function will leave skills_dict with the skill at max_level.
    def test_with_incrementing_skill(skill, max_level, expected_efrs):
        assert max_level == skill.value.limit
        assert len(expected_efrs) == (max_level + 1)

        for level in range(max_level + 1):
            skills_dict[skill] = level
            vals = lookup(weapon, skills_dict, skill_states_dict)
            if round(vals.efr) != round(expected_efrs[level]):
                raise ValueError(f"EFR value mismatch for skill level {level}. Got EFR = {vals.efr}.")
        return

    print("Incrementing Handicraft.")
    test_with_incrementing_skill(Skill.HANDICRAFT, 5, [366.00, 366.00, 366.00, 402.60, 402.60, 423.95])
    # We now have full Handicraft.
    print("Incrementing Critical Boost with zero Affinity.")
    test_with_incrementing_skill(Skill.CRITICAL_BOOST, 3, [423.95, 423.95, 423.95, 423.95])
    # We now have full Handicraft and Critical Boost.

    weapon = "Royal Venus Blade"

    print("Incrementing Critical Boost with non-zero Affinity.")
    test_with_incrementing_skill(Skill.CRITICAL_BOOST, 3, [411.01, 413.98, 416.95, 419.92])
    print("Incrementing Critical Eye.")
    test_with_incrementing_skill(Skill.CRITICAL_EYE, 7, [419.92, 427.84, 435.77, 443.69, 451.61, 459.53, 467.46, 483.30])
    # We now have full Handicraft, Critical Boost, and Critical Eye.
    print("Incrementing Attack Boost.")
    test_with_incrementing_skill(Skill.ATTACK_BOOST, 7, [483.30, 488.39, 493.48, 498.57, 511.91, 517.08, 522.25, 527.42])
    # We now have full Handicraft, Critical Boost, Critical Eye, and Attack Boost.

    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 2,
        }

    print("Incrementing Weakness Exploit on a wounded part.")
    test_with_incrementing_skill(Skill.WEAKNESS_EXPLOIT, 3, [527.42, 552.94, 578.46, 595.48])
    # Last EFR should exceed 100% Affinity.

    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 1,
        }

    print("Incrementing Weakness Exploit on a weak point.")
    test_with_incrementing_skill(Skill.WEAKNESS_EXPLOIT, 3, [527.42, 544.44, 552.94, 578.46])

    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 0,
        }

    print("Incrementing Weakness Exploit on a non-weak point.")
    test_with_incrementing_skill(Skill.WEAKNESS_EXPLOIT, 3, [527.42]*4)
    # We now have full Handicraft, Critical Boost, Critical Eye, Attack Boost, and Weakness Exploit.

    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 1,
            Skill.AGITATOR        : 0,
        }

    print("Incrementing Agitator when monster is not enraged.")
    test_with_incrementing_skill(Skill.AGITATOR, 5, [578.46]*6)

    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 1,
            Skill.AGITATOR        : 1,
        }

    print("Incrementing Agitator when monster is enraged.")
    test_with_incrementing_skill(Skill.AGITATOR, 5, [578.46, 594.64, 602.31, 613.52, 621.24, 634.40])
    # We now have full Handicraft, Critical Boost, Critical Eye, Attack Boost, Weakness Exploit, and Agitator.
    
    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT : 2,
            Skill.AGITATOR         : 1,
            Skill.PEAK_PERFORMANCE : 1,
        }

    print("Incrementing Peak Performance.")
    test_with_incrementing_skill(Skill.PEAK_PERFORMANCE, 3, [634.40, 644.13, 653.86, 673.32])

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

