# -*- coding: ascii -*-

"""
Filename: database_decorations.py
Author:   contact@simshadows.com
"""

from collections import namedtuple, defaultdict
from enum import Enum, unique
from itertools import product

from database_skills import Skill
from utils import json_read


DECORATIONS_DATA_FILENAME = "database_decorations.json"


DecorationInfo = namedtuple(
    "DecorationInfo",
    [
        "name",        # string
        "slot_size",   # int
        "skills_dict", # {Skill: level}
    ],
)


def _obtain_decorations_enum():
    json_data = json_read(DECORATIONS_DATA_FILENAME)

    def validation_error(info, deco=None):
        if deco is None:
            raise ValueError(f"{DECORATIONS_DATA_FILENAME}: {info}")
        else:
            raise ValueError(f"{DECORATIONS_DATA_FILENAME} {deco}: {info}")

    decos_intermediate = {}

    ###############################################
    # STAGE 1: Build up the components collection #
    ###############################################
    # All decorations are based on the simple single-skill decorations.
    # The single-skill decorations will first be processed into the deco_components dict first.
    # This is NOT a collection of size-1 decorations, but it is ALMOST one.
    # We will process it again in stage 2.

    deco_components = {}
    component_names = set()
    component_skills = set()

    for (component_id, component_json_data) in json_data["simple_decorations"].items():
        if not isinstance(component_id, str):
            validation_error("Decoration IDs must be strings. Instead, we have: " + str(component_id))
        elif len(component_id) == 0:
            validation_error("Decoration IDs must be non-empty strings.")
        elif component_id in deco_components:
            validation_error("Decoration IDs must be unique.", deco=component_id)
        # TODO: Also put a condition that skill IDs must be capitalized with underscores.

        component = {}
        component["name"] = component_json_data["name"]
        component["slot_size"] = component_json_data["slot"]
        component["skill"] = Skill[component_json_data["skill"]]

        if not isinstance(component["name"], str):
            validation_error("Decoration names must be strings. Instead, we have: " + str(component["name"]))
        elif len(component["name"]) == 0:
            validation_error("Decoration names must be non-empty strings.")
        elif component["name"] in component_names:
            validation_error("Decoration names must be unique.", deco=component_id)
        elif (not isinstance(component["slot_size"], int)) or (component["slot_size"] <= 0) or (component["slot_size"] > 3):
            validation_error("Decoration slot sizes for simple decorations must be ints between 1 and 3.", deco=component_id)
        elif component["skill"] in component_skills:
            validation_error("Decoration skills must be unique.", deco=component_id)

        component_names.add(component["name"])
        component_skills.add(component["skill"])
        deco_components[component_id] = component

    ###############################
    # STAGE 2: Simple Decorations #
    ###############################
    # Now, we process the components into the simple decorations.

    for (component_id, component_info) in deco_components.items():
        decos_intermediate[component_id] = DecorationInfo(
                name        = component_info["name"] + " Jewel " + str(component_info["slot_size"]),
                slot_size   = component_info["slot_size"],
                skills_dict = {component_info["skill"]: 1},
            )

    #############################################
    # STAGE 3: Size-4 Slot Compound Decorations #
    #############################################

    for (_, combo_json_data) in json_data["4slot_compound_decorations_batch_definitions"].items():
        for (left_component_id, right_component_id) in product(combo_json_data["left_side"], combo_json_data["right_side"]):
            left_component = deco_components[left_component_id]
            right_component = deco_components[right_component_id]

            if left_component_id == right_component_id:
                validation_error(f"Two of the same simple decoration ID in a combination.", deco=left_component_id)
            elif left_component["skill"] is right_component["skill"]: # This one is probably not necessary.
                validation_error(f"Two of the same simple decoration skill in a combination.", deco=left_component_id)
            
            deco_id = f"COMPOUND_{left_component_id}_{right_component_id}"
            tup = DecorationInfo(
                    name        = left_component["name"] + "/" + right_component["name"] + " Jewel 4",
                    slot_size   = 4,
                    skills_dict = {left_component["skill"]: 1, right_component["skill"]: 1},
                )

            deco_id_flipped = f"COMPOUND_{right_component_id}_{left_component_id}"

            if deco_id in decos_intermediate:
                validation_error("Decoration ID already exists.", deco=deco_id)
            elif deco_id_flipped in decos_intermediate:
                validation_error(f"Decoration ID already exists in the flipped form {deco_id_flipped}.", deco=deco_id)

            decos_intermediate[deco_id] = tup
            
    ############################################
    # STAGE 4: Size-4 Single-Skill Decorations #
    ############################################

    for (component_id, versions) in json_data["4slot_single_skill_decorations"].items():
        component = deco_components[component_id]
        for version in versions:
            if version == 2:
                deco_id = f"{component_id}_X2"
                tup = DecorationInfo(
                        name        = component["name"] + " Jewel+ 4",
                        slot_size   = 4,
                        skills_dict = {component["skill"]: 2},
                    )
            elif version == 3:
                deco_id = f"{component_id}_X3"
                tup = DecorationInfo(
                        name        = "Hard " + component["name"] + " Jewel 4",
                        slot_size   = 4,
                        skills_dict = {component["skill"]: 3},
                    )
            else:
                validation_error("Invalid size-4 single-skill version(s). Must be an int of value 2 or 3.", deco=component_id)

            if deco_id in decos_intermediate:
                validation_error("Decoration ID already exists.", deco=deco_id)

            decos_intermediate[deco_id] = tup

    if len(decos_intermediate) == 0:
        validation_error("No decorations have been recorded.")

    return Enum("Decoration", decos_intermediate)


