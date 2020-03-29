# -*- coding: ascii -*-

"""
Filename: loggingutils.py
Author:   contact@simshadows.com

Logging stuff.
"""

import logging

LOGGER_LEVEL = logging.DEBUG
LOGFILE_PATH = "debugging_dumps/mhwi-build-search.log"

_APPSTATS_LOGGER_NAME = "appstats"

_root_logger = None
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

def setup_logging():
    global _root_logger
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

    # Application Statistics Logger

    _appstats_logger = logging.getLogger(_APPSTATS_LOGGER_NAME)

    return

