#!/usr/bin/env python3
# -*- coding: ascii -*-

"""
Filename: mhwi_build_search.py
Author:   contact@simshadows.com

The entrypoint for my Monster Hunter World Iceborne build optimization tool!

In this version, we assume each level under maximum Handicraft will subtract sharpness by 10 points.
"""

import sys

from collections import defaultdict

from src.unit_testing import run_tests
from src.search       import find_highest_efr_build
from src.utils        import ENCODING

from src.database_armour      import (ArmourDiscriminator,
                                     ArmourVariant,
                                     ArmourSlot,
                                     armour_db)
from src.database_decorations import Decoration
from src.database_skills      import Skill
from src.database_weapons     import weapon_db

from src.query_weapons import IBWeaponAugmentType


def print_debugging_statistics():
    armour_set_total = 0
    for (_, armour_set) in armour_db.items():
        armour_set_total += sum(len(v) for (k, v) in armour_set.variants.items())

    print("=== Application Statistics ===")
    print()
    print("Number of skills: " + str(len(list(Skill))))
    print()
    print("Total number of armour pieces: " + str(armour_set_total))
    print("Total number of weapons: " + str(len(weapon_db)))
    print()
    print("Number of decorations: " + str(len(list(Decoration))))
    print("\n==============================\n")
    return


def search_command(search_parameters_filename):
    assert isinstance(search_parameters_filename, str)

    print("Carrying out a pre-defined search.")

    with open(search_parameters_filename, encoding=ENCODING, mode="r") as f:
        search_parameters_jsonstr = f.read()

    find_highest_efr_build(search_parameters_jsonstr)
    return


