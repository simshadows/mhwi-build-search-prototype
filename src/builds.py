# -*- coding: ascii -*-

"""
Filename: builds.py
Author:   contact@simshadows.com

This file contains build data structures, functions to operate on them, and how to save/read
a build to file (and serialize/deserialize to text).
"""

import json
from copy import copy

from collections import namedtuple, Counter

from .database_armour      import (ArmourDiscriminator,
                                  ArmourVariant,
                                  ArmourSlot,
                                  armour_db)
from .database_charms      import (CharmInfo,
                                  charms_db)
from .database_decorations import Decoration
from .database_misc        import (POWERCHARM_ATTACK_POWER,
                                  POWERTALON_ATTACK_POWER)
from .database_weapons     import (RAW_SHARPNESS_MODIFIERS,
                                  weapon_db)

from .query_armour      import calculate_armour_contribution
from .query_charms      import calculate_skills_dict_from_charm
from .query_decorations import calculate_decorations_skills_contribution
from .query_skills      import (HANDICRAFT_MAX_LEVEL,
                               RAW_BLUNDER_MULTIPLIER,
                               clipped_skills_defaultdict,
                               calculate_set_bonus_skills,
                               calculate_skills_contribution)
from .query_weapons     import (WeaponAugmentTracker,
                               WeaponUpgradeTracker,
                               calculate_final_weapon_values,
                               get_weapon_config_humanreadable)


BuildValues = namedtuple(
    "BuildValues",
    [
        "efr",
        "affinity",
        "sharpness_values",

        "skills",

        "usable_slots",
    ],
)


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
    weapon_true_raw       = kwargs["weapon_true_raw"]
    weapon_affinity       = kwargs["weapon_affinity"]
    weapon_raw_multiplier = kwargs["weapon_raw_multiplier"]

    added_raw      = kwargs["added_raw"]
    added_affinity = kwargs["added_affinity"]

    raw_sharpness_modifier = kwargs["raw_sharpness_modifier"]
    raw_crit_multiplier    = kwargs["raw_crit_multiplier"]
    raw_crit_chance        = min(weapon_affinity + added_affinity, 100) / 100

    if raw_crit_chance < 0:
        # Negative Affinity
        raw_blunder_chance = -raw_crit_chance
        raw_crit_modifier = (RAW_BLUNDER_MULTIPLIER * raw_blunder_chance) + (1 - raw_blunder_chance)
    else:
        # Positive Affinity
        raw_crit_modifier = (raw_crit_multiplier * raw_crit_chance) + (1 - raw_crit_chance)

    weapon_new_raw = weapon_true_raw * weapon_raw_multiplier
    true_raw = round(weapon_new_raw, 0) + added_raw

    efr = true_raw * raw_sharpness_modifier * raw_crit_modifier

    return efr


def skill_states_are_fully_defined(skills_dict, skill_states_dict):
    return all((lvl == 0) or (s.value.states is None) or (s in skill_states_dict) for (s, lvl) in skills_dict.items())


