# -*- coding: ascii -*-

"""
Filename: database_skills.py
Author:   contact@simshadows.com

This file provides the MHWI build optimizer script's skills database data.
"""

from collections import namedtuple
from enum import Enum

from .utils import json_read


SKILLS_DATA_FILENAME = "data/database_skills.json"


SkillInfo = namedtuple(
    "SkillInfo",
    [
        # FIELDS REQUIRED TO BE SET

        "name",    # In-game name, exactly as written. All skills must have a name string.
        "limit",   # Maximum number of levels obtainable NORMALLY.
        "tooltip", # In-game tooltip, exactly as written. All skills must have a tooltip string.

        # FIELDS WITH DEFAULTS

        "extended_limit", # Extra levels over the maximum, obtainable with special skills like Agitator Secret.
                          # This ADDS onto the number set by the limit field. E.g. extended_limit=2 for Agitator Secret.
                          # IMPORTANT: We are assuming for now that there are only two limits.
        
        "states", # If an ability has multiple "meaningful" states, this field will be a tuple of strings.
                  # Each string corresponds to a particular state of the ability.
                  # Each string must concisely describe the condition and the state with as little reliance on context
                  # cues as possible. (You must be able to look at the string on its own an understand it.)
                  #
                  # This field alone determines how many states a skill can have.
                  # E.g. if self.states == ("ability inactive", "charging", "ability active"), then we can read the
                  # length of the tuple to determine that there are three possible states.
                  # 
                  # Generally, stateful skills are all either binary, or have an escalation in strength.
                  # (I'm unaware of any ability that operates differently.)
                  # For this, states are actually represented in code by the pair:
                  #     1) a Skill (see the Skill class below), and
                  #     2) an integer.
                  # The integer corresponds to an index into the states tuple.
                  # Integer 0 will ALWYAS be the "off" state.
                  # Increasing integers will correspond to the escalation. (For a binary state, 1 is "on".)
                  #
                  # If an ability is always active, then this field is set to None.

        "zeroth_state_can_be_blank", # If True, then self.states[0] can be easily omitted without losing meaning.
                                     # If False, then it is not omitted.
                                     # If states is None, then this can be anything.

        "info",          # More information about the skill. I probably wrote this myself. If no info, put an empty string.
        "previous_name", # If the skill name was changed, put it here. If no previous name, put None.
    ]
)

SetBonusInfo = namedtuple(
    "SetBonusInfo",
    [
        "name",   # string
        "stages", # {number_of_pieces: Skill}
    ],
)


