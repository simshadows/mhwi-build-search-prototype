# -*- coding: ascii -*-

"""
Filename: query_decorations.py
Author:   contact@simshadows.com

This file provides the MHWI build optimizer script's decorations database queries.
"""

from collections import defaultdict

from .database_skills import Skill

from .database_decorations import Decoration

# For now, this implementation will just give all decorations that provide at least one of the required skills.
def get_pruned_deco_set(required_skills):
    assert isinstance(required_skills, set)
    pruned_set = set()
    for deco in Decoration:
        if any((skill in required_skills) for (skill, _) in deco.value.skills_dict.items()):
            pruned_set.add(deco)
    return pruned_set
# Use this implementation again later.
#def get_pruned_deco_set(required_skills, bonus_skills=[]):
#    assert isinstance(required_skills, set)
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
#            if skill not in required_skills:
#                continue
#
#            if len(deco.value.skills_dict) == 1:
#                pruned_set.add(deco)
#            elif skill in required_skills:
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


def calculate_decorations_skills_contribution(decorations_counter):
    skills = defaultdict(lambda : 0)
    for (deco, total) in decorations_counter.items():
        for (skill, level) in deco.value.skills_dict.items():
            skills[skill] += level * total
    return skills

