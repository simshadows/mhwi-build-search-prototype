# -*- coding: ascii -*-

"""
Filename: serialize.py
Author:   contact@simshadows.com

Anything to do with serializing/deserializing.

This is with two exceptions:
    1) Builds (see the Builds class)
    2) Database data (see database_weapons.py, database_charms.py, etc.)
"""


import json
from collections import namedtuple

from .enums import Tier
from .utils import all_unique, json_dumps_formatted

from .database_weapons     import WeaponClass
from .database_skills      import Skill


def writejson_search_parameters(**kwargs):

    # KWARGS: Search Parameters

    selected_armour_tier      = kwargs["selected_armour_tier"]
    selected_weapon_class     = kwargs["selected_weapon_class"]
    selected_skills           = kwargs["selected_skills"]
    selected_set_bonus_skills = kwargs["selected_set_bonus_skills"]

    min_health_regen_level    = kwargs["min_health_regen_level"]

    skill_states              = kwargs["skill_states"]

    assert isinstance(selected_armour_tier, Tier) or (selected_armour_tier is None)
    assert isinstance(selected_weapon_class, WeaponClass)
    assert all(isinstance(k, Skill) and isinstance(v, int) and (v >= 0) for (k, v) in selected_skills.items())
    assert all(isinstance(x, Skill) for x in selected_set_bonus_skills) and all_unique(selected_set_bonus_skills)

    assert isinstance(min_health_regen_level, int) and (min_health_regen_level >= 0)

    assert all(isinstance(k, Skill) and isinstance(v, int) and (v >= 0) for (k, v) in skill_states.items())


    data = {
            "selected_armour_tier"      : selected_armour_tier,
            "selected_weapon_class"     : selected_weapon_class.name,
            "selected_skills"           : {k.name: v for (k, v) in selected_skills.items()},
            "selected_set_bonus_skills" : [x.name for x in selected_set_bonus_skills],

            "min_health_regen_augment_level": min_health_regen_level,

            "skill_states": {k.name: v for (k, v) in skill_states.items()},
        }
    return json_dumps_formatted(data)


SearchParameters = namedtuple(
    "SearchParameters",
    [
        "selected_armour_tier",
        "selected_weapon_class",
        "selected_skills",
        "selected_set_bonus_skills",

        "min_health_regen_augment_level",

        "skill_states",
    ]
)
def readjson_search_parameters(json_str):
    assert isinstance(json_str, str)
    json_data = json.loads(json_str)

    # Get Data: Search Parameters

    selected_armour_tier_json      = json_data["selected_armour_tier"]
    selected_weapon_class_json     = json_data["selected_weapon_class"]
    selected_skills_json           = json_data["selected_skills"]
    selected_set_bonus_skills_json = json_data["selected_set_bonus_skills"]

    min_health_regen_json          = json_data["min_health_regen_augment_level"]

    skill_states_json              = json_data["skill_states"]

    # Translate Data

    selected_armour_tier = None if selected_armour_tier_json is None else Tier[selected_armour_tier_json]

    tup = SearchParameters(
            selected_armour_tier      = selected_armour_tier,
            selected_weapon_class     = WeaponClass[selected_weapon_class_json],
            selected_skills           = {Skill[k]: v   for (k, v) in selected_skills_json.items()},
            selected_set_bonus_skills = {Skill[x]      for x      in selected_set_bonus_skills_json},

            min_health_regen_augment_level = min_health_regen_json,

            skill_states = {Skill[k]: v for (k, v) in skill_states_json.items()},
        )

    # Data Validation
    # (TODO: Make user-friendly error messages for any exceptions that may be thrown before this.)

    if any((not isinstance(v, int)) or (v < 0) for (_, v) in tup.selected_skills.items()):
        raise ValueError("Selected skill levels must be integers above or equal to zero.")
    elif any((not isinstance(v, int)) or (v < 0) or (v >= len(k.value.states)) for (k, v) in tup.skill_states.items()):
        raise ValueError("Skill states must be integers above or equal to zero.")

    return tup

