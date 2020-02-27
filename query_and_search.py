#!/usr/bin/env python3
# -*- coding: ascii -*-

"""
Filename: query_and_search.py
Author:   contact@simshadows.com

This file contains various queries and search algorithms.
"""

import sys
from copy import copy

#from math import floor
from collections import namedtuple, defaultdict, Counter

from database_skills      import (RAW_BLUNDER_MULTIPLIER,
                                 Skill,
                                 clipped_skills_defaultdict,
                                 calculate_set_bonus_skills,
                                 calculate_skills_contribution)
from database_weapons     import (WeaponClass,
                                 weapon_db,
                                 IBWeaponAugmentType,
                                 WeaponAugmentationScheme,
                                 WeaponUpgradeScheme)
from database_armour      import (ArmourDiscriminator,
                                 ArmourVariant,
                                 ArmourSlot,
                                 armour_db,
                                 calculate_armour_contribution)
from database_charms      import (charms_db,
                                 charms_indexed_by_skill,
                                 calculate_skills_dict_from_charm)
from database_decorations import (Decoration,
                                 calculate_decorations_skills_contribution)
from database_misc        import (POWERCHARM_ATTACK_POWER,
                                  POWERTALON_ATTACK_POWER)


# Corresponds to each level from red through to purple, in increasing-modifier order.
SHARPNESS_LEVEL_NAMES   = ("Red", "Orange", "Yellow", "Green", "Blue", "White", "Purple")
RAW_SHARPNESS_MODIFIERS = (0.5,   0.75,     1.0,      1.05,    1.2,    1.32,    1.39    )


# Returns both the values of the new sharpness bar, and the highest sharpness level.
# The new sharpness bar corresponds to the indices in RAW_SHARPNESS_LEVEL_MODIFIERS and SHARPNESS_LEVEL_NAMES.
# The highest sharpness level also corresponds to the same indices.
def _actual_sharpness_level_values(weapon_maximum_sharpness, handicraft_level):
    assert (handicraft_level >= 0) and (handicraft_level <= 5)
    assert (len(weapon_maximum_sharpness) == 7) and (len(RAW_SHARPNESS_MODIFIERS) == 7)

    # We traverse the weapon sharpness bar in reverse, subtracting based on missing handicraft levels.
    points_to_subtract = (5 - handicraft_level) * 10
    stop_level = 7
    actual_values = []
    for (level, points) in reversed(list(enumerate(weapon_maximum_sharpness))):
        if points > points_to_subtract:
            points_to_subtract = 0
            actual_values.insert(0, points - points_to_subtract)
        else:
            stop_level = level
            points_to_subtract -= points
            actual_values.insert(0, 0)

    assert len(actual_values) == 7
    return (tuple(actual_values), stop_level - 1)

# This will be useful in the future for algorithm performance optimization.
#def calculate_highest_sharpness_modifier(weapon_maximum_sharpness, handicraft_level):
#    assert (handicraft_level >= 0) and (handicraft_level <= 5)
#    assert (len(weapon_maximum_sharpness) == 7) and (len(RAW_SHARPNESS_MODIFIERS) == 7)
#
#    # We traverse the weapon sharpness bar in reverse, then
#    # keep subtracting missing handicraft levels until we stop.
#    points_to_subtract = (5 - handicraft_level) * 10
#    for (level, points) in reversed(list(enumerate(weapon_maximum_sharpness))):
#        points_to_subtract -= weapon_maximum_sharpness[level]
#        if points_to_subtract < 0:
#            break
#
#    #print(f"Points of sharpness until next level = {-points_to_subtract}")
#    #print()
#    
#    maximum_sharpness_level = level
#    return RAW_SHARPNESS_MODIFIERS[maximum_sharpness_level]


def _calculate_efr(**kwargs):
    weapon_type = kwargs["weapon_type"]
    bloat       = weapon_type.value.bloat

    weapon_base_raw            = kwargs["weapon_raw"] / bloat
    weapon_affinity_percentage = kwargs["weapon_affinity_percentage"]
    weapon_raw_multiplier      = kwargs["weapon_raw_multiplier"]

    added_raw                 = kwargs["added_raw"]
    added_affinity_percentage = kwargs["added_affinity_percentage"]

    augment_added_raw = kwargs["augment_added_raw"]

    raw_sharpness_modifier = kwargs["raw_sharpness_modifier"]
    raw_crit_multiplier    = kwargs["raw_crit_multiplier"]
    raw_crit_chance        = min(weapon_affinity_percentage + added_affinity_percentage, 100) / 100

    if raw_crit_chance < 0:
        # Negative Affinity
        raw_blunder_chance = -raw_crit_chance
        raw_crit_modifier = (RAW_BLUNDER_MULTIPLIER * raw_blunder_chance) + (1 - raw_blunder_chance)
    else:
        # Positive Affinity
        raw_crit_modifier = (raw_crit_multiplier * raw_crit_chance) + (1 - raw_crit_chance)

    true_raw_unrounded = ((weapon_base_raw + augment_added_raw) * weapon_raw_multiplier) + added_raw 
    true_raw           = round(true_raw_unrounded, 0)

    efr = true_raw * raw_sharpness_modifier * raw_crit_modifier

    return efr


