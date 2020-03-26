# -*- coding: ascii -*-

"""
Filename: query_armour.py
Author:   contact@simshadows.com

This file provides the MHWI build optimizer script's armour database queries.
"""

from copy import copy
from collections import namedtuple, defaultdict, Counter
from itertools import product

from .enums import Tier
from .utils import ExecutionProgress, prune_by_superceding

from .database_decorations import skill_to_simple_deco_size
from .database_skills import Skill, SetBonus

from .query_skills import calculate_set_bonus_skills

from .database_armour import (ArmourSlot,
                             ArmourPieceInfo,
                             easyiterate_armour)


# Returns if p1 supercedes p2.
def _armour_piece_supercedes(p1, p1_set_bonus, p2, p2_set_bonus, skill_subset=None):
    assert isinstance(p1, ArmourPieceInfo)
    assert isinstance(p2, ArmourPieceInfo)
    assert isinstance(p1_set_bonus, SetBonus) or (p1_set_bonus is None)
    assert isinstance(p2_set_bonus, SetBonus) or (p2_set_bonus is None)
    assert (isinstance(skill_subset, set) and all(isinstance(x, Skill) for x in skill_subset)) or (skill_subset is None)

    if (p2_set_bonus is not None) and (p1_set_bonus is not p2_set_bonus):
        # If p2 provides a set bonus that p1 doesn't, then p1 can't supercede it.
        return False

    p1_skills = p1.skills
    p2_skills = p2.skills
    p1_slots = Counter(p1.decoration_slots)
    p2_slots = Counter(p2.decoration_slots)
    return _skills_and_slots_supercedes(p1_skills, p1_slots, p2_skills, p2_slots, skill_subset=skill_subset)


# Returns if armour set p1 supercedes armour set p2.
#
# IMPORTANT: p1_skills and p2_skills include skills provided by set bonuses.
#
# What this means is that p1 supercedes p2 if it is guaranteed that every possible set of skills, levels, and
# the set bonus of p2 can be recreated by p1 with more flexibility, and/or more skills.
#
# The code for this function is (particularly) disgusting. We should clean it up when possible.
#
# You can technically just make this function return False and the program will still work, albeit super-slow.
# This function only determines if it knows *for sure* if p1 supercedes p2.
# There may be cases where p1 can actually supercede p2, but the current version of this function doesn't
# check for the specific conditions allowing p1 to supercede p2.
def _skills_and_slots_supercedes(p1_skills, p1_slots, p2_skills, p2_slots, skill_subset=None):
    assert isinstance(p1_skills, dict)
    assert isinstance(p2_skills, dict)
    assert isinstance(p1_slots, Counter)
    assert isinstance(p2_slots, Counter)
    assert (isinstance(skill_subset, set) and all(isinstance(x, Skill) for x in skill_subset)) or (skill_subset is None)

    # Stage 1: We gather available information.

    p1_size1 = p1_slots[1]
    p1_size2 = p1_slots[2]
    p1_size3 = p1_slots[3]
    p1_size4 = p1_slots[4]
    #assert len(p1_slots) == 4 # It's probably a defaultdict

    p2_size1 = p2_slots[1]
    p2_size2 = p2_slots[2]
    p2_size3 = p2_slots[3]
    p2_size4 = p2_slots[4]
    #assert len(p2_slots) == 4 # It's probably a defaultdict

    # Stage 2: We simplify available information.

    # At worst, we put size-1 jewels in size-4 slots
    p1_slots_underest = (p1_size1, p1_size2, p1_size3 + p1_size4)
    # At best, we can put the equivalent of two size-3 jewels into a size-4 slot
    p2_slots_overest = (p2_size1, p2_size2, p2_size3 + (p2_size4 * 2)) 

    all_skills = set(p1_skills) | set(p2_skills)
    if skill_subset is not None:
        all_skills = all_skills & skill_subset # We ignore anything not in the subset

    skills_unique_to_p1 = {}
    skills_unique_to_p2 = {}
    for skill in all_skills:
        p1_level = p1_skills.get(skill, 0)
        p2_level = p2_skills.get(skill, 0)

        if p1_level - p2_level > 0:
            skills_unique_to_p1[skill] = p1_level - p2_level
        elif p2_level - p1_level > 0:
            skills_unique_to_p2[skill] = p2_level - p1_level
        else:
            assert p1_level - p2_level == 0
    
    slots_required_to_recreate_p2_unique_skills = [0, 0, 0]
    for (skill, level) in skills_unique_to_p2.items():
        if skill not in skill_to_simple_deco_size:
            return False # We return here since we know p2 has unique skills that don't have decorations.
        size_required = skill_to_simple_deco_size[skill]
        slots_required_to_recreate_p2_unique_skills[size_required - 1] += level

    # Stage 3: We do the more complex processing.

    p2_required = slots_required_to_recreate_p2_unique_skills
    p2_available = list(p2_slots_overest)
    p1_available = list(p1_slots_underest)

    # Subtracts slots in b from slots in a.
    # Effectively "a minus b".
    # Returns None if a cannot be subtracted by b.
    def subtract_slots(a, b):
        assert len(a) == 3
        assert len(b) == 3

        # (We could try being more algorithmic, but doing a cascade of if-statements will work for this small set of sizes.)

        a = copy(a)
        b = copy(b)

        if a[0] >= b[0]:
            a[0] -= b[0]
        else:
            b[1] += b[0] - a[0]
            a[0] = 0
        # Don't care about b[0] anymore.

        if a[1] >= b[1]:
            a[1] -= b[1]
        else:
            b[2] += b[1] - a[1]
            a[1] = 0
        # Don't care about b[1] anymore.

        if a[2] >= b[2]:
            a[2] -= b[2]
        else:
            return None # We return here since we know we don't have enough p1_available decoration slots.
        # Don't care about b[2] anymore.

        return a

    p1_initialy_has_decos = any(x > 0 for x in p1_available)

    p1_available = subtract_slots(p1_available, p2_available)

    p1_has_more_decos = any(x > 0 for x in p1_available) if (p1_available is not None) else NotImplemented

    if p1_available is None:
        return False # p1 cannot supercede p2 because p1 effectively has less slots than p2

    p1_available = subtract_slots(p1_available, p2_required)

    if p1_available is None:
        return False # p1 cannot supercede p2 because p1 isn't guaranteed to be able to also recreate p2's skills.

    p1_has_extra_slots = any(x > 0 for x in p1_available)

    if p1_has_more_decos:
        return True # We can recreate the same skills with room to spare.
    elif len(skills_unique_to_p1) > 0:
        return True # We can recreate exactly the same skills, but also with additional skills.

    # Stage 4: What happens if we don't necessarily have room to spare?

    return None # We defer the decision to the tiebreaker.


