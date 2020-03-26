# -*- coding: ascii -*-

"""
Filename: search.py
Author:   contact@simshadows.com

This file contains various queries and search algorithms.
"""

import time
from copy import copy
import multiprocessing as mp
from queue import Empty

from collections import defaultdict, Counter

from .builds    import (Build,
                       lookup_from_skills)
from .serialize import (SearchParameters,
                       readjson_search_parameters)
from .utils     import (ExecutionProgress,
                       grouper,
                       interleaving_shuffle)

from .database_armour import ArmourSlot

from .query_armour      import (get_pruned_armour_combos,
                               calculate_armour_contribution)
from .query_charms      import (get_charms_subset,
                               calculate_skills_dict_from_charm)
from .query_decorations import calculate_decorations_skills_contribution
from .query_skills      import (calculate_possible_set_bonus_combos,
                               relax_set_bonus_combos,
                               calculate_set_bonus_skills)
from .query_weapons     import (calculate_final_weapon_values,
                               get_pruned_weapon_combos)


def _split_armour_combos_into_batches(armour_combos, batch_size, batch_shuffle_rounds):
    assert isinstance(armour_combos, list)
    assert isinstance(batch_size, int) and (batch_size > 0)
    assert isinstance(batch_shuffle_rounds, int) and (batch_shuffle_rounds > 0)

    def armour_combo_sort_key_fn(x):
        head  = x[ArmourSlot.HEAD]
        chest = x[ArmourSlot.CHEST]
        arms  = x[ArmourSlot.ARMS]
        waist = x[ArmourSlot.WAIST]
        legs  = x[ArmourSlot.LEGS]

        buf = head.armour_set.set_name + head.armour_set.discriminator.name + head.armour_set_variant.name \
                + chest.armour_set.set_name + chest.armour_set.discriminator.name + chest.armour_set_variant.name \
                + arms.armour_set.set_name  + arms.armour_set.discriminator.name  + arms.armour_set_variant.name  \
                + waist.armour_set.set_name + waist.armour_set.discriminator.name + waist.armour_set_variant.name \
                + legs.armour_set.set_name  + legs.armour_set.discriminator.name  + legs.armour_set_variant.name
        return buf
    sorted_armour_combos = sorted(armour_combos, key=armour_combo_sort_key_fn)

    armour_combos_batches = list(grouper(sorted_armour_combos, batch_size))
    assert sum(len(x) for x in armour_combos_batches) >= len(armour_combos)
    armour_combos_batches = list(interleaving_shuffle(armour_combos_batches, max_partitions=batch_shuffle_rounds))
    assert sum(len(x) for x in armour_combos_batches) >= len(armour_combos)

    return armour_combos_batches


# get_pruned_armour_combos caches results, so we just trigger it before entering the worker processes.
def _cache_pruned_armour_combos(search_parameters):
    assert isinstance(search_parameters, SearchParameters)

    skills_with_minimum_levels = {k: v for (k, v) in search_parameters.selected_skills.items() if (v > 0)}
    skill_subset = set(search_parameters.selected_skills) # Get all the keys

    required_set_bonus_skills = search_parameters.selected_set_bonus_skills
    # IMPORTANT: We're not checking yet if these skills are actually attainable via. set bonus.

    minimum_set_bonus_combos = calculate_possible_set_bonus_combos(required_set_bonus_skills)
    relaxed_minimum_set_bonus_combos = relax_set_bonus_combos(minimum_set_bonus_combos)

    x = get_pruned_armour_combos(search_parameters.selected_armour_tier, skill_subset=skill_subset, \
                                        required_set_bonus_skills=required_set_bonus_skills)
    assert isinstance(x, list)
    return x


