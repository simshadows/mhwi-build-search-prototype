# -*- coding: ascii -*-

"""
Filename: query_charms.py
Author:   contact@simshadows.com

This file provides the MHWI build optimizer script's charm database queries.
"""

from .database_skills import Skill

from .database_charms import (CharmInfo,
                             charms_indexed_by_skill)


def get_charms_subset(skill_subset):
    charms = set()
    for skill in skill_subset:
        if skill in charms_indexed_by_skill:
            for charm in charms_indexed_by_skill[skill]:
                charms.add(charm)
    return charms


# You give it a CharmInfo object, it gives you back info about the max level of the charm.
def calculate_skills_dict_from_charm(charm_info, level):
    assert isinstance(charm_info, CharmInfo)
    assert isinstance(level, int)
    assert (level > 0) and (level <= charm_info.max_level)
    skills_dict = {skill: level for skill in charm_info.skills}
    assert all(isinstance(k, Skill) for (k, v) in skills_dict.items())
    return skills_dict
