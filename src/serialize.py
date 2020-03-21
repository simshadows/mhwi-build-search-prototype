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

from .utils import all_unique, json_dumps_formatted

from .database_weapons     import WeaponClass
from .database_skills      import Skill
from .database_decorations import Decoration


def writejson_search_parameters(**kwargs):

    # KWARGS: Search Parameters

    selected_weapon_class  = kwargs["selected_weapon_class"]
    selected_skills        = kwargs["selected_skills"]
    selected_set_bonuses   = kwargs["selected_set_bonuses"]
    selected_decorations   = kwargs["selected_decorations"]

    min_health_regen_level = kwargs["min_health_regen_level"]

    skill_states           = kwargs["skill_states"]

    # KWARGS: Algorithm Performance Parameters

    num_worker_threads = kwargs["num_worker_threads"]
    batch_size = kwargs["batch_size"]
    batch_shuffle_rounds = kwargs["batch_shuffle_rounds"]

    assert isinstance(selected_weapon_class, WeaponClass)
    assert all(isinstance(k, Skill) and isinstance(v, int) and (v >= 0) for (k, v) in selected_skills.items())
    assert all(isinstance(x, Skill) for x in selected_set_bonuses) and all_unique(selected_set_bonuses)
    assert all(isinstance(x, Decoration) for x in selected_decorations) and all_unique(selected_decorations)

    assert isinstance(min_health_regen_level, int) and (min_health_regen_level >= 0)

    assert all(isinstance(k, Skill) and isinstance(v, int) and (v >= 0) for (k, v) in skill_states.items())

    assert isinstance(num_worker_threads, int) and (num_worker_threads > 0)
    assert isinstance(batch_size, int) and (num_worker_threads > 0)

    data = {
            "selected_weapon_class": selected_weapon_class.name,
            "selected_skills": {k.name: v for (k, v) in selected_skills.items()},
            "selected_set_bonuses": [x.name for x in selected_set_bonuses],
            "selected_decorations": [x.name for x in selected_decorations],

            "min_health_regen_augment_level": min_health_regen_level,

            "skill_states": {k.name: v for (k, v) in skill_states.items()},

            "algorithm_performance_parameters": {
                "num_worker_threads": num_worker_threads,
                "batch_size": batch_size,
                "batch_shuffle_rounds": batch_shuffle_rounds,
            }
        }
    return json_dumps_formatted(data)


SearchParameters = namedtuple(
    "SearchParameters",
    [
        "selected_weapon_class",
        "selected_skills",
        "selected_set_bonuses",
        "selected_decorations",

        "min_health_regen_augment_level",

        "skill_states",

        # Algorithm Performance Parameters

        "num_worker_threads",
        "batch_size",
        "batch_shuffle_rounds",
    ]
)
def readjson_search_parameters(json_str):
    assert isinstance(json_str, str)
    json_data = json.loads(json_str)

    # Get Data: Search Parameters

    selected_weapon_class_json = json_data["selected_weapon_class"]
    selected_skills_json       = json_data["selected_skills"]
    selected_set_bonuses_json  = json_data["selected_set_bonuses"]
    selected_decorations_json  = json_data["selected_decorations"]

    min_health_regen_json      = json_data["min_health_regen_augment_level"]

    skill_states_json          = json_data["skill_states"]

    # Get Data: Algorithm Performance Parameters

    num_worker_threads         = json_data["algorithm_performance_parameters"]["num_worker_threads"]
    batch_size                 = json_data["algorithm_performance_parameters"]["batch_size"]
    batch_shuffle_rounds       = json_data["algorithm_performance_parameters"]["batch_shuffle_rounds"]

    # Translate Data

    tup = SearchParameters(
            selected_weapon_class = WeaponClass[selected_weapon_class_json],
            selected_skills       = {Skill[k]: v   for (k, v) in selected_skills_json.items()},
            selected_set_bonuses  = {Skill[x]      for x      in selected_set_bonuses_json},
            selected_decorations  = {Decoration[x] for x      in selected_decorations_json},

            min_health_regen_augment_level = min_health_regen_json,

            skill_states = {Skill[k]: v for (k, v) in skill_states_json.items()},

            # Algorithm Performance Parameters

            num_worker_threads   = num_worker_threads,
            batch_size           = batch_size,
            batch_shuffle_rounds = batch_shuffle_rounds,
        )

    # Data Validation
    # (TODO: Make user-friendly error messages for any exceptions that may be thrown before this.)

    if any((not isinstance(v, int)) or (v < 0) for (_, v) in tup.selected_skills.items()):
        raise ValueError("Selected skill levels must be integers above or equal to zero.")
    elif any((not isinstance(v, int)) or (v < 0) or (v >= len(k.value.states)) for (k, v) in tup.skill_states.items()):
        raise ValueError("Skill states must be integers above or equal to zero.")
    elif (not isinstance(tup.num_worker_threads, int)) or (tup.num_worker_threads <= 0):
        raise ValueError("Number of worker threads must be an integer above zero.")

    return tup

