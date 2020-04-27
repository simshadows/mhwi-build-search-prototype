# -*- coding: ascii -*-

"""
Filename: database_armour.py
Author:   contact@simshadows.com

This file provides the MHWI build optimizer script's armour database data.
"""

from collections import namedtuple
from enum import Enum, auto
from itertools import product

from .enums import Tier
from .utils import json_read

from .database_skills import Skill, SetBonus


ARMOUR_DATA_FILENAME = "data/database_armour.json"


ArmourDiscriminatorInfo = namedtuple("ArmourDiscriminatorInfo", ["tier"])
class ArmourDiscriminator(Enum):
    LOW_RANK    = ArmourDiscriminatorInfo(tier=Tier.LOW_RANK)
    HIGH_RANK   = ArmourDiscriminatorInfo(tier=Tier.HIGH_RANK)
    MASTER_RANK = ArmourDiscriminatorInfo(tier=Tier.MASTER_RANK)

ArmourVariantInfo = namedtuple("ArmourVersionInfo", ["tier", "ascii_postfix", "unicode_postfix"])
class ArmourVariant(Enum):
    LR            = ArmourVariantInfo(tier=Tier.LOW_RANK,    ascii_postfix=None,     unicode_postfix=None)
    HR_ALPHA      = ArmourVariantInfo(tier=Tier.HIGH_RANK,   ascii_postfix="Alpha",  unicode_postfix="\u03b1")
    HR_BETA       = ArmourVariantInfo(tier=Tier.HIGH_RANK,   ascii_postfix="Beta",   unicode_postfix="\u03b2")
    HR_GAMMA      = ArmourVariantInfo(tier=Tier.HIGH_RANK,   ascii_postfix="Gamma",  unicode_postfix="\u03b3")
    MR_ALPHA_PLUS = ArmourVariantInfo(tier=Tier.MASTER_RANK, ascii_postfix="Alpha+", unicode_postfix="\u03b1+")
    MR_BETA_PLUS  = ArmourVariantInfo(tier=Tier.MASTER_RANK, ascii_postfix="Beta+",  unicode_postfix="\u03b2+")
    MR_GAMMA_PLUS = ArmourVariantInfo(tier=Tier.MASTER_RANK, ascii_postfix="Gamma+", unicode_postfix="\u03b3+")

class ArmourSlot(Enum):
    HEAD  = auto()
    CHEST = auto()
    ARMS  = auto()
    WAIST = auto()
    LEGS  = auto()


ArmourNamingScheme = namedtuple(
        "ArmourNamingScheme",
        [
            "head",  # string
            "chest", # string
            "arms",  # string
            "waist", # string
            "legs",  # string
        ]
    )

ArmourSetInfo = namedtuple(
        "ArmourInfo",
        [
            "set_name",      # string                          # Left side of the key.
            "discriminator", # ArmourDiscriminator             # Right side of the key.
            "rarity",        # int

            "prefix",        # string
            "naming_scheme", # ArmourNamingScheme

            "set_bonus",     # SetBonus

            "variants",      # {ArmourVariant: {ArmourSlot: ArmourPieceInfo}}
        ]
    )

ArmourPieceInfo = namedtuple(
        "ArmourVariantInfo",
        [
            "armour_set",         # ArmourSetInfo              # This points us back to the original set.

            "armour_set_variant", # ArmourVariant
            "armour_slot",        # ArmourSlot
            "decoration_slots",   # [int]
            "skills",             # {Skill: int}
        ]
    )