def prune_easyiterate_armour_db(selected_armour_tier, original_easyiterate_armour_db, skill_subset=None):
    assert isinstance(selected_armour_tier, Tier) or (selected_armour_tier is None)

    print()
    print()
    print("======= Armour Pruning =======")
    print()

    intermediate = {}
    for (gear_slot, piece_list) in original_easyiterate_armour_db.items():

        # First, we need to filter by tier.
        if selected_armour_tier is not None:
            piece_list = [x for x in piece_list if (x.armour_set.discriminator.value.tier is selected_armour_tier)]

        def left_supercedes_right(piece1, piece2):
            piece1_set_bonus = piece1.armour_set.set_bonus
            piece2_set_bonus = piece2.armour_set.set_bonus
            return _armour_piece_supercedes(piece1, piece1_set_bonus, piece2, piece2_set_bonus, skill_subset=skill_subset) 

        intermediate[gear_slot] = prune_by_superceding(piece_list, left_supercedes_right)

    total_kept = sum(len(x) for (_, x) in intermediate.items())
    total_original = sum(len(x) for (_, x) in original_easyiterate_armour_db.items())

    print("kept: " + str(total_kept))
    print("pruned: " + str(total_original - total_kept))
    print()
    print("=============================")
    print()
    print()

    return intermediate


_pruned_armour_combos_cache = [] # [(skill_subset, required_set_bonus_skills, pruned_armour_combos)]


def get_pruned_armour_combos(selected_armour_tier, skill_subset, required_set_bonus_skills):
    assert isinstance(selected_armour_tier, Tier) or (selected_armour_tier is None)
    assert isinstance(skill_subset, set) or (skill_subset is None)
    assert isinstance(required_set_bonus_skills, set)

    # Check cache first.
    for (c_selected_armour_tier, c_skill_subset, c_required_set_bonus_skills, c_armour_combo_list) in _pruned_armour_combos_cache:
        if (c_selected_armour_tier is selected_armour_tier) and (c_skill_subset == skill_subset) \
                            and (c_required_set_bonus_skills == required_set_bonus_skills):
            return c_armour_combo_list

    # If it's not in the cache, then we have to generate it.
    pruned_armour_db = prune_easyiterate_armour_db(selected_armour_tier, easyiterate_armour, skill_subset=skill_subset)
    pruned_armour_combos = generate_and_prune_armour_combinations(pruned_armour_db, skill_subset=skill_subset, \
                                                                    required_set_bonus_skills=required_set_bonus_skills)

    # Add to the cache.
    t = (selected_armour_tier, copy(skill_subset), copy(required_set_bonus_skills), pruned_armour_combos)
    _pruned_armour_combos_cache.append(t)

    return copy(pruned_armour_combos)


