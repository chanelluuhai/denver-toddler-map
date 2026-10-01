# Denver / Arvada toddler outing map

Self-contained web map of toddler-friendly spots near **Arvada, CO 80004**, pulled from:

- [Days.in.denver](https://www.instagram.com/days.in.denver/) (`@days.in.denver`)
- [Colorado Kids Explore](https://www.instagram.com/colorado.kids.explore/) (`@colorado.kids.explore`)
- [Colorado Kids Are Rad](https://www.instagram.com/coloradokidsarerad/) (`@coloradokidsarerad`)

## Open the map (no Google My Maps import)

1. Open **`output/index.html`** in Chrome/Safari/Firefox (double-click or `file://` URL).
2. Or from this folder: `python3 -m http.server 8765 --directory output` then visit http://127.0.0.1:8765/

Markers are green if roughly within ~30 min of Arvada 80004, orange if farther. Click a marker or list row for **why** (from the source), address, hours, cost, and links.

## Update after a future scrub

1. Edit **`data/places.json`** (source of truth): add/edit places with `name`, `lat`, `lng`, `address`, `why`, `source`, `links`, optional `hours`/`cost`/`toddler_notes`.
2. Recompute drive notes if you change coords (or re-run a small helper); simplest: set `lat`/`lng` and run build — for drive fields, either update them by hand or re-run the distance logic in a prior script session.
3. Run: `python3 scripts/build_map.py`
4. Refresh the browser on `output/index.html`.
5. `git add -A && git commit -m "Scrub: …"` so changes stay versioned.

Drive times in the JSON are **rough estimates** from Arvada 80004 — always confirm in Google Maps before leaving.

## Files

| Path | Role |
|------|------|
| `data/places.json` | Editable source of truth |
| `scripts/build_map.py` | Embeds JSON into a file://-safe HTML map + markdown index |
| `output/index.html` | Open this in a browser |
| `output/INDEX.md` | Same places as a readable list |
| `output/places.json` | Snapshot copy next to the HTML |
| `docs/SOURCES.md` | Account links + scrub notes |

## Constraints (Chanel)

- Prefer ~30 min from Arvada 80004; farther spots are flagged.
- Toddler ~20 months.
- Keep source attribution + clickable links on every pin.
