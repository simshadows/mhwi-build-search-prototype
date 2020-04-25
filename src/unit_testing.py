# -*- coding: ascii -*-

"""
Filename: unit_testing.py
Author:   contact@simshadows.com
"""

import time
import sys
import logging
from copy import copy

from collections import namedtuple, defaultdict, Counter

from .builds       import (Build,
                          lookup_from_skills,
                          lookup_from_skills_multiple_states)
from .search       import _generate_deco_additions
from .utils        import subtract_deco_slots

from .database_armour      import (ArmourDiscriminator,
                                  ArmourVariant,
                                  ArmourSlot,
                                  armour_db)
from .database_charms      import (charms_db,
                                  charms_indexed_by_skill)
from .database_decorations import Decoration
from .database_misc        import (POWERCHARM_ATTACK_POWER,
                                  POWERTALON_ATTACK_POWER)
from .database_skills      import Skill
from .database_weapons     import (WeaponAugmentationScheme,
                                  WeaponUpgradeScheme,
                                  WeaponClass,
                                  weapon_db)

from .query_armour      import (_armour_piece_supercedes, # For testing.
                               calculate_armour_contribution)
from .query_charms      import calculate_skills_dict_from_charm
from .query_decorations import calculate_decorations_skills_contribution
from .query_skills      import (clipped_skills_defaultdict,
                               calculate_set_bonus_skills,
                               calculate_skills_contribution)
from .query_weapons     import (WeaponAugmentTracker,
                               IBWeaponAugmentType,
                               WeaponUpgradeTracker,
                               IBCWeaponUpgradeType,
                               SafiWeaponStandardUpgradeType,
                               SafiWeaponSetBonusUpgradeType)


logger = logging.getLogger(__name__)


def run_tests():
    logger.info("Running unit tests.")

    _run_tests_lookup()
    _run_tests_armour_pruning()
    _run_tests_serializing()
    _run_tests_deco_list_generation()

    logger.info("")
    logger.info("All unit tests passed.")
    logger.info("")
    logger.info("==============================")
    logger.info("")
    return


