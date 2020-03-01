#!/usr/bin/env python3
# -*- coding: ascii -*-

"""
Filename: unit_testing.py
Author:   contact@simshadows.com
"""

import sys
from copy import copy

#from math import floor
from collections import namedtuple, defaultdict, Counter

from query_and_search import lookup_from_skills, lookup_from_gear

from database_skills      import (Skill,
                                 clipped_skills_defaultdict,
                                 calculate_set_bonus_skills,
                                 calculate_skills_contribution)
from database_weapons     import (WeaponClass,
                                 weapon_db,
                                 IBWeaponAugmentType,
                                 WeaponAugmentationScheme,
                                 IBCWeaponUpgradeType,
                                 WeaponUpgradeScheme)
from database_armour      import (ArmourDiscriminator,
                                 ArmourVariant,
                                 ArmourSlot,
                                 armour_db,
                                 _armour_piece_supercedes, # For testing.
                                 calculate_armour_contribution)
from database_charms      import (charms_db,
                                 charms_indexed_by_skill,
                                 calculate_skills_dict_from_charm)
from database_decorations import (Decoration,
                                 calculate_decorations_skills_contribution)
from database_misc        import (POWERCHARM_ATTACK_POWER,
                                  POWERTALON_ATTACK_POWER)


def run_tests():
    print("Running unit tests.")

    _run_tests_lookup()
    _run_tests_armour_pruning()

    print("\nUnit tests are all passed.")
    print("\n==============================\n")
    return


