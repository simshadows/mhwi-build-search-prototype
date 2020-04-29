# Sim's MHWI Build Search Tool (Prototype)

This is a prototype automated build optimization program for the game Monster Hunter World Iceborne!

Being a prototype codebase, it's terribly written and many questionable decisions have been made. Hopefully, these will be improved on in future rewrites. I don't want to spend too much time on something that is not intended to be the final version.

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

## Planned Development Roadmap

1) Make a simple EFR optimizer for GS and SnS. I want this script to automatically create entire builds with as little manual tweaking as possible (except for updating the database, or stating build constraints).

2) Implement some form of handling for common non-EFR parameters, notably the Focus and Health Boost skills.

3) Implement elemental/status calculations.

4) Implement elemental/status optimization for the automated build searcher.

5) Implement build saving. (It might just be as simple as saving the terminal output, but maybe I can make something better? Maybe it automatically generates a honeyhunterworld.com link?)

6) Slowly implement each of the other weapon types. (This is expected to be a complex stage due to all the different mechanics and oddities unique to certain weapons, not to mention the fact that I hardly understand many of them.)

7) Implement a GUI front-end. (Ideally something cross-platform.)

8) Create a framework that can be used to help build other build optimization tools.

Because the runtime is turning out to be pretty slow and Python's multithreaded coordination is really messy, **I'm also planning on rewriting this in faster languages, like *C++* or *Haskell*.** I suppose this Python program could be considered more of a prototype, and a proof of concept that the combinatorial complexity can indeed be cut down to give somewhat decent runtimes, even on a slow implementation like CPython!

## TODOs

- Free Element will need to be taken into account since adding it can actually reduce a build's EFR by disabling Non-elemental Boost. My pruning algorithms currently don't take this into account, so it is possible for a gear piece with Free Element to cause another gear piece without Free Element to be pruned, even if it may be better for pure-raw builds.

## License

This software is licensed under the GNU General Public License v3.0.

```
MIT License

Copyright (c) 2020 simshadows

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

