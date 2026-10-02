#!/usr/bin/env python3
"""Build self-contained map HTML from data/places.json (file:// + GitHub Pages friendly)."""
from __future__ import annotations
import json
import pathlib
import html
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "places.json"
EVENTS_DATA = ROOT / "data" / "events.json"
OUT_DIR = ROOT / "output"
DOCS_DIR = ROOT / "docs"
OUT_HTML = OUT_DIR / "index.html"
OUT_JSON = OUT_DIR / "places.json"
OUT_EVENTS = OUT_DIR / "events.json"
OUT_MD = OUT_DIR / "INDEX.md"

TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<meta name="theme-color" content="#2A9D8F"/>
<meta name="apple-mobile-web-app-capable" content="yes"/>
<meta name="apple-mobile-web-app-status-bar-style" content="default"/>
<meta name="description" content="Toddler outing map near Arvada/Denver — parks, museums, indoor play, farms from local parent guides."/>
<title>Toddler Spots · Denver / Arvada</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap" rel="stylesheet"/>
<link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet"/>
<style>
  :root {
    --accent: #2A9D8F;
    --accent-soft: #E6F5F3;
    --accent-dark: #1F7A6E;
    --ink: #1A1A1A;
    --ink-2: #3D3D3D;
    --muted: #6B7280;
    --line: #E8E6E1;
    --bg: #F7F5F2;
    --card: #FFFFFF;
    --far: #C45C26;
    --far-soft: #FBEDE6;
    --near: #2A9D8F;
    --near-soft: #E6F5F3;
    --free: #3B6EA5;
    --free-soft: #E8F0F8;
    --indoor: #7A5C9E;
    --indoor-soft: #F0EAF5;
    --shadow: 0 4px 24px rgba(26,26,26,0.08);
    --shadow-lg: 0 12px 40px rgba(26,26,26,0.14);
    --radius: 18px;
    --radius-sm: 12px;
    --tap: 48px;
    --tab-h: calc(56px + env(safe-area-inset-bottom, 0px));
    --top-h: 56px;
    --safe-top: env(safe-area-inset-top, 0px);
    --safe-bottom: env(safe-area-inset-bottom, 0px);
    --font: "DM Sans", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    --display: "Fraunces", Georgia, "Times New Roman", serif;
  }
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  html, body { height: 100%; margin: 0; overflow: hidden; }
  body {
    font-family: var(--font);
    color: var(--ink);
    background: var(--bg);
    -webkit-font-smoothing: antialiased;
  }
  button, input { font-family: inherit; }

  #app {
    position: relative;
    height: 100%;
    height: 100dvh;
    width: 100%;
    overflow: hidden;
  }

  /* —— Top chrome —— */
  .topbar {
    position: absolute;
    top: 0; left: 0; right: 0;
    z-index: 20;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: calc(8px + var(--safe-top)) 14px 8px;
    pointer-events: none;
  }
  .topbar > * { pointer-events: auto; }
  /* The map-only chrome must not reserve or cover space in other views. */
  .topbar[hidden] { display: none; }
  .brand {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(255,255,255,0.92);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(232,230,225,0.9);
    border-radius: 999px;
    padding: 8px 14px 8px 10px;
    box-shadow: var(--shadow);
    flex-shrink: 0;
  }
  .brand-mark {
    width: 28px; height: 28px;
    border-radius: 9px;
    background: var(--accent);
    color: #fff;
    display: grid; place-items: center;
    font-family: var(--display);
    font-weight: 700;
    font-size: 0.95rem;
  }
  .brand-text {
    font-family: var(--display);
    font-weight: 600;
    font-size: 0.95rem;
    letter-spacing: -0.02em;
    line-height: 1.1;
  }
  .brand-sub {
    display: block;
    font-family: var(--font);
    font-weight: 500;
    font-size: 0.65rem;
    color: var(--muted);
    letter-spacing: 0.01em;
  }
  .search-pill {
    flex: 1;
    min-width: 0;
    position: relative;
    max-width: 420px;
  }
  .search-pill input {
    position: relative;
    z-index: 0;
    width: 100%;
    min-height: 44px;
    border: 1px solid rgba(232,230,225,0.9);
    border-radius: 999px;
    padding: 10px 16px 10px 42px;
    /* 16px prevents iOS Safari from auto-zooming on focus. */
    font-size: 16px;
    line-height: 1.25;
    -webkit-appearance: none;
    appearance: none;
    background: rgba(255,255,255,0.94);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    box-shadow: var(--shadow);
    outline: none;
    color: var(--ink);
  }
  .search-pill input::placeholder { color: #9CA3AF; }
  .search-pill input:focus {
    border-color: var(--accent);
    box-shadow: var(--shadow), 0 0 0 3px rgba(42,157,143,0.18);
  }
  .search-pill .ico {
    position: absolute; left: 14px; top: 50%; z-index: 1;
    display: block; transform: translateY(-50%);
    color: var(--muted); pointer-events: none; width: 18px; height: 18px;
    stroke: currentColor; stroke-width: 2; overflow: visible;
  }
  .count-chip {
    flex-shrink: 0;
    background: var(--accent);
    color: #fff;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 8px 12px;
    border-radius: 999px;
    box-shadow: var(--shadow);
    white-space: nowrap;
  }

  /* —— Map (full-bleed) —— */
  #map {
    position: absolute;
    inset: 0;
    bottom: 0;
    z-index: 1;
  }
  .maplibregl-ctrl-bottom-left,
  .maplibregl-ctrl-bottom-right {
    margin-bottom: calc(var(--tab-h) + 8px) !important;
  }
  .maplibregl-ctrl-attrib {
    font-size: 10px !important;
    background: rgba(255,255,255,0.75) !important;
  }
  .maplibregl-popup { display: none !important; }

  /* Marker dots */
  .pin {
    width: 18px; height: 18px;
    border-radius: 50%;
    border: 2.5px solid #fff;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    cursor: pointer;
    transition: transform .15s;
  }
  .pin.near { background: var(--near); }
  .pin.far { background: var(--far); }
  .pin.active { transform: scale(1.35); box-shadow: 0 0 0 4px rgba(42,157,143,0.28), 0 2px 10px rgba(0,0,0,0.3); }
  .home-pin {
    background: var(--free);
    color: #fff;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.04em;
    padding: 4px 8px;
    border-radius: 8px;
    border: 2px solid #fff;
    box-shadow: 0 2px 8px rgba(0,0,0,0.28);
    white-space: nowrap;
  }

  /* —— Views (List / Filters / About overlay panels) —— */
  .panel {
    position: absolute;
    inset: 0;
    z-index: 10;
    background: var(--bg);
    display: none;
    flex-direction: column;
    padding-top: var(--safe-top);
    padding-bottom: var(--tab-h);
    overflow: hidden;
  }
  .panel.active { display: flex; }
  .panel-header {
    padding: 18px 20px 12px;
    flex-shrink: 0;
  }
  .panel-header h1 {
    font-family: var(--display);
    font-size: 1.55rem;
    font-weight: 600;
    margin: 0;
    letter-spacing: -0.03em;
    line-height: 1.15;
  }
  .panel-header p {
    margin: 6px 0 0;
    color: var(--muted);
    font-size: 0.88rem;
    line-height: 1.4;
  }
  .panel-body {
    flex: 1;
    overflow: auto;
    -webkit-overflow-scrolling: touch;
    padding: 4px 16px 24px;
  }

  /* List cards */
  .place-card {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    padding: 16px 16px 14px;
    margin-bottom: 12px;
    cursor: pointer;
    box-shadow: 0 1px 3px rgba(26,26,26,0.04);
    transition: transform .12s, box-shadow .15s, border-color .15s;
  }
  .place-card:active { transform: scale(0.985); }
  .place-card:hover, .place-card.active {
    border-color: #B8DED9;
    box-shadow: var(--shadow);
  }
  .place-card.active { outline: 2px solid var(--accent); outline-offset: 1px; }
  .card-top {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin-bottom: 8px;
  }
  .badge {
    display: inline-flex;
    align-items: center;
    font-size: 0.68rem;
    font-weight: 700;
    padding: 4px 9px;
    border-radius: 999px;
    letter-spacing: 0.01em;
  }
  .badge.near { background: var(--near-soft); color: var(--near); }
  .badge.far { background: var(--far-soft); color: var(--far); }
  .badge.free { background: var(--free-soft); color: var(--free); }
  .badge.indoor { background: var(--indoor-soft); color: var(--indoor); }
  .place-card h3 {
    margin: 0 0 8px;
    font-family: var(--display);
    font-size: 1.12rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    line-height: 1.25;
  }
  .why-snip {
    margin: 0 0 10px;
    font-size: 0.88rem;
    color: var(--ink-2);
    line-height: 1.45;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .card-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 14px;
    font-size: 0.78rem;
    color: var(--muted);
  }
  .card-meta span { display: inline-flex; align-items: center; gap: 4px; }
  .empty {
    text-align: center;
    color: var(--muted);
    padding: 48px 20px;
    font-size: 0.95rem;
    line-height: 1.5;
  }

  /* Events panel */
  .event-day { margin: 0 0 18px; }
  .event-day-heading {
    display: flex; align-items: baseline; justify-content: space-between;
    gap: 10px; margin: 4px 4px 8px;
    font-family: var(--display); font-size: 1.12rem; font-weight: 600;
  }
  .event-day-heading span { color: var(--muted); font-family: var(--font); font-size: .72rem; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; }
  .event-card {
    background: var(--card); border: 1px solid var(--line); border-radius: var(--radius-sm);
    padding: 14px 15px; margin-bottom: 9px; box-shadow: 0 1px 3px rgba(26,26,26,.04);
  }
  .event-card.linked { cursor: pointer; transition: transform .12s, box-shadow .15s, border-color .15s; }
  .event-card.linked:hover, .event-card.linked:focus { border-color: #B8DED9; box-shadow: var(--shadow); outline: none; }
  .event-card.linked:active { transform: scale(.985); }
  .event-date-label { color: var(--accent-dark); font-size: .72rem; font-weight: 700; margin-bottom: 4px; }
  .event-card h3 { margin: 0 0 6px; font-family: var(--display); font-size: 1.06rem; line-height: 1.25; font-weight: 600; }
  .event-meta { display: flex; flex-wrap: wrap; gap: 5px 12px; color: var(--muted); font-size: .78rem; margin-bottom: 7px; }
  .event-note { margin: 0 0 8px; color: var(--ink-2); font-size: .84rem; line-height: 1.4; }
  .event-place { color: var(--muted); font-size: .78rem; }
  .event-link { color: var(--accent-dark); font-size: .8rem; font-weight: 700; text-decoration: none; }
  .event-link:hover { text-decoration: underline; }

  /* Filters panel */
  .filter-grid {
    display: grid;
    gap: 10px;
  }
  .filter-chip {
    display: flex;
    align-items: center;
    gap: 14px;
    width: 100%;
    text-align: left;
    background: var(--card);
    border: 1.5px solid var(--line);
    border-radius: var(--radius);
    padding: 16px 18px;
    min-height: var(--tap);
    cursor: pointer;
    transition: border-color .15s, background .15s, transform .1s;
  }
  .filter-chip:active { transform: scale(0.98); }
  .filter-chip.active {
    border-color: var(--accent);
    background: var(--accent-soft);
  }
  .filter-chip .dot {
    width: 12px; height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
    background: var(--muted);
  }
  .filter-chip[data-filter="near"] .dot { background: var(--near); }
  .filter-chip[data-filter="far"] .dot { background: var(--far); }
  .filter-chip[data-filter="free"] .dot { background: var(--free); }
  .filter-chip[data-filter="indoor"] .dot { background: var(--indoor); }
  .filter-chip[data-filter="all"] .dot { background: var(--accent); }
  .filter-chip .label {
    flex: 1;
    font-weight: 600;
    font-size: 1rem;
  }
  .filter-chip .hint {
    font-size: 0.8rem;
    color: var(--muted);
    font-weight: 400;
  }
  .filter-chip .check {
    width: 22px; height: 22px;
    border-radius: 50%;
    border: 2px solid var(--line);
    flex-shrink: 0;
    display: grid; place-items: center;
  }
  .filter-chip.active .check {
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
  }
  .filter-chip.active .check::after { content: "✓"; font-size: 12px; font-weight: 700; }
  .active-filter-bar {
    position: absolute;
    left: 12px; right: 12px;
    bottom: calc(var(--tab-h) + 12px);
    z-index: 15;
    display: none;
    align-items: center;
    gap: 8px;
    background: rgba(255,255,255,0.95);
    backdrop-filter: blur(12px);
    border: 1px solid var(--line);
    border-radius: 999px;
    padding: 8px 8px 8px 16px;
    box-shadow: var(--shadow);
    font-size: 0.85rem;
    font-weight: 600;
  }
  .active-filter-bar.show { display: flex; }
  .active-filter-bar button {
    margin-left: auto;
    border: none;
    background: var(--bg);
    border-radius: 999px;
    padding: 8px 14px;
    min-height: 36px;
    font-weight: 600;
    font-size: 0.8rem;
    cursor: pointer;
    color: var(--ink);
  }

  /* About */
  .about-card {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    padding: 20px;
    margin-bottom: 14px;
  }
  .about-card h2 {
    font-family: var(--display);
    font-size: 1.1rem;
    margin: 0 0 10px;
    font-weight: 600;
  }
  .about-card p, .about-card li {
    font-size: 0.9rem;
    color: var(--ink-2);
    line-height: 1.55;
    margin: 0 0 8px;
  }
  .about-card ul { padding-left: 1.1em; margin: 0 0 8px; }
  .about-card a { color: var(--accent-dark); font-weight: 600; text-decoration: none; }
  .about-card a:hover { text-decoration: underline; }
  .legend-row {
    display: flex; align-items: center; gap: 10px;
    font-size: 0.88rem; margin-bottom: 8px; color: var(--ink-2);
  }
  .legend-row i {
    width: 12px; height: 12px; border-radius: 50%;
    border: 2px solid #fff; box-shadow: 0 1px 3px rgba(0,0,0,.2);
    display: inline-block;
  }

  /* —— Bottom tab bar —— */
  .tabbar {
    position: absolute;
    left: 0; right: 0; bottom: 0;
    z-index: 30;
    height: var(--tab-h);
    padding-bottom: var(--safe-bottom);
    background: rgba(255,255,255,0.94);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-top: 1px solid var(--line);
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    box-shadow: 0 -4px 24px rgba(26,26,26,0.06);
  }
  .tab {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    border: none;
    background: transparent;
    color: var(--muted);
    font-size: 0.68rem;
    font-weight: 600;
    cursor: pointer;
    min-height: 56px;
    padding: 6px 4px;
    transition: color .15s;
  }
  .tab svg { width: 24px; height: 24px; stroke-width: 1.75; }
  .tab.active { color: var(--accent); }
  .tab:active { opacity: 0.7; }

  /* —— Bottom sheet (place detail) —— */
  .sheet-backdrop {
    position: absolute;
    inset: 0;
    z-index: 40;
    background: rgba(26,26,26,0.35);
    opacity: 0;
    pointer-events: none;
    transition: opacity .25s;
  }
  .sheet-backdrop.open { opacity: 1; pointer-events: auto; }
  .sheet {
    position: absolute;
    left: 0; right: 0; bottom: 0;
    z-index: 50;
    max-height: min(78dvh, 640px);
    background: var(--card);
    border-radius: 22px 22px 0 0;
    box-shadow: var(--shadow-lg);
    transform: translateY(110%);
    transition: transform .32s cubic-bezier(.32,.72,0,1);
    display: flex;
    flex-direction: column;
    padding-bottom: var(--safe-bottom);
  }
  .sheet.open { transform: translateY(0); }
  .sheet-handle {
    width: 40px; height: 4px;
    background: #D1D5DB;
    border-radius: 999px;
    margin: 10px auto 6px;
    flex-shrink: 0;
  }
  .sheet-scroll {
    overflow: auto;
    -webkit-overflow-scrolling: touch;
    padding: 4px 22px 28px;
    flex: 1;
  }
  .sheet-scroll h2 {
    font-family: var(--display);
    font-size: 1.4rem;
    font-weight: 600;
    letter-spacing: -0.03em;
    margin: 4px 0 10px;
    line-height: 1.2;
  }
  .sheet-badges { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; }
  .sheet-section {
    margin-bottom: 14px;
    font-size: 0.92rem;
    line-height: 1.5;
    color: var(--ink-2);
  }
  .sheet-section strong {
    display: block;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--muted);
    margin-bottom: 4px;
    font-weight: 700;
  }
  .sheet-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 8px;
    padding-top: 4px;
  }
  .sheet-actions a, .sheet-close-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 44px;
    padding: 10px 16px;
    border-radius: 999px;
    font-weight: 600;
    font-size: 0.88rem;
    text-decoration: none;
    border: none;
    cursor: pointer;
  }
  .sheet-actions a.primary {
    background: var(--accent);
    color: #fff;
  }
  .sheet-actions a.ghost {
    background: var(--bg);
    color: var(--ink);
    border: 1px solid var(--line);
  }
  .sheet-close-btn {
    background: transparent;
    color: var(--muted);
    margin-left: auto;
  }

  /* Desktop: side list + map */
  @media (min-width: 900px) {
    .topbar { padding-left: 24px; padding-right: 24px; }
    .tabbar {
      left: auto;
      right: 24px;
      bottom: 24px;
      width: auto;
      height: auto;
      padding: 6px;
      padding-bottom: 6px;
      border-radius: 999px;
      border: 1px solid var(--line);
      grid-template-columns: repeat(5, auto);
      gap: 2px;
      box-shadow: var(--shadow-lg);
    }
    .tab {
      flex-direction: row;
      gap: 8px;
      padding: 10px 18px;
      min-height: 44px;
      border-radius: 999px;
      font-size: 0.82rem;
    }
    .tab.active { background: var(--accent-soft); }
    .panel {
      left: 0;
      width: min(420px, 40vw);
      right: auto;
      padding-bottom: 0;
      border-right: 1px solid var(--line);
      box-shadow: var(--shadow);
    }
    #map { left: 0; }
    .map-shifted #map { left: min(420px, 40vw); }
    .sheet {
      left: 50%;
      right: auto;
      width: min(440px, 92vw);
      transform: translate(-50%, 110%);
      bottom: 96px;
      border-radius: 22px;
      max-height: min(70vh, 560px);
      padding-bottom: 0;
    }
    .sheet.open { transform: translate(-50%, 0); }
    .active-filter-bar {
      left: auto;
      right: 24px;
      bottom: 96px;
      width: auto;
      max-width: 360px;
    }
    .map-shifted .active-filter-bar { /* stay over map */ }
  }
