# -*- coding: ascii -*-

"""
Filename: query.py
Author:   contact@simshadows.com

This file contains various queries and search algorithms.
"""

import sys, time
from math import ceil
from copy import copy
import multiprocessing as mp

from collections import namedtuple, defaultdict, Counter

from builds import (Build,
                   lookup_from_skills)
from utils  import update_and_print_progress

from database_skills      import (Skill,
                                 skills_with_implemented_features,
                                 calculate_set_bonus_skills)
from database_weapons     import (WeaponClass,
                                 weapon_db,
                                 WeaponAugmentTracker,
                                 WeaponUpgradeTracker)
from database_armour      import (armour_db,
                                 skillsonly_pruned_armour,
                                 prune_easyiterate_armour_db,
                                 generate_and_prune_armour_combinations,
                                 calculate_armour_contribution)
from database_charms      import (charms_db,
                                 charms_indexed_by_skill,
                                 calculate_skills_dict_from_charm)
from database_decorations import (Decoration,
                                 get_pruned_deco_set,
                                 calculate_decorations_skills_contribution)



def _generate_deco_dicts(slots_available_counter, all_possible_decos, existing_skills, skill_subset=None):
    assert isinstance(slots_available_counter, dict)
    assert isinstance(all_possible_decos, list)
    assert isinstance(existing_skills, dict)
    # assert all(x in slots_available_counter for x in [1, 2, 3, 4]) # This isn't enforced anymore.
    # assert all(x in all_possible_decos for x in [1, 2, 3, 4]) # This isn't enforced anymore.
    assert len(slots_available_counter) <= 4
    assert len(all_possible_decos) > 0

    # TODO: We should turn it into a list before even passing it into the function.
    initial_slots_available_list = list(sorted(slots_available_counter.elements()))
    assert initial_slots_available_list[0] <= initial_slots_available_list[-1] # Quick sanity check on order.

    intermediate = [({}, initial_slots_available_list)]

    for deco in all_possible_decos:
        #print(deco.value.name)
        next_intermediate = []
        deco_size = deco.value.slot_size
        deco_limit = 0
        for (skill, levels_granted_by_deco) in deco.value.skills_dict.items():
            if (skill_subset is not None) and (skill not in skill_subset):
                continue
            levels_to_go = skill.value.limit - existing_skills.get(skill, 0)
            # TODO: skip calculations if levels_to_go <= 0?
            # TODO: Consider using floor instead of ceiling. This is because we can assume
            # lower-size jewels will be tested instead of size-4 jewels (which are the only
            # jewels that have multiple levels).
            deco_limit_for_this_skill = ceil(levels_to_go / levels_granted_by_deco)
            if deco_limit_for_this_skill > deco_limit:
                deco_limit = deco_limit_for_this_skill

        if deco_limit == 0:
            continue

        # TODO: This algorithm is probably nowhere near as efficient as it could be.
        #       Try to rewrite it with a better algorithm :)
        for (trial_deco_dict, trial_slots_available) in intermediate:
            assert deco not in trial_deco_dict
            assert isinstance(trial_deco_dict, dict)

            trial_deco_dict = copy(trial_deco_dict)
            trial_slots_available = copy(trial_slots_available) # TODO: Consider not copying. Don't need to.

            # First we "add zero"

            next_intermediate.append((copy(trial_deco_dict), copy(trial_slots_available)))

            # Now, we add the deco incrementally.

            for num_to_add in range(deco_limit + 1):

                trial_deco_dict2 = copy(trial_deco_dict)
                trial_slots_available2 = copy(trial_slots_available)

                assert isinstance(trial_deco_dict, dict)

                trial_deco_dict2[deco] = num_to_add

                new_trial_slots_available = []
                while (num_to_add > 0) and (len(trial_slots_available2) > 0):
                    candidate_slot_size = trial_slots_available2.pop(0)
                    if candidate_slot_size >= deco_size:
                        num_to_add -= 1
                    else:
                        new_trial_slots_available.append(candidate_slot_size)

                if num_to_add == 0:
                    new_trial_slots_available += trial_slots_available2
                    assert len(new_trial_slots_available) == len(trial_slots_available) - trial_deco_dict2[deco]
                    next_intermediate.append((trial_deco_dict2, new_trial_slots_available))

        assert len(next_intermediate) > 0
        intermediate = next_intermediate

        #print("          deco limit = " + str(deco_limit))
        #print("                    deco combos: " + str(len(intermediate)))

        #if len(intermediate) < 300:
        #    print("\n".join(" ".join(y.name + " " + str(z) for (y,z) in x[0].items()) for x in intermediate))

    return [x[0] for x in intermediate]


