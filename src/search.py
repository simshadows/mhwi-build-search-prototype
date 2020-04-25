# -*- coding: ascii -*-

"""
Filename: search.py
Author:   contact@simshadows.com

A search algorithm that optimizes EFR!
"""

import time
import logging
from copy import copy
from math import ceil
from itertools import product
from collections import defaultdict, Counter

from .builds       import (Build,
                          lookup_from_skills)
from .enums        import Tier
from .loggingutils import (ExecutionProgress,
                          log_appstats,
                          log_appstats_reduction,
                          log_appstats_generic)
from .utils        import (counter_is_subset,
                          get_humanreadable_from_enum_counter,
                          get_humanreadable_from_enum_list,
                          get_humanreadable_from_list_of_enum_counter,
                          list_obeys_sort_order)
from .serialize    import (SearchParameters,
                          readjson_search_parameters)

from .database_armour import (ArmourSlot,
                             ArmourPieceInfo,
                             easyiterate_armour)
from .database_skills import Skill, SetBonus

from .query_armour      import prune_easyiterate_armour_db
from .query_charms      import (get_charms_subset,
                               calculate_skills_dict_from_charm)
from .query_decorations import (get_pruned_deco_set,
                               calculate_decorations_skills_contribution,
                               get_skill_from_simple_deco)
from .query_skills      import (calculate_possible_set_bonus_combos,
                               relax_set_bonus_combos,
                               calculate_set_bonus_skills,
                               #clipped_skills_defaultdict,
                               clipped_skills_defaultdict_includesecret,
                               convert_skills_dict_to_tuple,
                               convert_set_bonuses_dict_to_tuple,
                               get_highest_skill_limit)
from .query_weapons     import (calculate_final_weapon_values,
                               get_pruned_weapon_combos)


logger = logging.getLogger(__name__)


