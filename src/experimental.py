# -*- coding: ascii -*-

"""
Filename: experimental.py
Author:   contact@simshadows.com

Creates (and caches) a list of combinations of:
- armour (head, chest, arms, waist, legs),
- charms, and
- decorations.

This does not take into account weapons. That will need to be done elsewhere!
"""

import logging
from copy import copy
from math import ceil
from itertools import product
from collections import defaultdict, Counter

from .enums        import Tier
from .utils        import (counter_is_subset,
                          get_humanreadable_from_enum_list,
                          list_obeys_sort_order)
from .loggingutils import (ExecutionProgress,
                          log_appstats,
                          log_appstats_reduction)
from .serialize    import readjson_search_parameters

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
                               clipped_skills_defaultdict,
                               convert_skills_dict_to_tuple,
                               convert_set_bonuses_dict_to_tuple,
                               get_highest_skill_limit)


logger = logging.getLogger(__name__)


# We cache a single collection of sets.
_cache_data = None
_cache_selected_armour_tier = None
_cache_skill_subset = None
_cache_required_skills = None
_cache_minimum_set_bonus_combos = None


def get_combinations(selected_armour_tier, skill_subset, required_skills, minimum_set_bonus_combos):
    assert isinstance(selected_armour_tier, Tier) or (selected_armour_tier is None)
    assert isinstance(skill_subset, set) or (skill_subset is None)
    assert isinstance(required_skills, dict)
    assert all(isinstance(k, Skill) and isinstance(v, int) for (k, v) in required_skills.items())
    assert isinstance(minimum_set_bonus_combos, list)

    global _cache_data
    global _cache_selected_armour_tier
    global _cache_skill_subset
    global _cache_required_skills
    global _cache_minimum_set_bonus_combos

    # Check the cache first.
    if (_cache_data is not None) \
            and (selected_armour_tier is _cache_selected_armour_tier) \
            and (skill_subset == _cache_skill_subset) \
            and lists_of_dicts_are_equal(required_skills, _cache_required_skills) \
            and lists_of_dicts_are_equal(minimum_set_bonus_combos, _cache_minimum_set_bonus_combos):
        return _cache_data

    # If it's not cached, we generate it.
    pruned_armour_db = prune_easyiterate_armour_db(selected_armour_tier, easyiterate_armour, skill_subset=skill_subset)
    pruned_charms_list = list(get_charms_subset(skill_subset))
    pruned_combinations = _generate_combinations(pruned_armour_db, pruned_charms_list, skill_subset, required_skills, \
                                                        minimum_set_bonus_combos)

    # Save to the cache
    _cache_data = pruned_combinations
    _cache_selected_armour_tier = selected_armour_tier
    _cache_skill_subset = skill_subset
    _cache_required_skills = required_skills
    _cache_minimum_set_bonus_combos = minimum_set_bonus_combos

    return copy(pruned_combinations)


def run_experimental_stuff(search_parameters_jsonstr):
    search_parameters = readjson_search_parameters(search_parameters_jsonstr)

    skills_with_minimum_levels = {k: v for (k, v) in search_parameters.selected_skills.items() if (v > 0)}
    skill_subset = set(search_parameters.selected_skills) # Get all the keys

    required_set_bonus_skills = search_parameters.selected_set_bonus_skills
    # IMPORTANT: We're not checking yet if these skills are actually attainable via. set bonus.

    minimum_set_bonus_combos = calculate_possible_set_bonus_combos(required_set_bonus_skills)
    relaxed_minimum_set_bonus_combos = relax_set_bonus_combos(minimum_set_bonus_combos)

    # EXPERIMENTAL
    x = get_combinations(
            search_parameters.selected_armour_tier,
            skill_subset,
            skills_with_minimum_levels,
            relaxed_minimum_set_bonus_combos,
        )

    return


###############################################################################


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

        regular_skills = clipped_skills_defaultdict(regular_skills)
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


def _add_power_set(skill_counter, set_bonuses_counter, combo_map, seen_set):
    h = (convert_skills_dict_to_tuple(skill_counter), convert_set_bonuses_dict_to_tuple(set_bonuses_counter))
    if h in seen_set:
        if h in combo_map:
            del combo_map[h]
        return
    seen_set.add(h)
    for (skill, level) in skill_counter.items():
        new_skills = copy(skill_counter)
        if level > 1:
            new_skills[skill] = level - 1
        else:
            del new_skills[skill]
        _add_power_set(new_skills, set_bonuses_counter, combo_map, seen_set)
    for (set_bonus, pieces) in set_bonuses_counter.items():
        new_set_bonuses = copy(set_bonuses_counter)
        if pieces > 1:
            new_set_bonuses[set_bonus] = pieces - 1
        else:
            del new_set_bonuses[set_bonus]
        _add_power_set(skill_counter, new_set_bonuses, combo_map, seen_set)
    return