LookupFromSkillsValues = namedtuple(
    "LookupFromSkillsValues",
    [
        "efr",
        "sharpness_values",

        "skills",
    ],
)
# This function is recursive.
# For each condition missing from skill_conditions_dict,
# it will call itself again for each possible state of the skill.
def lookup_from_skills(weapon, skills_dict, skill_states_dict, augments_list):
    #assert isinstance(weapon, namedtuple) # idk how to implement this assertion. # TODO: This.
    assert isinstance(skills_dict, dict)
    assert isinstance(skill_states_dict, dict)
    assert isinstance(augments_list, list)

    skills_dict = clipped_skills_defaultdict(skills_dict)

    ret = None

    skill_states_missing = any(
            (lvl > 0) and (s.value.states is not None) and (s not in skill_states_dict)
            for (s, lvl) in skills_dict.items()
        )

    if skill_states_missing:
        # We do recursion here.

        if __debug__:
            # Determine if skills_states_dict contains any skills not in skills_dict.
            skills_keys = set(k for (k, v) in skills_dict.items())
            skill_states_keys = set(k for (k, v) in skill_states_dict.items())
            diff = skill_states_keys - skills_keys
            if len(diff) > 0:
                skills_str = " ".join(diff)
                raise RuntimeError(f"skill_states_dict has skills not in skills_dict. \
                        (Skills unique to skill_states_dict: {skills_str}.")

        # We first determine the missing skill name from skill_states_dict that is earliest in alphabetical order.

        skill_to_iterate = None

        for (skill, _) in skills_dict.items():
            if (skill.value.states is not None) and (skill not in skill_states_dict):
                if (skill_to_iterate is None) or (skill.value.name <= skill_to_iterate.value.name):
                    assert (skill_to_iterate is None) or (skill.value.name != skill_to_iterate.value.name)
                    skill_to_iterate = skill

        assert skill_to_iterate is not None

        ret = []
        total_states = len(skill_to_iterate.value.states)
        for level in range(total_states):
            new_skill_states_dict = skill_states_dict.copy()
            new_skill_states_dict[skill_to_iterate] = level
            ret.append(lookup_from_skills(weapon, skills_dict, new_skill_states_dict, augments_list))

    else:
        # We terminate recursion here.

        weapon_augments = weapon.augmentation_scheme.value(weapon.rarity)
        # TODO: Constructor as the enum value looks really fucking weird.

        if weapon.augmentation_scheme is WeaponAugmentationScheme.ICEBORNE:
            for augment in augments_list:
                assert isinstance(augment, tuple) and (len(augment) == 2)
                assert isinstance(augment[0], IBWeaponAugmentType) and isinstance(augment[1], int)
                weapon_augments.update_with_option(augment)

        maximum_sharpness_values = weapon.maximum_sharpness
        from_skills = calculate_skills_contribution(
                skills_dict,
                skill_states_dict,
                maximum_sharpness_values,
                weapon.is_raw
            )
        from_augments = weapon_augments.calculate_contribution()

        handicraft_level = from_skills.handicraft_level
        sharpness_values, highest_sharpness_level = _actual_sharpness_level_values(maximum_sharpness_values, handicraft_level)

        item_attack_power = POWERCHARM_ATTACK_POWER + POWERTALON_ATTACK_POWER

        kwargs = {}
        kwargs["weapon_raw"]                 = weapon.attack
        kwargs["weapon_type"]                = weapon.type
        kwargs["weapon_affinity_percentage"] = weapon.affinity
        kwargs["added_raw"]                  = from_skills.added_attack_power + item_attack_power
        kwargs["added_affinity_percentage"]  = from_skills.added_raw_affinity + from_augments.added_raw_affinity
        kwargs["raw_sharpness_modifier"]     = RAW_SHARPNESS_MODIFIERS[highest_sharpness_level]
        kwargs["raw_crit_multiplier"]        = from_skills.raw_critical_multiplier

        kwargs["weapon_raw_multiplier"] = from_skills.weapon_base_attack_power_multiplier
        kwargs["augment_added_raw"]     = from_augments.added_attack_power

        ret = LookupFromSkillsValues(
                efr               = _calculate_efr(**kwargs),
                sharpness_values  = sharpness_values,

                skills = skills_dict,
            )

    return ret



