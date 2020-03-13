# -*- coding: ascii -*-

"""
Filename: database_charms.py
Author:   contact@simshadows.com
"""

from collections import namedtuple

from .utils import json_read

from .database_skills import Skill


CHARMS_DATA_FILENAME = "data/database_charms.json"


CharmInfo = namedtuple(
    "CharmInfo",
    [
        "id",        # string

        "name",      # string
        "max_level", # int
        "skills",    # [Skill]
    ],
)
def _obtain_charms_db():
    json_data = json_read(CHARMS_DATA_FILENAME)

    def validation_error(info, charm=None):
        if charm is None:
            raise ValueError(f"{CHARMS_DATA_FILENAME}: {info}")
        else:
            raise ValueError(f"{CHARMS_DATA_FILENAME} {charm}: {info}")

    charms_intermediate = {}
    index_by_skill_intermediate = {}

    charm_names = set()
    charm_skill_combinations = set()

    for (charm_id, charm_json_data) in json_data["charms"].items():
        if not isinstance(charm_id, str):
            validation_error("Charm IDs must be strings. Instead, we have: " + str(charm_id))
        elif len(charm_id) == 0:
            validation_error("Charm IDs must be non-empty strings.")
        elif charm_id in charms_intermediate:
            validation_error("Charm IDs must be unique.", charm=charm)
        # TODO: Also put a condition that charm IDs must be capitalized with underscores.

        tup = CharmInfo(
                id = charm_id,
                name = charm_json_data["name"],
                max_level = charm_json_data["max_level"],
                skills = tuple(Skill[skill_id] for skill_id in charm_json_data["skills"])
            )

        if not isinstance(tup.name, str):
            validation_error("Charm names must be strings. Instead, we have: " + str(tup.name))
        elif len(tup.name) == 0:
            validation_error("Charm names must be non-empty strings.")
        elif tup.name in charm_names:
            validation_error("Charm names must be unique.", charm=charm_id)
        elif (not isinstance(tup.max_level, int)) or (tup.max_level <= 0):
            validation_error("Charm max levels must be ints between 1 and 10.", charm=charm_id)
        elif tup.max_level > 8:
            validation_error("Charm max level of {tup.max_level} is probably incorrect.", charm=charm_id)
        elif len(tup.skills) == 0:
            validation_error("Charm does not appear to have any skills.", charm=charm_id)
        elif len(tup.skills) > 2:
            validation_error("Charm has more than two skills. This is probably incorrect.", charm=charm_id)
        elif tup.skills in charm_skill_combinations:
            validation_error("Charm skill combinations must be unique.", charm=charm_id)

        charm_names.add(tup.name)
        charm_skill_combinations.add(tup.skills)
        charms_intermediate[charm_id] = tup

        # Now we make the alternative index

        for skill in tup.skills:
            if skill in index_by_skill_intermediate:
                index_by_skill_intermediate[skill].append(tup)
            else:
                index_by_skill_intermediate[skill] = [tup]

    return charms_intermediate, index_by_skill_intermediate

charms_db, charms_indexed_by_skill = _obtain_charms_db()


# You give it a CharmInfo object, it gives you back info about the max level of the charm.
def calculate_skills_dict_from_charm(charm_info, level):
    assert isinstance(charm_info, CharmInfo)
    assert isinstance(level, int)
    assert (level > 0) and (level <= charm_info.max_level)
    skills_dict = {skill: level for skill in charm_info.skills}
    assert all(isinstance(k, Skill) for (k, v) in skills_dict.items())
    return skills_dict