def _get_index_for_skill_to_size():
    intermediate_dict = {}
    for deco in Decoration:
        if len(deco.value.skills_dict) == 1:
            for (skill, level) in deco.value.skills_dict.items():
                pass
            if level == 1:
                if skill in intermediate_dict:
                    raise ValueError("Found a duplicate skill for the skill_to_simple_deco_size index.")
                intermediate_dict[skill] = deco.value.slot_size
    if len(intermediate_dict) == 0:
        raise RuntimeError("We should have at least one item for the index.")
    return intermediate_dict


# This provides all decorations
Decoration = _obtain_decorations_enum()

# This provides a useful index for finding a skill's associated single-skill decoration's size.
skill_to_simple_deco_size = _get_index_for_skill_to_size()


def get_pruned_deco_set(required_skills, bonus_skills=[]):
    assert isinstance(required_skills, set)
    assert isinstance(bonus_skills, list) # This must be a list because list order is used for priority.

    # This wil be referred to as a last resort if we need to pick a skill that isn't in bonus_skills.
    # This is an arbitrary list of skills that I've randomly decided to prioritize.
    # (If you actually care about the skills, specify it in bonus_skills :) )
    backup_bonus_skills_list = [
            Skill.HEALTH_BOOST,
            Skill.FREE_MEAL,
            Skill.FLINCH_FREE,
            Skill.FORTIFY,
            Skill.EVADE_WINDOW,
            Skill.DIVINE_BLESSING,
            Skill.CONSTITUTION,
            Skill.EARPLUGS,
        ]

    # This is set up as a map from skill to sorting order: {Skill: sorting_order}
    full_bonus_skills = {skill: i for (i, skill) in enumerate(bonus_skills + backup_bonus_skills_list)}
    assert len(full_bonus_skills) >= 2 # I don't know if this algorithm will work with an empty map. Good to have skills anyway.

    pruned_set = set()

    compound_decos = defaultdict(lambda : []) # {Skill: [Decoration,]}
    for deco in Decoration:
        for (skill, level) in deco.value.skills_dict.items():

            if skill not in required_skills:
                continue

            if len(deco.value.skills_dict) == 1:
                pruned_set.add(deco)
            elif skill in required_skills:
                assert len(deco.value.skills_dict) > 1
                extra_skills = set(deco.value.skills_dict) - {skill,}
                compound_decos[skill].append((deco, extra_skills))

    for (skill, deco_list) in compound_decos.items():
        chosen_deco = None
        chosen_sort_order = len(full_bonus_skills) # Set to a sort order lower than the least-prioritized skill.
        for (deco, extra_skills) in deco_list:
            assert len(extra_skills) == 1 # I will assume decorations can never have more than two skills in total.
            extra_skill = extra_skills.pop()
            if extra_skill in full_bonus_skills:
                sort_order = full_bonus_skills[extra_skill]
                if sort_order < chosen_sort_order:
                    chosen_deco = deco
                    chosen_sort_order = sort_order
            if chosen_deco is None: # Fix up this duplicate code.
                chosen_deco = deco
        assert chosen_deco is not None # We must have at least one deco.
        pruned_set.add(chosen_deco)

    return pruned_set


def calculate_decorations_skills_contribution(decorations_counter):
    skills = defaultdict(lambda : 0)
    for (deco, total) in decorations_counter.items():
        for (skill, level) in deco.value.skills_dict.items():
            skills[skill] += level * total
    return skills

