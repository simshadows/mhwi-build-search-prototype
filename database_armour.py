"""
Filename: database_armour.py
Author:   contact@simshadows.com

This file provides the MHWI build optimizer script's armour database.
"""

from copy import copy
from collections import namedtuple, defaultdict
from enum import Enum, auto

from database_skills import Skill, SetBonus
from database_decorations import skill_to_simple_deco_size
from enums import Tier
from utils import json_read


ARMOUR_DATA_FILENAME = "database_armour.json"


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
            "set_name",      # string
            "discriminator", # ArmourDiscriminator
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
            "armour_slot",      # ArmourSlot
            "decoration_slots", # [int]
            "skills",           # {Skill: int}
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

            "variants"     : None, # Will fill this again later.
        }

        tier = set_kwargs["discriminator"].value.tier

        # Quickly check if there are any unexpected keys.
        relevant_variant_names = {variant.name for variant in ArmourVariant if (variant.value.tier is tier)}
        all_possible_set_keys = {"set", "discriminator", "rarity", "prefix", "naming_scheme", \
                                        "set_bonus"} | relevant_variant_names
        unexpected_keys = set(armour_set) - all_possible_set_keys
        if len(unexpected_keys) > 0:
            validation_error("Got unexpected keys: " + str(unexpected_keys))

        variants = {}

        for variant in ArmourVariant:
            if (variant.value.tier is tier) and (variant.name in armour_set):
                variant_subset = armour_set[variant.name]
                
                subset = {}
                for (armour_slot_name, piece_json_data) in variant_subset.items():

                    if (not isinstance(piece_json_data, list)) or (len(piece_json_data) != 2):
                        validation_error("Expecting exactly two items in the list.", variant=variant, slot=armour_slot_name)
                    
                    piece = ArmourPieceInfo(
                            armour_slot      = ArmourSlot[armour_slot_name],
                            decoration_slots = tuple(piece_json_data[0]),
                            skills           = {Skill[k]: v for (k, v) in piece_json_data[1].items()},
                        )

                    if (len(piece.decoration_slots) > 3) or any((not isinstance(x, int)) for x in piece.decoration_slots):
                        validation_error("Expecting up to three integers to represent the decoration slot sizes.", \
                                variant=variant, slot=armour_slot_name)
                    elif any((not isinstance(level, int) or (level <= 0)) for (_, level) in piece.skills.items()):
                        validation_error("Skills must have integer levels above 0.", variant=variant, slot=armour_slot_name)

                    subset[piece.armour_slot] = piece

                variants[variant] = subset

        if len(variants) == 0:
            set_name = set_kwargs["set_name"]
            disc = set_kwargs["discriminator"]
            raise validation_error(f"No armour set variants found for {set_name} {disc}.")

        set_kwargs["variants"] = variants

        set_info_tup = ArmourSetInfo(**set_kwargs)

        if (set_info_tup.set_name, set_info_tup.discriminator) in armour_db_intermediate:
            raise validation_error(f"Duplicate set: {set_info_tup.set_name}, {set_info_tup.discriminator}")

        armour_db_intermediate[(set_info_tup.set_name, set_info_tup.discriminator)] = set_info_tup

    if len(armour_db_intermediate) == 0:
        validation_error("No armour sets found.")

    return armour_db_intermediate


def _obtain_easyiterate_armour_db(original_armour_db):
    intermediate = {slot: [] for slot in ArmourSlot}

    for ((set_name, discrim), set_info) in original_armour_db.items():
        for (variant, variant_pieces) in set_info.variants.items():
            for (gear_slot, piece) in variant_pieces.items():
                intermediate[gear_slot].append(ArmourEasyIterateInfo(set_name=set_name, discrim=discrim, variant=variant))
    return dict(intermediate) # TODO: We should make it so we just start off with a regular dictionary from the start.



# Returns if p1 supercedes p2.
# What this means is that p1 supercedes p2 if it is guaranteed that every possible set of skills, levels, and
# the set bonus of p2 can be recreated by p1 with more flexibility, and/or more skills.
#
# The code for this function is (particularly) disgusting. We should clean it up when possible.
#
# You can technically just make this function return False and the program will still work, albeit super-slow.
# This function only determines if it knows *for sure* if p1 supercedes p2.
# There may be cases where p1 can actually supercede p2, but the current version of this function doesn't
# check for the specific conditions allowing p1 to supercede p2.
def _armour_piece_supercedes(p1, p1_set_bonus, p2, p2_set_bonus, p1_is_preferred):
    assert isinstance(p1, ArmourPieceInfo)
    assert isinstance(p2, ArmourPieceInfo)
    assert isinstance(p1_set_bonus, SetBonus) or (p1_set_bonus is None)
    assert isinstance(p2_set_bonus, SetBonus) or (p2_set_bonus is None)
    assert isinstance(p1_is_preferred, bool)

    if (p2_set_bonus is not None) and (p1_set_bonus is not p2_set_bonus):
        # If p2 provides a set bonus that p1 doesn't, then p1 can't supercede it.
        return False

    # Stage 1: We gather available information.

    p1_size1 = sum(1 for slot_size in p1.decoration_slots if slot_size == 1)
    p1_size2 = sum(1 for slot_size in p1.decoration_slots if slot_size == 2)
    p1_size3 = sum(1 for slot_size in p1.decoration_slots if slot_size == 3)
    p1_size4 = sum(1 for slot_size in p1.decoration_slots if slot_size == 4)

    p2_size1 = sum(1 for slot_size in p2.decoration_slots if slot_size == 1)
    p2_size2 = sum(1 for slot_size in p2.decoration_slots if slot_size == 2)
    p2_size3 = sum(1 for slot_size in p2.decoration_slots if slot_size == 3)
    p2_size4 = sum(1 for slot_size in p2.decoration_slots if slot_size == 4)

    p1_skills = p1.skills
    p2_skills = p2.skills

    # Stage 2: We simplify available information.

    # At worst, we put size-1 jewels in size-4 slots
    p1_slots_underest = (p1_size1, p1_size2, p1_size3 + p1_size4)
    # At best, we can put the equivalent of two size-3 jewels into a size-4 slot
    p2_slots_overest = (p2_size1, p2_size2, p2_size3 + (p2_size4 * 2)) 

    all_skills = set(p1_skills) | set(p2_skills)

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

    if p1_is_preferred:
        return True # p1 is higher in the sort order, so we'll allow it to supercede p2.

    return False