def run_search(search_parameters_jsonstr):
    search_parameters = readjson_search_parameters(search_parameters_jsonstr)

    # STATISTICS STUFF
    start_time = time.time()

    build = _find_highest_efr_build(search_parameters)

    logger.info("")
    logger.info("FINAL BUILD")
    logger.info("")
    logger.info(build.get_humanreadable(search_parameters.skill_states))
    logger.info("")

    # STATISTICS STUFF
    end_time = time.time()
    search_time_min = int((end_time - start_time) // 60)
    search_time_sec = int((end_time - start_time) % 60)
    log_appstats_generic("")
    log_appstats_generic(f"Total execution time (in real time): {search_time_min:02}:{search_time_sec:02}")
    log_appstats_generic(f"({end_time - start_time} seconds)")
    log_appstats_generic("")

    return


###############################################################################


def _get_grouped_and_pruned_weapon_combos(weapon_class, health_regen_minimum, skill_subset, set_bonuses_subset, skill_states):

    # TODO: This doesn't actually exclude free element yet...
    all_skills_max_except_free_elem = {skill: skill.value.limit for skill in skill_subset}

    combos = get_pruned_weapon_combos(weapon_class, health_regen_minimum)

    weapon_groups = defaultdict(lambda : [])
    
    for (weapon, augments_tracker, upgrades_tracker) in combos:
        combination_values = calculate_final_weapon_values(weapon, augments_tracker, upgrades_tracker)

        results = lookup_from_skills(weapon, all_skills_max_except_free_elem, skill_states, augments_tracker, upgrades_tracker)
        ceiling_efr = results.efr


        # Sort deco slots from biggest to smallest.
        sorted_deco_slots = tuple(sorted(combination_values.slots, reverse=True))
        assert len(sorted_deco_slots) <= 3
        assert sorted_deco_slots[0] >= sorted_deco_slots[-1]
        assert all((x > 0) and (x <= 4) for x in sorted_deco_slots)

        assert None not in set_bonuses_subset
        set_bonus = combination_values.set_bonus if (combination_values.set_bonus in set_bonuses_subset) else None
        assert (set_bonus is None) or isinstance(set_bonus, SetBonus)

        hashable = (set_bonus, sorted_deco_slots)

        tup = (weapon, augments_tracker, upgrades_tracker, combination_values, ceiling_efr)
        weapon_groups[hashable].append(tup)

    ret = []
    
    for (group_identification, combo_list) in weapon_groups.items():

        ## We sort because we want the weapons with the highest potential at the front, for pruning purposes!
        #combo_list.sort(key=lambda x : x[4], reverse=True)
        #assert combo_list[0][4] >= combo_list[-1][4]

        ret.append((group_identification, combo_list))

    ## Sorting again for better pruning!
    #ret.sort(key=lambda x : max(y[4] for y in x[1]), reverse=True)

    return ret


def _reprune_weapon_combos(weapon_combo_groups, *, minimum_efr_noninclusive):
    assert isinstance(weapon_combo_groups, list)
    assert isinstance(minimum_efr_noninclusive, float)

    new_list = []

    for (group_identification, combo_list) in weapon_combo_groups:
        combo_list = [x for x in combo_list if (x[4] > minimum_efr_noninclusive)]

        if len(combo_list) == 0:
            continue

        new_list.append((group_identification, combo_list))

    return new_list


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


def _armour_and_charm_combo_iter(armour_collection, charms_list):
    assert isinstance(armour_collection, dict)
    assert isinstance(charms_list, list)

    armour_and_charms_iter = product(
            armour_collection[ArmourSlot.HEAD],
            armour_collection[ArmourSlot.CHEST],
            armour_collection[ArmourSlot.ARMS],
            armour_collection[ArmourSlot.WAIST],
            armour_collection[ArmourSlot.LEGS],
            charms_list
        )

    for (head, chest, arms, waist, legs, charm) in armour_and_charms_iter:

        # First, we calculate all skills and slots.

        regular_skills = defaultdict(lambda : 0)
        total_set_bonuses = defaultdict(lambda : 0)
        total_slots = Counter()

        # We start by processing the armour pieces.
        for armour_piece in [head, chest, arms, waist, legs]:
            assert isinstance(armour_piece, ArmourPieceInfo)

            set_bonus = armour_piece.armour_set.set_bonus
            assert isinstance(set_bonus, SetBonus) or (set_bonus is None)

            for (skill, level) in armour_piece.skills.items():
                regular_skills[skill] += level

            if set_bonus is not None:
                total_set_bonuses[set_bonus] += 1

            total_slots.update(armour_piece.decoration_slots)

        # Now, we add the charm.
        charm_skills = calculate_skills_dict_from_charm(charm, charm.max_level)
        for (skill, level) in charm_skills.items():
            regular_skills[skill] += level

        regular_skills = clipped_skills_defaultdict_includesecret(regular_skills)
        yield ((head, chest, arms, waist, legs), charm, regular_skills, total_slots, total_set_bonuses)


def _generate_deco_additions(deco_slots, regular_skills, decos):
    assert isinstance(regular_skills, defaultdict)
    assert isinstance(decos, list) and (len(decos) == 4)

    # We expect pre-sorted deco sublists
    assert all((x.value.slot_size == 1) for x in decos[0])
    assert list_obeys_sort_order(decos[1], key=lambda x : x.value.slot_size, reverse=True)
    assert list_obeys_sort_order(decos[2], key=lambda x : x.value.slot_size, reverse=True)
    assert list_obeys_sort_order(decos[3], key=lambda x : x.value.slot_size, reverse=True)
    assert decos[1][0].value.slot_size >= decos[1][-1].value.slot_size # More sanity checks
    assert decos[2][0].value.slot_size >= decos[2][-1].value.slot_size
    assert decos[3][0].value.slot_size >= decos[3][-1].value.slot_size

    if len(deco_slots) == 0:
        return [([], regular_skills)]

    # Sort deco slots from biggest to smallest.
    deco_slots = sorted(deco_slots, reverse=True)
    assert len(deco_slots) <= 3
    assert deco_slots[0] >= deco_slots[-1]
    assert all((x > 0) and (x <= 4) for x in deco_slots)

    incomplete_deco_combos = [([], deco_slots, regular_skills)] # [(decos, slots, skills)]
    complete_deco_combos = [] # same format

    decos_sublist = decos[deco_slots[0] - 1]
    for deco in decos_sublist:

        deco_skills = deco.value.skills_dict
        deco_size = deco.value.slot_size

        new_incomplete = copy(incomplete_deco_combos)

        for (curr_decos, curr_slots, curr_skills) in incomplete_deco_combos:

            max_to_add = ceil(max(
                    (get_highest_skill_limit(skill) - curr_skills.get(skill, 0)) / level
                    for (skill, level) in deco_skills.items()
                ))

            if max_to_add > 0:
                for _ in range(max_to_add):
                    assert len(curr_slots) > 0 # We assume anything in incomplete_deco_combos has slots.

                    if curr_slots[0] < deco_size:
                        break

                    curr_decos = copy(curr_decos)
                    curr_slots = copy(curr_slots)
                    curr_skills = copy(curr_skills)

                    curr_decos.append(deco)
                    curr_slots.pop(0)
                    for (skill, level) in deco_skills.items():
                        curr_skills[skill] += level

                    t = (curr_decos, curr_slots, curr_skills)
                    if len(curr_slots) == 0:
                        complete_deco_combos.append(t)
                        break
                    else:
                        new_incomplete.append(t)

        incomplete_deco_combos = new_incomplete

    return [(x[0], x[2]) for x in complete_deco_combos + incomplete_deco_combos]


def _distance_to_nearest_target_set_bonus_combo(set_bonus_combo, target_set_bonus_combos):
    assert all((v >= 0) for (_, v) in set_bonus_combo.items())
    return min(
            sum(
                max(pieces - set_bonus_combo.get(set_bonus, 0), 0)
                for (set_bonus, pieces) in combo.items()
            )
            for combo in target_set_bonus_combos
        )


# "Seen-set, by skills and set bonuses"
class SeenSetBySSB:

    __slots__ = [
            "_seen_set",
            "_combo_map"
        ]

    def __init__(self):
        self._seen_set = set()
        self._combo_map = {}
        return

    def add(self, skills_counter, set_bonuses_counter, object_to_store):
        h = (convert_skills_dict_to_tuple(skills_counter), convert_set_bonuses_dict_to_tuple(set_bonuses_counter))
        if h in self._seen_set:
            return

        # And we add it!
        self._add_power_set(skills_counter, set_bonuses_counter)
        self._combo_map[h] = object_to_store
        return

    def items_as_list(self):
        return [v for (k, v) in self._combo_map.items()]

    def _add_power_set(self, skill_counter, set_bonuses_counter):
        h = (convert_skills_dict_to_tuple(skill_counter), convert_set_bonuses_dict_to_tuple(set_bonuses_counter))
        if h in self._seen_set:
            if h in self._combo_map:
                del self._combo_map[h]
            return
        self._seen_set.add(h)

        new_skills = copy(skill_counter)
        for (skill, level) in skill_counter.items():
            if level > 1:
                new_skills[skill] = level - 1
            else:
                del new_skills[skill]
            self._add_power_set(new_skills, set_bonuses_counter)
            new_skills[skill] = level

        new_set_bonuses = copy(set_bonuses_counter)
        for (set_bonus, pieces) in set_bonuses_counter.items():
            if pieces > 1:
                new_set_bonuses[set_bonus] = pieces - 1
            else:
                del new_set_bonuses[set_bonus]
            self._add_power_set(skill_counter, new_set_bonuses)
            new_set_bonuses[set_bonus] = pieces

        return


def _generate_slot_combinations(slot_pieces, possible_decos, skill_subset, set_bonus_subset, *, progress_msg_slot):
    assert isinstance(slot_pieces, list)
    assert isinstance(possible_decos, list)
    assert isinstance(skill_subset, set)
    assert isinstance(set_bonus_subset, set)

    # An important feature of these lists it that they are sorted by decoration size!
    assert list_obeys_sort_order(possible_decos[0], key=lambda x : x.value.slot_size, reverse=True)
    assert list_obeys_sort_order(possible_decos[1], key=lambda x : x.value.slot_size, reverse=True)
    assert list_obeys_sort_order(possible_decos[2], key=lambda x : x.value.slot_size, reverse=True)
    assert list_obeys_sort_order(possible_decos[3], key=lambda x : x.value.slot_size, reverse=True)

    seen_set = SeenSetBySSB()

    # STATISTICS
    stats_pre = 0

    for piece in slot_pieces:
        assert isinstance(piece, ArmourPieceInfo)

        skills = defaultdict(lambda : 0, piece.skills)
        set_bonus = piece.armour_set.set_bonus
        assert None not in set_bonus_subset
        set_bonuses = {set_bonus: 1} if (set_bonus in set_bonus_subset) else {}

        deco_it = list(_generate_deco_additions(piece.decoration_slots, skills, possible_decos))
        stats_pre += len(deco_it) # STATISTICS
        for (deco_additions, new_skills) in deco_it:
            new_skills = clipped_skills_defaultdict_includesecret(new_skills)

            # Now, we have to decide if it's worth keeping.
            new_skills = defaultdict(lambda : 0, ((k, v) for (k, v) in new_skills.items() if (k in skill_subset)))

            t = (piece, deco_additions, new_skills, set_bonus)
            seen_set.add(new_skills, set_bonuses, t)

    piece_combos = seen_set.items_as_list()

    # STATISTICS
    stats_post = len(piece_combos)
    log_appstats_reduction(f"{progress_msg_slot} piece+deco combination reduction", stats_pre, stats_post)

    return piece_combos


def _add_armour_slot(curr_collection, piece_combos, skill_subset, minimum_set_bonus_combos, \
                                minimum_set_bonus_distance, *, seen_set, progress_msg_slot):
    assert isinstance(curr_collection, list)
    assert isinstance(piece_combos, list)
    assert isinstance(skill_subset, set)
    assert isinstance(minimum_set_bonus_combos, list)
    assert isinstance(seen_set, SeenSetBySSB)

    set_bonus_subset = set() # A little bit redundant?
    for set_bonus_combo in minimum_set_bonus_combos:
        set_bonus_subset.update(set(set_bonus_combo))

    # STATISTICS
    stage2_pre = len(curr_collection) * len(piece_combos)
    progress = ExecutionProgress(f"COMBINING {progress_msg_slot} PIECES -", stage2_pre, granularity=50000)

    for (pieces, deco_counter, regular_skills, set_bonuses) in curr_collection:

        assert isinstance(pieces, list)
        assert isinstance(deco_counter, Counter)
        assert isinstance(regular_skills, defaultdict)
        assert isinstance(set_bonuses, defaultdict)

        assert all((k in skill_subset) for (k, v) in regular_skills.items()) # Only skills in the subset are considered
        assert all((k in set_bonus_subset) for (k, v) in set_bonuses.items()) # Only set bonuses in the subset are considered

        for (pc_piece, pc_decos, pc_skills, pc_set_bonus) in piece_combos:
            assert isinstance(pc_piece, ArmourPieceInfo)
            assert isinstance(pc_decos, list)
            assert isinstance(pc_skills, dict)
            assert (pc_set_bonus is None) or isinstance(pc_set_bonus, SetBonus)

            new_pieces = pieces + [pc_piece]
            new_deco_counter = copy(deco_counter)
            new_regular_skills = copy(regular_skills)
            new_set_bonuses = copy(set_bonuses)

            new_deco_counter.update(pc_decos)

            for (skill, level) in pc_skills.items():
                if skill in skill_subset:
                    new_regular_skills[skill] += level

            if (pc_set_bonus is not None) and (pc_set_bonus in set_bonus_subset):
                new_set_bonuses[pc_set_bonus] += 1

            set_bonus_distance = _distance_to_nearest_target_set_bonus_combo(new_set_bonuses, minimum_set_bonus_combos)
            if set_bonus_distance > minimum_set_bonus_distance:
                progress.update_and_log_progress(logger) # Statistics Stuff
                continue

            # Now, we have to decide if it's worth keeping.
            new_regular_skills = defaultdict(lambda : 0, ((k, v) for (k, v) in new_regular_skills.items() if (k in skill_subset)))
            new_regular_skills = clipped_skills_defaultdict_includesecret(new_regular_skills)

            t = (new_pieces, new_deco_counter, new_regular_skills, new_set_bonuses)
            seen_set.add(new_regular_skills, new_set_bonuses, t)

            progress.update_and_log_progress(logger) # Statistics Stuff

    ret = seen_set.items_as_list()

    # Statistics stuff
    stage2_post = len(ret)

    log_appstats_reduction(f"{progress_msg_slot} full combining reduction", stage2_pre, stage2_post)

    #log_appstats_reduction("Set bonus filtering reduction", total_pre_deco_combos, final_pre_deco_combos)
    #log_appstats_reduction("Skill and set bonus filtering reduction", post_deco_combos_seen, len(ret))

    return ret


def _find_highest_efr_build(s):
    assert isinstance(s, SearchParameters)

    ####################################
    # STAGE 1: Read search parameters. #
    ####################################

    desired_weapon_class = s.selected_weapon_class
    min_health_regen_augment_level = s.min_health_regen_augment_level

    skills_with_minimum_levels = {k: v for (k, v) in s.selected_skills.items() if (v > 0)}
    skill_subset = set(s.selected_skills) # Get all the keys

    required_set_bonus_skills = s.selected_set_bonus_skills
    # IMPORTANT: We're not checking if these skills are actually attainable via. set bonus.
    minimum_set_bonus_combos = calculate_possible_set_bonus_combos(required_set_bonus_skills)
    relaxed_minimum_set_bonus_combos = relax_set_bonus_combos(minimum_set_bonus_combos)

    set_bonus_subset = set()
    for set_bonus_combo in minimum_set_bonus_combos:
        set_bonus_subset.update(set(set_bonus_combo))

    skill_states = s.skill_states

    #########################################
    # STAGE 2.1: Generate some collections. #
    #########################################

    armour = prune_easyiterate_armour_db(s.selected_armour_tier, easyiterate_armour, skill_subset=skill_subset)
    charms = list(get_charms_subset(skill_subset))

    decos = list(get_pruned_deco_set(set(skill_subset)))
    decos_maxsize1 = [x for x in decos if (x.value.slot_size == 1)]
    decos_maxsize2 = [x for x in decos if (x.value.slot_size == 2)] + decos_maxsize1
    decos_maxsize3 = [x for x in decos if (x.value.slot_size == 3)] + decos_maxsize2
    decos_maxsize4 = [x for x in decos if (x.value.slot_size == 4)] + decos_maxsize3
    # An important feature of these lists it that they are sorted by decoration size!
    assert list_obeys_sort_order(decos_maxsize1, key=lambda x : x.value.slot_size, reverse=True)
    assert list_obeys_sort_order(decos_maxsize2, key=lambda x : x.value.slot_size, reverse=True)
    assert list_obeys_sort_order(decos_maxsize3, key=lambda x : x.value.slot_size, reverse=True)
    assert list_obeys_sort_order(decos_maxsize4, key=lambda x : x.value.slot_size, reverse=True)
    decos = [decos_maxsize1, decos_maxsize2, decos_maxsize3, decos_maxsize4]

    # We also generate weapon combinations.
    grouped_weapon_combos = _get_grouped_and_pruned_weapon_combos(desired_weapon_class, min_health_regen_augment_level, \
                                                                    skill_subset, set_bonus_subset, skill_states)
    num_weapon_combos = sum(len(x) for (_, x) in grouped_weapon_combos)
    log_appstats("Weapon combinations", num_weapon_combos)

    ##############################################
    # STAGE 2.2: We make some reusable functions #
    ##############################################

    def check_combination_size(expected_size):
        if not all((len(pieces) == expected_size) for (pieces, _, _, _) in c):
            raise RuntimeError("We have retained at least one combination from a previous armour-combining stage. " \
                               "This code is not yet equipped to handle this case since we're " \
                               "assuming that all previous combinations can be improved on. " \
                               "This error might occur if we've maxed out on skills before combining all armour pieces, " \
                               "or in other weird cases. (We'll deal with this error when we find these cases!)")
        return

    ###########################################################################
    # STAGE 3: We combine armour, charms, and decorations, pruning in stages. #
    ###########################################################################

    c = []
    c_seen_set = SeenSetBySSB()

    # We first generate a list of just charms.
    for charm in charms:
        skills = defaultdict(lambda : 0)
        set_bonuses = defaultdict(lambda : 0)
        skills.update((k, v) for (k, v) in calculate_skills_dict_from_charm(charm, charm.max_level).items() if (k in skill_subset))
        c.append(([charm], Counter(), skills, set_bonuses))
    check_combination_size(1)

    log_appstats("Charms", len(c))
    
    kwargs = {"progress_msg_slot": "HEAD"}
    piece_combos = _generate_slot_combinations(armour[ArmourSlot.HEAD], decos, skill_subset, set_bonus_subset, **kwargs)
    c = _add_armour_slot(c, piece_combos, skill_subset, relaxed_minimum_set_bonus_combos, 5, seen_set=c_seen_set, **kwargs)

    check_combination_size(2)
    #c_seen_set = SeenSetBySSB() # Uncomment to force it to reset

    kwargs = {"progress_msg_slot": "CHEST"}
    piece_combos = _generate_slot_combinations(armour[ArmourSlot.CHEST], decos, skill_subset, set_bonus_subset, **kwargs)
    c = _add_armour_slot(c, piece_combos, skill_subset, relaxed_minimum_set_bonus_combos, 4, seen_set=c_seen_set, **kwargs)

    check_combination_size(3)
    #c_seen_set = SeenSetBySSB() # Uncomment to force it to reset

    kwargs = {"progress_msg_slot": "ARM"}
    piece_combos = _generate_slot_combinations(armour[ArmourSlot.ARMS], decos, skill_subset, set_bonus_subset, **kwargs)
    c = _add_armour_slot(c, piece_combos, skill_subset, relaxed_minimum_set_bonus_combos, 3, seen_set=c_seen_set, **kwargs)

    check_combination_size(4)
    #c_seen_set = SeenSetBySSB() # Uncomment to force it to reset

    kwargs = {"progress_msg_slot": "WAIST"}
    piece_combos = _generate_slot_combinations(armour[ArmourSlot.WAIST], decos, skill_subset, set_bonus_subset, **kwargs)
    c = _add_armour_slot(c, piece_combos, skill_subset, relaxed_minimum_set_bonus_combos, 2, seen_set=c_seen_set, **kwargs)

    check_combination_size(5)
    #c_seen_set = SeenSetBySSB() # Uncomment to force it to reset

    kwargs = {"progress_msg_slot": "LEGS"}
    piece_combos = _generate_slot_combinations(armour[ArmourSlot.LEGS], decos, skill_subset, set_bonus_subset, **kwargs)
    c = _add_armour_slot(c, piece_combos, skill_subset, relaxed_minimum_set_bonus_combos, 1, seen_set=c_seen_set, **kwargs)

    check_combination_size(6)

    # We sort by number of skills within the skill subset for better pruning!
    # We assume here that the best builds tend to be the ones that fit the most skills into it.
    assert all(
            all(
                (skill in skill_subset) and (level > 0) and (level <= get_highest_skill_limit(skill))
                for (skill, level) in x[2].items()
            )
            for x in c
        )
    c.sort(key=(lambda x : sum(level for (_, level) in x[2].items())), reverse=True)

    ######################################################################
    # STAGE 4: We now try weapon combinations to find our optimal build! #
    ######################################################################

    best_efr = 1
    associated_affinity = None
    associated_build = None

    #stats_combos_explored = 0
    progress = ExecutionProgress(f"COMBINING WEAPONS -", len(c), granularity=200)

    for (c_pieces, c_deco_counter, c_regular_skills, c_set_bonuses) in c:
        (c_charm, c_head, c_chest, c_arms, c_waist, c_legs) = c_pieces

        regenerate_weapon_list = False

        for ((wg_set_bonus, wg_sorted_deco_slots), weapon_combos) in grouped_weapon_combos:

            if wg_set_bonus not in set_bonus_subset:
                wg_set_bonus = None
            wg_set_bonus_skills = calculate_set_bonus_skills(c_set_bonuses, wg_set_bonus)
            if not all((wg_set_bonus_skills.get(x, 0) == 1) for x in required_set_bonus_skills):
                continue # We prune combinations that don't fulfill the required set bonus skills here.

            deco_it = list(_generate_deco_additions(wg_sorted_deco_slots, c_regular_skills, decos))
            #stats_combos_explored += len(deco_it) # STATISTICS
            for (deco_additions, d_regular_skills) in deco_it:

                # TODO: Do I need to filter and clip here?
                d_regular_skills = defaultdict(lambda : 0, ((k, v) for (k, v) in d_regular_skills.items() if (k in skill_subset)))
                d_regular_skills = clipped_skills_defaultdict_includesecret(d_regular_skills)

                if not all((d_regular_skills.get(k, 0) >= v) for (k, v) in skills_with_minimum_levels.items()):
                    continue # We prune combinations that don't fulfill the required skill minimums here.

                d_deco_counter = copy(c_deco_counter)
                d_deco_counter.update(deco_additions)

                for (weapon, w_augments_tracker, w_upgrades_tracker, w_combo_values, _) in weapon_combos:

                    results = lookup_from_skills(weapon, d_regular_skills, skill_states, w_augments_tracker, w_upgrades_tracker)

                    if results.efr > best_efr:
                        armour_dict = {
                                ArmourSlot.HEAD:  c_head,
                                ArmourSlot.CHEST: c_chest,
                                ArmourSlot.ARMS:  c_arms,
                                ArmourSlot.WAIST: c_waist,
                                ArmourSlot.LEGS:  c_legs,
                            }

                        best_efr = results.efr
                        associated_affinity = results.affinity
                        associated_build = Build(weapon, armour_dict, c_charm, w_augments_tracker, w_upgrades_tracker, \
                                                        d_deco_counter)
                        assert results.efr == associated_build.calculate_performance(skill_states).efr

                        regenerate_weapon_list = True

                        logger.info("")
                        logger.info(associated_build.get_humanreadable(skill_states))
                        logger.info("")

        progress.update_and_log_progress(logger) # STATISTICS

        # Prune away weapon combinations whose ceiling EFRs are less than our best EFR.
        if regenerate_weapon_list:
            #old_count = len(weapon_combos)
            grouped_weapon_combos = _reprune_weapon_combos(grouped_weapon_combos, minimum_efr_noninclusive=best_efr)
            new_count = sum(len(x) for (_, x) in grouped_weapon_combos)
            logger.info(f"New number of weapon configurations: {new_count} out of {num_weapon_combos}")

    return associated_build


