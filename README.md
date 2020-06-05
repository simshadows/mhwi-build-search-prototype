# Sim's MHWI Build Search Tool (Prototype)

A prototype automated build optimization program for the game Monster Hunter World Iceborne!

**This codebase has been completely rewritten in C++ ([here](https://github.com/simshadows/mhwi-build-search)) and will no longer be maintained. However, I will continue to host it for archival purposes.**

## How Do I Use It?

I'm not intending to give it a good user interface yet, but if you *really* insist, then:

1) Install at least Python 3.6.

2) Open a terminal window in the repository and execute `$ python3.6 -O mhwi_build_search.py search search_benchmark1.json`.

3) Enjoy. You literally have nothing else to do other than watch the terminal output because this program has no user interface.

## Database Note

### Weapons

Only greatswords have been added to the database (with a few minor additions from other weapon classes, for debugging purposes).

Additionally, the only Safi greatsword in the database is the blast variant (*Safi's Shattersplitter*). I'll add the other variants in later when the element actually matters.

### Armour

All Master Rank armour up until (and including) Guildwork has been added. Anything beyond that is a bit patchy (though I do try to add all of the important pieces of armour).

In the interest of simplicity, full armour sets will NOT be added to the database for now. At the time of writing, these are:

- Geralt Alpha
- Ciri Alpha
- Leon Alpha+
- Claire Alpha+

In the interest of validity, I will only add things that appear in the PC version of Monster Hunter World. All console exclusives will be left out (at least until I can figure out a good way to allow the user to filter things out).

Other notable sets that should hopefully be added in the near future:

- Acrobat Earrings
- Showman Earrings

## TODOs

- Free Element will need to be taken into account since adding it can actually reduce a build's EFR by disabling Non-elemental Boost. My pruning algorithms currently don't take this into account, so it is possible for a gear piece with Free Element to cause another gear piece without Free Element to be pruned, even if it may be better for pure-raw builds.