def _obtain_skillsonly_pruned_armour_db(original_easyiterate_armour_db):

    print()
    print("======= Armour Pruning =======")
    print()

    intermediate = {}
    for (gear_slot, piece_list) in original_easyiterate_armour_db.items():

        # We consider set bonuses to make certain pieces worth it.
        best_pieces = [] # [(set_name, discriminator, variant)]

        # This loop is a mostly-unnecessary O(n^2) for n pieces in the list.
        # I have a very good feeling this can be improved on later if needed. Just keeping things simple for now.
        for (i, piece1) in enumerate(piece_list):
            piece1_armour_set = armour_db[(piece1.set_name, piece1.discrim)]
            piece1_set_bonus = piece1_armour_set.set_bonus
            piece1_info = piece1_armour_set.variants[piece1.variant][gear_slot]

            assert isinstance(piece1_armour_set, ArmourSetInfo)
            assert isinstance(piece1_set_bonus, SetBonus) or (piece1_set_bonus is None)
            assert isinstance(piece1_info, ArmourPieceInfo)

            piece1_is_never_superceded = True

            for (j, piece2) in enumerate(piece_list):
                if piece1 is piece2:
                    continue

                piece2_armour_set = armour_db[(piece2.set_name, piece2.discrim)]
                piece2_set_bonus = piece2_armour_set.set_bonus
                piece2_info = piece2_armour_set.variants[piece2.variant][gear_slot]

                assert isinstance(piece2_armour_set, ArmourSetInfo)
                assert isinstance(piece2_set_bonus, SetBonus) or (piece2_set_bonus is None)
                assert isinstance(piece2_info, ArmourPieceInfo)

                # We determine tie-breaker preference using sort order.
                p2_is_preferred = (j > i)

                #piece1_supercedes_piece2 = _armour_piece_supercedes(piece1, piece1_set_bonus, piece2, piece2_set_bonus) 
                piece2_supercedes_piece1 = _armour_piece_supercedes(piece2_info, piece2_set_bonus, piece1_info, \
                                                                        piece1_set_bonus, p2_is_preferred) 
                #if piece2_supercedes_piece1:
                #    print(f"       !!! {gear_slot.name} {piece2.set_name} {piece2.variant.name}  supercedes  " + \
                #            f"{gear_slot.name} {piece1.set_name} {piece1.variant.name}")
                #else:
                #    print(f"           {gear_slot.name} {piece2.set_name} {piece2.variant.name}  does NOT supercede  " + \
                #            f"{gear_slot.name} {piece1.set_name} {piece1.variant.name}")
                
                #print("ret true" if piece2_supercedes_piece1 else "ret false")

                if piece2_supercedes_piece1:
                    piece1_is_never_superceded = False
                    break

            if piece1_is_never_superceded:
                best_pieces.append(piece1)
                #######################################
                buf = []
                buf.append(gear_slot.name.ljust(6))
                buf.append(piece1.set_name.ljust(15))
                #buf.append(piece1.discrim.name.ljust(12))
                buf.append(piece1.variant.value.ascii_postfix)
                buf = " ".join(buf)
                print(f"KEPT: {buf}")
                #######################################
            else:
                #######################################
                buf = []
                buf.append(gear_slot.name.ljust(6))
                buf.append(piece1.set_name.ljust(15))
                #buf.append(piece1.discrim.name.ljust(12))
                buf.append(piece1.variant.value.ascii_postfix)
                buf = " ".join(buf)
                print(f"                                               PRUNED: {buf}")
                #######################################

        print()
        print("=============================")
        print()

        intermediate[gear_slot] = best_pieces

    total_kept = sum(len(x) for (_, x) in intermediate.items())
    total_original = sum(len(x) for (_, x) in original_easyiterate_armour_db.items())

    print()
    print("kept: " + str(total_kept))
    print("pruned: " + str(total_original - total_kept))
    print()

    return intermediate


armour_db = _obtain_armour_db()

# This will contain a more iterator-friendly version, at the cost of indexability.
# (armour_db will be used for indexing.)
ArmourEasyIterateInfo = namedtuple("ArmourEasyIterateInfo", ["set_name", "discrim", "variant"])
easyiterate_armour = _obtain_easyiterate_armour_db(armour_db)

# This will prune out pieces that can be recreated better or more flexibly by another piece.
# Importantly, the data structure is the same as easyiterate_armour.
# This will make this practically interchangable with easyiterate_armour if all you care about are skills.
skillsonly_pruned_armour = _obtain_skillsonly_pruned_armour_db(easyiterate_armour)


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
        set_name, discriminator, variant = armour_dict[slot]

        armour_set = armour_db[(set_name, discriminator)]
        piece = armour_set.variants[variant][slot]

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

