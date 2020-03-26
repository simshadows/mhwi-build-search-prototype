# -*- coding: ascii -*-

"""
Filename: query_skills.py
Author:   contact@simshadows.com

This file provides the MHWI build optimizer script's skills database queries.
"""

from copy import copy
from itertools import product
from collections import namedtuple, defaultdict
from enum import Enum, unique

from .utils import json_read, prune_by_superceding

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


# From a set of skills attainable from set bonuses, this function calculates all possible
# combinations of set bonuses that, if at least one of these combinations is satisfied, will
# grant all skills listed in set_bonus_skills.
#
# This function returns a list of dicts:
#   [{SetBonus: minimum_number_of_pieces, ...}, ...]
def calculate_possible_set_bonus_combos(set_bonus_skills):
    assert isinstance(set_bonus_skills, set)
    assert all(isinstance(x, Skill) for x in set_bonus_skills)

    options = []
    for skill_required in set_bonus_skills:
        pick_one = []
        for set_bonus in SetBonus:
            for (num_pieces, skill_granted) in set_bonus.value.stages.items():
                if skill_granted is skill_required:
                    pick_one.append((set_bonus, num_pieces))
                    break
        if len(pick_one) == 0:
            raise RuntimeError("A skill in set_bonus_skills cannot be satisfied by set bonuses.")
        options.append(pick_one)

    # Now that we have options, we make the combinations.

    combinations = []
    for combination_intermediate in product(*options):
        combination = {}
        for (set_bonus, num_pieces) in combination_intermediate:
            if not ((set_bonus in combination) and (combination[set_bonus] <= num_pieces)):
                combination[set_bonus] = num_pieces
        combinations.append(combination)

    # And now, we prune the combinations.

    # left supercedes right if left is entirely a subset of right.
    def left_supercedes_right(left, right):
        assert isinstance(left, dict)
        assert isinstance(right, dict)
        if left == right:
            return None
        # Now, we check if the left is a strict subset of right.
        # Note that we know the two dictionaries can't be equivalent, even though we're using the
        # less-than-or-equal operator.
        return any(l_num_pieces <= right.get(l_set_bonus, 0) for (l_set_bonus, l_num_pieces) in left.items())

    return prune_by_superceding(combinations, left_supercedes_right)


# Returns a new list of set bonus combinations (with a similar format to the input) with all combinations
# relaxed by one piece.
#
# For example, if we have this as the input:
#   [
#     {
#         set_bonus_a: 2,
#         set_bonus_b: 4
#     },
#     {
#         set_bonus_a: 4
#     }
#   ]
# The output might look something like this:
#   [
#     {
#         set_bonus_a: 1,
#         set_bonus_b: 4
#     },
#     {
#         set_bonus_a: 2,
#         set_bonus_b: 3
#     },
#     {
#         set_bonus_a: 3
#     }
#   ]
def relax_set_bonus_combos(set_bonus_combos):
    assert isinstance(set_bonus_combos, list)

    ret = []

    for set_bonus_combo in set_bonus_combos:
        for (set_bonus, num_pieces) in set_bonus_combo.items():
            assert isinstance(set_bonus, SetBonus)
            assert isinstance(num_pieces, int) and (num_pieces > 0)

            new_combo = copy(set_bonus_combo)
            if num_pieces > 1:
                new_combo[set_bonus] = num_pieces - 1
            else:
                del new_combo[set_bonus]

            if len(new_combo) != 0:
                ret.append(new_combo)

    # We do a final step of pruning.

    # left supercedes right if left is entirely a subset of right.
    def left_supercedes_right(left, right):
        assert isinstance(left, dict)
        assert isinstance(right, dict)
        if left == right:
            return None
        # Now, we check if the left is a strict subset of right.
        # Note that we know the two dictionaries can't be equivalent, even though we're using the
        # less-than-or-equal operator.
        return any(l_num_pieces <= right.get(l_set_bonus, 0) for (l_set_bonus, l_num_pieces) in left.items())

    return prune_by_superceding(ret, left_supercedes_right)


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

