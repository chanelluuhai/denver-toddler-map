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
<meta name="theme-color" content="#E8E6E4"/>
<meta name="apple-mobile-web-app-capable" content="yes"/>
<meta name="apple-mobile-web-app-status-bar-style" content="default"/>
<meta name="description" content="Toddler outing map near Arvada/Denver — parks, museums, indoor play, farms from local parent guides."/>
<title>Toddler Spots · Denver / Arvada</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,500;8..60,600;8..60,700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet"/>
<style>
  :root {
    --accent: #B57A88;
    --accent-soft: #F6EBEE;
    --accent-dark: #8E5A68;
    --blush: #E5B8C2;
    --blush-deep: #C98998;
    --mauve: #C4A8B4;
    --ink: #2F2A27;
    --ink-2: #5A524C;
    --muted: #9A9088;
    --line: rgba(80, 60, 58, 0.08);
    --bg: #E8E6E4;
    --bg-mid: #EDE8E6;
    --card: #FFFEFC;
    --far: #4F6F86;
    --far-soft: #E6EEF2;
    --near: #C4536E;
    --near-soft: #F8E7EB;
    --free: #B57A88;
    --free-soft: #F6EBEE;
    --indoor: #A08B8E;
    --indoor-soft: #F0EAEA;
    --shadow: 0 10px 32px rgba(70, 50, 48, 0.06);
    --shadow-lg: 0 18px 48px rgba(60, 40, 42, 0.10);
    --radius: 34px;
    --radius-sm: 26px;
    --tap: 48px;
    --tab-h: calc(104px + env(safe-area-inset-bottom, 0px));
    --top-h: 56px;
    --safe-top: env(safe-area-inset-top, 0px);
    --safe-bottom: env(safe-area-inset-bottom, 0px);
    --font: "Inter", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    --display: "Source Serif 4", "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  }
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  html, body { height: 100%; margin: 0; overflow: hidden; }
  body {
    font-family: var(--font);
    color: var(--ink);
    background:
      linear-gradient(180deg,
        #E8E6E4 0%,
        #EBE7E5 38%,
        #F0E6E6 68%,
        #E9D5D8 100%);
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
  .topbar.search-focused { gap: 0; }
  .topbar.search-focused .brand { display: none; }
  .topbar.search-focused .search-pill {
    flex: 1 1 100%;
    max-width: none;
  }
  .topbar::before {
    content: "";
    position: absolute;
    left: 0; right: 0; top: 0;
    height: calc(120px + var(--safe-top));
    pointer-events: none;
    background: linear-gradient(to bottom, rgba(232, 230, 228, 0.82) 0%, rgba(232, 230, 228, 0.35) 55%, transparent 100%);
    backdrop-filter: blur(16px) saturate(1.1);
    -webkit-backdrop-filter: blur(16px) saturate(1.1);
    -webkit-mask-image: linear-gradient(to bottom, #000 25%, transparent 100%);
    mask-image: linear-gradient(to bottom, #000 25%, transparent 100%);
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(255, 254, 252, 0.78);
    backdrop-filter: blur(24px) saturate(1.2);
    -webkit-backdrop-filter: blur(24px) saturate(1.2);
    border: none;
    border-radius: 999px;
    padding: 8px 16px 8px 10px;
    box-shadow: 0 8px 24px rgba(70, 50, 48, 0.07);
    flex-shrink: 0;
  }
  .brand-mark {
    width: auto; height: auto;
    border-radius: 0;
    background: transparent;
    color: inherit;
    display: grid; place-items: center;
    flex-shrink: 0;
  }
  .brand-mark .brand-emoji {
    font-size: 22px;
    line-height: 1;
  }
  .brand-text {
    font-family: var(--display);
    font-weight: 600;
    font-size: 1.02rem;
    letter-spacing: -0.015em;
    line-height: 1.15;
  }
  .brand-sub {
    display: block;
    font-family: var(--font);
    font-weight: 400;
    font-size: 0.65rem;
    color: var(--muted);
    letter-spacing: 0.02em;
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
    border: none;
    border-radius: 999px;
    padding: 10px 16px 10px 42px;
    /* 16px prevents iOS Safari from auto-zooming on focus. */
    font-size: 16px;
    line-height: 1.25;
    -webkit-appearance: none;
    appearance: none;
    background: rgba(255, 254, 252, 0.82);
    backdrop-filter: blur(24px) saturate(1.2);
    -webkit-backdrop-filter: blur(24px) saturate(1.2);
    box-shadow: 0 8px 24px rgba(70, 50, 48, 0.07);
    outline: none;
    color: var(--ink);
  }
  .search-pill input::placeholder { color: #A89E96; }
  .search-pill input:focus {
    box-shadow: 0 8px 24px rgba(70, 50, 48, 0.09), 0 0 0 3px rgba(181, 122, 136, 0.22);
  }
  .search-pill .ico {
    position: absolute; left: 14px; top: 50%; z-index: 1;
    display: block; transform: translateY(-50%);
    color: var(--muted); pointer-events: none; width: 18px; height: 18px;
    stroke: currentColor; stroke-width: 2; overflow: visible;
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
    box-shadow: 0 2px 8px rgba(70,45,48,0.18);
    cursor: pointer;
    transition: transform .15s;
  }
  .pin.near { background: var(--near); }
  .pin.far { background: var(--far); }
  .pin.active { transform: scale(1.35); box-shadow: 0 0 0 4px rgba(196,137,152,0.35), 0 2px 10px rgba(60,40,45,0.22); }
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
    background:
      linear-gradient(180deg,
        #E8E6E4 0%,
        #EBE7E5 40%,
        #F0E6E6 72%,
        #E9D5D8 100%);
    display: none;
    overflow: auto;
    -webkit-overflow-scrolling: touch;
  }
  .panel.active { display: block; }
  .panel-header {
    position: sticky;
    top: 0;
    z-index: 4;
    padding: calc(22px + var(--safe-top)) 24px 10px;
  }
  /* Frosted fade: content scrolls under the title and blurs out, no hard edge. */
  .panel-header::before {
    content: "";
    position: absolute;
    left: 0; right: 0; top: 0;
    height: calc(100% + 18px);
    pointer-events: none;
    z-index: -1;
    background: linear-gradient(to bottom,
      rgba(232, 230, 228, 0.55) 0%,
      rgba(235, 231, 229, 0.28) 46%,
      rgba(235, 231, 229, 0.08) 72%,
      transparent 100%);
    backdrop-filter: blur(18px) saturate(1.25);
    -webkit-backdrop-filter: blur(18px) saturate(1.25);
    -webkit-mask-image: linear-gradient(to bottom, #000 0%, #000 48%, transparent 100%);
    mask-image: linear-gradient(to bottom, #000 0%, #000 48%, transparent 100%);
  }
  .panel-header h1 {
    position: relative;
    font-family: var(--display);
    font-size: 1.95rem;
    font-weight: 600;
    font-optical-sizing: auto;
    margin: 0;
    letter-spacing: -0.02em;
    line-height: 1.2;
    color: var(--ink);
  }
  .panel-body {
    /* Leave the frosted sticky heading room to fade before content begins. */
    padding: 12px 18px calc(var(--tab-h) + 22px);
  }

  /* List cards */
  .place-card {
    background: var(--card);
    border: none;
    border-radius: var(--radius);
    padding: 18px 22px;
    margin-bottom: 12px;
    cursor: pointer;
    box-shadow: var(--shadow);
    transition: transform .12s, box-shadow .15s;
  }
  .place-card:active { transform: scale(0.985); }
  .place-card:hover, .place-card.active {
    box-shadow: var(--shadow-lg);
  }
  .place-card.active { outline: 2px solid rgba(181,122,136,0.40); outline-offset: 2px; }
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
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 999px;
    letter-spacing: 0.02em;
  }
  .badge.near { background: var(--near-soft); color: var(--near); }
  .badge.far { background: var(--far-soft); color: var(--far); }
  .badge.free { background: var(--free-soft); color: var(--free); }
  .badge.indoor { background: var(--indoor-soft); color: var(--indoor); }
  .place-card h3 {
    margin: 0;
    font-family: var(--display);
    font-size: 1.22rem;
    font-weight: 600;
    letter-spacing: -0.015em;
    line-height: 1.3;
    color: var(--ink);
  }
  .card-line {
    margin: 4px 0 0;
    font-size: 0.84rem;
    color: var(--muted);
    line-height: 1.35;
  }
  .empty {
    text-align: center;
    color: var(--muted);
    padding: 48px 20px;
    font-size: 0.95rem;
    line-height: 1.5;
  }

  /* Events panel */
  .event-day { margin: 0 0 22px; }
  .event-day-heading {
    display: flex; align-items: baseline; justify-content: space-between;
    gap: 10px; margin: 6px 8px 12px;
    font-family: var(--display); font-size: 1.2rem; font-weight: 600;
    color: var(--ink); line-height: 1.3;
  }
  .event-day-heading span { color: var(--muted); font-family: var(--font); font-size: .7rem; font-weight: 500; text-transform: uppercase; letter-spacing: .08em; }
  .event-card {
    background: var(--card); border: none; border-radius: var(--radius);
    padding: 18px 22px; margin-bottom: 12px; box-shadow: var(--shadow);
  }
  .event-card.linked { cursor: pointer; transition: transform .12s, box-shadow .15s, border-color .15s; }
  .event-card.linked:hover, .event-card.linked:focus { box-shadow: var(--shadow-lg); outline: none; }
  .event-card.linked:active { transform: scale(.985); }
  .event-date-label { color: var(--muted); font-size: .72rem; font-weight: 500; margin-bottom: 6px; letter-spacing: 0.01em; }
  .event-card-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; margin: 0 0 6px; }
  .event-card h3 { margin: 0; flex: 1 1 auto; font-family: var(--display); font-size: 1.18rem; line-height: 1.3; font-weight: 600; color: var(--ink); }
  .cal-add {
    flex: 0 0 auto; align-self: flex-start;
    font-size: 0.75rem; font-weight: 600; line-height: 1.2;
    color: var(--accent-dark); text-decoration: none;
    background: var(--accent-soft); border-radius: 999px;
    padding: 7px 10px; white-space: nowrap;
  }
  .cal-add:hover { text-decoration: underline; }
  .event-meta { display: flex; flex-wrap: wrap; gap: 5px 12px; color: var(--muted); font-size: .78rem; margin: 0; }
  .event-time { color: var(--accent-dark); font-weight: 600; }
  .event-note {
    margin: 0 0 10px; color: var(--ink-2); font-size: .86rem; line-height: 1.4;
    display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 1;
    overflow: hidden; text-overflow: ellipsis;
  }
  .event-place {
    margin: 0 0 7px; color: var(--muted); font-size: .8rem; line-height: 1.3;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .event-link { color: var(--accent-dark); font-size: .82rem; font-weight: 600; text-decoration: none; }
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
    border: none;
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 18px 20px;
    min-height: var(--tap);
    cursor: pointer;
    transition: border-color .15s, background .15s, transform .1s;
  }
  .filter-chip:active { transform: scale(0.98); }
  .filter-chip.active {
    background: var(--accent-soft);
    box-shadow: 0 0 0 1.5px var(--accent), var(--shadow);
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
    font-weight: 500;
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
    left: 14px; right: 14px;
    bottom: calc(var(--tab-h) + 14px);
    z-index: 15;
    display: none;
    align-items: center;
    gap: 8px;
    background: rgba(255, 254, 252, 0.88);
    backdrop-filter: blur(20px) saturate(1.15);
    -webkit-backdrop-filter: blur(20px) saturate(1.15);
    border: none;
    border-radius: 999px;
    padding: 8px 8px 8px 16px;
    box-shadow: var(--shadow);
    font-size: 0.85rem;
    font-weight: 500;
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
    border: none;
    border-radius: var(--radius);
    padding: 24px 24px 20px;
    margin-bottom: 16px;
    box-shadow: var(--shadow);
  }
  .about-card h2 {
    font-family: var(--display);
    font-size: 1.18rem;
    margin: 0 0 12px;
    font-weight: 600;
    line-height: 1.3;
    color: var(--ink);
  }
  .about-card p, .about-card li {
    font-size: 0.92rem;
    color: var(--ink-2);
    line-height: 1.6;
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

  /* —— Split glass navigation —— */
  .dock {
    position: absolute;
    left: 12px; right: 12px;
    bottom: calc(10px + var(--safe-bottom));
    z-index: 45;
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 12px;
    pointer-events: none;
  }
  .dock-left, .dock-btn, .seg { pointer-events: auto; }
  .dock-left {
    display: flex;
    align-items: flex-end;
    gap: 10px;
    min-width: 0;
  }
  .glass {
    background: rgba(255, 254, 252, 0.28);
    backdrop-filter: blur(22px) saturate(1.45);
    -webkit-backdrop-filter: blur(22px) saturate(1.45);
    border: 1px solid rgba(255, 254, 252, 0.5);
    box-shadow: 0 10px 28px rgba(70, 45, 50, 0.10);
  }
  .seg {
    --tab-pad: 6px;
    --tab-left: 0px;
    --tab-width: 0px;
    position: relative;
    display: flex;
    align-items: stretch;
    height: 80px;
    padding: var(--tab-pad);
    border-radius: 999px;
  }
  .tab-indicator {
    position: absolute;
    z-index: 0;
    top: var(--tab-pad);
    bottom: var(--tab-pad);
    left: 0;
    width: var(--tab-width);
    border: 1px solid rgba(255, 254, 252, 0.52);
    border-radius: 999px;
    background: linear-gradient(135deg, rgba(229, 184, 194, 0.88), rgba(196, 168, 180, 0.78));
    box-shadow: 0 5px 14px rgba(142, 90, 104, 0.18), inset 0 1px 0 rgba(255, 255, 255, 0.28);
    pointer-events: none;
    transform: translateX(var(--tab-left));
    transition: transform 480ms cubic-bezier(.22, 1, .36, 1), width 220ms ease, opacity 200ms ease;
    will-change: transform;
  }
  .seg.idle .tab-indicator { opacity: 0; }
  .tab, .dock-btn {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 3px;
    border: none;
    background: transparent;
    color: var(--muted);
    font-size: 0.86rem;
    font-weight: 600;
    letter-spacing: 0.01em;
    cursor: pointer;
    border-radius: 999px;
    transition: color 220ms ease, background 220ms ease, opacity 160ms ease, transform 180ms ease;
  }
  .tab {
    min-width: 64px;
    padding: 8px 14px;
    font-size: 0.92rem;
  }
  .dock-btn {
    height: 80px;
    min-width: 74px;
    padding: 8px 14px;
    border-radius: 28px;
    font-size: 0.92rem;
  }
  .tab svg, .dock-btn svg { width: 26px; height: 26px; stroke-width: 1.75; }
  .tab.active { color: var(--accent-dark); }
  .dock-btn.on {
    color: var(--accent-dark);
    background: linear-gradient(135deg, rgba(229, 184, 194, 0.88), rgba(196, 168, 180, 0.78));
    border-color: rgba(255, 254, 252, 0.55);
    box-shadow: 0 8px 18px rgba(142, 90, 104, 0.16), inset 0 1px 0 rgba(255, 255, 255, 0.28);
  }
  .tab:focus-visible, .dock-btn:focus-visible, .brand:focus-visible { outline: 2px solid var(--accent-dark); outline-offset: 2px; }
  .tab:active, .dock-btn:active { opacity: 0.72; transform: scale(0.97); }
  @media (prefers-reduced-motion: reduce) {
    .tab-indicator, .tab, .dock-btn, .filter-sheet, .about-drawer, .drawer-backdrop, .filter-backdrop { transition: none; }
  }

  /* Filter sheet sits above the map, under the nav so Filter stays tappable. */
  .filter-backdrop, .drawer-backdrop {
    position: absolute;
    inset: 0;
    background: rgba(55, 42, 40, 0.18);
    opacity: 0;
    pointer-events: none;
    transition: opacity .25s;
  }
  .filter-backdrop { z-index: 34; }
  .drawer-backdrop { z-index: 60; }
  .filter-backdrop.open, .drawer-backdrop.open { opacity: 1; pointer-events: auto; }
  .filter-sheet {
    position: absolute;
    left: 12px; right: 12px;
    bottom: calc(var(--tab-h) - 6px);
    z-index: 36;
    max-height: min(64dvh, 520px);
    overflow: auto;
    -webkit-overflow-scrolling: touch;
    background: rgba(255, 254, 252, 0.94);
    backdrop-filter: blur(26px) saturate(1.2);
    -webkit-backdrop-filter: blur(26px) saturate(1.2);
    border-radius: 28px;
    box-shadow: var(--shadow-lg);
    padding: 8px 12px 14px;
    transform: translateY(18px);
    opacity: 0;
    pointer-events: none;
    transition: transform .36s cubic-bezier(.22, 1, .36, 1), opacity .24s;
  }
  .filter-sheet.open { transform: translateY(0); opacity: 1; pointer-events: auto; }
  .filter-sheet-head {
    display: flex; align-items: center; justify-content: space-between;
    gap: 10px; padding: 8px 8px 6px;
  }
  .filter-sheet-head h2 {
    margin: 0; font-family: var(--display); font-size: 1.35rem; font-weight: 600; color: var(--ink);
  }
  .icon-x {
    width: 40px; height: 40px; border: none; border-radius: 999px;
    background: rgba(232, 230, 228, 0.9); color: var(--ink);
    font-size: 1.35rem; line-height: 1; cursor: pointer; flex-shrink: 0;
  }
  .filter-sheet .filter-chip { border-radius: 22px; padding: 14px 16px; box-shadow: none; background: rgba(255,254,252,0.7); }
  .filter-sheet .filter-chip.active { background: var(--accent-soft); }

  .about-drawer {
    position: absolute;
    top: 0; right: 0; bottom: 0;
    width: min(440px, 100%);
    z-index: 70;
    overflow: auto;
    -webkit-overflow-scrolling: touch;
    transform: translateX(104%);
    transition: transform .42s cubic-bezier(.22, 1, .36, 1);
    background: linear-gradient(180deg, #E8E6E4 0%, #EBE7E5 42%, #F0E6E6 74%, #E9D5D8 100%);
    box-shadow: -18px 0 48px rgba(60, 40, 42, 0.14);
    padding: calc(14px + var(--safe-top)) 18px calc(24px + var(--safe-bottom));
    border-radius: 28px 0 0 28px;
  }
  .about-drawer.open { transform: translateX(0); }
  .drawer-top {
    display: flex; align-items: flex-start; justify-content: space-between;
    gap: 12px; margin-bottom: 12px; position: sticky; top: 0; z-index: 2;
    padding-bottom: 8px;
  }
  .drawer-top h1 {
    margin: 6px 0 0; font-family: var(--display); font-size: 1.8rem; font-weight: 600; color: var(--ink);
  }
  button.brand { cursor: pointer; color: inherit; text-align: left; font: inherit; }

  /* —— Bottom sheet (place detail) —— */
  .sheet-backdrop {
    position: absolute;
    inset: 0;
    z-index: 40;
    background: rgba(55, 42, 40, 0.22);
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
    background: rgba(255, 254, 252, 0.96);
    backdrop-filter: blur(28px) saturate(1.15);
    -webkit-backdrop-filter: blur(28px) saturate(1.15);
    border-radius: 36px 36px 0 0;
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
    background: rgba(181, 122, 136, 0.35);
    border-radius: 999px;
    margin: 12px auto 8px;
    flex-shrink: 0;
  }
  .sheet-scroll {
    overflow: auto;
    -webkit-overflow-scrolling: touch;
    padding: 4px 24px 32px;
    flex: 1;
  }
  .sheet-scroll h2 {
    font-family: var(--display);
    font-size: 1.7rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    margin: 4px 0 12px;
    line-height: 1.25;
    color: var(--ink);
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
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--muted);
    margin-bottom: 4px;
    font-weight: 500;
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
    background: var(--accent-dark);
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

  @media (min-width: 900px) {
    .topbar { padding-left: 24px; padding-right: 24px; }
    .dock { left: 24px; right: 24px; bottom: 24px; }
    .tab { flex-direction: row; gap: 8px; min-width: 108px; font-size: 1rem; padding: 10px 20px; }
    .dock-btn { flex-direction: row; gap: 8px; min-width: 112px; font-size: 1rem; padding: 10px 20px; border-radius: 999px; }
    .about-drawer { width: min(460px, 42vw); }
    .filter-sheet { left: 24px; right: auto; width: min(420px, 40vw); bottom: 122px; }
    .sheet {
      left: 50%;
      right: auto;
      width: min(440px, 92vw);
      transform: translate(-50%, 110%);
      bottom: calc(var(--tab-h) + 8px);
      border-radius: 36px;
      max-height: min(70vh, 560px);
      padding-bottom: 0;
    }
    .sheet.open { transform: translate(-50%, 0); }
    .active-filter-bar {
      left: auto;
      right: 24px;
      bottom: calc(var(--tab-h) + 12px);
      width: auto;
      max-width: 360px;
    }
  }
</style>
</head>
<body>
<div id="app">
  <div id="map" role="application" aria-label="Map of toddler outing spots"></div>

  <header class="topbar">
    <button type="button" class="brand" id="open-about" aria-haspopup="dialog" aria-controls="about-drawer" aria-expanded="false">
      <span class="brand-mark">
        <span class="brand-emoji" role="img" aria-label="Baby">👶</span>
      </span>
      <span class="brand-text">Toddler Spots<span class="brand-sub">Denver · Arvada</span></span>
    </button>
    <div class="search-pill">
      <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true" focusable="false"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5" stroke-linecap="round"/></svg>
      <input type="search" id="search" placeholder="Search" autocomplete="off" enterkeyhint="search" aria-label="Search places"/>
    </div>
  </header>

  <div class="active-filter-bar" id="filter-bar" aria-live="polite">
    <span id="filter-bar-label">Filtered</span>
    <button type="button" id="clear-filter">Clear</button>
  </div>

  <section class="panel" id="panel-list" aria-label="Place list">
    <div class="panel-header">
      <h1>All spots</h1>
    </div>
    <div class="panel-body" id="list"></div>
  </section>

  <section class="panel" id="panel-events" aria-label="Upcoming events">
    <div class="panel-header">
      <h1>Upcoming events</h1>
    </div>
    <div class="panel-body" id="events"></div>
  </section>

  <div class="filter-backdrop" id="filter-backdrop" hidden></div>
  <aside class="filter-sheet" id="filter-sheet" role="dialog" aria-modal="true" aria-labelledby="filter-title" hidden>
    <div class="filter-sheet-head">
      <h2 id="filter-title">Filters</h2>
      <button type="button" class="icon-x" id="filter-close" aria-label="Close filters">&times;</button>
    </div>
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
  </aside>

  <div class="drawer-backdrop" id="about-backdrop" hidden></div>
  <aside class="about-drawer" id="about-drawer" role="dialog" aria-modal="true" aria-labelledby="about-title" hidden>
    <div class="drawer-top">
      <h1 id="about-title">About</h1>
      <button type="button" class="icon-x" id="about-close" aria-label="Close">&times;</button>
    </div>
    <div class="about-card">
      <h2>Base & audience</h2>
      <p>Home base: <strong>__BASE_LABEL__</strong>. Aimed at a toddler ~20 months; prefer spots within ~30 minutes.</p>
      <p>Updated __UPDATED__ · __COUNT__ places · __EVENT_COUNT__ upcoming events</p>
    </div>
    <div class="about-card">
      <h2>Map legend</h2>
      <div class="legend-row"><i style="background:#C4536E"></i> Within ~30 min</div>
      <div class="legend-row"><i style="background:#4F6F86"></i> Farther</div>
      <div class="legend-row"><i style="background:#B57A88"></i> Home (80004)</div>
    </div>
    <div class="about-card">
      <h2>Sources</h2>
      <ul>
__SOURCES_HTML__
      </ul>
      <p>Why-notes paraphrased from those guides. Drive times are rough estimates — confirm in Maps.</p>
    </div>
  </aside>

  <nav class="dock" aria-label="Main">
    <div class="dock-left">
      <div class="seg glass" id="view-seg" role="tablist" aria-label="Map or list">
        <span class="tab-indicator" aria-hidden="true"></span>
        <button type="button" class="tab active" data-tab="map" role="tab" aria-selected="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M9 4l-5 2v14l5-2 6 2 5-2V4l-5 2-6-2z"/><path d="M9 4v14M15 6v14"/></svg>
          Map
        </button>
        <button type="button" class="tab" data-tab="list" role="tab" aria-selected="false">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M8 6h12M8 12h12M8 18h12" stroke-linecap="round"/><circle cx="4" cy="6" r="1.2" fill="currentColor" stroke="none"/><circle cx="4" cy="12" r="1.2" fill="currentColor" stroke="none"/><circle cx="4" cy="18" r="1.2" fill="currentColor" stroke="none"/></svg>
          List
        </button>
      </div>
      <button type="button" class="dock-btn glass" id="filter-btn" aria-pressed="false" aria-expanded="false" aria-controls="filter-sheet">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M4 6h16M7 12h10M10 18h4" stroke-linecap="round"/></svg>
        Filter
      </button>
    </div>
    <button type="button" class="dock-btn glass" id="events-btn" aria-pressed="false">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3.5" y="5" width="17" height="16" rx="2"/><path d="M7 3v4M17 3v4M3.5 10h17M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01" stroke-linecap="round" stroke-linejoin="round"/></svg>
      Events
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
  const searchEl = document.getElementById('search');
  const filterBar = document.getElementById('filter-bar');
  const filterBarLabel = document.getElementById('filter-bar-label');
  const sheet = document.getElementById('sheet');
  const sheetBody = document.getElementById('sheet-body');
  const sheetBackdrop = document.getElementById('sheet-backdrop');
  const seg = document.getElementById('view-seg');
  const tabIndicator = document.querySelector('.tab-indicator');
  const tabs = Array.from(document.querySelectorAll('.seg .tab'));
  const eventsBtn = document.getElementById('events-btn');
  const filterBtn = document.getElementById('filter-btn');
  const filterSheet = document.getElementById('filter-sheet');
  const filterBackdrop = document.getElementById('filter-backdrop');
  const aboutDrawer = document.getElementById('about-drawer');
  const aboutBackdrop = document.getElementById('about-backdrop');
  const openAboutBtn = document.getElementById('open-about');
  let filterOpen = false;
  let aboutOpen = false;

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
    if (!filtered.length) {
      listEl.innerHTML = '<div class="empty">No spots match.<br>Try another filter or clear search.</div>';
    } else {
      listEl.innerHTML = filtered.map(p => `
        <article class="place-card${activeId===p.id?' active':''}" data-id="${escapeHtml(p.id)}" role="button" tabindex="0">
          <h3>${escapeHtml(p.name)}</h3>
          <p class="card-line">${escapeHtml(placeKeyLine(p))}</p>
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
  function eventKeyLine(e){
    const date = eventDateLabel(e);
    const time = String(e.time || '').trim();
    if (time && !/confirm/i.test(time)) return date + ' · ' + time;
    return date;
  }
  function eventTimeLabel(e){
    const time = String(e.time || '').trim();
    return time && !/confirm/i.test(time) ? time : 'Time to be confirmed';
  }
  function placeKeyLine(p){
    if (p.drive_note) return p.drive_note;
    if (p.approx_drive_minutes) return '~' + p.approx_drive_minutes + ' min';
    return '';
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
  function pad2(n){ return String(n).padStart(2, '0'); }
  function addDays(iso, n){
    const d = new Date(iso + 'T12:00:00Z');
    d.setUTCDate(d.getUTCDate() + n);
    return d.toISOString().slice(0, 10);
  }
  function readClock(text, inherit){
    const m = String(text || '').trim().match(/^(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?$/i);
    if (!m) return null;
    let h = parseInt(m[1], 10);
    const min = m[2] ? parseInt(m[2], 10) : 0;
    if (h > 23 || min > 59) return null;
    let mer = m[3] ? m[3].replace(/\./g, '').toUpperCase() : (inherit || '');
    if (!mer) return { h: h, min: min, mer: '', minutes: null };
    if (h > 12) mer = '';
    if (mer === 'PM' && h < 12) h += 12;
    if (mer === 'AM' && h === 12) h = 0;
    return { h: h, min: min, mer: mer, minutes: h * 60 + min };
  }
  function withMer(text, mer){
    const c = readClock(text, mer);
    return c && c.minutes != null ? c : null;
  }
  function resolvePair(aRaw, bRaw){
    let a = readClock(aRaw, '');
    let b = readClock(bRaw, '');
    if (!a || !b) return null;
    if (!a.mer && b.mer) {
      const same = withMer(aRaw, b.mer);
      const other = withMer(aRaw, b.mer === 'PM' ? 'AM' : 'PM');
      a = (same && b.minutes != null && same.minutes < b.minutes) ? same : (other || same);
    }
    if (a && !b.mer && a.mer) {
      const same = withMer(bRaw, a.mer);
      const other = withMer(bRaw, a.mer === 'AM' ? 'PM' : 'AM');
      b = (same && a.minutes != null && same.minutes > a.minutes) ? same : (other || same);
    }
    if (a && a.minutes == null) a = withMer(aRaw, 'PM');
    if (b && b.minutes == null) b = withMer(bRaw, 'PM');
    if (!a || !b || a.minutes == null || b.minutes == null) return null;
    return [a, b];
  }
  function stamp(date, clock){
    return date.replace(/-/g, '') + 'T' + pad2(clock.h) + pad2(clock.min) + '00';
  }
  function calendarUrl(e){
    const startDate = e.date;
    const endDate = e.end_date || e.date;
    const time = String(e.time || '');
    const rangeRe = /(\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?)\s*[–—-]\s*(\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?)/gi;
    const ranges = [];
    let rm;
    while ((rm = rangeRe.exec(time))) ranges.push(rm);
    let dates = '';
    if (ranges.length) {
      const first = resolvePair(ranges[0][1], ranges[0][2]);
      if (first) {
        let endClock = first[1];
        let endD = startDate;
        if (endDate !== startDate && ranges.length > 1) {
          const last = resolvePair(ranges[ranges.length - 1][1], ranges[ranges.length - 1][2]);
          if (last) { endClock = last[1]; endD = endDate; }
        }
        const start = stamp(startDate, first[0]);
        let end = stamp(endD, endClock);
        if (end <= start) end = stamp(addDays(endD, 1), endClock);
        dates = start + '/' + end;
      }
    }
    if (!dates) {
      const clocks = [];
      const clockRe = /\b(\d{1,2}:\d{2}\s*(?:a\.?m\.?|p\.?m\.?)?)\b/gi;
      let cm;
      while ((cm = clockRe.exec(time))) clocks.push(cm[1]);
      if (clocks.length) {
        const a = readClock(clocks[0], /[ap]\.?m/i.test(clocks[0]) ? '' : 'PM');
        let b = clocks.length > 1 ? readClock(clocks[clocks.length - 1], /[ap]\.?m/i.test(clocks[clocks.length - 1]) ? '' : 'PM') : null;
        if (a && a.minutes != null) {
          if (!b || b.minutes == null || b.minutes <= a.minutes) {
            const mins = a.minutes + 120;
            b = { h: Math.floor(mins / 60) % 24, min: mins % 60 };
            dates = stamp(startDate, a) + '/' + stamp(addDays(startDate, Math.floor(mins / 1440)), b);
          } else {
            dates = stamp(startDate, a) + '/' + stamp(endDate !== startDate ? endDate : startDate, b);
          }
        }
      }
    }
    if (!dates) dates = startDate.replace(/-/g, '') + '/' + addDays(endDate, 1).replace(/-/g, '');
    const details = [e.note, e.time, e.source].filter(Boolean).join('\n');
    return 'https://calendar.google.com/calendar/render?action=TEMPLATE'
      + '&text=' + encodeURIComponent(e.title || 'Event')
      + '&dates=' + dates
      + '&details=' + encodeURIComponent(details)
      + '&location=' + encodeURIComponent(e.place || '')
      + '&ctz=America%2FDenver';
  }
  function renderEvents(){
    const today = new Intl.DateTimeFormat('en-CA', { year: 'numeric', month: '2-digit', day: '2-digit', timeZone: 'America/Denver' }).format(new Date());
    // Keep an event visible while any part of its date range is still upcoming,
    // but do not render already-past day groups.
    const upcoming = events.filter(e => String(e.end_date || e.date) >= today);
    const groups = {};
    upcoming.forEach(e => eventDateKeys(e).filter(day => day >= today).forEach(day => {
      (groups[day] ||= []).push(e);
    }));
    const days = Object.keys(groups).sort();
    if (!days.length) { eventsEl.innerHTML = '<div class="empty">No upcoming events listed yet.</div>'; return; }
    eventsEl.innerHTML = days.map(day => `
      <section class="event-day" aria-labelledby="event-day-${day}">
        <h2 class="event-day-heading" id="event-day-${day}">${escapeHtml(longDate(day))}<span>${groups[day].length} event${groups[day].length === 1 ? '' : 's'}</span></h2>
        ${groups[day].sort((a, b) => String(a.date).localeCompare(String(b.date)) || String(a.title).localeCompare(String(b.title))).map(e => {
          const linked = e.place_id && placesById[e.place_id];
          const venue = e.place || (linked && linked.name) || 'Location to be confirmed';
          return `<article class="event-card${linked?' linked':''}"${linked?` data-place-id="${escapeHtml(e.place_id)}" role="button" tabindex="0"`:''}>
            <div class="event-card-top">
              <h3>${escapeHtml(e.title)}</h3>
              <a class="cal-add" href="${calendarUrl(e)}" target="_blank" rel="noopener">Add to calendar</a>
            </div>
            <p class="event-place">${escapeHtml(venue)}</p>
            <p class="event-note">${escapeHtml(snippet(e.note || 'Family-friendly event details coming soon.', 120))}</p>
            <div class="event-meta"><span>${escapeHtml(eventDateLabel(e))}</span><span class="event-time">${escapeHtml(eventTimeLabel(e))}</span></div>
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

  function moveTabIndicator(name, immediate = false){
    const selected = tabs.find(t => t.dataset.tab === name);
    if (!selected || !tabIndicator || !seg || name === 'events') return;
    if (immediate) tabIndicator.style.transition = 'none';
    seg.style.setProperty('--tab-left', `${selected.offsetLeft}px`);
    seg.style.setProperty('--tab-width', `${selected.offsetWidth}px`);
    if (immediate) {
      requestAnimationFrame(() => { tabIndicator.style.removeProperty('transition'); });
    }
  }

  function paintFilterButton(){
    const on = filterOpen || filter !== 'all';
    filterBtn.classList.toggle('on', on);
    filterBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
    filterBtn.setAttribute('aria-expanded', filterOpen ? 'true' : 'false');
  }
  function openFilterSheet(){
    filterOpen = true;
    filterSheet.hidden = false;
    filterBackdrop.hidden = false;
    requestAnimationFrame(() => {
      filterSheet.classList.add('open');
      filterBackdrop.classList.add('open');
    });
    paintFilterButton();
  }
  function closeFilterSheet(){
    filterOpen = false;
    filterSheet.classList.remove('open');
    filterBackdrop.classList.remove('open');
    paintFilterButton();
    setTimeout(() => {
      if (!filterOpen) { filterSheet.hidden = true; filterBackdrop.hidden = true; }
    }, 320);
  }
  function openAbout(){
    aboutOpen = true;
    aboutDrawer.hidden = false;
    aboutBackdrop.hidden = false;
    openAboutBtn.setAttribute('aria-expanded', 'true');
    requestAnimationFrame(() => {
      aboutDrawer.classList.add('open');
      aboutBackdrop.classList.add('open');
    });
  }
  function closeAbout(){
    aboutOpen = false;
    aboutDrawer.classList.remove('open');
    aboutBackdrop.classList.remove('open');
    openAboutBtn.setAttribute('aria-expanded', 'false');
    setTimeout(() => {
      if (!aboutOpen) { aboutDrawer.hidden = true; aboutBackdrop.hidden = true; }
    }, 420);
  }

  function setTab(name){
    currentTab = name;
    const mapActive = name === 'map';
    topbar.hidden = !mapActive;
    topbar.setAttribute('aria-hidden', mapActive ? 'false' : 'true');
    const viewOn = name === 'map' || name === 'list';
    tabs.forEach(t => {
      const on = viewOn && t.dataset.tab === name;
      t.classList.toggle('active', on);
      t.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    seg.classList.toggle('idle', !viewOn);
    eventsBtn.classList.toggle('on', name === 'events');
    eventsBtn.setAttribute('aria-pressed', name === 'events' ? 'true' : 'false');
    if (viewOn) moveTabIndicator(name);
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    if (name === 'list') document.getElementById('panel-list').classList.add('active');
    if (name === 'events') document.getElementById('panel-events').classList.add('active');
    setTimeout(() => map.resize(), 50);
  }

  tabs.forEach(btn => {
    btn.addEventListener('click', () => setTab(btn.dataset.tab));
  });
  eventsBtn.addEventListener('click', () => setTab('events'));
  filterBtn.addEventListener('click', () => { filterOpen ? closeFilterSheet() : openFilterSheet(); });
  document.getElementById('filter-close').addEventListener('click', closeFilterSheet);
  filterBackdrop.addEventListener('click', closeFilterSheet);
  openAboutBtn.addEventListener('click', openAbout);
  document.getElementById('about-close').addEventListener('click', closeAbout);
  aboutBackdrop.addEventListener('click', closeAbout);
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    if (aboutOpen) closeAbout();
    else if (filterOpen) closeFilterSheet();
  });
  moveTabIndicator(currentTab, true);

  function setFilter(f){
    filter = f;
    document.querySelectorAll('.filter-chip').forEach(b => {
      const on = b.dataset.filter === f;
      b.classList.toggle('active', on);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    renderList();
    paintFilterButton();
  }

  document.querySelectorAll('.filter-chip').forEach(btn => {
    btn.addEventListener('click', () => setFilter(btn.dataset.filter));
  });
  document.getElementById('clear-filter').addEventListener('click', () => setFilter('all'));

  let searchTimer;
  searchEl.addEventListener('focus', () => {
    topbar.classList.add('search-focused');
  });
  searchEl.addEventListener('blur', () => {
    if (!searchEl.value.trim()) topbar.classList.remove('search-focused');
  });
  searchEl.addEventListener('input', () => {
    clearTimeout(searchTimer);
    if (!searchEl.value.trim()) topbar.classList.remove('search-focused');
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

  window.addEventListener('resize', () => {
    map.resize();
    if (currentTab === 'map' || currentTab === 'list') moveTabIndicator(currentTab, true);
  });
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