# Super-simple unit testing. Will probably switch to a testing framework if I have complex needs.
def _run_tests_lookup():
    logger.info("")

    skills_dict = {} # Start with no skills
    skill_states_dict = {} # Start with no states
    weapon_augments_config = [] # Start with no augments
    weapon_upgrades_config = None # Start with no upgrades
    weapon = weapon_db["ACID_SHREDDER_II"]
    decorations_list = [] # Start with no decorations
    charm = None

    # This function will leave skills_dict with the skill at max_level.
    def test_with_incrementing_skill(skill, max_level, expected_efrs):
        assert max_level == skill.value.limit
        assert len(expected_efrs) == (max_level + 1)

        for level in range(max_level + 1):
            skills_dict[skill] = level
            weapon_augments_tracker = WeaponAugmentTracker.get_instance(weapon)
            weapon_augments_tracker.update_with_config(weapon_augments_config)
            weapon_upgrades_tracker = WeaponUpgradeTracker.get_instance(weapon)
            weapon_upgrades_tracker.update_with_config(weapon_upgrades_config)
            result = lookup_from_skills(weapon, skills_dict, skill_states_dict, weapon_augments_tracker, weapon_upgrades_tracker)
            if round(result.efr) != round(expected_efrs[level]):
                raise ValueError(f"EFR value mismatch for skill level {level}. Got EFR = {result.efr}.")
        return

    logger.info("Incrementing Handicraft.")
    test_with_incrementing_skill(Skill.HANDICRAFT, 5, [366.00, 366.00, 366.00, 402.60, 402.60, 423.95])
    # We now have full Handicraft.
    logger.info("Incrementing Critical Boost with zero Affinity.")
    test_with_incrementing_skill(Skill.CRITICAL_BOOST, 3, [423.95, 423.95, 423.95, 423.95])
    # We now have full Handicraft and Critical Boost.

    weapon = weapon_db["ROYAL_VENUS_BLADE"]

    logger.info("Incrementing Critical Boost with non-zero Affinity.")
    test_with_incrementing_skill(Skill.CRITICAL_BOOST, 3, [411.01, 413.98, 416.95, 419.92])
    logger.info("Incrementing Critical Eye.")
    test_with_incrementing_skill(Skill.CRITICAL_EYE, 7, [419.92, 427.84, 435.77, 443.69, 451.61, 459.53, 467.46, 483.30])
    # We now have full Handicraft, Critical Boost, and Critical Eye.
    logger.info("Incrementing Attack Boost.")
    test_with_incrementing_skill(Skill.ATTACK_BOOST, 7, [483.30, 488.39, 493.48, 498.57, 511.91, 517.08, 522.25, 527.42])
    # We now have full Handicraft, Critical Boost, Critical Eye, and Attack Boost.

    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 2,
        }

    logger.info("Incrementing Weakness Exploit on a wounded part.")
    test_with_incrementing_skill(Skill.WEAKNESS_EXPLOIT, 3, [527.42, 552.94, 578.46, 595.48])
    # Last EFR should exceed 100% Affinity.

    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 1,
        }

    logger.info("Incrementing Weakness Exploit on a weak point.")
    test_with_incrementing_skill(Skill.WEAKNESS_EXPLOIT, 3, [527.42, 544.44, 552.94, 578.46])

    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 0,
        }

    logger.info("Incrementing Weakness Exploit on a non-weak point.")
    test_with_incrementing_skill(Skill.WEAKNESS_EXPLOIT, 3, [527.42]*4)
    # We now have full Handicraft, Critical Boost, Critical Eye, Attack Boost, and Weakness Exploit.

    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 1,
            Skill.AGITATOR        : 0,
        }

    logger.info("Incrementing Agitator when monster is not enraged.")
    test_with_incrementing_skill(Skill.AGITATOR, 5, [578.46]*6)

    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 1,
            Skill.AGITATOR        : 1,
        }

    logger.info("Incrementing Agitator when monster is enraged.")
    test_with_incrementing_skill(Skill.AGITATOR, 5, [578.46, 594.64, 602.31, 613.52, 621.24, 634.40])
    # We now have full Handicraft, Critical Boost, Critical Eye, Attack Boost, Weakness Exploit, and Agitator.
    
    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 2,
            Skill.AGITATOR        : 1,
            Skill.PEAK_PERFORMANCE: 1,
        }

    logger.info("Incrementing Peak Performance.")
    test_with_incrementing_skill(Skill.PEAK_PERFORMANCE, 3, [634.40, 644.13, 653.86, 673.32])
    logger.info("Incrementing Non-elemental Boost with a raw weapon.")
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

    logger.info("Incrementing Non-elemental Boost with a raw weapon again.")
    test_with_incrementing_skill(Skill.NON_ELEMENTAL_BOOST, 1, [476.59, 496.68])

    weapon = weapon_db["GREAT_DEMON_ROD"]

    logger.info("Incrementing Non-elemental Boost with an elemental weapon.")
    test_with_incrementing_skill(Skill.NON_ELEMENTAL_BOOST, 1, [456.12, 456.12])

    weapon = weapon_db["ROYAL_VENUS_BLADE"]

    logger.info("Testing without augments.")
    test_with_incrementing_skill(Skill.NON_ELEMENTAL_BOOST, 1, [478.17, 498.96])

    weapon_augments_config = [
            (IBWeaponAugmentType.ATTACK_INCREASE, 1),
        ]

    logger.info("Testing with Attack augment.")
    test_with_incrementing_skill(Skill.NON_ELEMENTAL_BOOST, 1, [485.60, 506.39])

    weapon_augments_config = [
            (IBWeaponAugmentType.ATTACK_INCREASE,   1),
            (IBWeaponAugmentType.AFFINITY_INCREASE, 1),
        ]

    logger.info("Testing with Attack and Affinity augment.")
    test_with_incrementing_skill(Skill.NON_ELEMENTAL_BOOST, 1, [496.39, 517.64])

    weapon_augments_config = [
            (IBWeaponAugmentType.AFFINITY_INCREASE, 2),
        ]

    logger.info("Testing with two Affinity augments.")
    test_with_incrementing_skill(Skill.NON_ELEMENTAL_BOOST, 1, [494.11, 515.59])

    def check_efr(expected_efr):
        transformed_armour_dict = {k: armour_db[(v[0], v[1])].variants[v[2]][k] for (k, v) in armour_dict.items()}
        weapon_augments_tracker = WeaponAugmentTracker.get_instance(weapon)
        weapon_augments_tracker.update_with_config(weapon_augments_config)
        weapon_upgrades_tracker = WeaponUpgradeTracker.get_instance(weapon)
        weapon_upgrades_tracker.update_with_config(weapon_upgrades_config)
        build = Build(weapon, transformed_armour_dict, charm, weapon_augments_tracker, weapon_upgrades_tracker, \
                                            decorations_list)
        results = build.calculate_performance(skill_states_dict)
        if round(results.efr, 2) != round(expected_efr, 2):
            raise ValueError(f"EFR value mismatch. Expected {expected_efr}. Got {results.efr}.")

    def check_skill(expected_skill, expected_level):
        transformed_armour_dict = {k: armour_db[(v[0], v[1])].variants[v[2]][k] for (k, v) in armour_dict.items()}
        weapon_augments_tracker = WeaponAugmentTracker.get_instance(weapon)
        weapon_augments_tracker.update_with_config(weapon_augments_config)
        weapon_upgrades_tracker = WeaponUpgradeTracker.get_instance(weapon)
        weapon_upgrades_tracker.update_with_config(weapon_upgrades_config)
        build = Build(weapon, transformed_armour_dict, charm, weapon_augments_tracker, weapon_upgrades_tracker, \
                                            decorations_list)
        results = build.calculate_performance(skill_states_dict)
        if (expected_level == 0) and (Skill[expected_skill] not in results.skills):
            return
        if Skill[expected_skill] not in results.skills:
            raise ValueError(f"Skill {expected_skill} not present.")
        returned_level = results.skills.get(Skill[expected_skill], 0)
        if returned_level != expected_level:
            raise ValueError(f"Skill level mismatch for {expected_skill}. Expected {expected_level}. Got {returned_level}.")

    weapon = weapon_db["ROYAL_VENUS_BLADE"]

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

    logger.info("Testing with a bunch of varying Teostra pieces from different ranks.")
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

    logger.info("Testing with four Velkhana pieces.")
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

    logger.info("Testing with full size-1 decorations.")
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
        logger.info("Testing with just one more size-1 jewel to see if it catches the error.")
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

    logger.info("Testing with four size-4 decorations.")
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
        logger.info("Testing with just one more size-4 jewel to see if it catches the error.")
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

    logger.info("Testing to see if one indeterminate stateful skill get iterated.")
    transformed_armour_dict = {k: armour_db[(v[0], v[1])].variants[v[2]][k] for (k, v) in armour_dict.items()}
    weapon_augments_tracker = WeaponAugmentTracker.get_instance(weapon)
    weapon_augments_tracker.update_with_config(weapon_augments_config)
    weapon_upgrades_tracker = WeaponUpgradeTracker.get_instance(weapon)
    weapon_upgrades_tracker.update_with_config(weapon_upgrades_config)
    build = Build(weapon, transformed_armour_dict, charm, weapon_augments_tracker, weapon_upgrades_tracker, \
                                        decorations_list)
    results = build.calculate_performance(skill_states_dict)
    if len(results) != 3:
        raise ValueError("Results should've returned a list of 3 items (since Weakness Exploit is the only stateful skill).")

    weapon = weapon_db["JAGRAS_DEATHCLAW_II"]

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
            Skill.AGITATOR: 1,
            Skill.PEAK_PERFORMANCE: 1,
        }

    weapon_augments_config = [
            (IBWeaponAugmentType.ATTACK_INCREASE,   1),
        ]

    weapon_upgrades_config = None # Start with no upgrades

    decorations_list = [
        Decoration.ELEMENTLESS,
    ]

    charm = charms_db["CRITICAL_CHARM"]

    logger.info("Testing without weapon upgrades.")
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

    logger.info("Testing with weapon upgrades.")

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

    decorations_list = [
        Decoration.ELEMENTLESS,
        Decoration.CRITICAL,
        Decoration.FLAWLESS,
        Decoration.FLAWLESS,
        Decoration.ATTACK,
        Decoration.ATTACK,
        Decoration.CHALLENGER,
        Decoration.CHALLENGER,
    ]

    check_efr(573.19)

    decorations_list.append(Decoration.DEFENSE_X3)

    if __debug__:
        try:
            check_efr(0)
        except:
            pass
        else:
            raise RuntimeError("Test failed. Expected an exception here.")

    decorations_list = [
        Decoration.ELEMENTLESS,
        Decoration.CRITICAL,
        Decoration.FLAWLESS,
        Decoration.FLAWLESS,
        Decoration.ATTACK,
        Decoration.ATTACK,
        Decoration.CHALLENGER,
        Decoration.CHALLENGER,
        Decoration.EXPERT, # Added this one compared to the last time
    ]

    weapon_augments_config = [
            (IBWeaponAugmentType.AFFINITY_INCREASE, 2),
            (IBWeaponAugmentType.SLOT_UPGRADE,      1),
        ]

    check_efr(562.16)

    decorations_list = [
        Decoration.ELEMENTLESS,
        Decoration.CRITICAL,
        Decoration.FLAWLESS,
        Decoration.FLAWLESS,
        Decoration.ATTACK,
        Decoration.ATTACK,
        Decoration.CHALLENGER,
        Decoration.CHALLENGER,
        Decoration.CHALLENGER, # Changed from Expert compared to the last time
    ]

    if __debug__:
        try:
            check_efr(0)
        except:
            pass
        else:
            raise RuntimeError("Test failed. Expected an exception here.")

    weapon_augments_config = [
            (IBWeaponAugmentType.AFFINITY_INCREASE, 1),
            (IBWeaponAugmentType.SLOT_UPGRADE,      2),
        ]

    check_efr(555.83)

    logger.info("Testing some Safi weapon builds.")

    weapon = weapon_db["SAFI_SHATTERSPLITTER"]

    charm = charms_db["CHALLENGER_CHARM"]

    armour_dict = {
            ArmourSlot.HEAD:  ("Teostra",     ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
            ArmourSlot.CHEST: ("Damascus",    ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
            ArmourSlot.ARMS:  ("Teostra",     ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
            ArmourSlot.WAIST: ("Teostra",     ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
            ArmourSlot.LEGS:  ("Yian Garuga", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
        }

    weapon_augments_config = [
            (IBWeaponAugmentType.ATTACK_INCREASE, 1),
            #(IBWeaponAugmentType.HEALTH_REGEN,    1), # TODO: Update the max slot values to allow this.
        ]

    weapon_upgrades_config = [
            (SafiWeaponStandardUpgradeType.ATTACK,    6),
            (SafiWeaponStandardUpgradeType.ATTACK,    5),
            (SafiWeaponStandardUpgradeType.ATTACK,    5),
            (SafiWeaponStandardUpgradeType.SHARPNESS, 5),
            (SafiWeaponStandardUpgradeType.SHARPNESS, 5),
        ]

    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 2,
            Skill.AGITATOR: 1,
        }

    decorations_list = [
            Decoration.ATTACK_X2,
            Decoration.COMPOUND_CHARGER_VITALITY,
            Decoration.ATTACK_X2,
            Decoration.CRITICAL,
            Decoration.EXPERT,
            Decoration.EXPERT_X2,
            Decoration.TENDERIZER,
            Decoration.COMPOUND_CHALLENGER_VITALITY,
            Decoration.TENDERIZER,
            Decoration.ATTACK,
            Decoration.ATTACK_X2,
            Decoration.CRITICAL,
            Decoration.CRITICAL,
        ]

    check_efr(706.40)
    check_skill("MASTERS_TOUCH", 1) # Set Bonus

    armour_dict[ArmourSlot.WAIST] = ("Damascus", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS)

    check_efr(706.40)
    check_skill("MASTERS_TOUCH", 0) # Set Bonus

    weapon_upgrades_config = [
            (SafiWeaponStandardUpgradeType.ATTACK,          6),
            (SafiWeaponStandardUpgradeType.ATTACK,          5),
            (SafiWeaponStandardUpgradeType.SHARPNESS,       5),
            (SafiWeaponStandardUpgradeType.SHARPNESS,       5),
            (SafiWeaponSetBonusUpgradeType.TEOSTRA_ESSENCE, 1),
        ]

    check_efr(688.88)
    check_skill("MASTERS_TOUCH", 1) # Set Bonus

    logger.info("Testing the Resentment skill.")

    weapon = weapon_db["ROYAL_VENUS_BLADE"]

    charm = charms_db["CHALLENGER_CHARM"]

    armour_dict = {
            ArmourSlot.HEAD:  ("Tigrex",      ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_ALPHA_PLUS),
            ArmourSlot.CHEST: ("Tigrex",      ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_ALPHA_PLUS),
            ArmourSlot.ARMS:  ("Tigrex",      ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_ALPHA_PLUS),
            ArmourSlot.WAIST: ("Tigrex",      ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_ALPHA_PLUS),
            ArmourSlot.LEGS:  ("Yian Garuga", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
        }

    weapon_augments_config = [
            (IBWeaponAugmentType.ATTACK_INCREASE, 1),
            (IBWeaponAugmentType.HEALTH_REGEN,    1),
        ]

    weapon_upgrades_config = None # Start with no upgrades

    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 1,
            Skill.AGITATOR: 1,
            Skill.RESENTMENT: 1,
        }

    decorations_list = [
            Decoration.TENDERIZER,
        ]

    check_efr(478.17)
    check_skill("MASTERS_TOUCH", 0) # Set Bonus
    check_skill("FREE_MEAL_SECRET", 1) # Set Bonus

    decorations_list.append(Decoration.FUROR)

    check_efr(485.60)

    return True


def _run_tests_utils():
    logger.info("")
    logger.info("Running tests on subtract_deco_slots().")

    def test_subtract(sample):
        result = subtract_deco_slots(a, b)
        if sample is None:
            if result is None:
                return
            else:
                raise ValueError(f"Test failed. {a} - {b} is impossible, but the function returned {result}.")
        elif result is None:
            raise ValueError(f"Test failed. The correct answer is {a} - {b} = {sample}, but the function claims it's impossible.")
        elif (len(sample) != 3) or (len(result) != 3) or any(x != y for (x, y) in zip(sample, result)):
            raise ValueError(f"Test failed. The correct answer is {a} - {b} = {sample}, but instead we got {result}.")
        return

    a = [1,1,1]
    b = [1,1,1]
    test_subtract([0,0,0])
    a = [1,1,1]
    b = [1,1,2]
    test_subtract(None)
    a = [1,1,2]
    b = [1,1,1]
    test_subtract([0,0,1])

    a = [3,4,5]
    b = [2,1,3]
    test_subtract([1,3,2])

    a = [3,1,5]
    b = [2,1,3]
    test_subtract([1,0,2])
    a = [3,0,5] # Changed size-2 to 0
    b = [2,1,3]
    test_subtract([1,0,1])
    a = [1,0,5] # Changed size-1 to 1
    b = [2,1,3]
    test_subtract([0,0,0])
    a = [1,0,5]
    b = [3,1,3] # Changed size-1 to 3
    test_subtract(None)
    a = [1,0,6] # Added a size-3 slot
    b = [3,1,3]
    test_subtract([0,0,0])

    a = [0,0,7]
    b = [4,0,0]
    test_subtract([0,0,3])
    a = [7,0,0]
    b = [0,0,4]
    test_subtract(None)

    # TODO: Find more corner-cases?

    return True


def _run_tests_armour_pruning():
    logger.info("")

    def test_supercedes_common(gear_slot, p1_set_name, p1_discrim, p1_variant, p2_set_name, p2_discrim, p2_variant, **kwargs):
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
        return _armour_piece_supercedes(p1, p1_set_bonus, p2, p2_set_bonus, **kwargs)

    def test_supercedes(*args, **kwargs):
        result = test_supercedes_common(*args, **kwargs)
        if result is False:
            raise ValueError("_armour_piece_supercedes() test failed. Arguments: " + str(args) + " " + str(kwargs))
        return

    def test_not_supercedes(*args, **kwargs):
        result = test_supercedes_common(*args, **kwargs)
        if result is True:
            raise ValueError("_armour_piece_supercedes() test failed. Arguments: " + str(args) + " " + str(kwargs))
        return

    def test_tie(*args, **kwargs):
        result = test_supercedes_common(*args, **kwargs)
        if result is None:
            raise ValueError("_armour_piece_supercedes() test failed. Arguments: " + str(args) + " " + str(kwargs))
        return

    def test_not_supercedes_in_reverse(*args, **kwargs):
        args = (args[0], args[4], args[5], args[6], args[1], args[2], args[3])
        test_not_supercedes(*args, **kwargs)
        return

    logger.info("Checking that (head) Kaiser Beta always supercedes Kaiser Alpha.")
    test_supercedes("HEAD", "Teostra", "HIGH_RANK", "HR_BETA", "Teostra", "HIGH_RANK", "HR_ALPHA")
    test_not_supercedes_in_reverse("HEAD", "Teostra", "HIGH_RANK", "HR_BETA", "Teostra", "HIGH_RANK", "HR_ALPHA")

    logger.info("Checking that (head) Kaiser Beta+ always supercedes Kaiser Alpha.")
    test_supercedes("HEAD", "Teostra", "MASTER_RANK", "MR_BETA_PLUS", "Teostra", "HIGH_RANK", "HR_ALPHA")
    test_not_supercedes_in_reverse("HEAD", "Teostra", "MASTER_RANK", "MR_BETA_PLUS", "Teostra", "HIGH_RANK", "HR_ALPHA")

    logger.info("Checking that (head) Kaiser Beta+ never supercedes Kaiser Alpha.")
    test_not_supercedes("HEAD", "Teostra", "MASTER_RANK", "MR_BETA_PLUS", "Teostra", "HIGH_RANK", "HR_GAMMA")
    test_not_supercedes_in_reverse("HEAD", "Teostra", "MASTER_RANK", "MR_BETA_PLUS", "Teostra", "HIGH_RANK", "HR_GAMMA")

    logger.info("Checking that (legs) Garuga Beta+ never supercedes Garuga Alpha+, even when filtering out Piercing Shots.")
    test_not_supercedes("LEGS", "Yian Garuga", "MASTER_RANK", "MR_BETA_PLUS", "Yian Garuga", "MASTER_RANK", "MR_ALPHA_PLUS", \
                                skill_subset={Skill.CRITICAL_EYE,})
    test_not_supercedes_in_reverse("LEGS", "Yian Garuga", "MASTER_RANK", "MR_BETA_PLUS", "Yian Garuga", "MASTER_RANK", \
                                    "MR_ALPHA_PLUS", skill_subset={Skill.CRITICAL_EYE,})

    return True


def _run_tests_serializing():
    logger.info("")
    logger.info("Testing serializing and deserializing of build data.")

    weapon = weapon_db["ACID_SHREDDER_II"]

    armour_dict = {
            ArmourSlot.HEAD:  ("Velkhana", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_ALPHA_PLUS),
            ArmourSlot.CHEST: ("Velkhana", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
            ArmourSlot.ARMS:  ("Teostra",  ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
            ArmourSlot.WAIST: ("Velkhana", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
            ArmourSlot.LEGS:  ("Velkhana", ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
        }
    armour_dict = {k: armour_db[(v[0], v[1])].variants[v[2]][k] for (k, v) in armour_dict.items()}

    charm = charms_db["CHALLENGER_CHARM"]

    weapon_augments_config = [
            (IBWeaponAugmentType.ATTACK_INCREASE  , 1),
            (IBWeaponAugmentType.AFFINITY_INCREASE, 1),
        ]

    weapon_upgrades_config = ([IBCWeaponUpgradeType.AFFINITY] * 4) + ([IBCWeaponUpgradeType.ATTACK] * 2)

    weapon_augments_tracker = WeaponAugmentTracker.get_instance(weapon)
    weapon_augments_tracker.update_with_config(weapon_augments_config)
    weapon_upgrades_tracker = WeaponUpgradeTracker.get_instance(weapon)
    weapon_upgrades_tracker.update_with_config(weapon_upgrades_config)

    decos = [Decoration.ELEMENTLESS] + [Decoration.COMPOUND_TENDERIZER_VITALITY] + [Decoration.ATTACK]

    skill_states_dict = {
            Skill.WEAKNESS_EXPLOIT: 2,
            Skill.AGITATOR:         1,
        }

    original_build_obj = Build(weapon, armour_dict, charm, weapon_augments_tracker, weapon_upgrades_tracker, decos)

    original_results = original_build_obj.calculate_performance(skill_states_dict)

    if round(original_results.efr, 2) != round(476.70, 2):
        raise ValueError(f"Test failed. Got {original_results.efr} EFR.")
    if original_results.affinity != 54:
        raise ValueError(f"Test failed. Got {original_results.affinity} affinity.")

    serialized_data = original_build_obj.serialize()

    if not isinstance(serialized_data, str):
        raise ValueError("Expected a string.")

    new_build_obj = Build.deserialize(serialized_data)

    new_results = new_build_obj.calculate_performance(skill_states_dict)

    if round(original_results.efr, 2) != round(476.70, 2):
        raise ValueError(f"Test failed. Got {original_results.efr} EFR.")
    if original_results.affinity != 54:
        raise ValueError(f"Test failed. Got {original_results.affinity} affinity.")
    
    return True


def _run_tests_deco_list_generation():
    logger.info("")
    logger.info("Testing decoration dictionary generation.")


    decos_size1 = [
            Decoration.ATTACK,
            Decoration.VITALITY,
        ]
    decos_size2 = [
            Decoration.CHALLENGER,
            Decoration.CHARGER,
        ]
    decos_size3 = [
            Decoration.EARPLUG,
            Decoration.PHOENIX,
        ]
    decos_size4 = [
            Decoration.COMPOUND_CHALLENGER_VITALITY,
            Decoration.ATTACK_X2,
            Decoration.CHALLENGER_X2,
        ]

    decos_maxsize2 = decos_size2 + decos_size1
    decos_maxsize3 = decos_size3 + decos_maxsize2
    decos_maxsize4 = decos_size4 + decos_maxsize3
    decos = [decos_size1, decos_maxsize2, decos_maxsize3, decos_maxsize4]

    def check_length(expected_length):
        x = _generate_deco_additions(slots, defaultdict(lambda : 0, skills), decos)
        #print("\n".join("[" + ", ".join(f"\"{y.name}\"" for y in deco_combo[0]) + "]" for deco_combo in x))
        #print()
        if len(x) != expected_length:
            raise ValueError(f"Expected {expected_length} results. Instead got {len(x)}.")

    slots = []
    skills = {}

    check_length(1)

    slots = [1]
    skills = {}

    check_length(3)

    slots = [2]
    skills = {}

    check_length(5)

    slots = [2, 1]
    skills = {}

    check_length(12)

    #slots = [3, 2, 1]
    #skills = {}

    #check_length(55)

    # TODO: Write out some more theoretically-obtained solutions!
    
    return True


if __name__ == '__main__':
    run_tests()
    sys.exit(0)

