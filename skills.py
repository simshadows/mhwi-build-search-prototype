"""
Filename: skills.py
Author:   contact@simshadows.com
"""

from collections import namedtuple, defaultdict
from enum import Enum, unique

SkillInfo = namedtuple(
    "SkillInfo",
    [
        # FIELDS REQUIRED TO BE SET

        "name",    # In-game name, exactly as written. All skills must have a name string.
        "limit",   # Maximum number of levels obtainable NORMALLY.
        "tooltip", # In-game tooltip, exactly as written. All skills must have a tooltip string.

        # FIELDS WITH DEFAULTS

        "extended_limit", # Extra levels over the maximum, obtainable with special skills like Agitator Secret.
                          # This ADDS onto the number set by the limit field. E.g. extended_limit=2 for Agitator Secret.
                          # IMPORTANT: We are assuming for now that there are only two limits.

        "info",          # More information about the skill. I probably wrote this myself. If no info, put an empty string.
        "previous_name", # If the skill name was changed, put it here. If no previous name, put None.
    ],
    defaults=[
        #1,   # levels          | Seems like a reasonable default. (Not currently used. Might use it to introduce set bonuses.)
        0,    # extended_levels | Most skills don't have extensions.
              #                 |
        "",   # info            | I don't care to write about *ALL* skills yet.
        None, # info            | Most skills don't have previous names.
    ],
)

