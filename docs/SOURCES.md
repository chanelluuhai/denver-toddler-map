# Sources scrubbed

## Accounts

| Account | Instagram | Facebook | Other |
|---------|-----------|----------|-------|
| Days.in.denver | https://www.instagram.com/days.in.denver/ | Days.in.denver | https://days-in-denver.beehiiv.com/ |
| Colorado Kids Explore | https://www.instagram.com/colorado.kids.explore/ | https://www.facebook.com/profile.php?id=61575843462964 (Colorado Kids Explore - Adventure Guide) | https://www.tiktok.com/@colorado.kids.explore |
| Colorado Kids Are Rad | https://www.instagram.com/coloradokidsarerad/ | Colorado Kids Are Rad | |
| Colorado Mama Life (Angelica) | https://www.instagram.com/coloradomamalife/ | https://www.facebook.com/profile.php?id=61577651781310 | https://www.tiktok.com/@coloradomamalife |

## Scrub window (2026-10-01 deep pass)

**Days.in.denver beehiiv (~90 days / Mar–Oct 2026 + Fall guide)**

- March, April, May, June, July, August, September, October newsletters
- Fall guide (pumpkin patches, farms, festivals)
- Steal-this-weekend idea (DMNS + Nature Play)

Major venue themes pulled: Apex Center, CSU Spur, Children's Museum (Bloom), DMNS Nature Play, Botanic Gardens Mordecai, Urban Farm, Clement Park, Cook Park, Denver Rock Park, Ralston Valley Park, Paul Derda Rec, Bookies, Tumble Haus, Bonfire Burritos Arvada, Wheat Ridge Rec pool, Lookout Mountain Nature Center, Denver Zoo, Centennial Center Park, Civic Green, Red-tailed Hawk, Pirates Cove, Surfside, creek spots, Yetman Farms, Hudson Gardens, Anythink libraries, Central Library, DreamLab, Colorado Railroad Museum, Chatfield Farms, Four Mile, Spano's, Maize in the City, Nick's, Bad Dog Farm, Tagawa, Eloise May, Stanley Marketplace, Mines Museum, City Park, Homegrown Arvada, and more.

**Colorado Kids Explore (@colorado.kids.explore / Facebook Colorado Kids Explore - Adventure Guide / TikTok @colorado.kids.explore)**

- Belleview Park Farm & Train (also reinforced in Days.in.denver May/Aug)
- Added 2026-10-01 from Chanel→Toddie Facebook reel share: https://www.facebook.com/share/r/1FVR7XnRg6/ → https://www.facebook.com/reel/1702181394414028/
- Reel tip: **McFall Park** (“Peter Pan Park”), 4801 W 92nd Ave, Westminster, CO 80031 — playground + water play; free breakfast & lunch for kids under 18 Mon–Fri 11am–1pm when summer meal program runs (adults small fee; check other locations). New map pin `mcfall-park` (~16 min from Arvada 80004).

**Colorado Kids Are Rad — evergreen 10-park list**

Cheyenne-Arapaho, Bates-Logan, Washington Park, City View, La Raza, Paco Sanchez, Joseph P. Martinez, Sloan’s Lake, Central Park, Wright Park.

**Colorado Mama Life (@coloradomamalife / Facebook Colorado Mama Life)**

- Added 2026-10-01 from Chanel→Toddie Facebook reel share: https://www.facebook.com/share/r/1DHAJTGes1/
- Reel promo tip: follow Angelica for free days & family-friendly Denver-area adventures (caption truncated by FB login wall; no specific venue named in visible text).
- Creator: Angelica Quintanilla — kid-friendly adventures, date nights, mom time, celiac food finds.

## Auth / scrape blockers

- Instagram public pages only expose follower counts in OG tags (login wall for captions/reels).
- Facebook pages often return empty/login interstitial for automated fetch; mobile reel OG tags + headless dump used for caption/page id.
- Primary deep content for this scrub: Days.in.denver beehiiv (fully readable) + prior CKAR 10-park list + CKE Belleview + CKE McFall reel.

## Weekly update notes

1. Scrub **all** accounts listed in this SOURCES.md Accounts table (IG/FB/TikTok/newsletter as linked) — currently Days.in.denver, Colorado Kids Explore, Colorado Kids Are Rad, Colorado Mama Life — plus Days.in.denver beehiiv.
2. Add/edit rows in `data/places.json` (keep `source` + `links`).
3. `python3 scripts/build_map.py` (writes `output/` and syncs `docs/` for Pages).
4. Commit & push `main` — GitHub Pages serves from `/docs`.
