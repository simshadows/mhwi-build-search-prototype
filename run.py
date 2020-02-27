#!/usr/bin/env python3
# -*- coding: ascii -*-

"""
Filename: run.py
Author:   contact@simshadows.com

The entrypoint for my Monster Hunter World Iceborne build optimization tool!

In this version, we assume each level under maximum Handicraft will subtract sharpness by 10 points.
"""

import sys

#from math import floor
from collections import namedtuple

from database_skills  import (Skill,
                              clipped_skills_defaultdict,
                              calculate_set_bonus_skills,
                              calculate_skills_contribution)
from database_weapons import (WeaponClass,
                              weapon_db,
                              IBWeaponAugmentType,
                              WeaponAugmentationScheme,
                              WeaponUpgradeScheme)
from database_armour  import (ArmourDiscriminator,
                              ArmourVariant,
                              ArmourSlot,
                              armour_db,
                              calculate_armour_contribution)
from database_misc    import (POWERCHARM_ATTACK_POWER,
                              POWERTALON_ATTACK_POWER)


# Corresponds to each level from red through to purple, in increasing-modifier order.
SHARPNESS_LEVEL_NAMES   = ("Red", "Orange", "Yellow", "Green", "Blue", "White", "Purple")
RAW_SHARPNESS_MODIFIERS = (0.5,   0.75,     1.0,      1.05,    1.2,    1.32,    1.39    )


def print_debugging_statistics():
    print("=== Application Statistics ===")
    print()
    print("Number of skills: " + str(len(list(Skill))))
    print("Total number of weapons: " + str(len(weapon_db)))
    print("\n==============================\n")
    return


# Returns both the values of the new sharpness bar, and the highest sharpness level.
# The new sharpness bar corresponds to the indices in RAW_SHARPNESS_LEVEL_MODIFIERS and SHARPNESS_LEVEL_NAMES.
# The highest sharpness level also corresponds to the same indices.
def actual_sharpness_level_values(weapon_maximum_sharpness, handicraft_level):
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


def calculate_efr(**kwargs):
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