@unique
class Skill(Enum):

    AFFINITY_SLIDING = \
            SkillInfo(
                name  = "Affinity Sliding",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    AGITATOR = \
            SkillInfo(
                name  = "Agitator",
                limit = 5,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    AIRBORNE = \
            SkillInfo(
                name  = "Airborne",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    AQUATIC_POLAR_MOBILITY = \
            SkillInfo(
                name  = "Aquatic/Polar Mobility",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    ARTILLERY = \
            SkillInfo(
                name  = "Artillery",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    ATTACK_BOOST = \
            SkillInfo(
                name  = "Attack Boost",
                limit = 7,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    BBQ_MASTER = \
            SkillInfo(
                name  = "BBQ Master",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    BLAST_ATTACK = \
            SkillInfo(
                name  = "Blast Attack",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    BLAST_FUNCTIONALITY = \
            SkillInfo(
                name  = "Blast Functionality",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    BLAST_RESISTANCE = \
            SkillInfo(
                name  = "Blast Resistance",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    BLEEDING_RESISTANCE = \
            SkillInfo(
                name  = "Bleeding Resistance",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    BLIGHT_RESISTANCE = \
            SkillInfo(
                name  = "Blight Resistance",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    BLINDSIDER = \
            SkillInfo(
                name  = "Blindsider",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    BOMBARDIER = \
            SkillInfo(
                name  = "Bombardier",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    BOTANIST = \
            SkillInfo(
                name  = "Botanist",
                limit = 4,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    BOW_CHARGE_PLUS = \
            SkillInfo(
                name  = "Bow Charge Plus",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    CAPACITY_BOOST = \
            SkillInfo(
                name  = "Capacity Boost",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    CARVING_PRO = \
            SkillInfo(
                name  = "Carving Pro",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    CLIFFHANGER = \
            SkillInfo(
                name  = "Cliffhanger",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    COALESCENCE = \
            SkillInfo(
                name  = "Coalescence",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    COLDPROOF = \
            SkillInfo(
                name  = "Coldproof",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    CONSTITUTION = \
            SkillInfo(
                name  = "Constitution",
                limit = 5,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    CRITICAL_BOOST = \
            SkillInfo(
                name  = "Critical Boost",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    CRITICAL_DRAW = \
            SkillInfo(
                name  = "Critical Draw",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    CRITICAL_ELEMENT = \
            SkillInfo(
                name  = "Critical Element",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    CRITICAL_EYE = \
            SkillInfo(
                name  = "Critical Eye",
                limit = 7,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    CRITICAL_STATUS = \
            SkillInfo(
                name  = "Critical Status",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    DEFENSE_BOOST = \
            SkillInfo(
                name  = "Defense Boost",
                limit = 7,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    DETECTOR = \
            SkillInfo(
                name  = "Detector",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    DIVINE_BLESSING = \
            SkillInfo(
                name  = "Divine Blessing",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    DRAGON_ATTACK = \
            SkillInfo(
                name  = "Dragon Attack",
                limit = 5,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    DRAGON_RESISTANCE = \
            SkillInfo(
                name  = "Dragon Resistance",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    DUNGMASTER = \
            SkillInfo(
                name  = "Dungmaster",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    EARPLUGS = \
            SkillInfo(
                name  = "Earplugs",
                limit = 5,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    EFFLUVIA_RESISTANCE = \
            SkillInfo(
                name  = "Effluvia Resistance",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    EFFLUVIAL_EXPERT = \
            SkillInfo(
                name  = "Effluvial Expert",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    ELDERSEAL_BOOST = \
            SkillInfo(
                name  = "Elderseal Boost",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    ENTOMOLOGIST = \
            SkillInfo(
                name  = "Entomologist",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    EVADE_EXTENDER = \
            SkillInfo(
                name  = "Evade Extender",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    EVADE_WINDOW = \
            SkillInfo(
                name  = "Evade Window",
                limit = 5,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    FIRE_ATTACK = \
            SkillInfo(
                name  = "Fire Attack",
                limit = 5,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    FIRE_RESISTANCE = \
            SkillInfo(
                name  = "Fire Resistance",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    FLINCH_FREE = \
            SkillInfo(
                name  = "Flinch Free",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    FOCUS = \
            SkillInfo(
                name  = "Focus",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    FORAGERS_LUCK = \
            SkillInfo(
                name  = "Forager's Luck",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    FORTIFY = \
            SkillInfo(
                name  = "Fortify",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    FREE_ELEM_AMMO_UP = \
            SkillInfo(
                name  = "Free Elem/Ammo Up",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    FREE_MEAL = \
            SkillInfo(
                name  = "Free Meal",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    GEOLOGIST = \
            SkillInfo(
                name  = "Geologist",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    GUARD = \
            SkillInfo(
                name  = "Guard",
                limit = 5,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    HANDICRAFT = \
            SkillInfo(
                name  = "Handicraft",
                limit = 5,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    HEALTH_BOOST = \
            SkillInfo(
                name  = "Health Boost",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    HEAT_GUARD = \
            SkillInfo(
                name  = "Heat Guard",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    HEAVY_ARTILLERY = \
            SkillInfo(
                name  = "Heavy Artillery",
                limit = 2,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    HEROICS = \
            SkillInfo(
                name  = "Heroics",
                limit = 5,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    HONEY_HUNTER = \
            SkillInfo(
                name  = "Honey Hunter",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    HORN_MAESTRO = \
            SkillInfo(
                name  = "Horn Maestro",
                limit = 2,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    HUNGER_RESISTANCE = \
            SkillInfo(
                name  = "Hunger Resistance",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    ICE_ATTACK = \
            SkillInfo(
                name  = "Ice Attack",
                limit = 5,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    ICE_RESISTANCE = \
            SkillInfo(
                name  = "Ice Resistance",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    INTIMIDATOR = \
            SkillInfo(
                name  = "Intimidator",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    IRON_SKIN = \
            SkillInfo(
                name  = "Iron Skin",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    ITEM_PROLONGER = \
            SkillInfo(
                name  = "Item Prolonger",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    JUMP_MASTER = \
            SkillInfo(
                name  = "Jump Master",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    LATENT_POWER = \
            SkillInfo(
                name  = "Latent Power",
                limit = 5,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    LEAP_OF_FAITH = \
            SkillInfo(
                name  = "Leap of Faith",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    MARATHON_RUNNER = \
            SkillInfo(
                name  = "Marathon Runner",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    MASTER_FISHER = \
            SkillInfo(
                name  = "Master Fisher",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    MASTER_GATHERER = \
            SkillInfo(
                name  = "Master Gatherer",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    MASTER_MOUNTER = \
            SkillInfo(
                name  = "Master Mounter",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    MAXIMUM_MIGHT = \
            SkillInfo(
                name  = "Maximum Might",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    MUCK_RESISTANCE = \
            SkillInfo(
                name  = "Muck Resistance",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    MUSHROOMANCER = \
            SkillInfo(
                name  = "Mushroomancer",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    NON_ELEMENTAL_BOOST = \
            SkillInfo(
                name  = "Non-elemental Boost",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    NORMAL_SHOTS = \
            SkillInfo(
                name  = "Normal Shots",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    OFFENSIVE_GUARD = \
            SkillInfo(
                name  = "Offensive Guard",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    PALICO_RALLY = \
            SkillInfo(
                name  = "Palico Rally",
                limit = 5,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    PARALYSIS_ATTACK = \
            SkillInfo(
                name  = "Paralysis Attack",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    PARALYSIS_FUNCTIONALITY = \
            SkillInfo(
                name  = "Paralysis Functionality",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    PARALYSIS_RESISTANCE = \
            SkillInfo(
                name  = "Paralysis Resistance",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    PARTBREAKER = \
            SkillInfo(
                name  = "Partbreaker",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    PEAK_PERFORMANCE = \
            SkillInfo(
                name  = "Peak Performance",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    PIERCING_SHOTS = \
            SkillInfo(
                name  = "Piercing Shots",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    POISON_ATTACK = \
            SkillInfo(
                name  = "Poison Attack",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    POISON_FUNCTIONALITY = \
            SkillInfo(
                name  = "Poison Functionality",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    POISON_RESISTANCE = \
            SkillInfo(
                name  = "Poison Resistance",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    POWER_PROLONGER = \
            SkillInfo(
                name  = "Power Prolonger",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    PRO_TRANSPORTER = \
            SkillInfo(
                name  = "Pro Transporter",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    PROVOKER = \
            SkillInfo(
                name  = "Provoker",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    QUICK_SHEATH = \
            SkillInfo(
                name  = "Quick Sheath",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    RECOVERY_SPEED = \
            SkillInfo(
                name  = "Recovery Speed",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    RECOVERY_UP = \
            SkillInfo(
                name  = "Recovery Up",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    RESENTMENT = \
            SkillInfo(
                name  = "Resentment",
                limit = 5,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    RESUSCITATE = \
            SkillInfo(
                name  = "Resuscitate",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    SAFE_LANDING = \
            SkillInfo(
                name  = "Safe Landing",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    SCENTHOUND = \
            SkillInfo(
                name  = "Scenthound",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    SCHOLAR = \
            SkillInfo(
                name  = "Scholar",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    SCOUTFLY_RANGE_UP = \
            SkillInfo(
                name  = "Scoutfly Range Up",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    SLEEP_ATTACK = \
            SkillInfo(
                name  = "Sleep Attack",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    SLEEP_FUNCTIONALITY = \
            SkillInfo(
                name  = "Sleep Functionality",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    SLEEP_RESISTANCE = \
            SkillInfo(
                name  = "Sleep Resistance",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    SLINGER_CAPACITY = \
            SkillInfo(
                name  = "Slinger Capacity",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    SLUGGER = \
            SkillInfo(
                name  = "Slugger",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    SPECIAL_AMMO_BOOST = \
            SkillInfo(
                name  = "Special Ammo Boost",
                limit = 2,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    SPEED_CRAWLER = \
            SkillInfo(
                name  = "Speed Crawler",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    SPEED_EATING = \
            SkillInfo(
                name  = "Speed Eating",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    SPEED_SHARPENING = \
            SkillInfo(
                name  = "Speed Sharpening",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    SPREAD_POWER_SHOTS = \
            SkillInfo(
                name  = "Spread/Power Shots",
                limit = 1,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    STAMINA_SURGE = \
            SkillInfo(
                name  = "Stamina Surge",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    STAMINA_THIEF = \
            SkillInfo(
                name  = "Stamina Thief",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    STEALTH = \
            SkillInfo(
                name  = "Stealth",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    STUN_RESISTANCE = \
            SkillInfo(
                name  = "Stun Resistance",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    SURVIVAL_EXPERT = \
            SkillInfo(
                name  = "Survival Expert",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,

                previous_name = "Sporepuff Expert"
            )

    THUNDER_ATTACK = \
            SkillInfo(
                name  = "Thunder Attack",
                limit = 5,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    THUNDER_RESISTANCE = \
            SkillInfo(
                name  = "Thunder Resistance",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    TOOL_SPECIALIST = \
            SkillInfo(
                name  = "Tool Specialist",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    TREMOR_RESISTANCE = \
            SkillInfo(
                name  = "Tremor Resistance",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    WATER_ATTACK = \
            SkillInfo(
                name  = "Water Attack",
                limit = 5,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    WATER_RESISTANCE = \
            SkillInfo(
                name  = "Water Resistance",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    WEAKNESS_EXPLOIT = \
            SkillInfo(
                name  = "Weakness Exploit",
                limit = 3,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    WIDE_RANGE = \
            SkillInfo(
                name  = "Wide-Range",
                limit = 5,

                tooltip =
                    """
                    ((TODO))
                    """,
            )

    WINDPROOF = \
            SkillInfo(
                name  = "Windproof",
                limit = 5,

                tooltip =
                    """
                    ((TODO))
                    """,
            )


# This will take a dict like {Skill.AGITATOR: 10, ...} and clip it down to the maximum.
# This also returns a defaultdict with default value of zero.
def clipped_skills_defaultdict(skills_dict):
    assert all(level >= 0 for (_, level) in skills_dict.items()) # We shouldn't be seeing negative skill levels.
    return defaultdict(lambda : 0, {skill: min(level, skill.value.limit) for (skill, level) in skills_dict.items()})


def _skills_integrity_check():
    prev_tup = None
    for skill in Skill:
        tup = skill.value

        # Type and value checking

        if (not isinstance(tup.name, str)) or (len(tup.name) == 0):
            raise ValueError(str(skill) + ": Invalid name value.")

        elif (not isinstance(tup.limit, int)) or (tup.limit <= 0):
            raise ValueError(str(skill) + ": Invalid level limit value.")
        elif (tup.limit + tup.extended_limit > 7):
            raise ValueError(str(skill) + ": Limit value doesn't seem reasonable.")
        
        elif (not isinstance(tup.tooltip, str)) or (len(tup.tooltip) == 0):
            raise ValueError(str(skill) + ": Invalid tooltip value.")

        elif (not isinstance(tup.extended_limit, int)) or (tup.extended_limit < 0):
            raise ValueError(str(skill) + ": Invalid extended level limit value.")

        elif (not isinstance(tup.tooltip, str)):
            raise ValueError(str(skill) + ": Invalid skill info value.")

        elif not (isinstance(tup.previous_name, str) or (tup.previous_name is None)):
            raise ValueError(str(skill) + ": Invalid previous-name value.")

        # Checking if we wrote out the tuples in alphabetical order.
        # (This doesn't actually affect program functionality, but it's more organized to do it this way.)

        if (prev_tup is not None) and (prev_tup.name >= tup.name):
            raise ValueError(str(skill) + ": Not in alphabetical order.")

        prev_tup = tup

    return
    
_skills_integrity_check()