LookupFromSkillsValues = namedtuple(
    "LookupFromSkillsValues",
    [
        "efr",
        "affinity",
        "sharpness_values",

        "skills",
    ],
)
def lookup_from_skills(weapon, skills_dict, skill_states_dict, weapon_augments_tracker, weapon_upgrades_tracker):
    #assert isinstance(weapon, namedtuple) # idk how to implement this assertion. # TODO: This.
    assert isinstance(skills_dict, dict)
    assert isinstance(skill_states_dict, dict)
    assert isinstance(weapon_augments_tracker, WeaponAugmentTracker)
    assert isinstance(weapon_upgrades_tracker, WeaponUpgradeTracker)

    skills_dict = clipped_skills_defaultdict(skills_dict)

    # skills_dict and skill_states_dict layout assertions.
    #assert all(lvl > 0 for (s, lvl) in skills_dict.items())
    assert all(state >= 0 for (s, state) in skill_states_dict.items())
    assert all(s.value.states is not None for (s, state) in skill_states_dict.items())
    # Assert that all skill states provided have corresponding skills in skills_dict.
    #assert all(s in skills_dict for (s, state) in skill_states_dict.items()) # We won't do this.

    assert skill_states_are_fully_defined(skills_dict, skill_states_dict)

    weapon_final_values = calculate_final_weapon_values(weapon, weapon_augments_tracker, weapon_upgrades_tracker)

    maximum_sharpness_values = weapon.maximum_sharpness
    from_skills = calculate_skills_contribution(
            skills_dict,
            skill_states_dict,
            maximum_sharpness_values,
            weapon.is_raw
        )

    handicraft_level = from_skills.handicraft_level
    maximum_sharpness_values = weapon_final_values.maximum_sharpness
    if weapon_final_values.constant_sharpness:
        handicraft_level = HANDICRAFT_MAX_LEVEL
    sharpness_values, highest_sharpness_level = _actual_sharpness_level_values(maximum_sharpness_values, handicraft_level)

    item_attack_power = POWERCHARM_ATTACK_POWER + POWERTALON_ATTACK_POWER

    kwargs = {}
    kwargs["weapon_true_raw"]        = weapon_final_values.true_raw
    kwargs["weapon_affinity"]        = weapon_final_values.affinity
    kwargs["added_raw"]              = from_skills.added_attack_power + item_attack_power
    kwargs["added_affinity"]         = from_skills.added_raw_affinity
    kwargs["raw_sharpness_modifier"] = RAW_SHARPNESS_MODIFIERS[highest_sharpness_level]
    kwargs["raw_crit_multiplier"]    = from_skills.raw_critical_multiplier

    kwargs["weapon_raw_multiplier"] = from_skills.weapon_base_attack_power_multiplier

    ret = LookupFromSkillsValues(
            efr               = _calculate_efr(**kwargs),
            affinity          = kwargs["weapon_affinity"] + kwargs["added_affinity"],
            sharpness_values  = sharpness_values,

            skills = skills_dict,
        )
    return ret


# Alternative version that produces a tree of missing states.
# TODO: Make this just produce a simple list. It's so unnecessarily complicated.
def lookup_from_skills_multiple_states(weapon, skills_dict, skill_states_dict, weapon_augments_tracker, weapon_upgrades_tracker):
    #assert isinstance(weapon, namedtuple) # idk how to implement this assertion. # TODO: This.
    assert isinstance(skills_dict, dict)
    assert isinstance(skill_states_dict, dict)
    assert isinstance(weapon_augments_tracker, WeaponAugmentTracker)
    assert isinstance(weapon_upgrades_tracker, WeaponUpgradeTracker)

    skills_dict = clipped_skills_defaultdict(skills_dict)

    # skills_dict and skill_states_dict layout assertions.
    #assert all(lvl > 0 for (s, lvl) in skills_dict.items())
    assert all(state >= 0 for (s, state) in skill_states_dict.items())
    assert all(s.value.states is not None for (s, state) in skill_states_dict.items())
    # Assert that all skill states provided have corresponding skills in skills_dict.
    #assert all(s in skills_dict for (s, state) in skill_states_dict.items()) # We won't do this.

    assert not skill_states_are_fully_defined(skills_dict, skill_states_dict)

    # We first determine all missing skills.
    stateful_skills = set(s for (s, _) in skills_dict.items() if (s.value.states is not None))
    missing_skills = list(stateful_skills - set(skill_states_dict))

    def generate_tree(new_skill_states_dict, missing_skills_remaining):
        nonlocal missing_skills
        if len(missing_skills_remaining) == 0:
            return lookup_from_skills(weapon, skills_dict, new_skill_states_dict, weapon_augments_tracker, weapon_upgrades_tracker)
        else:
            missing_skills = copy(missing_skills)
            curr_skill = missing_skills.pop(0)
            num_states = len(curr_skill.value.states)
            assert num_states > 1

            intermediate_tree = []
            for state in range(num_states):
                arg_skill_states_dict = copy(new_skill_states_dict)
                arg_skill_states_dict[curr_skill] = state
                intermediate_tree.append(generate_tree(arg_skill_states_dict, missing_skills))
            return intermediate_tree

    results_tree = generate_tree(skill_states_dict, missing_skills)

    return (results_tree, missing_skills)