BuildValues = namedtuple(
    "BuildValues",
    [
        "efr",
        "sharpness_values",

        "skills",

        "usable_slots",
    ],
)
# Input looks like this:
#
#       weapon_id = "ACID_SHREDDER_II"
#
#       armour_dict = {
#           ArmourSlot.HEAD:  ("Teostra",      ArmourDiscriminator.HIGH_RANK,   ArmourVariant.HR_GAMMA),
#           ArmourSlot.CHEST: ("Damascus",     ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
#           ArmourSlot.ARMS:  ("Teostra",      ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
#           ArmourSlot.WAIST: ("Teostra",      ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
#           ArmourSlot.LEGS:  ("Yian Garuga",  ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
#       }
#
#       skill_states_dict = {
#           Skill.AGITATOR: 1,
#           Skill.PEAK_PERFORMANCE: 1,
#       }
#
#       augments_list = [
#           (IBWeaponAugmentType.HEALTH_REGEN,      1),
#           (IBWeaponAugmentType.AFFINITY_INCREASE, 1),
#       ]
#
def lookup_from_gear(weapon_id, armour_dict, charm_id, decorations_list_or_dict, skill_states_dict, augments_list):
    assert isinstance(weapon_id, str)
    weapon = weapon_db[weapon_id]
    armour_contribution = calculate_armour_contribution(armour_dict)
    charm = charms_db[charm_id] if (charm_id is not None) else None
    decorations_counter = Counter(decorations_list_or_dict)

    slots_available_counter = Counter(list(weapon.slots) + list(armour_contribution.decoration_slots))

    # For debugging, we can first determine if the decorations fit in the selected gear.
    # (We should be able to rely on inputs here.
    # Both slots_*_counter are in the format {slot_size: count}
    if __debug__:
        tmp_slots_available_counter = copy(Counter(list(weapon.slots) + list(armour_contribution.decoration_slots)))
        assert len(tmp_slots_available_counter) <= 4 # We only have slot sizes 1 to 4.

        slots_used_counter = Counter()
        for (deco, total) in decorations_counter.items():
            slots_used_counter.update([deco.value.slot_size] * total)

        for (deco_size, n) in slots_used_counter.items():
            for usable_size in range(deco_size, 5):
                if usable_size in tmp_slots_available_counter:
                    if n <= tmp_slots_available_counter[usable_size]:
                        tmp_slots_available_counter[usable_size] -= n # we consume all the slots we can.
                        n = 0
                        break
                    else:
                        n -= tmp_slots_available_counter[usable_size]
                        tmp_slots_available_counter[usable_size] = 0
            if n > 0:
                raise ValueError(f"At least {n} more slots of at least size {deco_size} required.")

    # Now, we calculate the skills dictionary.

    # Armour regular skills
    skills_dict = armour_contribution.skills

    # Charm skills
    if charm is not None:
        charm_skills_dict = calculate_skills_dict_from_charm(charm, charm.max_level)
        for (skill, level) in charm_skills_dict.items():
            skills_dict[skill] += level

    # Decoration skills
    deco_skills_dict = calculate_decorations_skills_contribution(decorations_counter)
    for (skill, level) in deco_skills_dict.items():
        skills_dict[skill] += level

    # Armour set bonuses
    skills_from_set_bonuses = calculate_set_bonus_skills(armour_contribution.set_bonuses)
    if len(set(skills_dict) & set(skills_from_set_bonuses)) != 0:
        raise RuntimeError("We shouldn't be getting any mixing between regular skills and set bonuses here.")

    skills_dict.update(skills_from_set_bonuses)

    intermediate_results = lookup_from_skills(weapon, skills_dict, skill_states_dict, augments_list)

    def transform_results_recursively(obj):
        if isinstance(obj, list):
            return [transform_results_recursively(x) for x in obj]
        else:
            new_obj = BuildValues(
                    efr              = obj.efr,
                    sharpness_values = obj.sharpness_values,
                    
                    skills           = obj.skills,
                    
                    usable_slots     = slots_available_counter,
                )
            return new_obj
            
    return transform_results_recursively(intermediate_results)