</style>
</head>
<body>
<div id="app">
  <div id="map" role="application" aria-label="Map of toddler outing spots"></div>

  <header class="topbar">
    <div class="brand" aria-hidden="true">
      <span class="brand-mark">T</span>
      <span class="brand-text">Toddler Spots<span class="brand-sub">Denver · Arvada</span></span>
    </div>
    <div class="search-pill">
      <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true" focusable="false"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5" stroke-linecap="round"/></svg>
      <input type="search" id="search" placeholder="Search parks, museums…" autocomplete="off" enterkeyhint="search" aria-label="Search places"/>
    </div>
    <span class="count-chip" id="count-chip">__COUNT__</span>
  </header>

  <div class="active-filter-bar" id="filter-bar" aria-live="polite">
    <span id="filter-bar-label">Filtered</span>
    <button type="button" id="clear-filter">Clear</button>
  </div>

  <section class="panel" id="panel-list" aria-label="Place list">
    <div class="panel-header">
      <h1>All spots</h1>
      <p id="list-sub">Sorted by drive time from __BASE_LABEL__</p>
    </div>
    <div class="panel-body" id="list"></div>
  </section>

  <section class="panel" id="panel-events" aria-label="Upcoming events">
    <div class="panel-header">
      <h1>Upcoming events</h1>
      <p id="events-sub">Dated family activities, soonest first</p>
    </div>
    <div class="panel-body" id="events"></div>
  </section>

  <section class="panel" id="panel-filters" aria-label="Filters">
    <div class="panel-header">
      <h1>Filters</h1>
      <p>Narrow by drive time, cost, or indoor-friendly</p>
    </div>
    <div class="panel-body">
      <div class="filter-grid" role="listbox" aria-label="Filter options">
        <button type="button" class="filter-chip active" data-filter="all" role="option" aria-selected="true">
          <span class="dot"></span>
          <span class="label">All spots<span class="hint"><br>Show everything</span></span>
          <span class="check"></span>
        </button>
        <button type="button" class="filter-chip" data-filter="near" role="option" aria-selected="false">
          <span class="dot"></span>
          <span class="label">Near (~30 min)<span class="hint"><br>From __BASE_LABEL__</span></span>
          <span class="check"></span>
        </button>
        <button type="button" class="filter-chip" data-filter="far" role="option" aria-selected="false">
          <span class="dot"></span>
          <span class="label">Farther<span class="hint"><br>Worth the drive</span></span>
          <span class="check"></span>
        </button>
        <button type="button" class="filter-chip" data-filter="free" role="option" aria-selected="false">
          <span class="dot"></span>
          <span class="label">Free<span class="hint"><br>Parks & free-entry spots</span></span>
          <span class="check"></span>
        </button>
        <button type="button" class="filter-chip" data-filter="indoor" role="option" aria-selected="false">
          <span class="dot"></span>
          <span class="label">Indoor<span class="hint"><br>Museums, play, libraries</span></span>
          <span class="check"></span>
        </button>
      </div>
    </div>
  </section>

  <section class="panel" id="panel-about" aria-label="About">
    <div class="panel-header">
      <h1>About</h1>
      <p>Curated toddler outings near home</p>
    </div>
    <div class="panel-body">
      <div class="about-card">
        <h2>Base & audience</h2>
        <p>Home base: <strong>__BASE_LABEL__</strong>. Aimed at a toddler ~20 months; prefer spots within ~30 minutes.</p>
        <p>Updated __UPDATED__ · __COUNT__ places · __EVENT_COUNT__ upcoming events</p>
      </div>
      <div class="about-card">
        <h2>Map legend</h2>
        <div class="legend-row"><i style="background:#2A9D8F"></i> Within ~30 min</div>
        <div class="legend-row"><i style="background:#C45C26"></i> Farther</div>
        <div class="legend-row"><i style="background:#3B6EA5"></i> Home (80004)</div>
      </div>
      <div class="about-card">
        <h2>Sources</h2>
        <ul>