class Build:
    
    __slots__ = [
            "_head",
            "_chest",
            "_arms",
            "_waist",
            "_legs",

            "_charm",

            "_weapon",
            "_weapon_augments_tracker",
            "_weapon_upgrades_tracker",

            "_decos",
        ]

    # Input looks like this:
    #
    #       armour_dict = {
    #           ArmourSlot.HEAD:  ("Teostra",      ArmourDiscriminator.HIGH_RANK,   ArmourVariant.HR_GAMMA),
    #           ArmourSlot.CHEST: ("Damascus",     ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
    #           ArmourSlot.ARMS:  ("Teostra",      ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
    #           ArmourSlot.WAIST: ("Teostra",      ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
    #           ArmourSlot.LEGS:  ("Yian Garuga",  ArmourDiscriminator.MASTER_RANK, ArmourVariant.MR_BETA_PLUS),
    #       }
    #
    #       charm_id = charms_db["CHALLENGER_CHARM"]
    #
    #       weapon = weapon_db["ACID_SHREDDER_II"]
    #
    #       decos_list_or_dict = ???
    #
    def __init__(self, weapon, armour_dict, charm, weapon_augments_tracker, weapon_upgrades_tracker, decos_list_or_dict):

        self._head  = armour_dict.get(ArmourSlot.HEAD,  None)
        self._chest = armour_dict.get(ArmourSlot.CHEST, None)
        self._arms  = armour_dict.get(ArmourSlot.ARMS,  None)
        self._waist = armour_dict.get(ArmourSlot.WAIST, None)
        self._legs  = armour_dict.get(ArmourSlot.LEGS,  None)

        self._charm = charm
        assert isinstance(self._charm, CharmInfo) or (self._charm is None)

        self._weapon = weapon
        self._weapon_augments_tracker = weapon_augments_tracker.copy()
        self._weapon_upgrades_tracker = weapon_upgrades_tracker.copy()
        #assert isinstance(self._weapon, namedtuple) # TODO: Make a proper assertion for this.
        assert isinstance(self._weapon_augments_tracker, WeaponAugmentTracker)
        assert isinstance(self._weapon_upgrades_tracker, WeaponUpgradeTracker)

        self._decos = copy(decos_list_or_dict)
        assert isinstance(self._decos, dict) or isinstance(self._decos, list)

        return

    def calculate_performance(self, skill_states_dict):
        armour_contribution = calculate_armour_contribution(self._get_armour_dict())
        weapon_augment_contribution = self._weapon_augments_tracker.calculate_contribution()
        weapon_upgrades_contribution = self._weapon_upgrades_tracker.calculate_contribution()

        decorations_counter = Counter(self._decos)

        slots_available_list = list(self._weapon.slots) + list(armour_contribution.decoration_slots)
        if weapon_augment_contribution.extra_decoration_slot_level > 0:
            slots_available_list.append(weapon_augment_contribution.extra_decoration_slot_level)
        if weapon_upgrades_contribution.extra_decoration_slot_level > 0:
            slots_available_list.append(weapon_upgrades_contribution.extra_decoration_slot_level)
        slots_available_counter = Counter(slots_available_list)
        assert len(slots_available_counter) <= 4 # We only have slot sizes 1 to 4.

        # For debugging, we can first determine if the decorations fit in the selected gear.
        # (We should be able to rely on inputs here.
        # Both slots_*_counter are in the format {slot_size: count}
        if __debug__:
            slots_used_counter = Counter()
            for (deco, total) in decorations_counter.items():
                slots_used_counter.update([deco.value.slot_size] * total)

            tmp_slots_available_counter = copy(slots_available_counter)
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
        if self._charm is not None:
            charm_skills_dict = calculate_skills_dict_from_charm(self._charm, self._charm.max_level)
            for (skill, level) in charm_skills_dict.items():
                skills_dict[skill] += level

        # Decoration skills
        deco_skills_dict = calculate_decorations_skills_contribution(decorations_counter)
        for (skill, level) in deco_skills_dict.items():
            skills_dict[skill] += level

        # Armour set bonuses
        skills_from_set_bonuses = calculate_set_bonus_skills(armour_contribution.set_bonuses, \
                                                                weapon_upgrades_contribution.set_bonus)
        if len(set(skills_dict) & set(skills_from_set_bonuses)) != 0:
            raise RuntimeError("We shouldn't be getting any mixing between regular skills and set bonuses here.")

        skills_dict.update(skills_from_set_bonuses)

        # TODO: I want to refactor out this monstrosity.
        if skill_states_are_fully_defined(skills_dict, skill_states_dict):
            result = lookup_from_skills(self._weapon, skills_dict, skill_states_dict, \
                                                        self._weapon_augments_tracker, self._weapon_upgrades_tracker)
            ret = BuildValues(
                    efr                     = result.efr,
                    affinity                = result.affinity,
                    sharpness_values        = result.sharpness_values,
                    
                    skills                  = result.skills,
                    
                    usable_slots            = slots_available_counter,
                )
        else:
            intermediate_results, _ = lookup_from_skills_multiple_states(self._weapon, skills_dict, skill_states_dict, \
                                                        self._weapon_augments_tracker, self._weapon_upgrades_tracker)

            def transform_results_recursively(obj):
                if isinstance(obj, list):
                    return [transform_results_recursively(x) for x in obj]
                else:
                    new_obj = BuildValues(
                            efr                     = obj.efr,
                            affinity                = obj.affinity,
                            sharpness_values        = obj.sharpness_values,
                            
                            skills                  = obj.skills,
                            
                            usable_slots            = slots_available_counter,
                        )
                    return new_obj

            ret = transform_results_recursively(intermediate_results)
                
        return ret

    def get_humanreadable(self, skill_states_dict):
        performance = self.calculate_performance(skill_states_dict)

        buf = []

        buf.append("Build:")
        buf.append("")

        buf.append(f"{performance.efr} EFR @ {performance.affinity} affinity")
        buf.append("")

        s = get_weapon_config_humanreadable("      ", self._weapon, self._weapon_augments_tracker, self._weapon_upgrades_tracker)
        buf.append(s)
        buf.append("")

        def append_armour_piece(slot, piece):
            armour_str = (slot.name.ljust(5) + ": " + piece.armour_set.set_name + " " + \
                                    piece.armour_set_variant.value.ascii_postfix).ljust(25)
            deco_str = " ".join(str(x) for x in piece.decoration_slots) if (len(piece.decoration_slots) > 0) else "(none)"
            buf.append(f"      {armour_str} slots: {deco_str}")
            return

        append_armour_piece(ArmourSlot.HEAD,  self._head)
        append_armour_piece(ArmourSlot.CHEST, self._chest)
        append_armour_piece(ArmourSlot.ARMS,  self._arms)
        append_armour_piece(ArmourSlot.WAIST, self._waist)
        append_armour_piece(ArmourSlot.LEGS,  self._legs)
        
        buf.append("")
        buf.append("      CHARM: " + self._charm.name)

        buf.append("")
        for (deco, level) in sorted(self._decos.items(), key=(lambda x : (x[0].value.slot_size, x[1])), reverse=True):
            buf.append(f"      x{level} {deco.value.name}")

        buf.append("")

        return "\n".join(buf)

    def _get_armour_dict(self):
        return {
                ArmourSlot.HEAD:  self._head,
                ArmourSlot.CHEST: self._chest,
                ArmourSlot.ARMS:  self._arms,
                ArmourSlot.WAIST: self._waist,
                ArmourSlot.LEGS:  self._legs,
            }

    def serialize(self):
        armour_keys = {k.name: [v.armour_set.set_name, v.armour_set.discriminator.name, v.armour_set_variant.name]
                      for (k, v) in self._get_armour_dict().items()}
        charm_id = self._charm.id
        weapon_id = self._weapon.id
        weapon_augments_serialized = self._weapon_augments_tracker.get_serialized_config()
        weapon_upgrades_serialized = self._weapon_upgrades_tracker.get_serialized_config()
        decos = {k.name: v for (k, v) in Counter(self._decos).items()}

        data = {
                "armour": armour_keys,
                "charm": charm_id,
                "weapon": weapon_id,
                "weapon_augments": weapon_augments_serialized,
                "weapon_upgrades": weapon_upgrades_serialized,
                "decorations": decos,
            }
        return json.dumps(data) # This will fail if we mess something up.

    @classmethod
    def deserialize(self, serial_data):
        assert isinstance(serial_data, str)
        data = json.loads(serial_data)
        
        armour_dict = {ArmourSlot[k]: armour_db[(v[0], ArmourDiscriminator[v[1]])].variants[ArmourVariant[v[2]]][ArmourSlot[k]]
                      for (k, v) in data["armour"].items()}
        charm = charms_db[data["charm"]]
        weapon = weapon_db[data["weapon"]]
        weapon_augments_tracker = WeaponAugmentTracker.get_instance(weapon)
        weapon_augments_tracker.update_with_serialized_config(data["weapon_augments"])
        weapon_upgrades_tracker = WeaponUpgradeTracker.get_instance(weapon)
        weapon_upgrades_tracker.update_with_serialized_config(data["weapon_upgrades"])
        decos_dict = {Decoration[k]: v for (k, v) in data["decorations"].items()}

        obj = Build(weapon, armour_dict, charm, weapon_augments_tracker, weapon_upgrades_tracker, decos_dict)
        return obj

