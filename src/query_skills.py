# -*- coding: ascii -*-

"""
Filename: query_skills.py
Author:   contact@simshadows.com

This file provides the MHWI build optimizer script's skills database queries.
"""

from collections import namedtuple, defaultdict
from enum import Enum, unique

from .utils import json_read

from .database_skills import (Skill,
                             SetBonus)


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


skills_with_implemented_features = {
        Skill.AGITATOR,
        Skill.ATTACK_BOOST,
        Skill.CRITICAL_BOOST,
        Skill.CRITICAL_EYE,
        Skill.NON_ELEMENTAL_BOOST,
        Skill.HANDICRAFT,
        Skill.PEAK_PERFORMANCE,
        Skill.WEAKNESS_EXPLOIT
    }


# This will take a dict like {Skill.AGITATOR: 10, ...} and clip it down to the maximum.
# This also returns a defaultdict with default value of zero.
def clipped_skills_defaultdict(skills_dict):
    assert all(level >= 0 for (_, level) in skills_dict.items()) # We shouldn't be seeing negative skill levels.
    return defaultdict(lambda : 0, {skill: min(level, skill.value.limit) for (skill, level) in skills_dict.items()})


# From a set of skills attainable from set bonuses, this function calculates the subset of set bonuses that may
# provide them.
def calculate_possible_set_bonuses_from_skills(set_bonus_skills):
    assert isinstance(set_bonus_skills, set)
    assert all(isinstance(x, Skill) for x in set_bonus_skills)
    return set(x for x in SetBonus if any((skill in set_bonus_skills) for (_, skill) in x.value.stages.items()))


# This will take a dictionary of {SetBonus: number_of_pieces} and returns the skills it provides as a dictionary
# of {Skill: level}.
# This assumes that set bonus skills are all binary.
def calculate_set_bonus_skills(set_bonus_pieces_dict, weapon_set_bonus_contribution):
    assert isinstance(weapon_set_bonus_contribution, SetBonus) or (weapon_set_bonus_contribution is None)

    ret = {}

    for (set_bonus, num_pieces) in set_bonus_pieces_dict.items():

        if set_bonus is weapon_set_bonus_contribution:
            num_pieces += 1

        for (stage, skill) in set_bonus.value.stages.items():
            if num_pieces >= stage:
                ret[skill] = 1

    return ret


SkillsContribution = namedtuple(
    "SkillsContribution",
    [
        "handicraft_level",
        "added_attack_power",
        "weapon_base_attack_power_multiplier",
        "raw_critical_multiplier",
        "added_raw_affinity",
    ],
)
def calculate_skills_contribution(skills_dict, skill_states_dict, maximum_sharpness_values, weapon_is_raw):
    skills_dict = clipped_skills_defaultdict(skills_dict)

    added_attack_power = 0
    added_raw_affinity = 0
    weapon_base_attack_power_multiplier = 1

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

    # Non-elemental Boost
    if (skills_dict[Skill.NON_ELEMENTAL_BOOST] == 1) and weapon_is_raw:
        weapon_base_attack_power_multiplier = 1.05

    ret = SkillsContribution(
            handicraft_level                    = skills_dict[Skill.HANDICRAFT],
            added_attack_power                  = added_attack_power,
            weapon_base_attack_power_multiplier = weapon_base_attack_power_multiplier,
            raw_critical_multiplier             = CRITICAL_BOOST_RAW_CRIT_MULTIPLIERS[skills_dict[Skill.CRITICAL_BOOST]],
            added_raw_affinity                  = added_raw_affinity,
        )
    return ret
