# -*- coding: ascii -*-

"""
Filename: loggingutils.py
Author:   contact@simshadows.com

Logging stuff.
"""

import logging

from .utils import ENCODING

LOGGER_LEVEL = logging.DEBUG
LOGFILE_PATH = "debugging_dumps/mhwi-build-search.log"

_DEBUGGING_WEAPONS_PRUNED_DUMP_FILENAME = "debugging_dumps/weapons_pruned_dump.txt"
_DEBUGGING_WEAPONS_KEPT_DUMP_FILENAME = "debugging_dumps/weapons_kept_dump.txt"


_APPSTATS_LOGGER_NAME = "appstats"

_root_logger = None
logger = None
_appstats_logger = None


#_logger_levels = {
#    "CRITICAL": logging.CRITICAL,
#    "ERROR":    logging.ERROR,
#    "WARNING":  logging.WARNING,
#    "INFO":     logging.INFO,
#    "DEBUG":    logging.DEBUG,
#}
#def safe_parse_logging_level(text):
#    return _logger_levels[text.strip().upper()]


def log_appstats(name, stat):
    global _appstats_logger
    assert isinstance(name, str)
    assert isinstance(stat, int) # or float?
    _appstats_logger.info(f"{name} = {stat}")
    return


# This function is specifically intended for query_weapons.py get_pruned_weapon_combos().
def dump_pruned_weapon_combos(before_combos, after_combos, left_supercedes_right):
    # First, we print weapons pruned.
    diff = [x for x in before_combos if (x not in after_combos)]
    buf = []
    assert len(diff) > 0
    for x in diff:
        superceding_set = None
        effectively_equivalent = None
        for y in after_combos:
            result = left_supercedes_right(y, x)
            if result is True:
                superceding_set = y
                break
            elif result is None:
                effectively_equivalent = y
        assert (superceding_set is not None) or (effectively_equivalent is not None)
        buf.append(x[0][0].name)
        buf.append(x[0][1].to_str_debugging())
        buf.append(x[0][2].to_str_debugging())
        if effectively_equivalent:
            buf.append("<IS EQUIVALENT TO>")
            buf.append(effectively_equivalent[0][0].name)
            buf.append(effectively_equivalent[0][1].to_str_debugging())
            buf.append(effectively_equivalent[0][2].to_str_debugging())
        else:
            buf.append("<IS SUPERCEDED BY>")
            buf.append(superceding_set[0][0].name)
            buf.append(superceding_set[0][1].to_str_debugging())
            buf.append(superceding_set[0][2].to_str_debugging())
        buf.append("\n")
    with open(_DEBUGGING_WEAPONS_PRUNED_DUMP_FILENAME, encoding=ENCODING, mode="w") as f:
        f.write("\n".join(buf))
    logger.info(f"Generated dump: {_DEBUGGING_WEAPONS_PRUNED_DUMP_FILENAME}")
    # Then, we print weapons kept.
    buf = []
    assert len(after_combos) > 0
    for x in after_combos:
        buf.append(x[0][0].name)
        buf.append(x[0][1].to_str_debugging())
        buf.append(x[0][2].to_str_debugging())
        buf.append("\n")
    with open(_DEBUGGING_WEAPONS_KEPT_DUMP_FILENAME, encoding=ENCODING, mode="w") as f:
        f.write("\n".join(buf))
    logger.info(f"Generated dump: {_DEBUGGING_WEAPONS_KEPT_DUMP_FILENAME}")
    return


def setup_logging():
    global _root_logger
    global logger
    global _appstats_logger

    _root_logger = logging.getLogger(None)
    _root_logger.setLevel(LOGGER_LEVEL)

    logfile_fmt = logging.Formatter("%(asctime)s [%(levelname)s] (%(name)s) %(message)s")
    stderr_fmt  = logging.Formatter("[%(levelname)s] (%(name)s) %(message)s")

    # File Handler
    fh = logging.FileHandler(LOGFILE_PATH)
    #fh.setLevel(logging.DEBUG)
    fh.setFormatter(logfile_fmt)
    _root_logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    #ch.setLevel(logging.DEBUG)
    ch.setFormatter(stderr_fmt)
    _root_logger.addHandler(ch)

    # Other Loggers
    logger = logging.getLogger(__name__)
    _appstats_logger = logging.getLogger(_APPSTATS_LOGGER_NAME)

    return

