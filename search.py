# -*- coding: ascii -*-

"""
Filename: search.py
Author:   contact@simshadows.com

This file contains various queries and search algorithms.
"""

import sys, time
from math import ceil
from copy import copy
#from enum import Enum, auto
import multiprocessing as mp
from queue import Empty

from collections import namedtuple, defaultdict, Counter

from builds import (Build,
                   lookup_from_skills)
from utils  import (update_and_print_progress,
                   grouper)

from database_skills      import (Skill,
                                 skills_with_implemented_features,
                                 calculate_set_bonus_skills)
from database_weapons     import (WeaponClass,
                                 weapon_db,
                                 WeaponAugmentTracker,
                                 WeaponUpgradeTracker,
                                 print_weapon_config)
from database_armour      import (ArmourSlot,
                                 armour_db,
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


NUM_WORKERS = 32
NUM_BATCHES = 256

FULL_SKILL_STATES = {
    Skill.AGITATOR: 1,
    Skill.PEAK_PERFORMANCE: 1,
    Skill.WEAKNESS_EXPLOIT: 2,
}


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


def _generate_weapon_combinations(weapon_list, skills_for_ceiling_efr, skill_states_dict):
    assert isinstance(weapon_list, list)
    assert isinstance(skills_for_ceiling_efr, dict)
    assert isinstance(skill_states_dict, dict)
    for weapon in weapon_list:
        for weapon_augments_config in WeaponAugmentTracker.get_instance(weapon).get_maximized_configs():
            weapon_augments_tracker = WeaponAugmentTracker.get_instance(weapon)
            weapon_augments_tracker.update_with_config(weapon_augments_config)
            for weapon_upgrade_config in WeaponUpgradeTracker.get_instance(weapon).get_maximized_configs():
                weapon_upgrades_tracker = WeaponUpgradeTracker.get_instance(weapon)
                weapon_upgrades_tracker.update_with_config(weapon_upgrade_config)
                results = lookup_from_skills(weapon, skills_for_ceiling_efr, skill_states_dict, \
                                                    weapon_augments_tracker, weapon_upgrades_tracker)
                ceiling_efr = results.efr
                yield (weapon, weapon_augments_tracker, weapon_upgrades_tracker, ceiling_efr)


def find_highest_efr_build():

    start_time = time.time()

    with mp.Pool(NUM_WORKERS) as p:
        manager = mp.Manager()
        all_pipes = [mp.Pipe(duplex=False) for _ in range(NUM_WORKERS)]
        # all_pipes is a list of 2-tuples. With duplex=False, each tuple is (read_only, write_only).

        queue_children_to_parent = manager.Queue()
        job_queue = manager.Queue() # This one is a parent-to-children job queue to instruct children which batches to work on
        pipes_parent_to_children = [x for (_, x) in all_pipes] # Parent keeps the write-only half.

        # We fill up the queue with all batch numbers. Children just grab these values.
        for batch in range(NUM_BATCHES + NUM_WORKERS): # If a worker finds we've exceeded the batches, it exits.
            job_queue.put(batch)
        assert not job_queue.full()

        pipes_for_children = [x for (x, _) in all_pipes] # Children get the read-only end.
        children_args = [(i, queue_children_to_parent, job_queue, pipes_for_children[i]) for i in range(NUM_WORKERS)]
        async_result = p.map_async(_find_highest_efr_build_worker, children_args)

        def broadcast_new_best_efr(efr_value):
            for pipe in pipes_parent_to_children:
                pipe.send(["NEW_EFR", efr_value])
            return

        grandtotal_progress_segments = None
        curr_progress_segment = 0
        workers_complete = {i: False for i in range(NUM_WORKERS)}

        current_best_efr = 0
        current_best_build = None
        current_best_affinity = None

        while True:
            try:
                msg = queue_children_to_parent.get(block=True, timeout=1)
                if msg[1] == "PROGRESS":
                    if grandtotal_progress_segments is None:
                        grandtotal_progress_segments = msg[4]
                    assert msg[4] == grandtotal_progress_segments
                    assert msg[2] == 1
                    curr_progress_segment = update_and_print_progress("SEARCH", curr_progress_segment, \
                                                                        grandtotal_progress_segments, start_time)
                elif msg[1] == "BUILD":
                    serial_data = msg[2]
                    intermediate_build = Build.deserialize(serial_data)
                    intermediate_result = intermediate_build.calculate_performance(FULL_SKILL_STATES)

                    intermediate_efr = intermediate_result.efr
                    intermediate_affinity = intermediate_result.affinity
                    if current_best_efr < intermediate_efr:
                        current_best_efr = intermediate_efr
                        current_best_affinity = intermediate_affinity

                        current_best_build = intermediate_build

                        broadcast_new_best_efr(current_best_efr)

                        print()
                        print(f"{current_best_efr} EFR @ {current_best_affinity} affinity")
                        print()
                        current_best_build.print()
                        print()
                elif msg[1] == "WORKER_COMPLETE":
                    worker_number = msg[0]
                    workers_complete[worker_number] = True
                    if all(status for (_, status) in workers_complete.items()):
                        print()
                        print(f"Worker #{worker_number} finished. All workers have now concluded.")
                        print()
                    else:
                        buf = ", ".join(str(i) for (i, status) in workers_complete.items() if (not status))
                        print()
                        print(f"Worker #{worker_number} finished. Still waiting on: {buf}")
                        print()
                else:
                    raise ValueError("Unknown message: " + str(msg))
            except Empty:
                if async_result.ready():
                    break
        
        best_builds_serialized = async_result.get()

    best_efr = 0
    best_build = None
    for serialized_build in best_builds_serialized:
        build = Build.deserialize(serialized_build)
        results = build.calculate_performance(FULL_SKILL_STATES)
        if results.efr > best_efr:
            best_efr = results.efr
            best_build = build

    end_real_time = time.time()

    results = best_build.calculate_performance(FULL_SKILL_STATES)

    print()
    print("Final build:")
    print()
    print(f"{results.efr} EFR @ {results.affinity} affinity")
    print()
    best_build.print()
    print()

    end_time = time.time()

    search_time_min = int((end_time - start_time) // 60)
    search_time_sec = int((end_time - start_time) % 60)

    print()
    print(f"Total execution time (in real time): {search_time_min:02}:{search_time_sec:02}")
    print(f"({end_time - start_time} seconds)")
    print()

    return


def _find_highest_efr_build_worker(args):
    worker_number = args[0]
    queue_to_parent = args[1]
    job_queue = args[2]
    pipe_from_parent = args[3]

    worker_string = f"[WORKER #{worker_number}] "

    def send_progress_ping():
        msg = [worker_number, "PROGRESS", 1, total_progress_segments, grandtotal_progress_segments, curr_progress_segment]
        queue_to_parent.put(msg)
        return

    def send_complete_ping():
        queue_to_parent.put([worker_number, "WORKER_COMPLETE"])
        return

    def send_found_build(build_obj):
        assert isinstance(build_obj, Build)
        queue_to_parent.put([worker_number, "BUILD", build_obj.serialize()])
        return

    print_progress = (worker_number == 0)

    ##############################
    # STAGE 1: Basic Definitions #
    ##############################

    desired_weapon_class = WeaponClass.GREATSWORD

    efr_skills = skills_with_implemented_features 

    required_set_bonus_skills = { # IMPORTANT: We're not checking yet if these skills are actually attainable via. set bonus.
        Skill.MASTERS_TOUCH,
    }

    #decoration_skills = {
    #    Skill.CRITICAL_EYE,
    #    Skill.WEAKNESS_EXPLOIT,
    #}

    decorations_test_subset = [
        Decoration.ELEMENTLESS,
        Decoration.TENDERIZER,
        Decoration.EXPERT,
        Decoration.CRITICAL,
        Decoration.CHALLENGER_X2,

        ##Decoration.CHALLENGER,
        #Decoration.HANDICRAFT,
        ##Decoration.HANDICRAFT_X2,
        ##Decoration.ATTACK,
        ##Decoration.ATTACK_X2,
        ##Decoration.FLAWLESS,
    ]

    ############################
    # STAGE 2: Component Lists #
    ############################

    weapons = [weapon for (_, weapon) in weapon_db.items() if weapon.type is desired_weapon_class]

    pruned_armour_db = prune_easyiterate_armour_db(skillsonly_pruned_armour, skill_subset=efr_skills, \
                                                                    print_progress=print_progress)
    pruned_armour_combos = generate_and_prune_armour_combinations(pruned_armour_db, skill_subset=efr_skills, \
                                                                    required_set_bonus_skills=required_set_bonus_skills,
                                                                    print_progress=print_progress)
    def sort_key_fn(x):
        head = x[ArmourSlot.HEAD]
        chest = x[ArmourSlot.CHEST]
        arms = x[ArmourSlot.ARMS]
        waist = x[ArmourSlot.WAIST]
        legs = x[ArmourSlot.LEGS]

        buf = head.armour_set.set_name + head.armour_set.discriminator.name + head.armour_set_variant.name \
                + chest.armour_set.set_name + chest.armour_set.discriminator.name + chest.armour_set_variant.name \
                + arms.armour_set.set_name + arms.armour_set.discriminator.name + arms.armour_set_variant.name \
                + waist.armour_set.set_name + waist.armour_set.discriminator.name + waist.armour_set_variant.name \
                + legs.armour_set.set_name + legs.armour_set.discriminator.name + legs.armour_set_variant.name
        return buf
    pruned_armour_combos.sort(key=sort_key_fn)


    charms = set()
    for skill in efr_skills:
        if skill in charms_indexed_by_skill:
            for charm in charms_indexed_by_skill[skill]:
                charms.add(charm)
    if len(charms) == 0:
        charms = [None]
    else:
        charms = list(charms)

    #decorations = list(get_pruned_deco_set(decoration_skills, bonus_skills=[Skill.FOCUS]))
    decorations = decorations_test_subset

    all_skills_max_except_free_elem = {skill: skill.value.limit for skill in efr_skills}
    all_weapon_configurations = list(_generate_weapon_combinations(weapons, all_skills_max_except_free_elem, FULL_SKILL_STATES))
    all_weapon_configurations.sort(key=lambda x : x[3], reverse=True)
    assert all_weapon_configurations[0][3] >= all_weapon_configurations[-1][3]

    debugging_num_initial_weapon_configs = len(all_weapon_configurations)

    print("Lowest ceiling EFR: " + str(all_weapon_configurations[-1][3]))

    sublist_ideal_len = int(ceil(len(pruned_armour_combos) / NUM_BATCHES))
    all_armour_combos_sublists = list(grouper(pruned_armour_combos, sublist_ideal_len))
    assert sum(len(x) for x in all_armour_combos_sublists) >= len(pruned_armour_combos)

    ####################
    # STAGE 3: Search! #
    ####################

    best_efr = 0
    associated_affinity = None
    associated_build = None

    grandtotal_progress_segments = len(pruned_armour_combos)

    def check_parent_for_new_best_efr_and_update():
        nonlocal best_efr
        is_updated = False
        while pipe_from_parent.poll(0):
            msg = pipe_from_parent.recv()
            assert msg[0] == "NEW_EFR"
            intermediate_efr = msg[1]
            if intermediate_efr > best_efr:
                best_efr = intermediate_efr
                is_updated = True
        return is_updated

    def regenerate_weapon_list():
        nonlocal all_weapon_configurations
        new_weapon_configuration_list = []
        for weapon_configuration in all_weapon_configurations:
            if weapon_configuration[3] > best_efr: # Check if the ceiling EFR is over the best EFR
                new_weapon_configuration_list.append(weapon_configuration)
        all_weapon_configurations = new_weapon_configuration_list
        print(worker_string + f"New number of weapon configurations: {len(all_weapon_configurations)} " + \
                                    f"out of {debugging_num_initial_weapon_configs}")
        return

    while True:
        # We get a job from the queue.
        new_batch_index = job_queue.get(block=True)
        if new_batch_index >= len(all_armour_combos_sublists):
            break
        print(worker_string + f"New batch number: {new_batch_index} of 0-{len(all_armour_combos_sublists)-1}")

        armour_combos_sublist = all_armour_combos_sublists[new_batch_index]

        total_progress_segments = len(armour_combos_sublist)
        curr_progress_segment = 0

        for curr_armour in armour_combos_sublist:

            if curr_armour is None: # This is because the list splitting function fills with Nones so the lists are equal size.
                continue

            armour_contribution = calculate_armour_contribution(curr_armour)
            armour_set_bonus_skills = calculate_set_bonus_skills(armour_contribution.set_bonuses)

            all_armour_skills = defaultdict(lambda : 0)
            all_armour_skills.update(armour_contribution.skills)
            all_armour_skills.update(armour_set_bonus_skills)
            assert len(set(armour_contribution.skills) & set(armour_set_bonus_skills)) == 0 # No intersection.
            # Now, we have all armour skills and set bonus skills

            for charm in charms:

                including_charm_skills = copy(all_armour_skills)
                for skill in calculate_skills_dict_from_charm(charm, charm.max_level):
                    including_charm_skills[skill] += charm.max_level
                # Now, we also have charm skills included.

                do_regenerate_weapon_list = False

                for (weapon, weapon_augments_tracker, weapon_upgrades_tracker, weapon_ceil_efr) in all_weapon_configurations:

                    deco_slots = Counter(list(weapon.slots) + list(armour_contribution.decoration_slots))
                    deco_dicts = _generate_deco_dicts(deco_slots, decorations, including_charm_skills, skill_subset=efr_skills)
                    assert len(deco_dicts) > 0
                    # Every possible decoration that can go in.

                    for deco_dict in deco_dicts:

                        including_deco_skills = copy(including_charm_skills)
                        for (skill, level) in calculate_decorations_skills_contribution(deco_dict).items():
                            including_deco_skills[skill] += level
                            # Now, we also have decoration skills included.
                        
                        results = lookup_from_skills(weapon, including_deco_skills, FULL_SKILL_STATES, \
                                                        weapon_augments_tracker, weapon_upgrades_tracker)
                        assert results is not list

                        if results.efr > best_efr:
                            best_efr = results.efr
                            associated_affinity = results.affinity
                            associated_build = Build(weapon, curr_armour, charm, weapon_augments_tracker, \
                                                        weapon_upgrades_tracker, deco_dict)
                            send_found_build(associated_build)
                            do_regenerate_weapon_list = True

                best_efr_is_updated = check_parent_for_new_best_efr_and_update()

                if best_efr_is_updated or do_regenerate_weapon_list:
                    regenerate_weapon_list()

            curr_progress_segment += 1
            send_progress_ping()

    send_complete_ping()

    return associated_build.serialize()

