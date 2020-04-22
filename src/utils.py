# -*- coding: ascii -*-

"""
Filename: utils.py
Author:   contact@simshadows.com

Contains general utility stuff.
"""

import os
import json
from enum import Enum, auto
from math import floor, ceil
from itertools import zip_longest


_CWD = os.getcwd()
ENCODING = "utf-8"


class _InternalToken(Enum):
    NULL_REFERENCE = auto()


def ensure_directory(relfilepath):
    absfilepath = os.path.join(_CWD, relfilepath)
    absdir = os.path.dirname(absfilepath)
    try:
        os.makedirs(absdir)
    except FileExistsError:
        pass
    return


def json_read(relfilepath):
    with open(relfilepath, encoding=ENCODING, mode="r") as f:
        return json.loads(f.read())


def json_dumps_formatted(data):
    return json.dumps(data, sort_keys=True, indent=4)


# Also will probably be useful, e.g. when I implement caching.
#def json_write(relfilepath, *, data=None):
#    mkdir_recursive(relfilepath)
#    with open(relfilepath, encoding=ENCODING, mode="w") as f:
#        f.write(json.dumps(data, sort_keys=True, indent=4))
#    return


# Recipe from Python 3.8 Itertools documentation.
def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


# A predictable shuffle function, as long as the list length remains constant, regardless of list element contents.
# Predictability is a very important feature of this function's applications.
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


def all_unique(iterable_obj):
    return len(set(iterable_obj)) == len(iterable_obj)


# Prunes by a "supercedes" rule, where some objects in iterable can be replaced by other objects.
#
# left_supercedes_right is a function (of two arguments) that returns one of three values:
#   1) True if it is guaranteed that the first argument can replace the right argument,
#   2) False otherwise, or
#   3) None if both arguments are effectively equal, but that we want one of them to be pruned
#      away. In this case, prune_by_superceding() will arbitrarily prune one of the two elements
#      (probably by sort order).
#
# execute_per_iteration is a function (of no arguments) that is called at the end of every
# iteration through iterable. The very last execution of this function happens once
# prune_by_superceding() has dealt with the last element in iterable. This is useful for
# implementing progress counters (since this function can run rather slow).
#
# IMPORTANT NOTE:
#   left_supercedes_right may be an underestimating function. What this means is that if
#   left_supercedes_right returns True, it is guaranteed that the left argument supercedes
#   the right argument, but if left_supercedes_right returns False, then the left argument
#   may or may not actually supercede the right argument.
#
#   For example, it is logically sound to have this function be a constant function that
#   returns False. This will mean this function simply returns a list containing exactly
#   all elements of iterable.
#
#   If left_supercedes_right returns True on a pair of elements where the left argument
#   does not actually supercede the right argument, then the behaviour of this function
#   is undefined and invalid.
#
def prune_by_superceding(iterable, left_supercedes_right, execute_per_iteration=lambda : None):
    assert callable(left_supercedes_right)

    ret = []

    li = list(iterable)
    for i, right in enumerate(li):
        right_is_never_superceded = True
        for j, left in enumerate(li):
            if i == j:
                continue # We don't compare the same element
            result = left_supercedes_right(left, right)
            if result is None: # The decision function calls for a tie-breaker.
                result = (i < j) # We arbitrarily favour the left element.
            if result:
                right_is_never_superceded = False
                break
        if right_is_never_superceded:
            ret.append(right)
        execute_per_iteration()
    return ret


def lists_of_dicts_are_equal(a, b):
    assert isinstance(a, list)
    assert isinstance(b, list)
    assert all(isinstance(x, dict) for x in a)
    assert all(isinstance(x, dict) for x in b)

    if len(a) != len(b):
        return False

    for d1 in a:
        d1_in_b = False
        for d2 in b:
            if d1 == d2:
                d1_in_b = True
                break
        if not d1_in_b:
            return False
    return True


# Determines if Counter a is equal to Counter b.
def counters_are_equal(a, b):
    assert isinstance(a, dict) and all(isinstance(v, int) for (_, v) in a.items())
    assert isinstance(b, dict) and all(isinstance(v, int) for (_, v) in b.items())
    return (set(a) == set(b)) and all(av == b[ak] for (ak, av) in a.items())


# Determines if Counter a is a subset of Counter b.
# Do note that this function can also accept dictionaries with data that act like Counters!
def counter_is_subset(a, b):
    assert isinstance(a, dict) and all(isinstance(v, int) for (_, v) in a.items())
    assert isinstance(b, dict) and all(isinstance(v, int) for (_, v) in b.items())
    if not (set(a) <= set(b)):
        return False
    return all(av <= b[ak] for (ak, av) in a.items())


def dict_enumkey_intval_str(d):
    return "\n".join(f"{k.name}: {v}" for (k, v) in d.items())


def get_humanreadable_from_enum_counter(d):
    return "\n".join(f"{k.name}: {v}" for (k, v) in d.items())
def get_humanreadable_from_enum_list(x):
    return "\n".join(f"{v.name}" for v in x)


def list_obeys_sort_order(l, key=lambda x : x, reverse=False):
    assert isinstance(l, list)
    assert callable(key)
    if reverse:
        for i in range(len(l) - 1):
            if key(l[i]) < key(l[i + 1]):
                return False
    else:
        for i in range(len(l) - 1):
            if key(l[i]) > key(l[i + 1]):
                return False
    return True