__SOURCES_HTML__
        </ul>
        <p>Why-notes paraphrased from those guides. Drive times are rough estimates — confirm in Maps.</p>
      </div>
    </div>
  </section>

  <nav class="tabbar" role="tablist" aria-label="Main">
    <button type="button" class="tab active" data-tab="map" role="tab" aria-selected="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M9 4l-5 2v14l5-2 6 2 5-2V4l-5 2-6-2z"/><path d="M9 4v14M15 6v14"/></svg>
      Map
    </button>
    <button type="button" class="tab" data-tab="list" role="tab" aria-selected="false">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M8 6h12M8 12h12M8 18h12" stroke-linecap="round"/><circle cx="4" cy="6" r="1.2" fill="currentColor" stroke="none"/><circle cx="4" cy="12" r="1.2" fill="currentColor" stroke="none"/><circle cx="4" cy="18" r="1.2" fill="currentColor" stroke="none"/></svg>
      List
    </button>
    <button type="button" class="tab" data-tab="events" role="tab" aria-selected="false">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3.5" y="5" width="17" height="16" rx="2"/><path d="M7 3v4M17 3v4M3.5 10h17M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01" stroke-linecap="round" stroke-linejoin="round"/></svg>
      Events
    </button>
    <button type="button" class="tab" data-tab="filters" role="tab" aria-selected="false">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M4 6h16M7 12h10M10 18h4" stroke-linecap="round"/></svg>
      Filters
    </button>
    <button type="button" class="tab" data-tab="about" role="tab" aria-selected="false">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="9"/><path d="M12 10v6M12 7.5v.5" stroke-linecap="round"/></svg>
      About
    </button>
  </nav>

  <div class="sheet-backdrop" id="sheet-backdrop"></div>
  <aside class="sheet" id="sheet" role="dialog" aria-modal="true" aria-labelledby="sheet-title" hidden>
    <div class="sheet-handle" aria-hidden="true"></div>
    <div class="sheet-scroll" id="sheet-body"></div>
  </aside>