def _generate_deco_dicts(slots_available_counter, all_possible_decos, existing_skills, skill_subset=None, required_skills={}):
    assert isinstance(slots_available_counter, Counter)
    assert isinstance(all_possible_decos, list)
    assert isinstance(existing_skills, defaultdict)
    assert isinstance(required_skills, dict)
    # assert all(x in slots_available_counter for x in [1, 2, 3, 4]) # This isn't enforced anymore.
    # assert all(x in all_possible_decos for x in [1, 2, 3, 4]) # This isn't enforced anymore.
    if not (len(slots_available_counter) <= 4):
        print(slots_available_counter)
    assert len(slots_available_counter) <= 4
    assert len(all_possible_decos) > 0

    # TODO: We should turn it into a list before even passing it into the function.
    initial_slots_available_list = list(sorted(slots_available_counter.elements()))
    assert initial_slots_available_list[0] <= initial_slots_available_list[-1] # Quick sanity check on order.

    # We split the deco list into decos with any of the required skills, and deco list without required skills.
    decos_with_required_skills = set()
    decos_without_required_skills = set()
    for deco in all_possible_decos:
        if any((skill in required_skills) for (skill, _) in deco.value.skills_dict.items()):
            decos_with_required_skills.add(deco)
        else:
            decos_without_required_skills.add(deco)
    assert len(decos_with_required_skills) + len(decos_without_required_skills) == len(all_possible_decos)

    intermediate = [(defaultdict(lambda : 0), initial_slots_available_list, copy(existing_skills))]

    def process_decos(deco_set, required_skills):
        nonlocal intermediate

        assert isinstance(deco_set, set)

        if len(deco_set) == 0:
            return

        for deco in deco_set:
            next_intermediate = []
            deco_size = deco.value.slot_size

            for (trial_deco_dict, trial_slots_available, trial_skill_dict) in intermediate:
                assert deco not in trial_deco_dict
                assert isinstance(trial_deco_dict, dict)
                assert isinstance(trial_skill_dict, dict)

                trial_deco_dict = copy(trial_deco_dict)
                trial_slots_available = copy(trial_slots_available)
                trial_skill_dict = copy(trial_skill_dict)

                # First we "add zero"

                next_intermediate.append((copy(trial_deco_dict), copy(trial_slots_available), copy(trial_skill_dict)))

                # Now, we add the deco incrementally.

                if __debug__:
                    debugging_num_added = 0
                
                while True:

                    if __debug__:
                        debugging_num_added += 1
                        debugging_slots_initsize = len(trial_slots_available)

                    # Trivial case for Step 3. (See below.) # Uncomment it later and measure performance impact.
                    #if len(trial_slots_available) == 0:
                    #    break # LOOP EXIT POINT

                    # Step 1: Increment the deco count
                    trial_deco_dict[deco] += 1
                    assert trial_deco_dict[deco] == debugging_num_added

                    # Step 2: Check if we will overflow a skill. If not, we add the decoration and increment the skill levels.
                    will_overflow = False
                    for (skill, levels_granted_by_deco) in deco.value.skills_dict.items():
                        if (skill_subset is not None) and (skill not in skill_subset):
                            # We're technically considering this to be an overflowing of a skill we limit to zero.
                            # This should help prune the combinations by ignoring skills we don't really care about.
                            # TODO: Consider removing this restriction, to allow "bonus skills" to be added to builds.
                            will_overflow = True
                            break
                        new_skill_level = trial_skill_dict[skill] + levels_granted_by_deco
                        if new_skill_level > skill.value.limit:
                            will_overflow = True
                            break
                        trial_skill_dict[skill] = new_skill_level # We update the skill dictionary here
                    if will_overflow:
                        break # LOOP EXIT POINT

                    # Step 3: Remove an available deco slot if possible. If not, we break.
                    # We have already checked for the trivial case.
                    slot_was_consumed = False
                    new_trial_slots_available = []
                    while len(trial_slots_available) > 0:
                        candidate_slot_size = trial_slots_available.pop(0)
                        if candidate_slot_size >= deco_size:
                            # We "consume" the candidate slot and append the rest of the list.
                            new_trial_slots_available += trial_slots_available
                            slot_was_consumed = True
                            break
                        else:
                            new_trial_slots_available.append(candidate_slot_size)
                    if not slot_was_consumed:
                        break # LOOP EXIT POINT
                    assert (debugging_slots_initsize == 0) or (debugging_slots_initsize == len(new_trial_slots_available) + 1)
                    trial_slots_available = new_trial_slots_available

                    # Step 4: Add back to the intermediate list :)
                    next_intermediate.append((copy(trial_deco_dict), copy(trial_slots_available), copy(trial_skill_dict)))

            intermediate = next_intermediate
        
        # If we're processing with required skills, we'll need to filter out results
        if required_skills is not None:
            next_intermediate = []
            for tup in intermediate:
                assert len(tup) == 3
                trial_deco_dict = tup[0]
                trial_skills = tup[2]

                keep_this = True
                for skill, required_level in required_skills.items():
                    if trial_skills[skill] < required_level:
                        keep_this = False
                        break
                if keep_this:
                    next_intermediate.append(tup)
            intermediate = next_intermediate
        return

    process_decos(decos_with_required_skills, required_skills)

    # TODO: Should I be exiting early? My algorithm seems to handle these rare cases fine.
    #if len(intermediate) == 0:
    #    return []

    process_decos(decos_without_required_skills, None)
    
    ret = [x[0] for x in intermediate if (len(x[1]) == 0)]
    if len(ret) == 0:
        return [x[0] for x in intermediate] # We return everything since we can't utilize all slots anyway.
    else:
        return ret # We return the subset where all slots are consumed.


