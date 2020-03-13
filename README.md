# Sim's MHWI Build Search Tool

**CURRENT A WORK IN PROGRESS.** I'm developing this to aid in build optimization for the game Monster Hunter World Iceborne!

This project is written for Python 3.8.

## How Do I Use It?

I'm not intending to give it a good user interface yet, but if you *really* insist, then:

1) Install at least Python 3.8.

2) Open a terminal window in the repository and execute `$ python3.8 -O mhwi_build_search.py search search_benchmark1.json`.

3) Enjoy. You literally have nothing else to do other than watch the terminal output because this program has no user interface.

However, the code has 32 hardcoded as the number of worker threads. Just go in and change this to however many CPU threads exist in your computer. It should be the line `NUM_WORKERS = 32` somewhere on the top of `search.py`.

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

1) I'll need to be confident that the armour pruning doesn't throw away armour pieces that are still useful. This will need continued testing.

2) I'll also need to be confident that the armour pruning doesn't throw away armour *sets* that are still useful. This will need continued testing.

3) Free Element will need to be taken into account since adding it can actually reduce a build's EFR by disabling Non-elemental Boost. My pruning algorithms currently don't take this into account, so it is possible for a gear piece with Free Element to cause another gear piece without Free Element to be pruned, even if it may be better for pure-raw builds.

4) I think the decoration combination pruning has a few bugs that cause it to over-prune. However, the over-pruning will *rarely affect real builds* as it's really only applicable for cases where you have too few decorations to actually put into the slots. However, I shoudl really fix the bugs anyway.

## Nerd Stuff (THIS IS OUTDATED)

The current version of the search algorithm is brute force with pruning.

This works by first going through the list of head pieces and pruning away all head pieces that is *clearly inferior* to any other head piece. Head piece A is clearly inferior to head piece B if B can reproduce any possible combination of skills (and their respective levels) that you can make with A, possibly even with extras. This process is then repeated for the chest, hands, waist, and leg slots.

As a concrete example, *Kaiser Vambraces Alpha+* is clearly inferior to *Kaiser Vambraces Beta+*. This is because while Beta+ lacks a level of Weakness Exploit, it comes with an extra Level 4 decoration slot compared to Alpha+. A decoration containing Weakness Exploit easily fits in this slot.

Charms and decorations are also pruned to ignore charms with skills we don't care about. Weapon augments are always practically maximized. For example, we don't care about having only Attack I if we can also add Attack II or Affinity I on top of it. Weapon custom upgrades are also somewhat pruned in a similar fashion.

Once all the pruning described above has taken place, we simply try every possible combination.

### Current Efficiency

Armour piece pruning has the potential to prune all gear down to mostly Master Rank Beta+. Assuming a ballpark of `300` pieces for each of the categories of head, chest, hands, waist, and legs, we have `300^5 = approx. 2.4 * 10^12` before pruning. Pruning down to a conservative `150` pieces brings us down to `7.6 * 10^10`. **Though, this is yet to be tested on a full armour database since I'm using a subset of armour for testing.** My current pruning algorithm runs in `O(n^2)` for `n` individual pieces in each armour set.

Charms and decorations are much easier to filter out due to their simplicity. All we do is check if a charm/decoration contains a skill that we care about. Charms don't have decorations lots, and decorations are already their own atomic unit. These operations are easily `O(n)`.

Weapon augments and custom upgrades are simply hard-coded for the meantime since there are very few useful augment combinations. A proper algorithm may be written in the future if the need arises.

After pruning, the worst-case time complexity of the overall algorithm may be considered to be `O(s^5 * c * w * a * u * d * l)` for `s` armour sets, `c` charms, `w` weapons, `a` weapon augments, `u` custom upgrades, `d` decorations, and `l` for the maximum level of any skill.

**This is about as bad as it gets in the overall.**

### Ideas for optimization: Dynamic programming? Divide and conquer?

We can probably try techniques like dynamic programming, or divide and conquer.

I'll need to do some research into how these and other techniques might be applied.

### Ideas for optimization: Slightly over-pruning the level 4 decorations.

There may be times where the algorithm can, for example, put Critical/Vitality, Critical/Vitality, Critical/Vitality, and Tenderizer/Maintenance into the build. But what if we just don't care about highly optional skills? This may lead the algorithm to add Tenderizer instead of the clearly superior Tenderizer/Maintenance decoration.

But for the sake of efficiency, we might want to consider doing it anyway. We don't really care about those *extra* skills anyway in many level 4 decorations, and we don't lose any core features in our build to use lower-level ones. If it's discovered that our final build can fit more extra skills after all, then it's easy to make modifications to add these extra skills in.

### Ideas for optimization: Pruning entire combinations of armour.

As discussed above, we can easily prune within a category of head, chest, waist, or legs, and my algorithm currently runs in `O(n^2)` on each category separately.

But what if we applied the same pruning technique over *a set of gear combinations*? Instead of just considering whether a head piece is clearly inferior to another head piece, what if we also considered if a specific combination of head+chest+arms+waist+legs is clearly inferior to another combination of head+chest+arms+waist+legs?

However, that would have a blown up time complexity of `O((n^5)^2)` for `n` armour pieces within each category. Assuming we pruned down to 150 pieces per category, we get `(150^5)^2 = 5.8 * 10^21`. That is a buttload of combinations.

To improve on the efficiency, I'm thinking of applying *memoization* to check every armour combination in a single pass, building a data structure of "superior armour combinations" (likely some sort of tree) that can simply be traversed instead of a brute-force pair-wise comparison. This data structure may require an overhead of `s` skills (counting only skills that affect the build meaningfully) to access, though `s` is unlikely to exceed roughly 12 skills (in my opinion). Being a single-pass, the worst-case time complexity is `O(s*(n^5))` if we include `s`, or `O(n^5)` for practical purposes.

### Ideas for optimization: Pruning weapons.

There may be some condition in which we can prune a weapon out. In most cases, weapons that are direct upgrades of each other can lead to one of these weapons being pruned away.

But I'll need to somehow formalize the conditions necessary for this to happen.

## License

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

