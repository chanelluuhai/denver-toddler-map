# Design system

One shared system for our personal apps. Toddler Spots is the source of the chrome. New apps copy this file. The only thing an app may override is its color theme (accent, soft, dark, named wash, and the body gradient). Ink, type, blur, radii, shadows, motion, the header, the dock, and sheets stay shared.

Do not restyle Toddler Spots to match a later app. Fraunces and Outfit are not part of this system.

## Typography

Google fonts link, used on every app:

```html
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Alice&family=Nunito:wght@400;500;600;700&display=swap" rel="stylesheet"/>
```

| Role | Family | Weights | CSS |
|------|--------|---------|-----|
| UI | Nunito | 400, 500, 600, 700 | `--font: "Nunito", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;` |
| Display (wordmarks, sheet titles) | Alice | 400 (the face is a single roman) | `--display: "Alice", "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;` |

In-app titles use `--display` at weight 600. Buttons, tabs, and body copy use `--font`. A clay wordmark image is only for the welcome screen (see Clay).

## Shared tokens

These are not a palette. Apps do not change them.

| Token | Value |
|-------|--------|
| `--ink` | `#2F2A27` |
| `--ink-2` | `#5A524C` |
| `--muted` | `#9A9088` |
| `--line` | `rgba(80, 60, 58, 0.08)` |
| `--card` | `#FFFEFC` |
| `--radius` | `34px` |
| `--radius-sm` | `26px` |
| `--tap` | `48px` |
| `--shadow` | `0 10px 32px rgba(70, 50, 48, 0.06)` |
| `--shadow-lg` | `0 18px 48px rgba(60, 40, 42, 0.10)` |
| Glass pill shadow | `0 8px 24px rgba(70, 50, 48, 0.07)` |
| Ease | `cubic-bezier(0.4, 0, 0.2, 1)` |
| Chrome transitions | about `460ms` on that ease (search pill width, brand collapse, about drawer) |

The app is a full-viewport shell (`100dvh`, `overflow: hidden`) with safe areas: `--safe-top` and `--safe-bottom` from `env(safe-area-inset-*)`. Hit targets are at least 48px.

## Themes

Only these change per app.

### Toddler Spots (blush)

From the map template. Do not edit these in the app.

| Token | Value |
|-------|--------|
| `--accent` | `#B57A88` |
| `--accent-soft` | `#F6EBEE` |
| `--accent-dark` | `#8E5A68` |
| `--blush` | `#E5B8C2` |
| `--blush-deep` | `#C98998` |
| `--mauve` | `#C4A8B4` |
| `--bg` | `#E8E6E4` |
| `--bg-mid` | `#EDE8E6` |

Body wash:

```css
background:
  linear-gradient(180deg,
    #E8E6E4 0%,
    #EBE7E5 38%,
    #F0E6E6 68%,
    #E9D5D8 100%);
```

Manifest paper stays `#E8E6E4` (`background_color` and `theme_color`).

### Little Library (sage)

Accent and wash only. Ink, type, blur, radii, and motion stay the shared tokens above.

| Token | Value |
|-------|--------|
| `--accent` | `#6E8B71` |
| `--accent-soft` | `#E6F0E4` |
| `--accent-dark` | `#3F5C43` |
| `--sage` | `#A9C4A4` |
| `--sage-deep` | `#5E7A5C` |

Body wash:

```css
background: linear-gradient(180deg, #E7EBE4 0%, #E4EDE3 42%, #D3E4D2 100%);
```

Manifest paper is `#E4EDE3`.

Little Library's dock does not use the shared active pill. Shelf and For you stay the same width whether selected or not; selection only changes the icon and label color. Those icons are Phosphor (`books`, `plus`, `sparkle`), not hand-drawn paths. Recommendation links go to a Fahasa search for Vietnamese titles (`language` `vi`) and an Amazon.com search otherwise. Covers may still come from Open Library or Google Books, with the clay book when neither has one.

## Blurred header

The top bar does not paint its own fill. A `::before` mask sits behind it:

