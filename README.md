# Sim's MHWI Build Search Tool

**CURRENT A WORK IN PROGRESS.** I'm developing this to aid in build optimization for the game Monster Hunter World Iceborne!

This project is written for Python 3.8.

## Planned Development Roadmap

1) Make a simple EFR optimizer for GS and SnS. I want this script to automatically create entire builds with as little manual tweaking as possible (except for updating the database, or stating build constraints).

2) Implement some form of handling for common non-EFR parameters, notably the Focus and Health Boost skills.

3) Implement elemental/status calculations.

4) Implement elemental/status optimization for the automated build searcher.

5) Implement build saving. (It might just be as simple as saving the terminal output, but maybe I can make something better? Maybe it automatically generates a honeyhunterworld.com link?)

6) Slowly implement each of the other weapon types. (This is expected to be a complex stage due to all the different mechanics and oddities unique to certain weapons, not to mention the fact that I hardly understand many of them.)

7) Implement a GUI front-end. (Ideally something cross-platform.)

8) Create a framework that can be used to help build other build optimization tools.

## TODOs

1) I'll need to be confident that the armour pruning doesn't throw away armour pieces that are still useful.

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