def _armour_combination_iter(original_easyiterate_armour_db):

    combinations_iter = product(
            original_easyiterate_armour_db[ArmourSlot.HEAD],
            original_easyiterate_armour_db[ArmourSlot.CHEST],
            original_easyiterate_armour_db[ArmourSlot.ARMS],
            original_easyiterate_armour_db[ArmourSlot.WAIST],
            original_easyiterate_armour_db[ArmourSlot.LEGS],
        ) # TODO: Ugh, this is so ugly.

    for (head, chest, arms, waist, legs) in combinations_iter:

        combination = {
                ArmourSlot.HEAD:  head,
                ArmourSlot.CHEST: chest,
                ArmourSlot.ARMS:  arms,
                ArmourSlot.WAIST: waist,
                ArmourSlot.LEGS:  legs,
            }

        total_skills = defaultdict(lambda : 0)
        total_slots = Counter()

        total_set_bonuses = defaultdict(lambda : 0) # Don't use this after we update total_skills.

        # We fill the totals in this loop.
        for (gear_slot, piece) in combination.items():
            assert isinstance(piece, ArmourPieceInfo)

            set_bonus = piece.armour_set.set_bonus
            assert isinstance(set_bonus, SetBonus) or (set_bonus is None)

            for (skill, level) in piece.skills.items():
                total_skills[skill] += level

            if set_bonus is not None:
                total_set_bonuses[set_bonus] += 1

            total_slots.update(piece.decoration_slots)

        if __debug__:
            num_total_regular_skills = len(total_skills)

        total_set_bonus_skills = calculate_set_bonus_skills(total_set_bonuses, None)
        total_skills.update(total_set_bonus_skills)
        assert len(total_skills) == len(total_set_bonus_skills) + num_total_regular_skills

        yield (combination, total_skills, total_slots)


# Applies the same pruning rule as _armour_piece_supercedes(), but over an entire armour set instead!
#
# Returns a list of dictionaries of {ArmourSlot: ArmourEasyIterateInfo}
def generate_and_prune_armour_combinations(original_easyiterate_armour_db, skill_subset=None, \
                                            required_set_bonus_skills=set()):
    assert isinstance(required_set_bonus_skills, set)

    print()
    print()
    print("===== Armour Set Pruning =====")
    print()

    all_combinations = list(_armour_combination_iter(original_easyiterate_armour_db))
    print(f"Number of armour combinations, before pruning: {len(all_combinations)}")

    all_combinations = [x for x in all_combinations if all(skill in x[1] for skill in required_set_bonus_skills)]
    print(f"Number of armour combinations, after filtering by set bonus: {len(all_combinations)}")

    progress = ExecutionProgress("COMBINATION PRUNING", len(all_combinations), granularity=100)

    def left_supercedes_right(left, right):
        (combination_1, total_skills_1, total_slots_1) = left
        (combination_2, total_skills_2, total_slots_2) = right
        return _skills_and_slots_supercedes(total_skills_1, total_slots_1, total_skills_2, total_slots_2, \
                                                skill_subset=skill_subset) 

    def update_progress():
        progress.update_and_print_progress()

    best_combinations = prune_by_superceding(all_combinations, left_supercedes_right, execute_per_iteration=update_progress)

    print()
    print(f"Number of armour combinations, after pruning: {len(best_combinations)}")
    print()
    print("=============================")
    print()
    print()

    return [x[0] for x in best_combinations]


# calculate_armour_contribution() input looks like this:
#
#       armour_dict = {
#           ArmourSlot.HEAD:  ("Teostra",      ArmourDiscriminator.HIGH_RANK,   ArmourVariant.HR_GAMMA),
#           ArmourSlot.CHEST: ("Damascus",     ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
#           ArmourSlot.ARMS:  ("Teostra",      ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
#           ArmourSlot.WAIST: ("Teostra",      ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
#           ArmourSlot.LEGS:  ("Yian Garuga",  ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
#       }
#
ArmourContribution = namedtuple(
    "ArmourContribution",
    [
        "skills",
        "set_bonuses",
        "decoration_slots",
    ],
)
def calculate_armour_contribution(armour_dict):
    assert len(armour_dict) == 5
    assert len({x for x in ArmourSlot} - set(armour_dict)) == 0

    skills = defaultdict(lambda : 0)
    set_bonuses = defaultdict(lambda : 0)
    decoration_slots = []

    for slot in ArmourSlot:
        piece = armour_dict[slot]
        armour_set = piece.armour_set

        assert isinstance(piece.decoration_slots, tuple)
        assert all(isinstance(x, int) for x in piece.decoration_slots)
        decoration_slots += piece.decoration_slots

        for (skill, level_from_gear) in piece.skills.items():
            skills[skill] += level_from_gear

        if armour_set.set_bonus is not None:
            assert isinstance(armour_set.set_bonus, SetBonus)
            set_bonuses[armour_set.set_bonus] += 1

    #print([f"{k} : {v}" for (k,v) in set_bonuses.items()])

    ret = ArmourContribution(
        skills = skills,
        set_bonuses = set_bonuses,
        decoration_slots = decoration_slots,
    )
    return ret