- Height `calc(120px + var(--safe-top))`
- Gradient `linear-gradient(to bottom, rgba(232, 230, 228, 0.82) 0%, rgba(232, 230, 228, 0.35) 55%, transparent 100%)` (swap `232, 230, 228` for the app's paper if the wash is not blush)
- `backdrop-filter: blur(16px) saturate(1.1)` and the `-webkit-` twin
- Mask `linear-gradient(to bottom, #000 25%, transparent 100%)`

Glass pills (brand, search) sit on top of that fade:

- `background: rgba(255, 254, 252, 0.78)` for the brand, `0.82` for the search pill
- `backdrop-filter: blur(24px) saturate(1.2)`
- `border-radius: 999px`
- shadow `0 8px 24px rgba(70, 50, 48, 0.07)`
- height `48px`

## Motion

| Name | What it does |
|------|----------------|
| `filterShellIn` | Dock action grows in: opacity 0→1, scale 0.82→1, width 0→68px, over `420ms` `cubic-bezier(.22, 1, .36, 1)`. Played in reverse to leave. |
| `welcomeButtonGradient` | Welcome button background-position drifts 0%→100%→0% over 8s, ease-in-out, infinite. |
| `welcomeIconBounce` | Welcome marks rise in: opacity 0 and `translateY(12px) scale(.88)`, overshoot to `translateY(-5px) scale(1.03)`, settle to rest. `500ms` `cubic-bezier(.22, 1, .36, 1)`. |

Chrome that is not a keyframe uses `460ms cubic-bezier(0.4, 0, 0.2, 1)` (top bar gap, brand max-width, search pill width). The dock tab indicator uses `transform 480ms cubic-bezier(.22, 1, .36, 1)`.

New UI (the hub, Little Library, anything after) respects `prefers-reduced-motion: reduce` by turning those transitions and animations off.

## Chrome

**Dock.** Anchored to the bottom with safe-area inset. A frosted fade (`::before`, height ~148px, `blur(16px) saturate(1.08)`, mask from transparent to solid) keeps content from fighting the bar. The bar itself is glass: `rgba(255, 254, 252, 0.28)`, `blur(22px) saturate(1.45)`, 1px white border at 0.5 alpha, radius `999px`, shadow `0 10px 28px rgba(70, 45, 50, 0.10)`. The active tab is a soft pill in the theme wash. Pressed tabs scale to `0.97`.

**Sheets.** Slide up from the bottom over a dim backdrop (`rgba(55, 42, 40, 0.22)`). Sheet fill `rgba(255, 254, 252, 0.96)`, `blur(28px) saturate(1.15)`, radius `36px 36px 0 0`, shadow `--shadow-lg`. A 40×4px handle, radius 999px, tinted with the accent at about 0.35 alpha. Transform eases with `cubic-bezier(.32, .72, 0, 1)`.

**Shell.** Mobile, full viewport, safe areas, 48px targets, focus ring `2px solid var(--accent-dark)`.


## Clay

Clay photos are cut out to transparent PNGs before they ship. Never show the original rectangular photo, and never leave a white or cream halo around the clay.

Little Library's welcome is the exception. Those three clay books keep the soft contact shadow from the photo, and the welcome ground is the photo's floor (`#E7E9E4`) so the shadow fades into the page instead of ending on a hard crop. The header icon stays a clean cutout, with no shadow plate. The clay wordmark stays on that welcome only.

The clay wordmark image appears only on the first-visit welcome. Everywhere else, titles are set in Alice (`--display`), not the clay wordmark.

That welcome is a full-screen dialog, once per browser, remembered in localStorage, with a replay control (Toddler Spots uses "What is this"):

1. A row of small transparent clay object icons that bounce in (`welcomeIconBounce`, staggered).
2. The clay wordmark image.
3. One short line in Nunito.
4. An Enter button whose fill drifts with `welcomeButtonGradient`.

The dock uses small stroke SVG icons with a short text label beneath each icon, inside the same glass bar as the rest of the chrome. Do not put clay words or clay letters in the tab bar.

The blurred header overlay stays shared. The glass pill in that header uses Alice, not the clay wordmark. An app may keep a small clay object beside that serif title (Toddler Spots does). It may not put the clay wordmark there.

Each app brings its own clay objects and its own color theme. The welcome shape, the serif titles, the icon dock, and the blurred header do not change.

## Rule

New apps copy this chrome and this type. They swap theme color tokens only.
