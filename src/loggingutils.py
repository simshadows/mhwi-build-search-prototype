# -*- coding: ascii -*-

"""
Filename: loggingutils.py
Author:   contact@simshadows.com

Logging and data-dumping utilities.
"""

import logging
import time

from .utils import (ENCODING,
                   ensure_directory)

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
    assert isinstance(stat, int) or isinstance(stat, float)
    _appstats_logger.info(f"{name} = {stat}")
    return

def log_appstats_reduction(name, pre, post):
    global _appstats_logger
    assert isinstance(name, str)
    assert isinstance(pre, int)
    assert isinstance(post, int)
    prop = round((post / pre) * 100, 2)
    _appstats_logger.info(f"{name}: {pre} --> {post} ({prop}% kept)")
    return

def log_appstats_generic(msg):
    global _appstats_logger
    assert isinstance(msg, str)
    _appstats_logger.info(msg)
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


class ExecutionProgress:

    __slots__ = [
            "_msg",
            "_total_progress_segments",
            "_curr_progress_segment",
            "_start_time",
            "_granularity",
        ]

    def __init__(self, msg, total_progress_segments, granularity=1):
        assert isinstance(msg, str) and (len(msg.strip()) > 0)
        assert (isinstance(total_progress_segments, int) and (total_progress_segments > 0)) or (total_progress_segments is None)
        assert isinstance(granularity, int) and (granularity > 0)

        self._msg = msg
        self._total_progress_segments = total_progress_segments # If this is none, we update later.
        self._curr_progress_segment = 0
        self._start_time = time.time()
        self._granularity = granularity
        return

    def ensure_total_progress_count(self, total_progress_segments):
        if self._total_progress_segments is None:
            self._total_progress_segments = total_progress_segments
        elif self._total_progress_segments != total_progress_segments:
            raise RuntimeError(f"Progress segment mismatch! Expected {self._total_progress_segments}, " \
                                    f"we got {total_progress_segments}")
        return

    def update_and_log_progress(self, foreign_logger):
        assert self._total_progress_segments is not None
        self._curr_progress_segment += 1

        if (self._granularity == 1) or (self._curr_progress_segment % (self._granularity - 1) == 0) \
                or (self._curr_progress_segment == 1) \
                or (self._curr_progress_segment == self._total_progress_segments):

            progress_segment_size = 1 / self._total_progress_segments
            seg_str = f"{self._curr_progress_segment}/{self._total_progress_segments}"

            curr_progress = self._curr_progress_segment * progress_segment_size
            curr_progress_percent_rnd = round(curr_progress * 100, 2)
            curr_progress_str = f"{curr_progress_percent_rnd:.02f}%"

            progress_real_time = time.time() - self._start_time
            progress_real_time_minutes = int(progress_real_time // 60)
            progress_real_time_seconds = int(progress_real_time % 60)
            progress_real_time_str = f"{progress_real_time_minutes:02}:{progress_real_time_seconds:02}"

            seconds_per_segment = progress_real_time / self._curr_progress_segment
            seconds_estimate = seconds_per_segment * self._total_progress_segments
            estimate_minutes = int(seconds_estimate // 60)
            estimate_seconds = int(seconds_estimate % 60) # This naming is so confusing lmao
            estimate_str = f"{estimate_minutes:02}:{estimate_seconds:02}"

            buf = f"[{self._msg} PROGRESS: {seg_str} ({curr_progress_str})] elapsed {progress_real_time_str}, estimate {estimate_str}"
            foreign_logger.info(buf)
        return


def setup_logging():
    global _root_logger
    global logger
    global _appstats_logger

    ensure_directory(LOGFILE_PATH)

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

