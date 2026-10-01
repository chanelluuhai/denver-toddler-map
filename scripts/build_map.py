#!/usr/bin/env python3
"""Build self-contained map HTML from data/places.json (file:// friendly)."""
from __future__ import annotations
import json
import pathlib
import datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "places.json"
OUT_DIR = ROOT / "output"
OUT_HTML = OUT_DIR / "index.html"
OUT_JSON = OUT_DIR / "places.json"
OUT_MD = OUT_DIR / "INDEX.md"

TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Denver/Arvada Toddler Outing Map</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
  integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
<style>
  :root { --ink:#1a2332; --muted:#5a6a7a; --card:#fff; --bg:#f4f7fb; --accent:#0b6e4f; --far:#b45309; --near:#0b6e4f; }
  * { box-sizing: border-box; }
  html, body { height:100%; margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; color:var(--ink); background:var(--bg); }
  #app { display:grid; grid-template-columns: 360px 1fr; height:100%; }
  @media (max-width: 860px) { #app { grid-template-columns: 1fr; grid-template-rows: 45% 55%; } }
  aside { overflow:auto; background:var(--card); border-right:1px solid #dbe3ec; padding:14px 14px 28px; }
  h1 { font-size:1.15rem; margin:0 0 4px; }
  .sub { color:var(--muted); font-size:0.82rem; margin:0 0 12px; line-height:1.35; }
  .filters { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:12px; }
  .filters button { border:1px solid #c9d4e0; background:#fff; border-radius:999px; padding:5px 10px; font-size:0.75rem; cursor:pointer; }
  .filters button.active { background:var(--accent); color:#fff; border-color:var(--accent); }
  .place { border:1px solid #e2e8f0; border-radius:10px; padding:10px; margin-bottom:8px; cursor:pointer; background:#fff; }
  .place:hover { border-color:#9ec5b3; }
  .place.active { outline:2px solid var(--accent); }
  .place h3 { margin:0 0 4px; font-size:0.95rem; }
  .badge { display:inline-block; font-size:0.68rem; font-weight:600; padding:2px 7px; border-radius:999px; margin-right:4px; }
  .badge.near { background:#d8f3e7; color:var(--near); }
  .badge.far { background:#ffedd5; color:var(--far); }
  .meta { font-size:0.78rem; color:var(--muted); }
  #map { height:100%; width:100%; }
  .leaflet-popup-content { min-width:220px; max-width:300px; font-size:0.88rem; line-height:1.35; }
  .popup h3 { margin:0 0 6px; font-size:1rem; }
  .popup a { color:#0b57a4; }
  .why { margin:8px 0; }
  .src { font-size:0.78rem; color:var(--muted); }
  footer.note { font-size:0.72rem; color:var(--muted); margin-top:16px; line-height:1.4; }
</style>
</head>
<body>
<div id="app">
  <aside>
    <h1>Toddler outings — Denver / Arvada</h1>
    <p class="sub">Base: Arvada 80004 · ~20 months · sources: Days.in.denver, Colorado Kids Explore, Colorado Kids Are Rad · updated __UPDATED__</p>
    <div class="filters">
      <button type="button" data-filter="all" class="active">All (__COUNT__)</button>
      <button type="button" data-filter="near">Within ~30 min</button>
      <button type="button" data-filter="far">Farther</button>
    </div>
    <div id="list"></div>
    <footer class="note">Open this file in a browser (file:// works). To update: edit <code>data/places.json</code>, run <code>python3 scripts/build_map.py</code>, refresh. Drive times are rough estimates — confirm in Google Maps.</footer>
  </aside>
  <div id="map"></div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
  integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<script>
// Embedded source-of-truth snapshot (file:// safe). Rebuild via scripts/build_map.py
const PLACES_DOC = __PLACES_JSON__;
</script>
<script>
(function(){
  const places = PLACES_DOC.places || [];
  const base = PLACES_DOC.meta && PLACES_DOC.meta.base;
  const map = L.map('map', { scrollWheelZoom: true });
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap'
  }).addTo(map);

  const markers = {};
  const group = L.featureGroup();

  function escapeHtml(s){
    return String(s==null?'':s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  function popupHtml(p){
    const links = (p.links||[]).map(l => `<div><a href="${escapeHtml(l.url)}" target="_blank" rel="noopener">${escapeHtml(l.label||l.url)}</a></div>`).join('');
    const far = p.farther_than_30min ? '<span class="badge far">Farther</span>' : '<span class="badge near">~30 min</span>';
    return `<div class="popup">
      <h3>${escapeHtml(p.name)} ${far}</h3>
      <div><strong>Address:</strong> ${escapeHtml(p.address||'—')}</div>
      <div class="why"><strong>Why:</strong> ${escapeHtml(p.why||'')}</div>
      <div class="src"><strong>Source:</strong> ${escapeHtml(p.source||'')}</div>
      <div class="src">${escapeHtml(p.drive_note||'')}</div>
      ${p.hours ? `<div class="src"><strong>Hours:</strong> ${escapeHtml(p.hours)}</div>` : ''}
      ${p.cost ? `<div class="src"><strong>Cost:</strong> ${escapeHtml(p.cost)}</div>` : ''}
      ${p.toddler_notes ? `<div class="src"><strong>Toddler tip:</strong> ${escapeHtml(p.toddler_notes)}</div>` : ''}
      <div style="margin-top:6px">${links}</div>
    </div>`;
  }

  function colorFor(p){ return p.farther_than_30min ? '#b45309' : '#0b6e4f'; }

  places.forEach(p => {
    const m = L.circleMarker([p.lat, p.lng], {
      radius: 9, color: '#fff', weight: 2, fillColor: colorFor(p), fillOpacity: 0.95
    });
    m.bindPopup(popupHtml(p), { maxWidth: 320 });
    m.bindTooltip(p.name);
    m.on('click', () => highlightList(p.id));
    markers[p.id] = m;
    group.addLayer(m);
  });

  if (base) {
    const home = L.marker([base.lat, base.lng], {
      title: 'Arvada 80004 base',
      icon: L.divIcon({ className:'', html:'<div style="background:#2563eb;color:#fff;border-radius:8px;padding:3px 6px;font-size:11px;font-weight:700;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.3)">HOME</div>', iconSize:[48,20], iconAnchor:[24,10] })
    }).bindPopup('<strong>Base:</strong> Arvada, CO 80004');
    group.addLayer(home);
  }

  group.addTo(map);
  if (group.getLayers().length) map.fitBounds(group.getBounds().pad(0.12));

  const listEl = document.getElementById('list');
  let filter = 'all';

  function highlightList(id){
    listEl.querySelectorAll('.place').forEach(el => el.classList.toggle('active', el.dataset.id===id));
  }

  function renderList(){
    const sorted = places.slice().sort((a,b)=> (a.approx_drive_minutes||999)-(b.approx_drive_minutes||999));
    const filtered = sorted.filter(p => {
      if (filter==='near') return !p.farther_than_30min;
      if (filter==='far') return !!p.farther_than_30min;
      return true;
    });
    listEl.innerHTML = filtered.map(p => {
      const badge = p.farther_than_30min ? '<span class="badge far">Farther</span>' : '<span class="badge near">Near</span>';
      return `<div class="place" data-id="${escapeHtml(p.id)}">
        <h3>${badge}${escapeHtml(p.name)}</h3>
        <div class="meta">${escapeHtml(p.drive_note||'')}</div>
        <div class="meta">${escapeHtml(p.source||'')}</div>
      </div>`;
    }).join('');
    listEl.querySelectorAll('.place').forEach(el => {
      el.addEventListener('click', () => {
        const p = places.find(x => x.id===el.dataset.id);
        if (!p) return;
        map.setView([p.lat, p.lng], 14);
        markers[p.id].openPopup();
        highlightList(p.id);
      });
    });
    // show/hide markers
    places.forEach(p => {
      const show = filter==='all' || (filter==='near' && !p.farther_than_30min) || (filter==='far' && p.farther_than_30min);
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

  renderList();
})();
</script>
</body>
</html>
'''

def build():
    doc = json.loads(DATA.read_text())
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # snapshot JSON next to HTML for reference / future http fetch
    OUT_JSON.write_text(json.dumps(doc, indent=2) + "\n")
    places_json = json.dumps(doc, ensure_ascii=False)
    html_out = (TEMPLATE
        .replace("__PLACES_JSON__", places_json)
        .replace("__UPDATED__", str(doc.get("meta", {}).get("updated", "")))
        .replace("__COUNT__", str(len(doc.get("places", []))))
    )
    OUT_HTML.write_text(html_out)
    # markdown index
    lines = [
        f"# {doc['meta'].get('title', 'Toddler outing map')}",
        "",
        f"Updated: {doc['meta'].get('updated')}  ",
        f"Base: {doc['meta']['base'].get('label')}  ",
        f"Audience: {doc['meta'].get('audience')}",
        "",
        "Each pin has a why-note from a named social source. Drive times are rough estimates.",
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
    print(f"Wrote {OUT_HTML}")
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    print(f"Places: {len(doc['places'])}")

if __name__ == "__main__":
    build()