def find_highest_efr_build():

    total_start_real_time = time.time()

    ##############################
    # STAGE 1: Basic Definitions #
    ##############################

    desired_weapon = WeaponClass.GREATSWORD

    efr_skills = skills_with_implemented_features 

    full_skill_states = {
        Skill.AGITATOR: 1,
        Skill.PEAK_PERFORMANCE: 1,
        Skill.WEAKNESS_EXPLOIT: 2,
    }

    required_set_bonus_skills = { # IMPORTANT: We're not checking yet if these skills are actually attainable via. set bonus.
        Skill.MASTERS_TOUCH,
    }

    decoration_skills = {
        Skill.CRITICAL_EYE,
        Skill.WEAKNESS_EXPLOIT,
    }

    decorations_test_subset = [
        Decoration.TENDERIZER,
        Decoration.ELEMENTLESS,
        Decoration.EXPERT,
    ]

    ############################
    # STAGE 2: Component Lists #
    ############################

    weapon_ids = [weapon_id for (weapon_id, weapon_info) in weapon_db.items() if weapon_info.type is desired_weapon]

    pruned_armour_db = prune_easyiterate_armour_db(skillsonly_pruned_armour, skill_subset=efr_skills)
    pruned_armour_combos = generate_and_prune_armour_combinations(pruned_armour_db, skill_subset=efr_skills, \
                                                                    required_set_bonus_skills=required_set_bonus_skills)


    charm_ids = set()
    for skill in efr_skills:
        if skill in charms_indexed_by_skill:
            for charm_id in charms_indexed_by_skill[skill]:
                charm_ids.add(charm_id)
    if len(charm_ids) == 0:
        charm_ids = [None]
    else:
        charm_ids = list(charm_ids)

    #decorations = list(get_pruned_deco_set(decoration_skills, bonus_skills=[Skill.FOCUS]))
    decorations = decorations_test_subset

    # Not currently used.
    #decos_dict = {
    #        1: [deco for deco in decorations if deco.value.slot_size == 1],
    #        2: [deco for deco in decorations if deco.value.slot_size == 2],
    #        3: [deco for deco in decorations if deco.value.slot_size == 3],
    #        4: [deco for deco in decorations if deco.value.slot_size == 4],
    #    }
    #assert len(decos_dict[1]) + len(decos_dict[2]) + len(decos_dict[3]) + len(decos_dict[4]) == len(decorations)

    ####################
    # STAGE 3: Search! #
    ####################

    best_efr = 0
    associated_affinity = None
    associated_build = None

    start_real_time = time.time()

    total_progress_segments = len(pruned_armour_combos)
    progress_segment_size = 1 / total_progress_segments
    curr_progress_segment = 0

    def progress():
        nonlocal curr_progress_segment
        nonlocal total_progress_segments
        nonlocal start_real_time
        curr_progress_segment = update_and_print_progress("SEARCH", curr_progress_segment, total_progress_segments, start_real_time)

    for curr_armour in pruned_armour_combos:

        armour_contribution = calculate_armour_contribution(curr_armour)
        armour_set_bonus_skills = calculate_set_bonus_skills(armour_contribution.set_bonuses)

        all_armour_skills = defaultdict(lambda : 0)
        all_armour_skills.update(armour_contribution.skills)
        all_armour_skills.update(armour_set_bonus_skills)
        assert len(set(armour_contribution.skills) & set(armour_set_bonus_skills)) == 0 # No intersection.
        # Now, we have all armour skills and set bonus skills

        for charm_id in charm_ids:
            charm = charms_db[charm_id]

            including_charm_skills = copy(all_armour_skills)
            for skill in calculate_skills_dict_from_charm(charm, charm.max_level):
                including_charm_skills[skill] += charm.max_level
            # Now, we also have charm skills included.

            for weapon_id in weapon_ids:
                weapon = weapon_db[weapon_id]

                for weapon_augments_config in WeaponAugmentTracker.get_instance(weapon).get_maximized_configs():

                    deco_slots = Counter(list(weapon.slots) + list(armour_contribution.decoration_slots))
                    deco_dicts = _generate_deco_dicts(deco_slots, decorations, including_charm_skills, skill_subset=efr_skills)
                    assert len(deco_dicts) > 0
                    # Every possible decoration that can go in.

                    for weapon_upgrade_config in WeaponUpgradeTracker.get_instance(weapon).get_maximized_configs():

                        for deco_dict in deco_dicts:

                            including_deco_skills = copy(including_charm_skills)
                            for (skill, level) in calculate_decorations_skills_contribution(deco_dict).items():
                                including_deco_skills[skill] += level
                                # Now, we also have decoration skills included.
                            
                            results = lookup_from_skills(weapon, including_deco_skills, full_skill_states, \
                                                            weapon_augments_config, weapon_upgrade_config)
                            assert results is not list

                            if results.efr > best_efr:
                                best_efr = results.efr
                                associated_affinity = results.affinity
                                associated_build = Build(curr_armour, charm_id, weapon_id, \
                                                            weapon_augments_config, weapon_upgrade_config, \
                                                            deco_dict)
                                print()
                                print(f"{best_efr} EFR @ {associated_affinity} affinity")
                                print()
                                associated_build.print()
                                print()
        progress()

    end_real_time = time.time()

    print()
    print("Final build:")
    print()
    print(f"{best_efr} EFR @ {associated_affinity} affinity")
    print()
    associated_build.print()
    print()

    search_real_time_minutes = int((end_real_time - start_real_time) // 60)
    search_real_time_seconds = int((end_real_time - start_real_time) % 60)

    print()
    print(f"Search execution time (in real time): {search_real_time_minutes:02}:{search_real_time_seconds:02}")
    print(f"({end_real_time - start_real_time} seconds)")
    print()

    total_real_time_minutes = int((end_real_time - total_start_real_time) // 60)
    total_real_time_seconds = int((end_real_time - total_start_real_time) % 60)

    print()
    print(f"Total execution time (in real time): {total_real_time_minutes:02}:{total_real_time_seconds:02}")
    print(f"({end_real_time - total_start_real_time} seconds)")
    print()

    return

