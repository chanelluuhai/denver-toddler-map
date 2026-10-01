# Denver / Arvada toddler outing map

Self-contained MapLibre map of toddler-friendly spots near **Arvada, CO 80004**, curated from:

- [Days.in.denver](https://www.instagram.com/days.in.denver/) (`@days.in.denver`) + [beehiiv newsletter](https://days-in-denver.beehiiv.com/)
- [Colorado Kids Explore](https://www.instagram.com/colorado.kids.explore/) (`@colorado.kids.explore`)
- [Colorado Kids Are Rad](https://www.instagram.com/coloradokidsarerad/) (`@coloradokidsarerad`)

## Live map (GitHub Pages)

**https://chanelluuhai.github.io/denver-toddler-map/**

Mobile-app shell with bottom tabs (**Map · List · Filters · About**), bottom-sheet place details, search, and filters (near / farther / free / indoor). Soft light basemap via **MapLibre GL + OpenFreeMap Positron** (no Mapbox token). Teal pins ≈ within 30 min of 80004; terracotta = farther.

## Open locally

1. Open **`output/index.html`** (or `docs/index.html`) in a browser — `file://` works (places are embedded). Needs network for MapLibre + tiles + fonts.
2. Or: `python3 -m http.server 8765 --directory docs` → http://127.0.0.1:8765/

## Update after a scrub (weekly)

1. Edit **`data/places.json`** — every place needs `id`, `name`, `lat`, `lng`, `address`, `why`, `source`, `source_accounts`, `links`, plus hours/cost/toddler notes when known.
2. Run: `python3 scripts/build_map.py`  
   - Rebuilds `output/index.html`, `output/places.json`, `output/INDEX.md`  
   - Syncs the built site into **`docs/`** (GitHub Pages root)
3. Commit & push `main`.
4. Confirm Pages still serves from `/docs` on `main`.

Drive times in the JSON are **rough estimates** from Arvada 80004 — always confirm in Google Maps.

## Files

| Path | Role |
|------|------|
| `data/places.json` | Editable source of truth |
| `scripts/build_map.py` | Embeds JSON into HTML + markdown; syncs `docs/` |
| `output/` | Local build artifacts |
| `docs/` | GitHub Pages site (`index.html` + `places.json` + `SOURCES.md`) |

## Constraints

- Prefer ~30 min from Arvada 80004; farther spots are flagged.
- Toddler ~20 months.
- Keep source attribution + clickable links on every pin.
- Do not invent venues not mentioned in the named sources.