def _obtain_skills_enum():
    json_data = json_read(SKILLS_DATA_FILENAME)

    ###################
    # STAGE 1: Skills #
    ###################

    def validation_error(info, skill=None):
        if skill is None:
            raise ValueError(f"{SKILLS_DATA_FILENAME}: {info}")
        else:
            raise ValueError(f"{SKILLS_DATA_FILENAME} {skill}: {info}")

    skills_intermediate = {}
    skill_names = set()

    for (skill_id, skill_json_data) in json_data["skills"].items():

        if not isinstance(skill_id, str):
            validation_error("Skill IDs must be strings. Instead, we have: " + str(skill_id))
        elif len(skill_id) == 0:
            validation_error("Skill IDs must be strings of non-zero length.")
        elif skill_id in skills_intermediate:
            validation_error(f"Skill IDs must be unique.", skill=skill_id)
        # TODO: Also put a condition that skill IDs must be capitalized with underscores.

        tup = SkillInfo(
                name = skill_json_data["name"],

                limit          = skill_json_data["limit"],
                extended_limit = skill_json_data.get("extended_limit", skill_json_data["limit"]),

                states                    = skill_json_data.get("states", None), # Most skills aren't stateful.
                zeroth_state_can_be_blank = skill_json_data.get("zeroth_state_can_be_blank", True), # Most stateful skills
                                                                                                    # are binary.

                tooltip       = skill_json_data["tooltip"],
                info          = skill_json_data.get("info", ""), # I don't care to write about *ALL* skills yet.
                previous_name = skill_json_data.get("previous_name", None), # Most skills don't have previous names.
            )

        if (not isinstance(tup.name, str)) or (len(tup.name) == 0):
            validation_error("Skill names must be non-empty strings.", skill=skill_id)
        elif tup.name in skill_names:
            validation_error("Skill names must be unique.", skill=skill_id)
        elif (not isinstance(tup.limit, int)) or (tup.limit <= 0):
            validation_error("Skill level limits must be ints above zero.", skill=skill_id)
        elif (not isinstance(tup.extended_limit, int)) or (tup.extended_limit < tup.limit):
            validation_error("Skill extended level limits must be ints, and not under the regular limit.", skill=skill_id)

        elif (tup.states is not None) and ((not isinstance(tup.states, list)) or (len(tup.states) < 2)):
            validation_error("Skill states must be represented as a list, or as null.", skill=skill_id)
        elif isinstance(tup.states, list) and any(((not isinstance(s, str)) or (len(s) == 0)) for s in tup.states):
            validation_error("Each skill state must be a non-empty string.", skill=skill_id)
        elif not isinstance(tup.zeroth_state_can_be_blank, bool):
            validation_error("zeroth_state_can_be_blank must be a boolean.", skill=skill_id)

        elif (not isinstance(tup.tooltip, str)) or (len(tup.tooltip) == 0):
            validation_error("Skill tooltips must be non-empty strings.", skill=skill_id)
        elif (not isinstance(tup.info, str)):
            validation_error("Skill info (not the tooltips!) must be either null, or a non-empty string.", skill=skill_id)
        elif (tup.previous_name is not None) and ((not isinstance(tup.previous_name, str)) or (len(tup.previous_name) == 0)):
            validation_error("Skill previous name must be either null, or a non-empty string.", skill=skill_id)

        skill_names.add(tup.name)
        skills_intermediate[skill_id] = tup

    if len(skills_intermediate) == 0:
        validation_error("Found no skills.")

    skills_intermediate_enum = Enum("Skill", skills_intermediate)

    ########################
    # STAGE 2: SET BONUSES #
    ########################

    def validation_error(info, bonus=None):
        if bonus is None:
            raise ValueError(f"{SKILLS_DATA_FILENAME}: {info}")
        else:
            raise ValueError(f"{SKILLS_DATA_FILENAME} {bonus}: {info}")

    set_bonuses_intermediate = {}
    set_bonus_names = set()

    for (bonus_id, bonus_json_data) in json_data["set_bonuses"].items():

        if not isinstance(bonus_id, str):
            validation_error("Set bonus IDs must be strings. Instead, we have: " + str(bonus_id))
        elif len(bonus_id) == 0:
            validation_error("Set bonus IDs must be strings of non-zero length.")
        elif bonus_id in set_bonuses_intermediate:
            validation_error(f"Set bonus IDs must be unique.", bonus=bonus_id)
        elif bonus_id in skills_intermediate:
            validation_error(f"Set bonus ID is also a skill ID. Is that intentional?", bonus=bonus_id)
        # TODO: Also put a condition that set bonus IDs must be capitalized with underscores.

        tup = SetBonusInfo(
                name = bonus_json_data["name"],
                stages = {x["parts"]: skills_intermediate_enum[x["skill"]] for x in bonus_json_data["stages"]}
            )

        if (not isinstance(tup.name, str)) or (len(tup.name) == 0):
            validation_error("Set bonus names must be strings of non-zero length.")
        elif tup.name in set_bonus_names:
            validation_error("Set bonus names should be unique.", skill=skill_id)
        elif len(tup.stages) == 0:
            validation_error("Set bonuses must have at least one stage.")
        elif any((not isinstance(parts, int)) or (parts < 1) or (parts > 5) for (parts, skill) in tup.stages.items()):
            validation_error("Set bonuses must have at least one stage.")

        set_bonus_names.add(tup.name)
        set_bonuses_intermediate[bonus_id] = tup

    set_bonuses_intermediate_enum = Enum("SetBonus", set_bonuses_intermediate)

    return (skills_intermediate_enum, set_bonuses_intermediate_enum)


Skill, SetBonus = _obtain_skills_enum()
