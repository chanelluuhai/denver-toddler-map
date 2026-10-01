#!/usr/bin/env python3
"""Build self-contained map HTML from data/places.json (file:// + GitHub Pages friendly)."""
from __future__ import annotations
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "places.json"
OUT_DIR = ROOT / "output"
DOCS_DIR = ROOT / "docs"
OUT_HTML = OUT_DIR / "index.html"
OUT_JSON = OUT_DIR / "places.json"
OUT_MD = OUT_DIR / "INDEX.md"

TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<meta name="theme-color" content="#0d9488"/>
<meta name="description" content="Toddler outing map near Arvada/Denver — parks, museums, indoor play, farms from local parent guides."/>
<title>Denver/Arvada Toddler Outing Map</title>
<link rel="preconnect" href="https://unpkg.com" crossorigin/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
  integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
<style>
  :root {
    --ink: #0f172a;
    --muted: #64748b;
    --card: #ffffff;
    --bg: #f0fdfa;
    --bg2: #ecfeff;
    --accent: #0d9488;
    --accent-dark: #0f766e;
    --far: #c2410c;
    --near: #0d9488;
    --free: #2563eb;
    --indoor: #7c3aed;
    --shadow: 0 8px 28px rgba(15, 23, 42, 0.08);
    --radius: 16px;
    --tap: 44px;
    --safe-bottom: env(safe-area-inset-bottom, 0px);
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; }
  body {
    font-family: "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, Roboto, "Helvetica Neue", sans-serif;
    color: var(--ink);
    background: linear-gradient(160deg, var(--bg) 0%, #f8fafc 45%, var(--bg2) 100%);
    -webkit-font-smoothing: antialiased;
  }
  #app {
    display: grid;
    grid-template-columns: minmax(320px, 400px) 1fr;
    height: 100%;
    height: 100dvh;
  }
  aside {
    display: flex;
    flex-direction: column;
    background: rgba(255,255,255,0.92);
    backdrop-filter: blur(12px);
    border-right: 1px solid #d1fae5;
    min-height: 0;
    z-index: 2;
  }
  .hero {
    padding: 16px 16px 10px;
    background: linear-gradient(135deg, #ccfbf1 0%, #ffffff 55%, #e0f2fe 100%);
    border-bottom: 1px solid #d1fae5;
  }
  .hero-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
  h1 {
    font-size: 1.2rem;
    margin: 0;
    letter-spacing: -0.02em;
    line-height: 1.25;
    font-weight: 750;
  }
  .pill-count {
    flex-shrink: 0;
    background: var(--accent);
    color: #fff;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 6px 10px;
    border-radius: 999px;
    min-height: 28px;
  }
  .sub {
    color: var(--muted);
    font-size: 0.8rem;
    margin: 8px 0 0;
    line-height: 1.4;
  }
  .sticky-tools {
    position: sticky;
    top: 0;
    z-index: 5;
    background: rgba(255,255,255,0.96);
    backdrop-filter: blur(10px);
    padding: 10px 14px 12px;
    border-bottom: 1px solid #e2e8f0;
    box-shadow: 0 4px 16px rgba(15,23,42,0.04);
  }
  .search-wrap { position: relative; margin-bottom: 10px; }
  .search-wrap input {
    width: 100%;
    min-height: var(--tap);
    border: 1.5px solid #cbd5e1;
    border-radius: 12px;
    padding: 10px 14px 10px 40px;
    font-size: 1rem;
    background: #fff;
    outline: none;
    transition: border-color .15s, box-shadow .15s;
  }
  .search-wrap input:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(13,148,136,0.2);
  }
  .search-wrap .icon {
    position: absolute; left: 12px; top: 50%; transform: translateY(-50%);
    color: var(--muted); font-size: 1rem; pointer-events: none;
  }
  .filters {
    display: flex;
    flex-wrap: nowrap;
    gap: 8px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    padding-bottom: 2px;
  }
  .filters::-webkit-scrollbar { display: none; }
  .filters button {
    flex: 0 0 auto;
    border: 1.5px solid #cbd5e1;
    background: #fff;
    border-radius: 999px;
    min-height: 40px;
    padding: 8px 14px;
    font-size: 0.82rem;
    font-weight: 600;
    cursor: pointer;
    color: var(--ink);
    white-space: nowrap;
    transition: background .15s, color .15s, border-color .15s, transform .1s;
  }
  .filters button:active { transform: scale(0.97); }
  .filters button.active {
    background: var(--accent);
    color: #fff;
    border-color: var(--accent);
  }
  .filters button.active.far { background: var(--far); border-color: var(--far); }
  .filters button.active.free { background: var(--free); border-color: var(--free); }
  .filters button.active.indoor { background: var(--indoor); border-color: var(--indoor); }
  #list {
    flex: 1;
    overflow: auto;
    padding: 12px 14px calc(20px + var(--safe-bottom));
    -webkit-overflow-scrolling: touch;
  }
  .place {
    border: 1px solid #e2e8f0;
    border-radius: var(--radius);
    padding: 14px;
    margin-bottom: 10px;
    cursor: pointer;
    background: var(--card);
    box-shadow: 0 2px 8px rgba(15,23,42,0.04);
    transition: border-color .15s, box-shadow .15s, transform .12s;
    min-height: 72px;
  }
  .place:active { transform: scale(0.99); }
  .place:hover, .place.active {
    border-color: #5eead4;
    box-shadow: var(--shadow);
  }
  .place.active { outline: 2px solid var(--accent); outline-offset: 1px; }
  .place h3 {
    margin: 0 0 6px;
    font-size: 1rem;
    line-height: 1.3;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
  }
  .badge {
    display: inline-flex;
    align-items: center;
    font-size: 0.68rem;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 999px;
    letter-spacing: 0.01em;
  }
  .badge.near { background: #ccfbf1; color: var(--near); }
  .badge.far { background: #ffedd5; color: var(--far); }
  .badge.free { background: #dbeafe; color: var(--free); }
  .badge.indoor { background: #ede9fe; color: var(--indoor); }
  .meta { font-size: 0.8rem; color: var(--muted); line-height: 1.35; }
  .meta + .meta { margin-top: 2px; }
  #map-wrap { position: relative; min-height: 0; }
  #map { height: 100%; width: 100%; }
  .map-legend {
    position: absolute;
    left: 12px;
    bottom: calc(12px + var(--safe-bottom));
    z-index: 500;
    background: rgba(255,255,255,0.95);
    border-radius: 12px;
    padding: 8px 12px;
    font-size: 0.72rem;
    box-shadow: var(--shadow);
    border: 1px solid #e2e8f0;
    line-height: 1.4;
  }
  .map-legend span { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px; vertical-align: middle; }
  .leaflet-popup-content-wrapper {
    border-radius: 14px;
    box-shadow: var(--shadow);
    padding: 0;
  }
  .leaflet-popup-content {
    margin: 14px 16px 16px;
    min-width: min(280px, 78vw);
    max-width: min(320px, 86vw);
    font-size: 0.9rem;
    line-height: 1.4;
  }
  .leaflet-container a.leaflet-popup-close-button {
    width: 28px; height: 28px; font-size: 20px; padding: 4px;
  }
  .popup h3 { margin: 0 0 8px; font-size: 1.05rem; line-height: 1.3; }
  .popup .badges { margin-bottom: 8px; display: flex; flex-wrap: wrap; gap: 4px; }
  .popup a {
    color: #0369a1;
    font-weight: 600;
    word-break: break-word;
    display: inline-block;
    padding: 4px 0;
    min-height: 32px;
  }
  .why { margin: 10px 0; }
  .src { font-size: 0.8rem; color: var(--muted); margin-top: 4px; }
  footer.note {
    font-size: 0.72rem;
    color: var(--muted);
    margin-top: 8px;
    line-height: 1.45;
    padding: 0 2px 8px;
  }
  .empty {
    text-align: center;
    color: var(--muted);
    padding: 28px 12px;
    font-size: 0.9rem;
  }

  /* Mobile: map on top, list sheet below */
  @media (max-width: 860px) {
    #app {
      grid-template-columns: 1fr;
      grid-template-rows: minmax(42vh, 48vh) 1fr;
    }
    aside {
      border-right: none;
      border-top: 1px solid #d1fae5;
      border-radius: 18px 18px 0 0;
      box-shadow: 0 -8px 28px rgba(15,23,42,0.08);
      margin-top: -12px;
      z-index: 3;
    }
    .hero { padding-top: 10px; border-radius: 18px 18px 0 0; }
    .hero::before {
      content: "";
      display: block;
      width: 40px; height: 4px;
      background: #cbd5e1;
      border-radius: 999px;
      margin: 0 auto 10px;
    }
    h1 { font-size: 1.08rem; }
    .map-legend { bottom: 20px; font-size: 0.68rem; }
  }
  @media (max-width: 420px) {
    .filters button { min-height: 38px; padding: 7px 12px; font-size: 0.78rem; }
    .place { padding: 12px; }
  }
</style>
</head>
<body>
<div id="app">
  <div id="map-wrap">
    <div id="map" role="application" aria-label="Map of toddler outing spots"></div>
    <div class="map-legend" aria-hidden="true">
      <div><span style="background:#0d9488"></span> Within ~30 min</div>
      <div><span style="background:#c2410c"></span> Farther</div>
      <div><span style="background:#2563eb"></span> Home (80004)</div>
    </div>
  </div>
  <aside>
    <div class="hero">
      <div class="hero-top">
        <h1>Toddler outings — Denver / Arvada</h1>
        <span class="pill-count">__COUNT__ spots</span>
      </div>
      <p class="sub">Base: Arvada 80004 · ~20 months · Days.in.denver · Colorado Kids Explore · Colorado Kids Are Rad · updated __UPDATED__</p>
    </div>
    <div class="sticky-tools">
      <div class="search-wrap">
        <span class="icon" aria-hidden="true">⌕</span>
        <input type="search" id="search" placeholder="Search parks, museums, farms…" autocomplete="off" enterkeyhint="search"/>
      </div>
      <div class="filters" role="toolbar" aria-label="Filters">
        <button type="button" data-filter="all" class="active">All</button>
        <button type="button" data-filter="near">Near (~30 min)</button>
        <button type="button" data-filter="far" class="far">Farther</button>
        <button type="button" data-filter="free" class="free">Free</button>
        <button type="button" data-filter="indoor" class="indoor">Indoor</button>
      </div>
    </div>
    <div id="list"></div>
  </aside>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
  integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<script>
const PLACES_DOC = __PLACES_JSON__;
</script>
<script>
(function(){
  const places = PLACES_DOC.places || [];
  const base = PLACES_DOC.meta && PLACES_DOC.meta.base;
  const map = L.map('map', { scrollWheelZoom: true, tapTolerance: 25 });
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap'
  }).addTo(map);

  const markers = {};
  const group = L.featureGroup();

  function escapeHtml(s){
    return String(s==null?'':s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  function isFree(p){
    const c = (p.cost||'').toLowerCase();
    const tags = (p.tags||[]).map(t => String(t).toLowerCase());
    return tags.includes('free') || tags.includes('free-playground') || tags.includes('free-entry') ||
      /^free\b/.test(c) || c.includes('park free') || c === 'free';
  }
  function isIndoor(p){
    const tags = (p.tags||[]).map(t => String(t).toLowerCase());
    return tags.includes('indoor') || tags.includes('museum') || tags.includes('library') || tags.includes('bookstore');
  }

  function popupHtml(p){
    const links = (p.links||[]).map(l => `<div><a href="${escapeHtml(l.url)}" target="_blank" rel="noopener">${escapeHtml(l.label||l.url)}</a></div>`).join('');
    const badges = [];
    badges.push(p.farther_than_30min ? '<span class="badge far">Farther</span>' : '<span class="badge near">~30 min</span>');
    if (isFree(p)) badges.push('<span class="badge free">Free-ish</span>');
    if (isIndoor(p)) badges.push('<span class="badge indoor">Indoor-friendly</span>');
    return `<div class="popup">
      <h3>${escapeHtml(p.name)}</h3>
      <div class="badges">${badges.join('')}</div>
      <div><strong>Address:</strong> ${escapeHtml(p.address||'—')}</div>
      <div class="why"><strong>Why:</strong> ${escapeHtml(p.why||'')}</div>
      <div class="src"><strong>Source:</strong> ${escapeHtml(p.source||'')}</div>
      <div class="src">${escapeHtml(p.drive_note||'')}</div>
      ${p.hours ? `<div class="src"><strong>Hours:</strong> ${escapeHtml(p.hours)}</div>` : ''}
      ${p.cost ? `<div class="src"><strong>Cost:</strong> ${escapeHtml(p.cost)}</div>` : ''}
      ${p.toddler_notes ? `<div class="src"><strong>Toddler tip:</strong> ${escapeHtml(p.toddler_notes)}</div>` : ''}
      <div style="margin-top:8px">${links}</div>
    </div>`;
  }

  function colorFor(p){ return p.farther_than_30min ? '#c2410c' : '#0d9488'; }

  places.forEach(p => {
    const m = L.circleMarker([p.lat, p.lng], {
      radius: 10, color: '#fff', weight: 2, fillColor: colorFor(p), fillOpacity: 0.95
    });
    m.bindPopup(popupHtml(p), { maxWidth: 340, autoPanPadding: [48, 48] });
    m.bindTooltip(p.name, { direction: 'top', offset: [0, -8] });
    m.on('click', () => highlightList(p.id));
    markers[p.id] = m;
    group.addLayer(m);
  });

  if (base) {
    const home = L.marker([base.lat, base.lng], {
      title: 'Arvada 80004 base',
      icon: L.divIcon({
        className: '',
        html: '<div style="background:#2563eb;color:#fff;border-radius:10px;padding:5px 8px;font-size:12px;font-weight:800;border:2px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.28);letter-spacing:.02em">HOME</div>',
        iconSize: [54, 24],
        iconAnchor: [27, 12]
      })
    }).bindPopup('<strong>Base:</strong> Arvada, CO 80004');
    group.addLayer(home);
  }

  group.addTo(map);
  if (group.getLayers().length) map.fitBounds(group.getBounds().pad(0.12));
  setTimeout(() => map.invalidateSize(), 200);

  const listEl = document.getElementById('list');
  const searchEl = document.getElementById('search');
  let filter = 'all';
  let query = '';

  function highlightList(id){
    listEl.querySelectorAll('.place').forEach(el => el.classList.toggle('active', el.dataset.id===id));
    const el = listEl.querySelector(`.place[data-id="${CSS.escape(id)}"]`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function matchesQuery(p, q){
    if (!q) return true;
    const blob = [p.name, p.address, p.why, p.source, p.toddler_notes, ...(p.tags||[])].join(' ').toLowerCase();
    return blob.includes(q);
  }

  function passesFilter(p){
    if (filter==='near') return !p.farther_than_30min;
    if (filter==='far') return !!p.farther_than_30min;
    if (filter==='free') return isFree(p);
    if (filter==='indoor') return isIndoor(p);
    return true;
  }

  function renderList(){
    const sorted = places.slice().sort((a,b)=> (a.approx_drive_minutes||999)-(b.approx_drive_minutes||999));
    const filtered = sorted.filter(p => passesFilter(p) && matchesQuery(p, query));
    if (!filtered.length) {
      listEl.innerHTML = '<div class="empty">No spots match. Try another filter or clear search.</div>';
    } else {
      listEl.innerHTML = filtered.map(p => {
        const badges = [];
        badges.push(p.farther_than_30min ? '<span class="badge far">Farther</span>' : '<span class="badge near">Near</span>');
        if (isFree(p)) badges.push('<span class="badge free">Free</span>');
        if (isIndoor(p)) badges.push('<span class="badge indoor">Indoor</span>');
        return `<div class="place" data-id="${escapeHtml(p.id)}" role="button" tabindex="0">
          <h3>${badges.join('')}<span>${escapeHtml(p.name)}</span></h3>
          <div class="meta">${escapeHtml(p.drive_note||'')}</div>
          <div class="meta">${escapeHtml(p.source||'')}</div>
        </div>`;
      }).join('') + '<footer class="note">Drive times are rough estimates from Arvada 80004 — confirm in Maps. Edit <code>data/places.json</code>, run <code>python3 scripts/build_map.py</code>, refresh. Sources: Days.in.denver newsletter, Colorado Kids Explore, Colorado Kids Are Rad.</footer>';
    }
    listEl.querySelectorAll('.place').forEach(el => {
      const go = () => {
        const p = places.find(x => x.id===el.dataset.id);
        if (!p) return;
        map.setView([p.lat, p.lng], 14);
        markers[p.id].openPopup();
        highlightList(p.id);
      };
      el.addEventListener('click', go);
      el.addEventListener('keydown', e => { if (e.key==='Enter' || e.key===' ') { e.preventDefault(); go(); } });
    });
    places.forEach(p => {
      const show = passesFilter(p) && matchesQuery(p, query);
      if (show) { if (!map.hasLayer(markers[p.id])) markers[p.id].addTo(map); }
      else { if (map.hasLayer(markers[p.id])) map.removeLayer(markers[p.id]); }
    });
  }

  document.querySelectorAll('.filters button').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filters button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      filter = btn.dataset.filter;
      renderList();
    });
  });

  let searchTimer;
  searchEl.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      query = searchEl.value.trim().toLowerCase();
      renderList();
    }, 120);
  });

  renderList();
})();
</script>
</body>
</html>
'''

def build():
    doc = json.loads(DATA.read_text())
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, indent=2) + "\n")
    places_json = json.dumps(doc, ensure_ascii=False)
    html_out = (TEMPLATE
        .replace("__PLACES_JSON__", places_json)
        .replace("__UPDATED__", str(doc.get("meta", {}).get("updated", "")))
        .replace("__COUNT__", str(len(doc.get("places", []))))
    )
    OUT_HTML.write_text(html_out)

    lines = [
        f"# {doc['meta'].get('title', 'Toddler outing map')}",
        "",
        f"Updated: {doc['meta'].get('updated')}  ",
        f"Base: {doc['meta']['base'].get('label')}  ",
        f"Audience: {doc['meta'].get('audience')}  ",
        f"Places: {len(doc.get('places', []))}",
        "",
        "Each pin has a why-note from a named social/newsletter source. Drive times are rough estimates.",
        "",
    ]
    for p in sorted(doc["places"], key=lambda x: x.get("approx_drive_minutes", 999)):
        flag = "FARTHER" if p.get("farther_than_30min") else "near"
        lines += [
            f"## {p['name']} ({flag})",
            "",
            f"- **Address:** {p.get('address','')}",
            f"- **Drive:** {p.get('drive_note','')}",
            f"- **Why:** {p.get('why','')}",
            f"- **Source:** {p.get('source','')}",
            f"- **Hours:** {p.get('hours','')}",
            f"- **Cost:** {p.get('cost','')}",
            f"- **Toddler tip:** {p.get('toddler_notes','')}",
        ]
        for l in p.get("links") or []:
            lines.append(f"- [{l.get('label', l.get('url'))}]({l.get('url')})")
        lines.append("")
    OUT_MD.write_text("\n".join(lines) + "\n")

    # GitHub Pages: serve from /docs with built site + keep SOURCES.md
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    sources = DOCS_DIR / "SOURCES.md"
    sources_backup = sources.read_text() if sources.exists() else None
    # Clear old HTML/JSON from docs then copy built artifacts
    for name in ("index.html", "places.json", "INDEX.md"):
        src = OUT_DIR / name
        if src.exists():
            shutil.copy2(src, DOCS_DIR / name)
    if sources_backup is not None:
        sources.write_text(sources_backup)

    print(f"Wrote {OUT_HTML}")
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    print(f"Synced docs/ for GitHub Pages")
    print(f"Places: {len(doc['places'])}")

if __name__ == "__main__":
    build()
