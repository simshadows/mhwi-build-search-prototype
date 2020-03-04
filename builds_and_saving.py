# -*- coding: ascii -*-

"""
Filename: builds_and_saving.py
Author:   contact@simshadows.com

This file contains build data structures, functions to operate on them, and how to save/read
a build to file (and serialize/deserialize to text).
"""

import sys, time
from math import ceil
from copy import copy

from collections import namedtuple, defaultdict, Counter

from database_armour  import ArmourSlot, armour_db
from database_charms  import charms_db
from database_weapons import weapon_db


class Build:
    
    __slots__ = [
            "_head", # These are all in easyiterate format.
            "_chest",
            "_arms",
            "_waist",
            "_legs",

            "_charm_id", # TODO: We should just use the charm object.

            "_weapon_id", # TODO: We should just use the weapon object.
            "_weapon_augments_config",
            "_weapon_upgrades_config",

            "_decos",
        ]

    def __init__(self, armour_dict, charm_id, weapon_id, weapon_augments_config, weapon_upgrades_config, decos_dict):

        self._head  = armour_dict.get(ArmourSlot.HEAD,  None)
        self._chest = armour_dict.get(ArmourSlot.CHEST, None)
        self._arms  = armour_dict.get(ArmourSlot.ARMS,  None)
        self._waist = armour_dict.get(ArmourSlot.WAIST, None)
        self._legs  = armour_dict.get(ArmourSlot.LEGS,  None)

        self._charm_id = charm_id
        assert isinstance(self._charm_id, str)

        self._weapon_id = weapon_id
        self._weapon_augments_config = copy(weapon_augments_config)
        self._weapon_upgrades_config = copy(weapon_upgrades_config)
        assert isinstance(self._weapon_id, str)
        assert isinstance(self._weapon_augments_config, list)
        assert isinstance(self._weapon_upgrades_config, list) or (self._weapon_upgrades_config is None)

        self._decos = copy(decos_dict)
        assert isinstance(self._decos, dict)

        return

    def print(self):
        print("      " + weapon_db[self._weapon_id].name)

        print()
        for (augment, level) in self._weapon_augments_config:
            print(f"      {augment.name} {level}")
        if self._weapon_upgrades_config is not None:
            for (stage, upgrade) in enumerate(self._weapon_upgrades_config):
                print(f"      Custom Upgrade: {upgrade.name} {stage+1}")

        print()

        def print_armour_piece(slot, slot_data):
            a = armour_db[(slot_data[0], slot_data[1])].variants[slot_data[2]][slot]
            armour_str = (slot.name.ljust(5) + ": " + slot_data[0] + " " + slot_data[2].value.ascii_postfix).ljust(25)
            deco_str = " ".join(str(x) for x in a.decoration_slots) if (len(a.decoration_slots) > 0) else "(none)"
            print(f"      {armour_str} slots: {deco_str}")
            return

        print_armour_piece(ArmourSlot.HEAD,  self._head)
        print_armour_piece(ArmourSlot.CHEST, self._chest)
        print_armour_piece(ArmourSlot.ARMS,  self._arms)
        print_armour_piece(ArmourSlot.WAIST, self._waist)
        print_armour_piece(ArmourSlot.LEGS,  self._legs)
        
        print()
        print("      CHARM: " + charms_db[self._charm_id].name)

        print()
        for (deco, level) in self._decos.items():
            print(f"      x{level} {deco.value.name}")
        return

