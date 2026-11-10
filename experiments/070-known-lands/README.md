# Known lands: outlines of famous fantasy and science-fiction lands

2026-11-10; generator **1.2.2 (unreleased)**, installed EU5 **1.4.7**, Steam **26377361**. No EU5
launch.

The land editor offers four outlines of known lands as starting points (`src/rnw/lands`,
`rnw.knownlands`). Each is the **shape of a coast** cut out of a map picture: a grey picture of
three kinds (sea, land, lake), kept at most 1100 pixels on its longer side. No name, drawing,
colour or text of the map is kept. Owner decision, 2026-11-10: the shape of a coast is used as
such, and no further clearance is needed for these outlines.

## Sources and recipes

Each picture was processed by its own recipe in `build_lands.py`, tuned by eye against the
picture: the maps are drawn in different ways.

| id | land | map picture | how the outline is read |
| --- | --- | --- | --- |
| `westeros` | Westeros with its islands (Skagos, Bear Island, the Iron Islands, the Three Sisters, Tarth, the Shield Islands, the Arbor and the Stepstones) | A road-map style map of Westeros with Essos at its right edge, supplied by the owner on 2026-11-10 (replaced the plainer Commons map) | Sea is light blue, land white and grey; lettering (black with a white halo), the dark boxes of the roads and the orange roads belong to neither, and take the side their surroundings are on, grown a pixel at a time; Essos is cut off; lakes are the blue enclosed by land; the cut north stays straight and runs on (`open = "n"`) |
| `tamriel` | Tamriel | [Map of Tamriel.png](https://commons.wikimedia.org/wiki/File:Map_of_Tamriel.png) | Everything but the sea blue |
| `kalimdor` | Kalimdor with its islands (Azuremyst, Alcaz, Tel'Abim, Kezan, the Echo Isles and the Teldrassil ruins) | *Kalimdor after the 4th war* by Sturmbart, supplied by the owner on 2026-11-10 | Hypsometric map: land is the greens, yellows and reds, water the blues; routes and lettering are thin and go; the piece of the Eastern Kingdoms cut by the frame is dropped; lakes are the blue enclosed by land |
| `ansalon` | Ansalon with its islands (Sancrist, Cristyne, Enstar, Nostar, Schallsea, Karthay, Mithas, Kothas, Saifhum) and the Icewall Glacier | A detailed painted map of Ansalon, supplied by the owner on 2026-11-10 (replaced the Commons chart, which cut the edges and lacked the Icewall) | Sea is dark blue-grey, the Blood Sea of Istar red (its swirl closed) and both are sea; everything else is land, the white Icewall in the south included; lettering, rivers and the legend are thin and go; the cut south stays straight and runs on (`open = "s"`) |

Where the picture ends in the middle of a continent (Westeros to the north, Ansalon to the south)
the recipe leaves the cut straight and `lands.toml` names the side in `open` (letters of `nesw`).
A land is not given a coast there: `rnw.knownlands.place` lays it so that its land reaches the edge
of the usable area on that side, and carries on what is left to the edge of the sheet by mirroring
the map across the cut. Both lands lie whole inside the area, with nothing clipped.

## Lands left out

Only outlines that lie on the usable area whole and look like their land are kept: quality over
quantity (owner, 2026-11-10).

- Middle-earth, Hyrule, Thedas and Faerûn: their maps are cut on three sides and the continent runs
  on, so that joined to the edges they filled 56 to 85 % of the usable area and the area clipped
  them into rectangles; with a coast on the cut sides they became islands.
- Azeroth (the chart's islands), the Eastern Kingdoms and Atlantis: smooth, crude shapes without the
  coast of their land.
- Not made: Narnia (line art whose coast runs off the sheet), Hyboria (Russian-lettered, hatched),
  Oz (the Land of Oz is a rectangle), Arrakis, Skyrim (a province with three straight borders), Pern
  and Earthsea (no picture found on Commons).

## Rebuilding

```
uv run python experiments/070-known-lands/build_lands.py --maps DIR --out src/rnw/lands
```

`DIR` holds the pictures as `tamriel.png`, `westeros.png`, `kalimdor.png` and `ansalon.png`. The
pictures themselves are not kept in the repository.

## Checks

- [V-EXEC] `tests/test_knownlands.py`: every picture is sea, land and enclosed lakes only; each lies
  on a synthetic sheet with nothing dropped, no speck, no open lake and no refusal; the same inputs
  give the same sheet; a land whose map is cut reaches the edge of the usable area on that side and
  no other.
- [V-LOCAL] On the installed game's area (1.4.7), all four lands pass the editor's check at 100 %
  kept.
- [V-EXEC] A full world made on an outline with the largest lakes (Hyrule's, since left out)
  finished the generator and every validator in 196 s; the game was not launched.
