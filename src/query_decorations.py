# -*- coding: ascii -*-

"""
Filename: query_decorations.py
Author:   contact@simshadows.com

This file provides the MHWI build optimizer script's decorations database queries.
"""

import logging
from collections import defaultdict

from .utils import (prune_by_superceding,
                   counters_are_equal,
                   counter_is_subset)
from .loggingutils import log_appstats_reduction

from .database_skills import Skill

from .database_decorations import Decoration


logger = logging.getLogger(__name__)


def get_pruned_deco_set(skill_subset):
    assert isinstance(skill_subset, set)

    simple_decos = {x for x in Decoration if (x.value.slot_size < 4)}
    assert all((len(x.value.skills_dict) == 1) and (sum(v for (_, v) in x.value.skills_dict.items()) == 1) for x in simple_decos)
    simple_decos = {x for x in simple_decos if (set(x.value.skills_dict) <= skill_subset)}

    simple_deco_skills = set()
    for deco in simple_decos:
        for (skill, _) in deco.value.skills_dict.items():
            assert skill not in simple_deco_skills # We don't expect duplicates
            simple_deco_skills.add(skill)

    size4_decos = set()
    for deco in Decoration:
        if deco.value.slot_size == 4:
            filtered_skills = {k: v for (k, v) in deco.value.skills_dict.items() if (k in skill_subset)}
            if len(filtered_skills) == 1:
                (skill, level) = filtered_skills.popitem()
                if (skill in simple_deco_skills) and (level == 1):
                    continue
                size4_decos.add(deco)
            elif len(filtered_skills) > 0:
                size4_decos.add(deco)

    # Finally, we prune away clearly-inferior size-4 decos.
    def left_supercedes_right(left, right):
        left = {k: v for (k, v) in left.value.skills_dict.items() if (k in skill_subset)}
        right = {k: v for (k, v) in right.value.skills_dict.items() if (k in skill_subset)}
        assert not counters_are_equal(left, right) # No two size-4 decos should look the same.
        return counter_is_subset(right, left)
    size4_decos = set(prune_by_superceding(size4_decos, left_supercedes_right))

    ret = simple_decos | size4_decos

    # Statistics stuff
    log_appstats_reduction("Decorations pruned", len(Decoration), len(ret))
    for deco in sorted(ret, key=lambda x : x.value.slot_size):
        logger.info(f"Decoration kept: {deco.value.name}")

    return ret
    
## Less-pruned alternative
#def get_pruned_deco_set(skill_subset, bonus_skills=[]):
#    assert isinstance(skill_subset, set)
#    assert isinstance(bonus_skills, list) # This must be a list because list order is used for priority.
#
#    # This wil be referred to as a last resort if we need to pick a skill that isn't in bonus_skills.
#    # This is an arbitrary list of skills that I've randomly decided to prioritize.
#    # (If you actually care about the skills, specify it in bonus_skills :) )
#    backup_bonus_skills_list = [
#            Skill.HEALTH_BOOST,
#            Skill.FREE_MEAL,
#            Skill.FLINCH_FREE,
#            Skill.FORTIFY,
#            Skill.EVADE_WINDOW,
#            Skill.DIVINE_BLESSING,
#            Skill.CONSTITUTION,
#            Skill.EARPLUGS,
#        ]
#
#    # This is set up as a map from skill to sorting order: {Skill: sorting_order}
#    full_bonus_skills = {skill: i for (i, skill) in enumerate(bonus_skills + backup_bonus_skills_list)}
#    assert len(full_bonus_skills) >= 2 # I don't know if this algorithm will work with an empty map. Good to have skills anyway.
#
#    pruned_set = set()
#
#    compound_decos = defaultdict(lambda : []) # {Skill: [Decoration,]}
#    for deco in Decoration:
#        for (skill, level) in deco.value.skills_dict.items():
#
#            if skill not in skill_subset:
#                continue
#
#            if len(deco.value.skills_dict) == 1:
#                pruned_set.add(deco)
#            elif skill in skill_subset:
#                assert len(deco.value.skills_dict) > 1
#                extra_skills = set(deco.value.skills_dict) - {skill,}
#                compound_decos[skill].append((deco, extra_skills))
#
#    for (skill, deco_list) in compound_decos.items():
#        chosen_deco = None
#        chosen_sort_order = len(full_bonus_skills) # Set to a sort order lower than the least-prioritized skill.
#        for (deco, extra_skills) in deco_list:
#            assert len(extra_skills) == 1 # I will assume decorations can never have more than two skills in total.
#            extra_skill = extra_skills.pop()
#            if extra_skill in full_bonus_skills:
#                sort_order = full_bonus_skills[extra_skill]
#                if sort_order < chosen_sort_order:
#                    chosen_deco = deco
#                    chosen_sort_order = sort_order
#            if chosen_deco is None: # Fix up this duplicate code.
#                chosen_deco = deco
#        assert chosen_deco is not None # We must have at least one deco.
#        pruned_set.add(chosen_deco)
#
#    return pruned_set
## Least-pruned alternative
#def get_pruned_deco_set(skill_subset):
#    assert isinstance(skill_subset, set)
#    pruned_set = set()
#    for deco in Decoration:
#        if any((skill in skill_subset) for (skill, _) in deco.value.skills_dict.items()):
#            pruned_set.add(deco)
#    return pruned_set


def calculate_decorations_skills_contribution(decorations_counter):
    skills = defaultdict(lambda : 0)
    for (deco, total) in decorations_counter.items():
        for (skill, level) in deco.value.skills_dict.items():
            skills[skill] += level * total
    return skills

