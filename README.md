# Denver / Arvada toddler outing map

Self-contained MapLibre map of toddler-friendly spots near **W 64th Ave & Ward Rd, Arvada, CO 80004**, curated from:

- [Days.in.denver](https://www.instagram.com/days.in.denver/) (`@days.in.denver`) + [beehiiv newsletter](https://days-in-denver.beehiiv.com/)
- [Colorado Kids Explore](https://www.instagram.com/colorado.kids.explore/) (`@colorado.kids.explore`)
- [Colorado Kids Are Rad](https://www.instagram.com/coloradokidsarerad/) (`@coloradokidsarerad`)

## Live (GitHub Pages)

One site, separate apps. Design system: [`design.md`](design.md).

- Hub: **https://chanelluuhai.github.io/denver-toddler-map/**
- Toddler Spots: **https://chanelluuhai.github.io/denver-toddler-map/spots/**
- Little Library: **https://chanelluuhai.github.io/denver-toddler-map/library/**

Toddler Spots is a mobile-app shell with bottom tabs (**Map · List · Filters · About**), bottom-sheet place details, search, and filters (near / farther / free / indoor). Soft light basemap via **MapLibre GL + OpenFreeMap Positron** (no Mapbox token). Dusty-purple pins ≈ within 30 min of 80004; warm clay = farther.

Little Library is the home shelf (scan, genres, favorites, recommendations). It follows `design.md` with a sage palette.

## Open locally

1. Open **`output/spots/index.html`** (or `docs/spots/index.html`) in a browser — `file://` works (places are embedded). Needs network for MapLibre + tiles + fonts.
2. Or: `python3 -m http.server 8765 --directory docs` → http://127.0.0.1:8765/ (hub), `/spots/`, `/library/`.

## Update after a scrub (weekly)

1. Edit **`data/places.json`** — every place needs `id`, `name`, `lat`, `lng`, `address`, `why`, `source`, `source_accounts`, `links`, plus hours/cost/toddler notes when known.
2. Run: `python3 scripts/build_map.py`  
   - Rebuilds `output/spots/index.html`, `output/spots/places.json`, `output/spots/INDEX.md`  
   - Syncs the built Toddler Spots app into **`docs/spots/`** (the hub stays at `docs/index.html`)
3. Commit & push `main`.
4. Confirm Pages still serves from `/docs` on `main`.

Drive times in the JSON are **rough estimates** from W 64th Ave & Ward Rd, Arvada 80004 — always confirm in Google Maps.

## Files

| Path | Role |
|------|------|
| `data/places.json` | Editable source of truth |
| `scripts/build_map.py` | Embeds JSON into HTML + markdown; syncs `docs/spots/` |
| `output/spots/` | Local Toddler Spots build |
| `docs/` | GitHub Pages root: hub, `spots/`, `library/` |
| `design.md` | Shared chrome and type; apps swap color themes only |

## Constraints

- Prefer ~30 min from W 64th Ave & Ward Rd, Arvada 80004; farther spots are flagged.
- Toddler ~20 months.
- Keep source attribution + clickable links on every pin.
- Do not invent venues not mentioned in the named sources.

## Events

Upcoming dated family events live in `data/events.json` and appear in the mobile-friendly Events tab, grouped by day.