def lookup_command(weapon_name):

    armour_dict = {
        ArmourSlot.HEAD:  ("Teostra", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
        ArmourSlot.CHEST: ("Teostra", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
        ArmourSlot.ARMS:  ("Teostra", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
        ArmourSlot.WAIST: ("Teostra", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
        ArmourSlot.LEGS:  ("Teostra", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
    }

    charm_id = "CHALLENGER_CHARM"
    #charm_id = None

    #skills_dict = {
    #        #Skill.HANDICRAFT: 5,
    #        Skill.CRITICAL_EYE: 4,
    #        Skill.CRITICAL_BOOST: 0,
    #        Skill.ATTACK_BOOST: 3,
    #        Skill.WEAKNESS_EXPLOIT: 1,
    #        Skill.AGITATOR: 2,
    #        Skill.PEAK_PERFORMANCE: 3,
    #        Skill.NON_ELEMENTAL_BOOST: 1,
    #    }

    decorations_list = [
            Decoration.EXPERT,
            Decoration.TENDERIZER,
            Decoration.EARPLUG,
            Decoration.COMPOUND_FLAWLESS_VITALITY,
            Decoration.COMPOUND_TENDERIZER_VITALITY,
            Decoration.COMPOUND_TENDERIZER_VITALITY,
            Decoration.COMPOUND_TENDERIZER_VITALITY,
            Decoration.COMPOUND_TENDERIZER_VITALITY,
        ]

    skill_states_dict = {
            #Skill.WEAKNESS_EXPLOIT: 2,
            #Skill.AGITATOR: 1,
            #Skill.PEAK_PERFORMANCE: 1,
        }

    augments_list = [
            (IBWeaponAugmentType.ATTACK_INCREASE,   1),
            #(IBWeaponAugmentType.AFFINITY_INCREASE, 1),
        ]
    
    results = lookup_from_gear(weapon_name, armour_dict, charm_id, decorations_list, skill_states_dict, augments_list)
    sharpness_values = None
    efrs_strings = []

    ref = results
    while isinstance(ref, list):
        ref = ref[0]

    representative_skills_dict = ref.skills
    representative_usable_slots_dict = ref.usable_slots
    # TODO: Make an assertion that all builds in the tree are all similar.

    iterated_skills = [
            skill for (skill, level) in representative_skills_dict.items()
            if (level > 0) and (skill.value.states is not None) and (skill not in skill_states_dict)
        ]

    if isinstance(iterated_skills, list) and (len(iterated_skills) > 0):
        # We have an arbitrarily-deep list with nested lists of result tuples.

        # It should be in alphabetical order, so we sort first.
        iterated_skills.sort(key=lambda skill : skill.value.name)

        states_strings = []
        efrs = []
        sharpness_values = None
        def traverse_results_structure(states, subresults):
            nonlocal sharpness_values
            assert isinstance(states, list)

            next_index = len(states)
            if next_index >= len(iterated_skills):
                # Terminate recursion here.
                
                states_strings.append("; ".join(s.value.states[states[i]] for (i, s) in enumerate(iterated_skills)))
                efrs.append(subresults.efr)

                assert (sharpness_values is None) or (sharpness_values == subresults.sharpness_values)
                sharpness_values = subresults.sharpness_values
            else:
                # Do more recursion here!

                skill_to_iterate = iterated_skills[next_index]
                assert len(skill_to_iterate.value.states) > 1
                for state_value, _ in enumerate(skill_to_iterate.value.states):
                    traverse_results_structure(states + [state_value], subresults[state_value])
            return

        traverse_results_structure([], results)

        # Make state_strings look nicer
        states_strings = [s + ":" for s in states_strings]
        max_str_len = max(len(s) for s in states_strings)
        states_strings = [s.ljust(max_str_len, " ") for s in states_strings]

        efrs_strings.append("EFR values:")
        efrs_strings.extend(f"   {state_str} {efr}" for (state_str, efr) in zip(states_strings, efrs))

    else:
        # We have just a single result tuple.

        sharpness_values = results.sharpness_values
        efrs_strings.append(f"EFR: {results.efr}")

    minimum_slot_sizes_required = defaultdict(lambda : 0)
    for deco in decorations_list:
        minimum_slot_sizes_required[deco.value.slot_size] += 1

    print("Decoration slots:")
    print(f"   [Size 1] Slots Available = {representative_usable_slots_dict[1]}, " \
                            f"Decos of this size = {minimum_slot_sizes_required[1]}")
    print(f"   [Size 2] Slots Available = {representative_usable_slots_dict[2]}, " \
                            f"Decos of this size = {minimum_slot_sizes_required[2]}")
    print(f"   [Size 3] Slots Available = {representative_usable_slots_dict[3]}, " \
                            f"Decos of this size = {minimum_slot_sizes_required[3]}")
    print(f"   [Size 4] Slots Available = {representative_usable_slots_dict[4]}, " \
                            f"Decos of this size = {minimum_slot_sizes_required[4]}")
    print()

    print("Skills:")
    print("\n".join(f"   {skill.value.name} {level}" for (skill, level) in representative_skills_dict.items()))
    print()

    print("Sharpness values:")
    print(f"   Red:    {sharpness_values[0]} hits")
    print(f"   Orange: {sharpness_values[1]} hits")
    print(f"   Yellow: {sharpness_values[2]} hits")
    print(f"   Green:  {sharpness_values[3]} hits")
    print(f"   Blue:   {sharpness_values[4]} hits")
    print(f"   White:  {sharpness_values[5]} hits")
    print(f"   Purple: {sharpness_values[6]} hits")
    print()

    print("\n".join(efrs_strings))
    return


def run():
    if __debug__:
        print_debugging_statistics()
        run_tests()

    # Determine whether to run in search or lookup mode.
    if len(sys.argv) > 1:
        if sys.argv[1].lower() == "search":
            search_parameters_filename = sys.argv[2]
            search_command(search_parameters_filename)
        else:
            weapon_name = sys.argv[1]
            lookup_command(weapon_name)
    else:
        raise ValueError("Needs more arguments. (Just check the code. I can't be assed writing documentation at this time.)")

    return 0


if __name__ == '__main__':
    sys.exit(run())