BuildValues = namedtuple(
    "BuildValues",
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
        sharpness_values, highest_sharpness_level = actual_sharpness_level_values(maximum_sharpness_values, handicraft_level)

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

        ret = BuildValues(
                efr               = calculate_efr(**kwargs),
                sharpness_values  = sharpness_values,

                skills = skills_dict,
            )

    return ret


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
def lookup_from_gear(weapon_name, armour_dict, skill_states_dict, augments_list):
    assert isinstance(weapon_name, str)
    weapon = weapon_db[weapon_name]
    armour_contribution = calculate_armour_contribution(armour_dict)

    skills_dict = armour_contribution.skills # IMPORTANT: This is without set bonuses.

    skills_from_set_bonuses = calculate_set_bonus_skills(armour_contribution.set_bonuses)
    if len(set(skills_dict) & set(skills_from_set_bonuses)) != 0:
        raise RuntimeError("We shouldn't be getting any mixing between regular skills and set bonuses here.")

    skills_dict.update(skills_from_set_bonuses) # IMPORTANT: Now, we update the skill dictionary to include set bonuses.

    return lookup_from_skills(weapon, skills_dict, skill_states_dict, augments_list)


def search_command():
    raise NotImplementedError("search feature not yet implemented")


def lookup_command(weapon_name):

    armour_dict = {
        ArmourSlot.HEAD:  ("Teostra", ArmourDiscriminator.HIGH_RANK,   ArmourVariant.HR_GAMMA),
        ArmourSlot.CHEST: ("Teostra", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_ALPHA_PLUS),
        ArmourSlot.ARMS:  ("Teostra", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
        ArmourSlot.WAIST: ("Teostra", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
        ArmourSlot.LEGS:  ("Teostra", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_ALPHA_PLUS),
    }

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

    skill_states_dict = {
            #Skill.WEAKNESS_EXPLOIT: 2,
            #Skill.AGITATOR: 1,
            #Skill.PEAK_PERFORMANCE: 1,
        }

    augments_list = [
            (IBWeaponAugmentType.ATTACK_INCREASE,   1),
            #(IBWeaponAugmentType.AFFINITY_INCREASE, 1),
        ]
    
    results = lookup_from_gear(weapon_name, armour_dict, skill_states_dict, augments_list)
    sharpness_values = None
    efrs_strings = []

    # We're assuming all results returned operate on the same set of skills.
    representative_skills_dict = results[0].skills
    assert all(len(representative_skills_dict) == len(result.skills) for result in results)# Equal number of keys
    # TODO: Make a better assertion that is more strict on this.

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


# Super-simple unit testing. Will probably switch to a testing framework if I have complex needs.
def tests_passed():
    print("Running unit tests.\n")

    skills_dict = {} # Start with no skills
    skill_states_dict = {} # Start with no states
    augments_list = [] # Start with no augments
    weapon = weapon_db["Acid Shredder II"]

    # This function will leave skills_dict with the skill at max_level.
    def test_with_incrementing_skill(skill, max_level, expected_efrs):
        assert max_level == skill.value.limit
        assert len(expected_efrs) == (max_level + 1)

        for level in range(max_level + 1):
            skills_dict[skill] = level
            vals = lookup_from_skills(weapon, skills_dict, skill_states_dict, augments_list)
            if round(vals.efr) != round(expected_efrs[level]):
                raise ValueError(f"EFR value mismatch for skill level {level}. Got EFR = {vals.efr}.")
        return

    print("Incrementing Handicraft.")
    test_with_incrementing_skill(Skill.HANDICRAFT, 5, [366.00, 366.00, 366.00, 402.60, 402.60, 423.95])
    # We now have full Handicraft.
    print("Incrementing Critical Boost with zero Affinity.")
    test_with_incrementing_skill(Skill.CRITICAL_BOOST, 3, [423.95, 423.95, 423.95, 423.95])
    # We now have full Handicraft and Critical Boost.

    weapon = weapon_db["Royal Venus Blade"]

    print("Incrementing Critical Boost with non-zero Affinity.")
    test_with_incrementing_skill(Skill.CRITICAL_BOOST, 3, [411.01, 413.98, 416.95, 419.92])
    print("Incrementing Critical Eye.")
    test_with_incrementing_skill(Skill.CRITICAL_EYE, 7, [419.92, 427.84, 435.77, 443.69, 451.61, 459.53, 467.46, 483.30])
    # We now have full Handicraft, Critical Boost, and Critical Eye.
    print("Incrementing Attack Boost.")
    test_with_incrementing_skill(Skill.ATTACK_BOOST, 7, [483.30, 488.39, 493.48, 498.57, 511.91, 517.08, 522.25, 527.42])
    # We now have full Handicraft, Critical Boost, Critical Eye, and Attack Boost.

    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 2,
        }

    print("Incrementing Weakness Exploit on a wounded part.")
    test_with_incrementing_skill(Skill.WEAKNESS_EXPLOIT, 3, [527.42, 552.94, 578.46, 595.48])
    # Last EFR should exceed 100% Affinity.

    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 1,
        }

    print("Incrementing Weakness Exploit on a weak point.")
    test_with_incrementing_skill(Skill.WEAKNESS_EXPLOIT, 3, [527.42, 544.44, 552.94, 578.46])

    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 0,
        }

    print("Incrementing Weakness Exploit on a non-weak point.")
    test_with_incrementing_skill(Skill.WEAKNESS_EXPLOIT, 3, [527.42]*4)
    # We now have full Handicraft, Critical Boost, Critical Eye, Attack Boost, and Weakness Exploit.

    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 1,
            Skill.AGITATOR        : 0,
        }

    print("Incrementing Agitator when monster is not enraged.")
    test_with_incrementing_skill(Skill.AGITATOR, 5, [578.46]*6)

    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 1,
            Skill.AGITATOR        : 1,
        }

    print("Incrementing Agitator when monster is enraged.")
    test_with_incrementing_skill(Skill.AGITATOR, 5, [578.46, 594.64, 602.31, 613.52, 621.24, 634.40])
    # We now have full Handicraft, Critical Boost, Critical Eye, Attack Boost, Weakness Exploit, and Agitator.
    
    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 2,
            Skill.AGITATOR        : 1,
            Skill.PEAK_PERFORMANCE: 1,
        }

    print("Incrementing Peak Performance.")
    test_with_incrementing_skill(Skill.PEAK_PERFORMANCE, 3, [634.40, 644.13, 653.86, 673.32])
    print("Incrementing Non-elemental Boost with a raw weapon.")
    test_with_incrementing_skill(Skill.NON_ELEMENTAL_BOOST, 1, [673.32, 700.56]) # Game does weird rounding.

    weapon = weapon_db["Immovable Dharma"]

    skills_dict = {
            Skill.CRITICAL_EYE       : 4,
            Skill.ATTACK_BOOST       : 3,
            Skill.PEAK_PERFORMANCE   : 3,
            Skill.AGITATOR           : 2,
            Skill.WEAKNESS_EXPLOIT   : 1,
        }
    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 1,
            Skill.AGITATOR        : 1,
            Skill.PEAK_PERFORMANCE: 1,
        }
    # Obtained with just:
    #   Head:  Kaiser Crown Gamma
    #   Chest: Rex Roar Mail Beta+
    #   Hands: Ruinous Vambraces Beta+
    #   Waist: (anything)
    #   Legs:  Garuga Greaves Beta+

    print("Incrementing Non-elemental Boost with a raw weapon again.")
    test_with_incrementing_skill(Skill.NON_ELEMENTAL_BOOST, 1, [476.59, 496.68])

    weapon = weapon_db["Great Demon Rod"]

    print("Incrementing Non-elemental Boost with an elemental weapon.")
    test_with_incrementing_skill(Skill.NON_ELEMENTAL_BOOST, 1, [456.12, 456.12])

    weapon = weapon_db["Royal Venus Blade"]

    print("Testing without augments.")
    test_with_incrementing_skill(Skill.NON_ELEMENTAL_BOOST, 1, [478.17, 498.96])

    augments_list = [
            (IBWeaponAugmentType.ATTACK_INCREASE, 1),
        ]

    print("Testing with Attack augment.")
    test_with_incrementing_skill(Skill.NON_ELEMENTAL_BOOST, 1, [485.60, 506.39])

    augments_list = [
            (IBWeaponAugmentType.ATTACK_INCREASE,   1),
            (IBWeaponAugmentType.AFFINITY_INCREASE, 1),
        ]

    print("Testing with Attack and Affinity augment.")
    test_with_incrementing_skill(Skill.NON_ELEMENTAL_BOOST, 1, [496.39, 517.64])

    augments_list = [
            (IBWeaponAugmentType.AFFINITY_INCREASE, 1),
            (IBWeaponAugmentType.AFFINITY_INCREASE, 2),
        ]

    print("Testing with two Affinity augments.")
    test_with_incrementing_skill(Skill.NON_ELEMENTAL_BOOST, 1, [494.11, 515.59])

    def check_efr(expected_efr):
        results = lookup_from_gear(weapon_name, armour_dict, skill_states_dict, augments_list)
        if round(results.efr) != round(expected_efr):
            raise ValueError(f"EFR value mismatch. Expected {expected_efr}. Got {results.efr}.")

    def check_skill(expected_skill, expected_level):
        results = lookup_from_gear(weapon_name, armour_dict, skill_states_dict, augments_list)
        if Skill[expected_skill] not in results.skills:
            raise ValueError(f"Skill {expected_skill} not present.")
        returned_level = results.skills[Skill[expected_skill]]
        if returned_level != expected_level:
            raise ValueError(f"Skill level mismatch for {expected_skill}. Expected {expected_level}. Got {returned_level}.")

    weapon_name = "Royal Venus Blade"

    armour_dict = {
            ArmourSlot.HEAD:  ("Teostra", ArmourDiscriminator.HIGH_RANK,   ArmourVariant.HR_GAMMA),
            ArmourSlot.CHEST: ("Teostra", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_ALPHA_PLUS),
            ArmourSlot.ARMS:  ("Teostra", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
            ArmourSlot.WAIST: ("Teostra", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
            ArmourSlot.LEGS:  ("Teostra", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_ALPHA_PLUS),
        }

    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 2,
        }

    augments_list = [
            (IBWeaponAugmentType.ATTACK_INCREASE,   1),
            #(IBWeaponAugmentType.AFFINITY_INCREASE, 1),
        ]

    print("Testing with a bunch of varying Teostra pieces from different ranks.")
    check_efr(421.08)
    check_skill("MASTERS_TOUCH", 1) # Set Bonus
    check_skill("BLAST_ATTACK", 4)
    check_skill("LATENT_POWER", 3)
    check_skill("CRITICAL_EYE", 2)
    check_skill("SPECIAL_AMMO_BOOST", 2)
    check_skill("WEAKNESS_EXPLOIT", 1)
    check_skill("HEAT_GUARD", 1)

    armour_dict = {
            ArmourSlot.HEAD:  ("Velkhana", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_ALPHA_PLUS),
            ArmourSlot.CHEST: ("Velkhana", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
            ArmourSlot.ARMS:  ("Teostra",  ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
            ArmourSlot.WAIST: ("Velkhana", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
            ArmourSlot.LEGS:  ("Velkhana", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
        }

    print("Testing with four Velkhana pieces.")
    check_efr(411.51)
    check_skill("CRITICAL_ELEMENT", 1) # Set Bonus
    check_skill("FROSTCRAFT", 1) # Set Bonus
    check_skill("DIVINE_BLESSING", 2)
    check_skill("QUICK_SHEATH", 2)
    check_skill("CRITICAL_DRAW", 2)
    check_skill("COALESCENCE", 1)
    check_skill("WEAKNESS_EXPLOIT", 1)
    check_skill("HEAT_GUARD", 1)
    check_skill("FLINCH_FREE", 1)

    print("\nUnit tests are all passed.")
    print("\n==============================\n")
    return True


def run():
    print_debugging_statistics()
    assert tests_passed()

    # Determine whether to run in search or lookup mode.
    if len(sys.argv) > 1:
        weapon_name = sys.argv[1]
        lookup_command(weapon_name)
    else:
        search()
    return 0


if __name__ == '__main__':
    sys.exit(run())

