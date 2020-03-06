# -*- coding: ascii -*-

"""
Filename: utils.py
Author:   contact@simshadows.com

Contains general utility stuff.
"""

#import os
import time
import json
from enum import Enum, auto
from math import floor, ceil
from itertools import zip_longest

#_CWD = os.getcwd()
_ENCODING = "utf-8"

class _InternalToken(Enum):
    NULL_REFERENCE = auto()

# Probably will be useful, e.g. when I implement caching.
#def mkdir_recursive(relfilepath):
#    absfilepath = os.path.join(_CWD, relfilepath)
#    absdir = os.path.dirname(absfilepath)
#    try:
#        os.makedirs(absdir)
#    except FileExistsError:
#        pass
#    return

def json_read(relfilepath):
    with open(relfilepath, encoding=_ENCODING, mode="r") as f:
        return json.loads(f.read())

# Also will probably be useful, e.g. when I implement caching.
#def json_write(relfilepath, *, data=None):
#    mkdir_recursive(relfilepath)
#    with open(relfilepath, encoding=_ENCODING, mode="w") as f:
#        f.write(json.dumps(data, sort_keys=True, indent=3))
#    return

def update_and_print_progress(msg, curr_progress_segment, total_progress_segments, start_real_time_seconds):
    progress_segment_size = 1 / total_progress_segments

    curr_progress_segment += 1
    curr_progress = curr_progress_segment * progress_segment_size
    curr_progress_percent_rnd = round(curr_progress * 100, 2)
    curr_progress_str = f"{curr_progress_percent_rnd:.02f}%"

    progress_real_time = time.time() - start_real_time_seconds
    progress_real_time_minutes = int(progress_real_time // 60)
    progress_real_time_seconds = int(progress_real_time % 60)
    progress_real_time_str = f"{progress_real_time_minutes:02}:{progress_real_time_seconds:02}"

    seconds_per_segment = progress_real_time / curr_progress_segment
    seconds_estimate = seconds_per_segment * total_progress_segments
    estimate_minutes = int(seconds_estimate // 60)
    estimate_seconds = int(seconds_estimate % 60) # This naming is so confusing lmao
    estimate_str = f"{estimate_minutes:02}:{estimate_seconds:02}"

    print(f"[{msg} PROGRESS: {curr_progress_str}] elapsed {progress_real_time_str}, estimate {estimate_str}")

    return curr_progress_segment

# Recipe from Python 3.8 Itertools documentation.
def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)

# A predictable shuffle function, as long as the list length remains constant.
def interleaving_shuffle(list_obj, max_partitions=8):
    assert isinstance(list_obj, list)
    num_partitions = min(int(floor(len(list_obj) / 32)), max_partitions)
    partition_size = int(ceil(len(list_obj) / num_partitions))
    partitions = list(grouper(list_obj, partition_size, fillvalue=_InternalToken.NULL_REFERENCE))
    for i in range(partition_size):
        for partition in partitions:
            obj = partition[i]
            if obj is not _InternalToken.NULL_REFERENCE:
                yield partition[i]
    return