def _add_armour_slot(curr_collection, pieces_collection, decos, skill_subset, minimum_set_bonus_combos, \
                                minimum_set_bonus_distance, *, progress_msg):
    assert isinstance(pieces_collection, list)
    assert isinstance(decos, list)

    set_bonus_subset = set()
    for set_bonus_combo in minimum_set_bonus_combos:
        set_bonus_subset.update(set(set_bonus_combo))

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

    # Statistics stuff
    total_pre_deco_combos = len(curr_collection) * len(pieces_collection)
    progress = ExecutionProgress(progress_msg, total_pre_deco_combos, granularity=400)
    removed_pre_deco_combos = 0
    post_deco_combos_seen = 0

    combo_map = {}
    seen_set = set()

    for (pieces, deco_counter, regular_skills, set_bonuses) in curr_collection:

        assert isinstance(pieces, list)
        assert isinstance(deco_counter, Counter)
        assert isinstance(regular_skills, defaultdict)
        assert isinstance(set_bonuses, defaultdict)

        assert all((k in skill_subset) for (k, v) in regular_skills.items()) # Only skills in the subset are considered
        assert all((k in set_bonus_subset) for (k, v) in set_bonuses.items()) # Only set bonuses in the subset are considered

        for new_piece in pieces_collection:
            assert isinstance(new_piece, ArmourPieceInfo)

            new_pieces = pieces + [new_piece]
            new_regular_skills = copy(regular_skills)
            new_set_bonuses = copy(set_bonuses)

            for (skill, level) in new_piece.skills.items():
                if skill in skill_subset:
                    new_regular_skills[skill] += level

            new_set_bonus = new_piece.armour_set.set_bonus
            if (new_set_bonus is not None) and (new_set_bonus in set_bonus_subset):
                new_set_bonuses[new_set_bonus] += 1

            set_bonus_distance = _distance_to_nearest_target_set_bonus_combo(new_set_bonuses, minimum_set_bonus_combos)
            if set_bonus_distance > minimum_set_bonus_distance:
                progress.update_and_log_progress(logger) # Statistics Stuff
                removed_pre_deco_combos += 1 # Statistics Stuff
                continue

            deco_it = list(_generate_deco_additions(new_piece.decoration_slots, regular_skills, decos))
            post_deco_combos_seen += len(deco_it) # Statistics Stuff
            for (deco_additions, new_skills) in deco_it:
                new_skills = clipped_skills_defaultdict(new_skills)
                new_deco_counter = copy(deco_counter)

                new_deco_counter.update(deco_additions)

                # Now, we have to decide if it's worth keeping.
                new_skills = defaultdict(lambda : 0, ((k, v) for (k, v) in new_skills.items() if (k in skill_subset)))
                h = (convert_skills_dict_to_tuple(new_skills), convert_set_bonuses_dict_to_tuple(new_set_bonuses))
                if h in seen_set:
                    continue

                # And we add it!
                combo_map[h] = (new_pieces, new_deco_counter, new_skills, new_set_bonuses)
                _add_power_set(new_skills, new_set_bonuses, combo_map, seen_set)

            progress.update_and_log_progress(logger) # Statistics Stuff

    ret = [v for (k, v) in combo_map.items()]

    # Statistics stuff
    final_pre_deco_combos = total_pre_deco_combos - removed_pre_deco_combos
    log_appstats_reduction("Set bonus filtering reduction", total_pre_deco_combos, final_pre_deco_combos)
    log_appstats_reduction("Skill and set bonus filtering reduction", post_deco_combos_seen, len(ret))

    return ret


def _generate_combinations(armour_collection, charms_list, skill_subset, required_skills, minimum_set_bonus_combos):

    ret = []

    decos = list(get_pruned_deco_set(set(skill_subset)))

    # We start by generating a list of charms.
    for charm in charms_list:
        skills = defaultdict(lambda : 0)
        set_bonuses = defaultdict(lambda : 0)
        skills.update((k, v) for (k, v) in calculate_skills_dict_from_charm(charm, charm.max_level).items() if (k in skill_subset))
        ret.append(([charm], Counter(), skills, set_bonuses))

    log_appstats("Charms", len(ret))

    ret = _add_armour_slot(ret, armour_collection[ArmourSlot.HEAD], decos, skill_subset, minimum_set_bonus_combos, 5, \
                                    progress_msg="ADDING HEAD PIECES -")

    ret = _add_armour_slot(ret, armour_collection[ArmourSlot.CHEST], decos, skill_subset, minimum_set_bonus_combos, 4, \
                                    progress_msg="ADDING CHEST PIECES -")

    ret = _add_armour_slot(ret, armour_collection[ArmourSlot.ARMS], decos, skill_subset, minimum_set_bonus_combos, 3, \
                                    progress_msg="ADDING ARM PIECES -")

    ret = _add_armour_slot(ret, armour_collection[ArmourSlot.WAIST], decos, skill_subset, minimum_set_bonus_combos, 2, \
                                    progress_msg="ADDING WAIST PIECES -")

    ret = _add_armour_slot(ret, armour_collection[ArmourSlot.LEGS], decos, skill_subset, minimum_set_bonus_combos, 1, \
                                    progress_msg="ADDING LEG PIECES -")

    return ret