def _obtain_armour_db():
    json_data = json_read(ARMOUR_DATA_FILENAME)

    # First, we parse the naming schemes.

    def validation_error(info, naming_scheme=None):
        if naming_scheme is None:
            raise ValueError(f"{ARMOUR_DATA_FILENAME}: {info}")
        else:
            raise ValueError(f"{ARMOUR_DATA_FILENAME} {naming_scheme}: {info}")

    naming_schemes_intermediate = {}

    for (naming_scheme_id, piece_postfixes) in json_data["naming_schemes"].items():

        if not isinstance(naming_scheme_id, str):
            validation_error("Armour naming schemes must be strings. Instead, we have: " + str(naming_scheme_id))
        elif len(naming_scheme_id) == 0:
            validation_error("Armour naming schemes must be strings of non-zero length.")
        elif naming_scheme_id in naming_schemes_intermediate:
            validation_error("Armour naming scheme IDs must be unique.", naming_scheme=naming_scheme_id)
        
        elif (not isinstance(piece_postfixes, list)) or (len(piece_postfixes) != 5):
            validation_error("Armour naming schemes must be lists of 5 items.", naming_scheme=naming_scheme_id)
        elif any((not isinstance(x, str)) or (len(x) == 0) for x in piece_postfixes):
            validation_error("Armour naming schemes must be lists of non-empty strings.", naming_scheme=naming_scheme_id)

        naming_schemes_intermediate[naming_scheme_id] = ArmourNamingScheme(*piece_postfixes)

    # Next, we parse the armour pieces.

    def validation_error(info, variant=None, slot=None):
        if (variant is None) and (slot is None):
            raise ValueError(f"{ARMOUR_DATA_FILENAME}: {info}")
        else:
            assert (variant is not None) and (slot is not None)
            raise ValueError(f"{ARMOUR_DATA_FILENAME} {variant.name} {slot}: {info}")

    armour_db_intermediate = {}

    for armour_set in json_data["armour"]:

        set_kwargs = {
            "set_name"     : armour_set["set"],
            "discriminator": ArmourDiscriminator[armour_set["discriminator"]],
            "rarity"       : armour_set["rarity"],

            "prefix"       : armour_set["prefix"],
            "naming_scheme": naming_schemes_intermediate[armour_set["naming_scheme"]],

            "set_bonus"    : SetBonus[armour_set["set_bonus"]] if (armour_set["set_bonus"] is not None) else None,

            "variants"     : {},
        }

        set_info = ArmourSetInfo(**set_kwargs)

        if (set_info.set_name, set_info.discriminator) in armour_db_intermediate:
            raise validation_error(f"Duplicate set: {set_info.set_name}, {set_info.discriminator}")

        # Quickly check if there are any unexpected keys.
        tier = set_info.discriminator.value.tier
        relevant_variant_names = {variant.name for variant in ArmourVariant if (variant.value.tier is tier)}
        all_possible_set_keys = {"set", "discriminator", "rarity", "prefix", "naming_scheme", \
                                        "set_bonus"} | relevant_variant_names
        unexpected_keys = set(armour_set) - all_possible_set_keys
        if len(unexpected_keys) > 0:
            validation_error("Got unexpected keys: " + str(unexpected_keys))

        for variant in ArmourVariant:
            if (variant.value.tier is tier) and (variant.name in armour_set):
                variant_subset = armour_set[variant.name]
                
                subset = {}
                for (armour_slot_name, piece_json_data) in variant_subset.items():

                    if (not isinstance(piece_json_data, list)) or (len(piece_json_data) != 2):
                        validation_error("Expecting exactly two items in the list.", variant=variant, slot=armour_slot_name)
                    
                    piece = ArmourPieceInfo(
                            armour_set         = set_info,

                            armour_set_variant = variant,
                            armour_slot        = ArmourSlot[armour_slot_name],
                            decoration_slots   = tuple(piece_json_data[0]),
                            skills             = {Skill[k]: v for (k, v) in piece_json_data[1].items()},
                        )

                    if (len(piece.decoration_slots) > 3) or any((not isinstance(x, int)) for x in piece.decoration_slots):
                        validation_error("Expecting up to three integers to represent the decoration slot sizes.", \
                                variant=variant, slot=armour_slot_name)
                    elif any((not isinstance(level, int) or (level <= 0)) for (_, level) in piece.skills.items()):
                        validation_error("Skills must have integer levels above 0.", variant=variant, slot=armour_slot_name)

                    subset[piece.armour_slot] = piece

                set_info.variants[variant] = subset

        if len(set_info.variants) == 0:
            set_name = set_kwargs["set_name"]
            disc = set_kwargs["discriminator"]
            raise validation_error(f"No armour set variants found for {set_name} {disc}.")

        armour_db_intermediate[(set_info.set_name, set_info.discriminator)] = set_info

    if len(armour_db_intermediate) == 0:
        validation_error("No armour sets found.")

    return armour_db_intermediate


def _obtain_easyiterate_armour_db(original_armour_db):
    intermediate = {slot: [] for slot in ArmourSlot}

    for ((set_name, discrim), set_info) in original_armour_db.items():
        for (variant, variant_pieces) in set_info.variants.items():
            for (gear_slot, piece) in variant_pieces.items():
                intermediate[gear_slot].append(piece)
    return dict(intermediate) # TODO: We should make it so we just start off with a regular dictionary from the start.


armour_db = _obtain_armour_db()

# This will contain a more iterator-friendly version, at the cost of indexability.
# (armour_db will be used for indexing.)
ArmourEasyIterateInfo = namedtuple("ArmourEasyIterateInfo", ["set_name", "discrim", "variant"])
easyiterate_armour = _obtain_easyiterate_armour_db(armour_db)

# This will prune out pieces that can be recreated better or more flexibly by another piece.
# Importantly, the data structure is the same as easyiterate_armour.
# This will make this practically interchangable with easyiterate_armour if all you care about are skills.
#skillsonly_pruned_armour = prune_easyiterate_armour_db(easyiterate_armour) # We don't need this right now.