# Super-simple unit testing. Will probably switch to a testing framework if I have complex needs.
def _run_tests_lookup():
    print()

    skills_dict = {} # Start with no skills
    skill_states_dict = {} # Start with no states
    weapon_augments_config = [] # Start with no augments
    weapon_upgrades_config = None # Start with no upgrades
    weapon = weapon_db["ACID_SHREDDER_II"]
    decorations_list = [] # Start with no decorations
    charm_id = None

    # This function will leave skills_dict with the skill at max_level.
    def test_with_incrementing_skill(skill, max_level, expected_efrs):
        assert max_level == skill.value.limit
        assert len(expected_efrs) == (max_level + 1)

        for level in range(max_level + 1):
            skills_dict[skill] = level
            vals = lookup_from_skills(weapon, skills_dict, skill_states_dict, weapon_augments_config, weapon_upgrades_config)
            if round(vals.efr) != round(expected_efrs[level]):
                raise ValueError(f"EFR value mismatch for skill level {level}. Got EFR = {vals.efr}.")
        return

    print("Incrementing Handicraft.")
    test_with_incrementing_skill(Skill.HANDICRAFT, 5, [366.00, 366.00, 366.00, 402.60, 402.60, 423.95])
    # We now have full Handicraft.
    print("Incrementing Critical Boost with zero Affinity.")
    test_with_incrementing_skill(Skill.CRITICAL_BOOST, 3, [423.95, 423.95, 423.95, 423.95])
    # We now have full Handicraft and Critical Boost.

    weapon = weapon_db["ROYAL_VENUS_BLADE"]

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

    weapon = weapon_db["IMMOVABLE_DHARMA"]

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

    weapon = weapon_db["GREAT_DEMON_ROD"]

    print("Incrementing Non-elemental Boost with an elemental weapon.")
    test_with_incrementing_skill(Skill.NON_ELEMENTAL_BOOST, 1, [456.12, 456.12])

    weapon = weapon_db["ROYAL_VENUS_BLADE"]

    print("Testing without augments.")
    test_with_incrementing_skill(Skill.NON_ELEMENTAL_BOOST, 1, [478.17, 498.96])

    weapon_augments_config = [
            (IBWeaponAugmentType.ATTACK_INCREASE, 1),
        ]

    print("Testing with Attack augment.")
    test_with_incrementing_skill(Skill.NON_ELEMENTAL_BOOST, 1, [485.60, 506.39])

    weapon_augments_config = [
            (IBWeaponAugmentType.ATTACK_INCREASE,   1),
            (IBWeaponAugmentType.AFFINITY_INCREASE, 1),
        ]

    print("Testing with Attack and Affinity augment.")
    test_with_incrementing_skill(Skill.NON_ELEMENTAL_BOOST, 1, [496.39, 517.64])

    weapon_augments_config = [
            (IBWeaponAugmentType.AFFINITY_INCREASE, 2),
        ]

    print("Testing with two Affinity augments.")
    test_with_incrementing_skill(Skill.NON_ELEMENTAL_BOOST, 1, [494.11, 515.59])

    def check_efr(expected_efr):
        results = lookup_from_gear(weapon_name, armour_dict, charm_id, decorations_list, skill_states_dict, \
                                            weapon_augments_config, weapon_upgrades_config)
        if round(results.efr) != round(expected_efr):
            raise ValueError(f"EFR value mismatch. Expected {expected_efr}. Got {results.efr}.")

    def check_skill(expected_skill, expected_level):
        results = lookup_from_gear(weapon_name, armour_dict, charm_id, decorations_list, skill_states_dict, \
                                            weapon_augments_config, weapon_upgrades_config)
        if Skill[expected_skill] not in results.skills:
            raise ValueError(f"Skill {expected_skill} not present.")
        returned_level = results.skills[Skill[expected_skill]]
        if returned_level != expected_level:
            raise ValueError(f"Skill level mismatch for {expected_skill}. Expected {expected_level}. Got {returned_level}.")

    weapon_name = "ROYAL_VENUS_BLADE"

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

    weapon_augments_config = [
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

    decorations_list = ([Decoration.EXPERT] * 6) + ([Decoration.ATTACK] * 4) + [Decoration.TENDERIZER]

    print("Testing with full size-1 decorations.")
    check_efr(478.37)
    check_skill("CRITICAL_ELEMENT", 1) # Set Bonus
    check_skill("FROSTCRAFT", 1) # Set Bonus
    check_skill("DIVINE_BLESSING", 2)
    check_skill("QUICK_SHEATH", 2)
    check_skill("CRITICAL_DRAW", 2)
    check_skill("COALESCENCE", 1)
    check_skill("WEAKNESS_EXPLOIT", 2)
    check_skill("HEAT_GUARD", 1)
    check_skill("FLINCH_FREE", 1)
    check_skill("CRITICAL_EYE", 6)
    check_skill("ATTACK_BOOST", 4)

    decorations_list.append(Decoration.ATTACK)

    if __debug__:
        print("Testing with just one more size-1 jewel to see if it catches the error.")
        try:
            check_efr(0)
        except:
            pass
        else:
            raise RuntimeError("Test failed. Expected an exception here.")

    decorations_list = ([Decoration.CHALLENGER_X2] * 2) + ([Decoration.COMPOUND_TENDERIZER_VITALITY] * 2)

    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 2,
            Skill.AGITATOR:         1,
        }

    print("Testing with four size-4 decorations.")
    check_efr(476.63)
    check_skill("CRITICAL_ELEMENT", 1) # Set Bonus
    check_skill("FROSTCRAFT", 1) # Set Bonus
    check_skill("DIVINE_BLESSING", 2)
    check_skill("QUICK_SHEATH", 2)
    check_skill("CRITICAL_DRAW", 2)
    check_skill("COALESCENCE", 1)
    check_skill("WEAKNESS_EXPLOIT", 3)
    check_skill("HEAT_GUARD", 1)
    check_skill("FLINCH_FREE", 1)
    check_skill("AGITATOR", 4)
    check_skill("HEALTH_BOOST", 2)

    decorations_list.append(Decoration.DEFENSE_X3)

    if __debug__:
        print("Testing with just one more size-4 jewel to see if it catches the error.")
        try:
            check_efr(0)
        except:
            pass
        else:
            raise RuntimeError("Test failed. Expected an exception here.")

    decorations_list = ([Decoration.CHALLENGER_X2] * 2) + ([Decoration.COMPOUND_TENDERIZER_VITALITY] * 2)

    skill_states_dict = {
            Skill.AGITATOR: 1,
        }

    print("Testing to see if one indeterminate stateful skill get iterated.")
    results = lookup_from_gear(weapon_name, armour_dict, charm_id, decorations_list, skill_states_dict, \
                                            weapon_augments_config, weapon_upgrades_config)
    if len(results) != 3:
        raise ValueError("Results should've returned a list of 3 items (since Weakness Exploit is the only stateful skill).")

    weapon_name = "JAGRAS_DEATHCLAW_II"

    armour_dict = {
            # Gonna keep it simple. All Teostra Alpha+.
            ArmourSlot.HEAD:  ("Teostra", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_ALPHA_PLUS),
            ArmourSlot.CHEST: ("Teostra", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_ALPHA_PLUS),
            ArmourSlot.ARMS:  ("Teostra", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_ALPHA_PLUS),
            ArmourSlot.WAIST: ("Teostra", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_ALPHA_PLUS),
            ArmourSlot.LEGS:  ("Teostra", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_ALPHA_PLUS),
        }

    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 2,
        }

    weapon_augments_config = [
            (IBWeaponAugmentType.ATTACK_INCREASE,   1),
        ]

    weapon_upgrades_config = None # Start with no upgrades

    decorations_list = [
        Decoration.ELEMENTLESS,
    ]

    charm_id = "CRITICAL_CHARM"

    print("Testing without weapon upgrades.")
    check_efr(467.98)

    weapon_augments_config = [
            (IBWeaponAugmentType.ATTACK_INCREASE,   2),
        ]

    check_efr(477.56)

    weapon_augments_config = [
            (IBWeaponAugmentType.ATTACK_INCREASE,   2),
            (IBWeaponAugmentType.AFFINITY_INCREASE, 2),
        ]

    check_efr(498.28)

    print("Testing with weapon upgrades.")

    weapon_upgrades_config = [
            IBCWeaponUpgradeType.ATTACK,
            IBCWeaponUpgradeType.ATTACK,
            IBCWeaponUpgradeType.ATTACK,
            IBCWeaponUpgradeType.ATTACK,
            IBCWeaponUpgradeType.ATTACK,
            IBCWeaponUpgradeType.ATTACK,
        ]

    check_efr(508.28)

    weapon_upgrades_config = [
            IBCWeaponUpgradeType.AFFINITY,
            IBCWeaponUpgradeType.AFFINITY,
            IBCWeaponUpgradeType.AFFINITY,
            IBCWeaponUpgradeType.AFFINITY,
            IBCWeaponUpgradeType.AFFINITY,
            IBCWeaponUpgradeType.ATTACK,
        ]

    check_efr(506.88)

    weapon_upgrades_config = [
            IBCWeaponUpgradeType.AFFINITY,
            IBCWeaponUpgradeType.ATTACK,
            IBCWeaponUpgradeType.AFFINITY,
            IBCWeaponUpgradeType.ATTACK,
            IBCWeaponUpgradeType.AFFINITY,
            IBCWeaponUpgradeType.ATTACK,
        ]

    check_efr(507.47)

    return True


