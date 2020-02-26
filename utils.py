"""
Filename: utils.py
Author:   contact@simshadows.com

Contains general utility stuff.
"""

#import os
import json

#_CWD = os.getcwd()
_ENCODING = "utf-8"

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