def find_highest_efr_build():

    ##############################
    # STAGE 1: Basic Definitions #
    ##############################

    desired_weapon = WeaponClass.GREATSWORD

    efr_skills = [
        #Skill.AGITATOR,
        #Skill.ATTACK_BOOST,
        Skill.CRITICAL_BOOST,
        #Skill.CRITICAL_EYE,
        #Skill.NON_ELEMENTAL_BOOST,
        #Skill.HANDICRAFT,
        #Skill.PEAK_PERFORMANCE,
        #Skill.WEAKNESS_EXPLOIT
    ]

    full_skill_states = {
        Skill.AGITATOR: 1,
        Skill.PEAK_PERFORMANCE: 1,
        Skill.WEAKNESS_EXPLOIT: 2,
    }

    ############################
    # STAGE 2: Component Lists #
    ############################

    weapon_ids = [weapon_id for (weapon_id, weapon_info) in weapon_db.items() if weapon_info.type is desired_weapon]

    armour_pieces = defaultdict(list)
    for ((set_name, discrim), set_info) in armour_db.items():
        for (variant, variant_pieces) in set_info.variants.items():
            # We assume that within variant_pieces, if we don't have the full set of 5 slots,
            # the missing slots are just missing
            for (gear_slot, piece) in variant_pieces.items():
                armour_pieces[gear_slot].append((set_name, discrim, variant))
    #print("\n".join(str(k.name) for (k, v) in armour_pieces.items()))

    charm_ids = set()
    for skill in efr_skills:
        if skill in charms_indexed_by_skill:
            for charm_id in charms_indexed_by_skill[skill]:
                charm_ids.add(charm_id)
    if len(charm_ids) == 0:
        charm_ids = [None]
    else:
        charm_ids = list(charm_ids)
    #print(charm_ids)

    decorations = set()
    for deco in Decoration:
        for skill in efr_skills:
            if skill in deco.value.skills_dict:
                decorations.add(deco)
    decorations = list(decorations) # More efficient for later stages

    ####################
    # STAGE 3: Search! #
    ####################

    #def recursively_iterate_decos(decos_dict, index_into_decos_list):
    #    if index_into_decos_list == len(decorations):
    #        try:
    #            results = lookup_from_gear(weapon_id, current_armour, charm_id, modified_decos_dict, \
    #                            full_skill_states, [])
    #        except:
    #            return
    #    else:
    #        for n in range(10):
    #            modified_decos_dict = copy(decos_dict)
    #            decorations[index_into_decos_list]
    #            modified_decos_dict[decorations[index_into_decos_list]] = n
    #            recursively_iterate_decos(modified_decos_dict, index_into_decos_list + 1)

    #segments = len(weapon_ids) * len(armour_pieces[ArmourSlot.HEAD]) * len(armour_pieces[ArmourSlot.CHEST]) * \
    #            len(armour_pieces[ArmourSlot.ARMS])
    #segment_percentage = 1 / segments
    #current_segment_count = 0

    #for weapon_id in weapon_ids:
    #    for head in armour_pieces[ArmourSlot.HEAD]:
    #        for chest in armour_pieces[ArmourSlot.CHEST]:
    #            for arms in armour_pieces[ArmourSlot.ARMS]:
    #                for waist in armour_pieces[ArmourSlot.WAIST]:
    #                    for legs in armour_pieces[ArmourSlot.LEGS]:
    #                        for charm_id in charm_ids:
    #                            #current_segment_count += 1
    #                            print(f"Progress: another segment")
    #                            #print(f"Progress: {current_segment_count*segment_percentage*100}%")
    #                            current_armour = {
    #                                ArmourSlot.HEAD:  head,
    #                                ArmourSlot.CHEST: chest,
    #                                ArmourSlot.ARMS:  arms,
    #                                ArmourSlot.WAIST: waist,
    #                                ArmourSlot.LEGS:  legs,
    #                            }
    #                            recursively_iterate_decos({}, 0)

    def print_current_build():
        print(best_efr)
        print("   " + weapon_id)
        for (k, v) in curr_armour.items():
            print("   " + k.name + " : " + v[0] + " " + v[1].name + " " + v[2].name)

    best_efr = 0

    for weapon_id in weapon_ids:
        for head in armour_pieces[ArmourSlot.HEAD]:
            for chest in armour_pieces[ArmourSlot.CHEST]:
                for arms in armour_pieces[ArmourSlot.ARMS]:
                    for waist in armour_pieces[ArmourSlot.WAIST]:
                        for legs in armour_pieces[ArmourSlot.LEGS]:
                            for charm_id in charm_ids:
                                curr_decos = {}
                                #curr_skill_states = {}
                                curr_augments = []
                                curr_armour = {
                                    ArmourSlot.HEAD:  head,
                                    ArmourSlot.CHEST: chest,
                                    ArmourSlot.ARMS:  arms,
                                    ArmourSlot.WAIST: waist,
                                    ArmourSlot.LEGS:  legs,
                                }
                                results = lookup_from_gear(weapon_id, curr_armour, charm_id, \
                                                curr_decos, full_skill_states, curr_augments)

                                if results.efr > best_efr:
                                    best_efr = results.efr
                                    print_current_build()

    return