def _run_tests_armour_pruning():
    print()

    def test_supercedes_common(gear_slot, p1_set_name, p1_discrim, p1_variant, p2_set_name, p2_discrim, p2_variant, \
                                                    p1_preferred, **kwargs):
        gear_slot = ArmourSlot[gear_slot]
        p1_discrim = ArmourDiscriminator[p1_discrim]
        p2_discrim = ArmourDiscriminator[p2_discrim]
        p1_variant = ArmourVariant[p1_variant]
        p2_variant = ArmourVariant[p2_variant]

        p1_set = armour_db[(p1_set_name, p1_discrim)]
        p2_set = armour_db[(p2_set_name, p2_discrim)]

        p1 = p1_set.variants[p1_variant][gear_slot]
        p2 = p2_set.variants[p2_variant][gear_slot]

        p1_set_bonus = p1_set.set_bonus
        p2_set_bonus = p2_set.set_bonus
        return _armour_piece_supercedes(p1, p1_set_bonus, p2, p2_set_bonus, p1_preferred, **kwargs)

    def test_supercedes(*args, **kwargs):
        result = test_supercedes_common(*args, **kwargs)
        if not result:
            raise ValueError("_armour_piece_supercedes() test failed. Arguments: " + str(args) + " " + str(kwargs))
        return

    def test_not_supercedes(*args, **kwargs):
        result = test_supercedes_common(*args, **kwargs)
        if result:
            raise ValueError("_armour_piece_supercedes() test failed. Arguments: " + str(args) + " " + str(kwargs))
        return

    def test_not_supercedes_in_reverse(*args, **kwargs):
        args = (args[0], args[4], args[5], args[6], args[1], args[2], args[3], args[7])
        test_not_supercedes(*args, **kwargs)
        return

    print("Checking that (head) Kaiser Beta always supercedes Kaiser Alpha.")
    test_supercedes("HEAD", "Teostra", "HIGH_RANK", "HR_BETA", "Teostra", "HIGH_RANK", "HR_ALPHA", True)
    test_supercedes("HEAD", "Teostra", "HIGH_RANK", "HR_BETA", "Teostra", "HIGH_RANK", "HR_ALPHA", False)
    test_not_supercedes_in_reverse("HEAD", "Teostra", "HIGH_RANK", "HR_BETA", "Teostra", "HIGH_RANK", "HR_ALPHA", True)
    test_not_supercedes_in_reverse("HEAD", "Teostra", "HIGH_RANK", "HR_BETA", "Teostra", "HIGH_RANK", "HR_ALPHA", False)

    print("Checking that (head) Kaiser Beta+ always supercedes Kaiser Alpha.")
    test_supercedes("HEAD", "Teostra", "MASTER_RANK", "MR_BETA_PLUS", "Teostra", "HIGH_RANK", "HR_ALPHA", True)
    test_supercedes("HEAD", "Teostra", "MASTER_RANK", "MR_BETA_PLUS", "Teostra", "HIGH_RANK", "HR_ALPHA", False)
    test_not_supercedes_in_reverse("HEAD", "Teostra", "MASTER_RANK", "MR_BETA_PLUS", "Teostra", "HIGH_RANK", "HR_ALPHA", True)
    test_not_supercedes_in_reverse("HEAD", "Teostra", "MASTER_RANK", "MR_BETA_PLUS", "Teostra", "HIGH_RANK", "HR_ALPHA", False)

    print("Checking that (head) Kaiser Beta+ never supercedes Kaiser Alpha.")
    test_not_supercedes("HEAD", "Teostra", "MASTER_RANK", "MR_BETA_PLUS", "Teostra", "HIGH_RANK", "HR_GAMMA", True)
    test_not_supercedes("HEAD", "Teostra", "MASTER_RANK", "MR_BETA_PLUS", "Teostra", "HIGH_RANK", "HR_GAMMA", False)
    test_not_supercedes_in_reverse("HEAD", "Teostra", "MASTER_RANK", "MR_BETA_PLUS", "Teostra", "HIGH_RANK", "HR_GAMMA", True)
    test_not_supercedes_in_reverse("HEAD", "Teostra", "MASTER_RANK", "MR_BETA_PLUS", "Teostra", "HIGH_RANK", "HR_GAMMA", False)

    print("Checking that (legs) Garuga Beta+ never supercedes Garuga Alpha+, even when filtering out Piercing Shots.")
    test_not_supercedes("LEGS", "Yian Garuga", "MASTER_RANK", "MR_BETA_PLUS", "Yian Garuga", "MASTER_RANK", "MR_ALPHA_PLUS", \
                                True, skill_subset={Skill.CRITICAL_EYE,})
    test_not_supercedes("LEGS", "Yian Garuga", "MASTER_RANK", "MR_BETA_PLUS", "Yian Garuga", "MASTER_RANK", "MR_ALPHA_PLUS", \
                                False, skill_subset={Skill.CRITICAL_EYE,})
    test_not_supercedes_in_reverse("LEGS", "Yian Garuga", "MASTER_RANK", "MR_BETA_PLUS", "Yian Garuga", "MASTER_RANK", \
                                    "MR_ALPHA_PLUS", True, skill_subset={Skill.CRITICAL_EYE,})
    test_not_supercedes_in_reverse("LEGS", "Yian Garuga", "MASTER_RANK", "MR_BETA_PLUS", "Yian Garuga", "MASTER_RANK", \
                                    "MR_ALPHA_PLUS", False, skill_subset={Skill.CRITICAL_EYE,})

    return True


if __name__ == '__main__':
    run_tests()
    sys.exit(0)