</div>

<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<script>
const PLACES_DOC = __PLACES_JSON__;
const EVENTS_DOC = __EVENTS_JSON__;
</script>
<script>
(function(){
  const places = PLACES_DOC.places || [];
  const events = EVENTS_DOC.events || [];
  const placesById = Object.fromEntries(places.map(p => [p.id, p]));
  const base = PLACES_DOC.meta && PLACES_DOC.meta.base;
  const app = document.getElementById('app');
  const topbar = document.querySelector('.topbar');
  const listEl = document.getElementById('list');
  const eventsEl = document.getElementById('events');
  const eventsSub = document.getElementById('events-sub');
  const searchEl = document.getElementById('search');
  const countChip = document.getElementById('count-chip');
  const filterBar = document.getElementById('filter-bar');
  const filterBarLabel = document.getElementById('filter-bar-label');
  const sheet = document.getElementById('sheet');
  const sheetBody = document.getElementById('sheet-body');
  const sheetBackdrop = document.getElementById('sheet-backdrop');
  const listSub = document.getElementById('list-sub');

  let filter = 'all';
  let query = '';
  let currentTab = 'map';
  let activeId = null;
  const markers = {};

  // Soft light basemap: OpenFreeMap Positron (MapLibre, no token)
  const map = new maplibregl.Map({
    container: 'map',
    style: 'https://tiles.openfreemap.org/styles/positron',
    center: base ? [base.lng, base.lat] : [-105.0, 39.74],
    zoom: 10.2,
    attributionControl: true
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
  map.addControl(new maplibregl.GeolocateControl({
    positionOptions: { enableHighAccuracy: true },
    trackUserLocation: false
  }), 'top-right');

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
  function snippet(text, n){
    const t = String(text||'').trim();
    if (t.length <= n) return t;
    return t.slice(0, n).replace(/\s+\S*$/, '') + '…';
  }
  function mapsUrl(p){
    const q = encodeURIComponent(p.address || (p.name + ' Denver CO'));
    return 'https://www.google.com/maps/search/?api=1&query=' + q;
  }

  function badgesHtml(p){
    const badges = [];
    badges.push(p.farther_than_30min ? '<span class="badge far">Farther</span>' : '<span class="badge near">Near</span>');
    if (isFree(p)) badges.push('<span class="badge free">Free</span>');
    if (isIndoor(p)) badges.push('<span class="badge indoor">Indoor</span>');
    return badges.join('');
  }

  function openSheet(p){
    activeId = p.id;
    Object.keys(markers).forEach(id => {
      markers[id].el.classList.toggle('active', id === p.id);
    });
    const links = (p.links||[]).slice(0, 4).map(l =>
      `<a class="ghost" href="${escapeHtml(l.url)}" target="_blank" rel="noopener">${escapeHtml(l.label||'Link')}</a>`
    ).join('');
    sheetBody.innerHTML = `
      <div class="sheet-badges">${badgesHtml(p)}</div>
      <h2 id="sheet-title">${escapeHtml(p.name)}</h2>
      <div class="sheet-section"><strong>Address</strong>${escapeHtml(p.address||'—')}</div>
      <div class="sheet-section"><strong>Why go</strong>${escapeHtml(p.why||'')}</div>
      <div class="sheet-section"><strong>Source</strong>${escapeHtml(p.source||'')}</div>
      ${p.drive_note ? `<div class="sheet-section"><strong>Drive</strong>${escapeHtml(p.drive_note)}</div>` : ''}
      ${p.hours ? `<div class="sheet-section"><strong>Hours</strong>${escapeHtml(p.hours)}</div>` : ''}
      ${p.cost ? `<div class="sheet-section"><strong>Cost</strong>${escapeHtml(p.cost)}</div>` : ''}
      ${p.toddler_notes ? `<div class="sheet-section"><strong>Toddler tip</strong>${escapeHtml(p.toddler_notes)}</div>` : ''}
      <div class="sheet-actions">
        <a class="primary" href="${mapsUrl(p)}" target="_blank" rel="noopener">Directions</a>
        ${links}
        <button type="button" class="sheet-close-btn" id="sheet-close">Close</button>
      </div>`;
    sheet.hidden = false;
    requestAnimationFrame(() => {
      sheet.classList.add('open');
      sheetBackdrop.classList.add('open');
    });
    const closeBtn = document.getElementById('sheet-close');
    if (closeBtn) closeBtn.onclick = closeSheet;
    listEl.querySelectorAll('.place-card').forEach(el => el.classList.toggle('active', el.dataset.id === p.id));
  }

  function closeSheet(){
    sheet.classList.remove('open');
    sheetBackdrop.classList.remove('open');
    activeId = null;
    Object.keys(markers).forEach(id => markers[id].el.classList.remove('active'));
    setTimeout(() => { if (!sheet.classList.contains('open')) sheet.hidden = true; }, 320);
  }
  sheetBackdrop.addEventListener('click', closeSheet);

  function flyTo(p){
    map.flyTo({ center: [p.lng, p.lat], zoom: Math.max(map.getZoom(), 13), essential: true, padding: { top: 80, bottom: 200, left: 40, right: 40 } });
  }

  // Markers after style loads
  map.on('load', () => {
    const bounds = new maplibregl.LngLatBounds();

    places.forEach(p => {
      const el = document.createElement('div');
      el.className = 'pin ' + (p.farther_than_30min ? 'far' : 'near');
      el.title = p.name;
      el.setAttribute('role', 'button');
      el.setAttribute('aria-label', p.name);
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        openSheet(p);
        flyTo(p);
      });
      const marker = new maplibregl.Marker({ element: el, anchor: 'center' })
        .setLngLat([p.lng, p.lat])
        .addTo(map);
      markers[p.id] = { marker, el, place: p };
      bounds.extend([p.lng, p.lat]);
    });

    if (base) {
      const homeEl = document.createElement('div');
      homeEl.className = 'home-pin';
      homeEl.textContent = 'HOME';
      new maplibregl.Marker({ element: homeEl, anchor: 'center' })
        .setLngLat([base.lng, base.lat])
        .addTo(map);
      bounds.extend([base.lng, base.lat]);
    }

    if (!bounds.isEmpty()) {
      map.fitBounds(bounds, { padding: { top: 100, bottom: 100, left: 40, right: 40 }, maxZoom: 11.5 });
    }
    setTimeout(() => map.resize(), 200);
  });

  function matchesQuery(p, q){
    if (!q) return true;
    const blob = [p.name, p.address, p.why, p.source, p.toddler_notes, ...(p.tags||[])].join(' ').toLowerCase();
    return blob.includes(q);
  }
  function passesFilter(p){
    if (filter === 'near') return !p.farther_than_30min;
    if (filter === 'far') return !!p.farther_than_30min;
    if (filter === 'free') return isFree(p);
    if (filter === 'indoor') return isIndoor(p);
    return true;
  }

  const FILTER_LABELS = {
    all: 'All spots',
    near: 'Near (~30 min)',
    far: 'Farther',
    free: 'Free',
    indoor: 'Indoor'
  };

  function updateFilterBar(){
    if (filter === 'all') {
      filterBar.classList.remove('show');
    } else {
      filterBar.classList.add('show');
      filterBarLabel.textContent = FILTER_LABELS[filter] || filter;
    }
  }

  function renderList(){
    const sorted = places.slice().sort((a,b)=> (a.approx_drive_minutes||999)-(b.approx_drive_minutes||999));
    const filtered = sorted.filter(p => passesFilter(p) && matchesQuery(p, query));
    countChip.textContent = filtered.length + (filtered.length === places.length ? '' : ' / ' + places.length);
    listSub.textContent = filtered.length + ' spot' + (filtered.length===1?'':'s') + ' · sorted by drive from ' + (base ? base.label : 'home');

    if (!filtered.length) {
      listEl.innerHTML = '<div class="empty">No spots match.<br>Try another filter or clear search.</div>';
    } else {
      listEl.innerHTML = filtered.map(p => `
        <article class="place-card${activeId===p.id?' active':''}" data-id="${escapeHtml(p.id)}" role="button" tabindex="0">
          <div class="card-top">${badgesHtml(p)}</div>
          <h3>${escapeHtml(p.name)}</h3>
          <p class="why-snip">${escapeHtml(snippet(p.why, 120))}</p>
          <div class="card-meta">
            <span>${escapeHtml(p.drive_note||'')}</span>
            <span>${escapeHtml(snippet(p.source, 42))}</span>
          </div>
        </article>`).join('');
    }

    listEl.querySelectorAll('.place-card').forEach(el => {
      const go = () => {
        const p = places.find(x => x.id === el.dataset.id);
        if (!p) return;
        setTab('map');
        openSheet(p);
        flyTo(p);
      };
      el.addEventListener('click', go);
      el.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); }
      });
    });

    // Toggle markers
    places.forEach(p => {
      const show = passesFilter(p) && matchesQuery(p, query);
      const m = markers[p.id];
      if (!m) return;
      m.el.style.display = show ? '' : 'none';
    });
    updateFilterBar();
  }

  function shortDate(key){
    const d = new Date(key + 'T12:00:00Z');
    return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' }).format(d);
  }
  function longDate(key){
    const d = new Date(key + 'T12:00:00Z');
    return new Intl.DateTimeFormat('en-US', { weekday: 'long', month: 'short', day: 'numeric', timeZone: 'UTC' }).format(d);
  }
  function eventDateLabel(e){
    return e.end_date && e.end_date !== e.date ? shortDate(e.date) + '–' + shortDate(e.end_date) : shortDate(e.date);
  }
  function eventDateKeys(e){
    const keys = [];
    const end = e.end_date || e.date;
    let d = new Date(e.date + 'T12:00:00Z');
    const last = new Date(end + 'T12:00:00Z');
    while (d <= last) {
      keys.push(d.toISOString().slice(0,10));
      d.setUTCDate(d.getUTCDate() + 1);
    }
    return keys;
  }
  function renderEvents(){
    const today = new Intl.DateTimeFormat('en-CA', { year: 'numeric', month: '2-digit', day: '2-digit', timeZone: 'America/Denver' }).format(new Date());
    const upcoming = events.filter(e => String(e.end_date || e.date) >= today).sort((a,b) => String(a.date).localeCompare(String(b.date)));
    eventsSub.textContent = upcoming.length + ' upcoming event' + (upcoming.length===1?'':'s') + ' · grouped by day';
    const groups = {};
    upcoming.forEach(e => eventDateKeys(e).forEach(key => { (groups[key] ||= []).push(e); }));
    const days = Object.keys(groups).sort();
    if (!days.length) { eventsEl.innerHTML = '<div class="empty">No upcoming events listed yet.</div>'; return; }
    eventsEl.innerHTML = days.map(day => `
      <section class="event-day" aria-labelledby="event-day-${day}">
        <h2 class="event-day-heading" id="event-day-${day}">${escapeHtml(longDate(day))}<span>${groups[day].length} event${groups[day].length===1?'':'s'}</span></h2>
        ${groups[day].map(e => {
          const linked = e.place_id && placesById[e.place_id];
          return `<article class="event-card${linked?' linked':''}"${linked?` data-place-id="${escapeHtml(e.place_id)}" role="button" tabindex="0"`:''}>
            <div class="event-date-label">${escapeHtml(eventDateLabel(e))}</div>
            <h3>${escapeHtml(e.title)}</h3>
            <div class="event-meta"><span>${escapeHtml(e.time||'Time to be confirmed')}</span><span class="event-place">${escapeHtml(e.place || '')}</span></div>
            <p class="event-note">${escapeHtml(e.note||'')}</p>
            ${e.drive_note ? `<div class="event-meta"><span>${escapeHtml(e.drive_note)}</span></div>` : ''}
            ${e.link ? `<a class="event-link" href="${escapeHtml(e.link)}" target="_blank" rel="noopener">Event details ↗</a>` : ''}
            ${linked ? '<span class="event-meta">Tap card to open map pin</span>' : ''}
          </article>`;
        }).join('')}
      </section>`).join('');
    eventsEl.querySelectorAll('.event-card[data-place-id]').forEach(el => {
      const go = () => {
        const place = placesById[el.dataset.placeId];
        if (!place) return;
        setTab('map'); openSheet(place); flyTo(place);
      };
      el.addEventListener('click', e => { if (!e.target.closest('a')) go(); });
      el.addEventListener('keydown', e => { if ((e.key === 'Enter' || e.key === ' ') && !e.target.closest('a')) { e.preventDefault(); go(); } });
    });
  }

  function setTab(name){
    currentTab = name;
    const mapActive = name === 'map';
    topbar.hidden = !mapActive;
    topbar.setAttribute('aria-hidden', mapActive ? 'false' : 'true');
    document.querySelectorAll('.tab').forEach(t => {
      const on = t.dataset.tab === name;
      t.classList.toggle('active', on);
      t.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    if (name === 'list') document.getElementById('panel-list').classList.add('active');
    if (name === 'events') document.getElementById('panel-events').classList.add('active');
    if (name === 'filters') document.getElementById('panel-filters').classList.add('active');
    if (name === 'about') document.getElementById('panel-about').classList.add('active');
    app.classList.toggle('map-shifted', name === 'list' || name === 'events' || name === 'filters' || name === 'about');
    if (name === 'map') setTimeout(() => map.resize(), 50);
    else setTimeout(() => map.resize(), 50);
  }

  document.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', () => setTab(btn.dataset.tab));
  });

  function setFilter(f){
    filter = f;
    document.querySelectorAll('.filter-chip').forEach(b => {
      const on = b.dataset.filter === f;
      b.classList.toggle('active', on);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    renderList();
  }

  document.querySelectorAll('.filter-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      setFilter(btn.dataset.filter);
      // After picking a filter, jump to list so results are visible
      if (btn.dataset.filter !== 'all') setTab('list');
    });
  });
  document.getElementById('clear-filter').addEventListener('click', () => setFilter('all'));

  let searchTimer;
  searchEl.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      query = searchEl.value.trim().toLowerCase();
      renderList();
    }, 100);
  });

  renderEvents();

  // Wait for markers then first render
  map.on('load', () => renderList());
  // Also render list HTML immediately (markers toggle later)
  renderList();

  window.addEventListener('resize', () => map.resize());
})();
</script>
</body>
</html>
'''

def source_link(label, url):
    """Return a safe external link for a source metadata field."""
    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        return ""
    return (f'<a href="{html.escape(url, quote=True)}" target="_blank" '
            f'rel="noopener">{html.escape(label)}</a>')


def sources_html(meta):
    """Render the About source list directly from meta.sources_scrubbed."""
    fields = (("instagram", "Instagram"), ("facebook", "Facebook"),
              ("newsletter", "newsletter"), ("tiktok", "TikTok"))
    rows = []
    for source in meta.get("sources_scrubbed", []):
        name = str(source.get("name", "")).strip()
        if not name:
            continue
        available = [(field, label, source.get(field)) for field, label in fields
                     if source_link(label, source.get(field))]
        if available:
            # Make the account name itself the primary social link, then expose
            # additional accounts/newsletters without hard-coding the list.
            primary_field, _, primary_url = next(
                (item for item in available if item[0] == "instagram"), available[0]
            )
            primary = source_link(name, primary_url)
            extras = [source_link(label, url) for field, label, url in available
                      if field != primary_field]
            rendered = primary + (" (" + " · ".join(extras) + ")" if extras else "")
        else:
            rendered = html.escape(name)
        rows.append(f"          <li>{rendered}</li>")
    return "\n".join(rows)

def build():
    doc = json.loads(DATA.read_text())
    events_doc = json.loads(EVENTS_DATA.read_text())
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    OUT_EVENTS.write_text(json.dumps(events_doc, indent=2, ensure_ascii=False) + "\n")
    places_json = json.dumps(doc, ensure_ascii=False)
    html_out = (TEMPLATE
        .replace("__SOURCES_HTML__", sources_html(doc.get("meta", {})))
        .replace("__PLACES_JSON__", places_json)
        .replace("__EVENTS_JSON__", json.dumps(events_doc, ensure_ascii=False))
        .replace("__UPDATED__", str(doc.get("meta", {}).get("updated", "")))
        .replace("__COUNT__", str(len(doc.get("places", []))))
        .replace("__EVENT_COUNT__", str(len(events_doc.get("events", []))))
        .replace("__BASE_LABEL__", str(doc.get("meta", {}).get("base", {}).get("label", "home")))
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

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    sources = DOCS_DIR / "SOURCES.md"
    sources_backup = sources.read_text() if sources.exists() else None
    for name in ("index.html", "places.json", "events.json", "INDEX.md"):
        src = OUT_DIR / name
        if src.exists():
            shutil.copy2(src, DOCS_DIR / name)
    if sources_backup is not None:
        sources.write_text(sources_backup)

    print(f"Wrote {OUT_HTML}")
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    print(f"Events: {len(events_doc.get('events', []))}")
    print(f"Synced docs/ for GitHub Pages")
    print(f"Places: {len(doc['places'])}")

if __name__ == "__main__":
    build()