def _extend_weapon_combos_tuples(weapon_combos, skills_for_ceiling_efr, skill_states_dict):
    assert isinstance(weapon_combos, list)
    assert isinstance(skills_for_ceiling_efr, dict)
    assert isinstance(skill_states_dict, dict)

    new_weapon_combos = []

    for (weapon, augments_tracker, upgrades_tracker) in weapon_combos:
        combination_values = calculate_final_weapon_values(weapon, augments_tracker, upgrades_tracker)

        results = lookup_from_skills(weapon, skills_for_ceiling_efr, skill_states_dict, augments_tracker, \
                                        upgrades_tracker)
        ceiling_efr = results.efr

        tup = (weapon, augments_tracker, upgrades_tracker, combination_values, ceiling_efr)

        new_weapon_combos.append(tup)

    return new_weapon_combos


def find_highest_efr_build(search_parameters_jsonstr):

    search_parameters = readjson_search_parameters(search_parameters_jsonstr)
    skill_states = search_parameters.skill_states
    num_workers = search_parameters.num_worker_threads

    start_time = time.time()

    # Cache armour combos and determine number of batches
    armour_combos = _cache_pruned_armour_combos(search_parameters)
    armour_combos_batches = _split_armour_combos_into_batches(armour_combos, search_parameters.batch_size, \
                                                                search_parameters.batch_shuffle_rounds)
    num_batches = len(armour_combos_batches)

    with mp.Pool(num_workers) as p:
        manager = mp.Manager()
        all_pipes = [mp.Pipe(duplex=False) for _ in range(num_workers)]
        # all_pipes is a list of 2-tuples. With duplex=False, each tuple is (read_only, write_only).

        queue_children_to_parent = manager.Queue()
        job_queue = manager.Queue() # This one is a parent-to-children job queue to instruct children which batches to work on
        pipes_parent_to_children = [x for (_, x) in all_pipes] # Parent keeps the write-only half.

        # We fill up the queue with all batch numbers. Children just grab these values.
        for batch in range(num_batches + num_workers): # If a worker finds we've exceeded the batches, it exits.
            job_queue.put(batch)
        assert not job_queue.full()

        pipes_for_children = [x for (x, _) in all_pipes] # Children get the read-only end.
        children_args = [(i, queue_children_to_parent, job_queue, pipes_for_children[i], search_parameters_jsonstr)
                         for i in range(num_workers)]
        async_result = p.map_async(_find_highest_efr_build_worker, children_args)

        def broadcast_new_best_efr(efr_value):
            for pipe in pipes_parent_to_children:
                pipe.send(["NEW_EFR", efr_value])
            return

        grandtotal_progress = ExecutionProgress("SEARCH", None)
        workers_complete = {i: False for i in range(num_workers)}

        current_best_efr = 0
        current_best_build = None
        current_best_affinity = None

        while True:
            try:
                msg = queue_children_to_parent.get(block=True, timeout=1)
                if msg[1] == "PROGRESS":
                    assert msg[2] == 1
                    grandtotal_progress.ensure_total_progress_count(msg[4])
                    grandtotal_progress.update_and_print_progress()
                elif msg[1] == "BUILD":
                    serial_data = msg[2]
                    intermediate_build = Build.deserialize(serial_data)
                    intermediate_result = intermediate_build.calculate_performance(skill_states)

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
        if serialized_build is None:
            continue
        build = Build.deserialize(serialized_build)
        results = build.calculate_performance(skill_states)
        if results.efr > best_efr:
            best_efr = results.efr
            best_build = build

    if best_build is None:
        print()
        print("No build was found within the constraints.")
        print()
    else:
        results = best_build.calculate_performance(skill_states)
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
    worker_number    = args[0]
    queue_to_parent  = args[1]
    job_queue        = args[2]
    pipe_from_parent = args[3]
    search_parameters_serialized = args[4]

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

    ########################################
    # STAGE 1: Determine Search Parameters #
    ########################################

    search_parameters = readjson_search_parameters(search_parameters_serialized)

    desired_weapon_class = search_parameters.selected_weapon_class

    minimum_health_regen_augment = search_parameters.min_health_regen_augment_level

    skills_with_minimum_levels = {k: v for (k, v) in search_parameters.selected_skills.items() if (v > 0)}
    skill_subset = set(search_parameters.selected_skills) # Get all the keys

    required_set_bonus_skills = set(search_parameters.selected_set_bonus_skills) # Just making sure it's a set
    # IMPORTANT: We're not checking yet if these skills are actually attainable via. set bonus.

    decorations = list(search_parameters.selected_decorations)

    skill_states = search_parameters.skill_states

    batch_size = search_parameters.batch_size
    batch_shuffle_rounds = search_parameters.batch_shuffle_rounds

    ############################
    # STAGE 2: Component Lists #
    ############################

    # minimum_set_bonus_combos is a set of set bonuses that can fulfill our specified set of required set bonus skills.
    minimum_set_bonus_combos = calculate_possible_set_bonus_combos(required_set_bonus_skills)
    relaxed_minimum_set_bonus_combos = relax_set_bonus_combos(minimum_set_bonus_combos)
    # NOT ACTUALLY USED YET!

    # For debugging candidate_set_bonuses
    #buf = []
    #for x in relaxed_minimum_set_bonus_combos:
    #    buf.append(",".join(k.name + "=" + str(v) for (k, v) in x.items()))
    #print("\n".join(buf))
    #print()

    weapon_combos = get_pruned_weapon_combos(desired_weapon_class, minimum_health_regen_augment)
    all_skills_max_except_free_elem = {skill: skill.value.limit for skill in skill_subset}
    weapon_combos = _extend_weapon_combos_tuples(weapon_combos, all_skills_max_except_free_elem, skill_states)
    weapon_combos.sort(key=lambda x : x[4], reverse=True)
    assert weapon_combos[0][4] >= weapon_combos[-1][4]

    armour_combos = get_pruned_armour_combos(search_parameters.selected_armour_tier, skill_subset, required_set_bonus_skills)
    armour_combos_batches = _split_armour_combos_into_batches(armour_combos, batch_size, batch_shuffle_rounds)

    charms = get_charms_subset(skill_subset)
    charms = [None] if (len(charms) == 0) else list(charms)

    ####################
    # STAGE 3: Search! #
    ####################

    best_efr = 0
    associated_affinity = None
    associated_build = None

    grandtotal_progress_segments = len(armour_combos)
    debugging_num_initial_weapon_configs = len(weapon_combos)

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
        nonlocal weapon_combos
        new_weapon_configuration_list = []
        for weapon_configuration in weapon_combos:
            if weapon_configuration[4] > best_efr: # Check if the ceiling EFR is over the best EFR
                new_weapon_configuration_list.append(weapon_configuration)
        weapon_combos = new_weapon_configuration_list
        print(worker_string + f"New number of weapon configurations: {len(weapon_combos)} " + \
                                    f"out of {debugging_num_initial_weapon_configs}")
        return

    while True:
        # We get a job from the queue.
        new_batch_index = job_queue.get(block=True)
        if new_batch_index >= len(armour_combos_batches):
            break
        print(worker_string + f"New batch number: {new_batch_index} of 0-{len(armour_combos_batches)-1}")

        armour_combos_sublist = armour_combos_batches[new_batch_index]

        total_progress_segments = len(armour_combos_sublist)
        curr_progress_segment = 0

        for curr_armour in armour_combos_sublist:

            if curr_armour is None: # This is because the list splitting function fills with Nones so the lists are equal size.
                continue

            armour_contribution = calculate_armour_contribution(curr_armour)
            armour_set_bonus_skills = calculate_set_bonus_skills(armour_contribution.set_bonuses, None)

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

                for (weapon, w_augments_tracker, w_upgrades_tracker, w_combo_values, _) in weapon_combos:

                    deco_slots = Counter(list(w_combo_values.slots) + list(armour_contribution.decoration_slots))
                    deco_dicts = _generate_deco_dicts(deco_slots, decorations, including_charm_skills, \
                                                        skill_subset=skill_subset, required_skills=skills_with_minimum_levels)
                    # deco_dicts may be an empty list if no decoration combination can fulfill skill requirements.
                    # If so, the inner loop just doesn't execute.

                    for deco_dict in deco_dicts:

                        including_deco_skills = copy(including_charm_skills)
                        for (skill, level) in calculate_decorations_skills_contribution(deco_dict).items():
                            including_deco_skills[skill] += level
                            # Now, we also have decoration skills included.
                        
                        results = lookup_from_skills(weapon, including_deco_skills, skill_states, w_augments_tracker, \
                                                        w_upgrades_tracker)
                        assert results is not list

                        if results.efr > best_efr:
                            best_efr = results.efr
                            associated_affinity = results.affinity
                            associated_build = Build(weapon, curr_armour, charm, w_augments_tracker, w_upgrades_tracker, \
                                                            deco_dict)
                            send_found_build(associated_build)
                            do_regenerate_weapon_list = True

                best_efr_is_updated = check_parent_for_new_best_efr_and_update()

                if best_efr_is_updated or do_regenerate_weapon_list:
                    regenerate_weapon_list()

            curr_progress_segment += 1
            send_progress_ping()

    send_complete_ping()

    if associated_build is not None:
        return associated_build.serialize()
    else:
        return None

