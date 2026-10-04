(() => {
  "use strict";

  const STORAGE_KEY = "littleShelf.v1";
  const GENRES = [
    "Board book", "Picture book", "Vietnamese", "Bilingual", "Animals",
    "Bedtime", "Family", "Feelings", "Nature", "Food", "Vehicles",
    "Adventure", "Friendship", "Nursery rhymes", "Folk tales",
    "Counting", "Letters", "Play"
  ];

  const DEFAULT_STATE = () => ({
    books: [],
    profile: {
      displayName: "Bé",
      birthday: "2025-01-15"
    }
  });

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  let state = load();
  let currentView = "shelf";
  let shelfFilter = { q: "", language: "all", genre: "all", favorites: false };
  let editingId = null;
  let pendingDeleteId = null;
  let scanController = null;
  let scanStarting = false;
  let scanDenied = false;
  let lastScanned = "";
  let scanCooldownUntil = 0;
  const coverCache = new Map();

  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return DEFAULT_STATE();
      const parsed = JSON.parse(raw);
      return {
        books: Array.isArray(parsed.books) ? parsed.books : [],
        profile: {
          displayName: (parsed.profile && parsed.profile.displayName) || "Bé",
          birthday: (parsed.profile && parsed.profile.birthday) || "2025-01-15"
        }
      };
    } catch {
      return DEFAULT_STATE();
    }
  }

  function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function uid() {
    return "b_" + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
  }

  function escapeHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function normalizeTitle(t) {
    return String(t || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9\u00c0-\u024f]+/gi, " ")
      .trim();
  }

  function monthsBetween(birthdayISO, now = new Date()) {
    const b = new Date(birthdayISO + "T12:00:00");
    if (Number.isNaN(b.getTime())) return 0;
    // Calendar-month age: exact day is approximate (month known), so count
    // year/month delta. Mid-January 2025 → October 2026 ≈ 21 months.
    const months = (now.getFullYear() - b.getFullYear()) * 12 + (now.getMonth() - b.getMonth());
    return Math.max(0, months);
  }

  function formatAge(months) {
    const y = Math.floor(months / 12);
    const m = months % 12;
    if (y <= 0) return m === 1 ? "1 month" : `${m} months`;
    if (m === 0) return y === 1 ? "1 year" : `${y} years`;
    const yPart = y === 1 ? "1 year" : `${y} years`;
    const mPart = m === 1 ? "1 month" : `${m} months`;
    return `${yPart} ${mPart}`;
  }

  function childAgeMonths() {
    return monthsBetween(state.profile.birthday || "2025-01-15");
  }

  function monogram(title) {
    const words = String(title || "?").trim().split(/\s+/).filter(Boolean);
    if (!words.length) return "?";
    if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
    return (words[0][0] + words[1][0]).toUpperCase();
  }

  function coverHtml(book, className = "cover", fallback = "mono") {
    if (book.coverUrl) {
      if (fallback === "clay") {
        return `<div class="${className}"><img src="${escapeHtml(book.coverUrl)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.onerror=null;this.src='icons/clay-book.png';this.classList.add('is-clay')"></div>`;
      }
      return `<div class="${className}"><img src="${escapeHtml(book.coverUrl)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove();this.parentElement.innerHTML='<span class=cover-mono>${escapeHtml(monogram(book.title))}</span>'"/></div>`;
    }
    if (fallback === "clay") {
      return `<div class="${className}"><img src="icons/clay-book.png" alt="" class="is-clay"></div>`;
    }
    return `<div class="${className}"><span class="cover-mono">${escapeHtml(monogram(book.title))}</span></div>`;
  }

  function heartSvg(on) {
    if (on) {
      return `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 20.2s-6.8-4.2-9.2-8.1C1.2 9.2 2.1 5.8 5.2 4.7c1.8-.6 3.7.1 4.8 1.5 1.1-1.4 3-2.1 4.8-1.5 3.1 1.1 4 4.5 2.4 7.4C18.8 16 12 20.2 12 20.2z"/></svg>`;
    }
    return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19.5s-6.2-3.9-8.4-7.4C2.1 9.6 2.9 6.6 5.6 5.6c1.6-.6 3.3.1 4.3 1.4 1-1.3 2.7-2 4.3-1.4 2.7 1 3.5 4 2.05 7.4C18.2 15.6 12 19.5 12 19.5z"/></svg>`;
  }

  function toast(msg) {
    const el = $("#toast");
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.remove("show"), 2600);
  }

  /* —— Sheets —— */
  function openSheet(id) {
    if (currentView === "scan") stopScanner();
    closeSheets();
    const sheet = document.getElementById(id);
    const backdrop = $("#sheet-backdrop");
    sheet.classList.add("open");
    sheet.setAttribute("aria-hidden", "false");
    backdrop.classList.add("open");
  }

  function closeSheets() {
    $$(".sheet.open").forEach((s) => {
      s.classList.remove("open");
      s.setAttribute("aria-hidden", "true");
    });
    $("#sheet-backdrop").classList.remove("open");
    queueMicrotask(() => {
      if (document.querySelector(".sheet.open")) return;
      if (currentView === "scan" && !scanController && !scanDenied && !scanStarting) startScanner();
    });
  }

  /* —— Navigation —— */
  function setView(name) {
    currentView = name;
    $$(".view").forEach((v) => {
      const on = v.dataset.view === name;
      v.classList.toggle("active", on);
      v.hidden = !on;
    });
    $$(".tab").forEach((t) => {
      const on = t.dataset.view === name;
      t.classList.toggle("active", on);
      if (on) t.setAttribute("aria-current", "page");
      else t.removeAttribute("aria-current");
    });
    updateTabIndicator();
    if (name !== "scan") stopScanner();
    else if (!scanController && !scanStarting) {
      scanDenied = false;
      startScanner();
    }
    if (name === "shelf") renderShelf();
    if (name === "genres") renderGenres();
    if (name === "foryou") renderRecs();
  }

  function updateTabIndicator() {
    const seg = $("#dock-seg");
    const tab = $(`.tab[data-view="${currentView}"]`);
    const ind = $("#tab-indicator");
    if (!seg || !tab || !ind) return;
    const sRect = seg.getBoundingClientRect();
    const tRect = tab.getBoundingClientRect();
    const pad = 6;
    ind.style.setProperty("--tab-left", `${tRect.left - sRect.left}px`);
    ind.style.setProperty("--tab-width", `${tRect.width}px`);
    // also set left via transform using CSS vars already used
    ind.style.width = `${tRect.width}px`;
    ind.style.transform = `translateX(${tRect.left - sRect.left}px)`;
  }

  /* —— Shelf —— */
  function filteredBooks() {
    const q = shelfFilter.q.trim().toLowerCase();
    return state.books
      .filter((b) => {
        if (shelfFilter.favorites && !b.favorite) return false;
        if (shelfFilter.language !== "all" && b.language !== shelfFilter.language) return false;
        if (shelfFilter.genre !== "all" && !(b.genres || []).includes(shelfFilter.genre)) return false;
        if (q) {
          const hay = `${b.title} ${b.author || ""}`.toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      })
      .sort((a, b) => {
        if (a.favorite !== b.favorite) return a.favorite ? -1 : 1;
        return String(b.addedAt || "").localeCompare(String(a.addedAt || ""));
      });
  }

  function renderShelfFilters() {
    const row = $("#shelf-filters");
    const chips = [
      { key: "all", label: "All" },
      { key: "fav", label: "Favorites" },
      { key: "vi", label: "Vietnamese" },
      { key: "bilingual", label: "Bilingual" },
      { key: "en", label: "English" }
    ];
    row.innerHTML = chips.map((c) => {
      let active = false;
      if (c.key === "all") active = !shelfFilter.favorites && shelfFilter.language === "all";
      if (c.key === "fav") active = shelfFilter.favorites;
      if (c.key === "vi") active = shelfFilter.language === "vi";
      if (c.key === "bilingual") active = shelfFilter.language === "bilingual";
      if (c.key === "en") active = shelfFilter.language === "en";
      return `<button type="button" class="chip${active ? " active" : ""}" data-chip="${c.key}">${c.label}</button>`;
    }).join("");
  }

  function renderShelf() {
    const age = childAgeMonths();
    $("#shelf-age-text").textContent = formatAge(age);
    renderShelfFilters();
    const list = $("#shelf-list");
    const empty = $("#shelf-empty");
    const books = filteredBooks();
    const noBooksAtAll = state.books.length === 0;

    if (noBooksAtAll) {
      list.innerHTML = "";
      empty.hidden = false;
      return;
    }
    empty.hidden = true;
    if (!books.length) {
      list.innerHTML = `<div class="empty"><h2>No matches</h2></div>`;
      return;
    }
    list.innerHTML = books.map((b) => bookCardHtml(b)).join("");
  }

  function bookCardHtml(b) {
    const tags = [];
    if (b.language === "vi") tags.push(`<span class="tag lang-vi">Vietnamese</span>`);
    if (b.language === "bilingual") tags.push(`<span class="tag lang-bilingual">Bilingual</span>`);
    (b.genres || []).slice(0, 2).forEach((g) => {
      if (g !== "Vietnamese" && g !== "Bilingual") tags.push(`<span class="tag">${escapeHtml(g)}</span>`);
    });
    return `
      <article class="book-card" data-id="${escapeHtml(b.id)}" role="button" tabindex="0">
        ${coverHtml(b)}
        <div class="book-meta">
          <h3>${escapeHtml(b.title)}</h3>
          <p class="author">${escapeHtml(b.author || "Unknown author")}</p>
          <div class="book-tags">${tags.join("")}</div>
        </div>
        <button type="button" class="heart-btn${b.favorite ? " on" : ""}" data-heart="${escapeHtml(b.id)}" aria-label="${b.favorite ? "Unfavorite" : "Favorite"}" aria-pressed="${b.favorite ? "true" : "false"}">
          ${heartSvg(!!b.favorite)}
        </button>
      </article>`;
  }

  function toggleFavorite(id, btn) {
    const book = state.books.find((b) => b.id === id);
    if (!book) return;
    book.favorite = !book.favorite;
    save();
    if (btn) {
      btn.classList.toggle("on", book.favorite);
      btn.classList.remove("pop");
      void btn.offsetWidth;
      btn.classList.add("pop");
      btn.setAttribute("aria-pressed", book.favorite ? "true" : "false");
      btn.setAttribute("aria-label", book.favorite ? "Unfavorite" : "Favorite");
      btn.innerHTML = heartSvg(book.favorite);
    }
    if (currentView === "shelf") renderShelf();
    if (currentView === "foryou") renderRecs();
    if ($("#sheet-detail").classList.contains("open")) openDetail(id);
  }

  /* —— Genres —— */
  function renderGenres() {
    const viCount = state.books.filter((b) => b.language === "vi" || b.language === "bilingual").length;
    $("#vi-stat").textContent = viCount === 1 ? "1 Vietnamese" : `${viCount} Vietnamese`;

    const grid = $("#genre-grid");
    grid.innerHTML = GENRES.map((g, i) => {
      const count = state.books.filter((b) => (b.genres || []).includes(g)).length;
      const thin = count <= 1 ? " thin" : "";
      return `<button type="button" class="genre-card${thin}" data-genre="${escapeHtml(g)}" style="animation-delay:${i * 25}ms">
        <h3>${escapeHtml(g)}</h3>
        <div class="genre-count">${count} book${count === 1 ? "" : "s"}</div>
      </button>`;
    }).join("");
  }

  /* —— Recommendations —— */
  function ownedTitles() {
    return new Set(state.books.map((b) => normalizeTitle(b.title)));
  }

  function genreCounts() {
    const map = {};
    GENRES.forEach((g) => (map[g] = 0));
    state.books.forEach((b) => (b.genres || []).forEach((g) => { map[g] = (map[g] || 0) + 1; }));
    return map;
  }

  function scoreCatalog() {
    const age = childAgeMonths();
    const owned = ownedTitles();
    const favs = state.books.filter((b) => b.favorite);
    const favGenres = new Set(favs.flatMap((b) => b.genres || []));
    const ownedGenres = new Set(state.books.flatMap((b) => b.genres || []));
    const favAuthors = new Set(favs.map((b) => normalizeTitle(b.author)).filter(Boolean));
    const counts = genreCounts();
    const total = state.books.length;
    const viOwned = state.books.filter((b) => b.language === "vi" || b.language === "bilingual").length;
    const viShare = total ? viOwned / total : 0;
    const hasViFav = favs.some((b) => b.language === "vi" || b.language === "bilingual");
    const catalog = window.LITTLE_SHELF_CATALOG || [];

    const scored = [];
    for (const c of catalog) {
      if (owned.has(normalizeTitle(c.title))) continue;
      const overlap =
        age + 6 >= (c.ageMinMonths ?? 0) && age - 6 <= (c.ageMaxMonths ?? 999);
      if (!overlap) continue;

      let score = 0;
      const reasons = [];
      const genres = c.genres || [];

      if (genres.some((g) => favGenres.has(g))) {
        score += 3;
        const g = genres.find((x) => favGenres.has(x));
        reasons.push(`Because he loves ${g.toLowerCase()} books`);
      }
      if (genres.some((g) => ownedGenres.has(g))) {
        score += 2;
        if (!reasons.length) {
          const g = genres.find((x) => ownedGenres.has(x));
          reasons.push(`Matches ${g.toLowerCase()} on your shelf`);
        }
      }

      const isVi = c.language === "vi" || c.language === "bilingual";
      if (isVi && (viShare < 0.3 || hasViFav || total === 0)) {
        score += 2;
        if (total === 0) reasons.push("A gentle Vietnamese starter");
        else if (viShare < 0.3) reasons.push("The Vietnamese shelf is light");
        else reasons.push("Because Vietnamese books are favorites");
      }

      if (c.author && favAuthors.has(normalizeTitle(c.author))) {
        score += 1;
        reasons.push(`Same author as a favorite`);
      }

      if (genres.some((g) => (counts[g] || 0) < 2)) {
        score += 1;
        if (!reasons.some((r) => r.includes("light") || r.includes("Coverage"))) {
          const g = genres.find((x) => (counts[x] || 0) < 2);
          if (g) reasons.push(`Fills out ${g.toLowerCase()}`);
        }
      }

      reasons.unshift(`Fits ${formatAge(age)}`);

      // Empty shelf: boost youngest Vietnamese nursery + classic board books
      if (total === 0) {
        if (isVi && (c.ageMaxMonths ?? 99) <= 36) score += 3;
        if ((c.ageMaxMonths ?? 99) <= 24) score += 1;
      }

      scored.push({ ...c, score, reasons: unique(reasons).slice(0, 2) });
    }

    scored.sort((a, b) => b.score - a.score || a.title.localeCompare(b.title));
    return scored.slice(0, 5);
  }

  function unique(arr) {
    return [...new Set(arr)];
  }

  function bestFor(min, max) {
    const label = (months) => {
      if (months <= 0) return "0";
      const years = months / 12;
      if (Number.isInteger(years)) return String(years);
      return String(Math.round(years * 2) / 2);
    };
    if (min == null && max == null) return "";
    const a = label(min ?? 0);
    if (max == null) return `Best from ${a} years`;
    return `Best for ${a}–${label(max)} years`;
  }

  function bookSearchLink(title, author) {
    const q = encodeURIComponent(`${title || ""} ${author || ""}`.trim());
    return `https://openlibrary.org/search?q=${q}`;
  }

  let recToken = 0;

  async function findCover(book) {
    const key = normalizeTitle(book.title);
    if (coverCache.has(key)) return coverCache.get(key);
    let url = "";
    try {
      const u = new URL("https://openlibrary.org/search.json");
      u.searchParams.set("title", book.title);
      u.searchParams.set("limit", "8");
      u.searchParams.set("fields", "title,author_name,cover_i");
      const r = await fetch(u);
      if (r.ok) {
        const data = await r.json();
        const want = normalizeTitle(book.title);
        const exact = (data.docs || []).filter((d) => d.cover_i && normalizeTitle(d.title) === want);
        const authorBit = normalizeTitle(String(book.author || "").split(" and ")[0].split(",")[0]);
        const preferred = exact.find((d) =>
          (d.author_name || []).some((a) => {
            const n = normalizeTitle(a);
            return authorBit && (n.includes(authorBit) || authorBit.includes(n));
          })
        ) || exact[0];
        if (preferred) url = `https://covers.openlibrary.org/b/id/${preferred.cover_i}-L.jpg`;
      }
    } catch { /* ignore */ }
    if (!url) {
      try {
        const q = `intitle:${book.title}`;
        const r = await fetch(`https://www.googleapis.com/books/v1/volumes?q=${encodeURIComponent(q)}&maxResults=5&printType=books`);
        if (r.ok) {
          const data = await r.json();
          const want = normalizeTitle(book.title);
          const items = data.items || [];
          const hit = items.find((it) => {
            const info = it.volumeInfo || {};
            return info.imageLinks && normalizeTitle(info.title) === want;
          });
          const link = hit && hit.volumeInfo && hit.volumeInfo.imageLinks;
          if (link) {
            url = (link.thumbnail || link.smallThumbnail || "").replace(/^http:/, "https:");
          }
        }
      } catch { /* ignore */ }
    }
    coverCache.set(key, url);
    return url;
  }

  function paintCover(img, url) {
    if (!img || !url) return;
    img.onerror = () => {
      img.onerror = null;
      img.src = "icons/clay-book.png";
      img.classList.add("is-clay");
    };
    img.classList.remove("is-clay");
    img.src = url;
  }

  function renderRecs() {
    const list = $("#rec-list");
    const recs = scoreCatalog();
    const token = ++recToken;
    if (!recs.length) {
      list.innerHTML = `<div class="empty"><h2>Nothing new</h2></div>`;
      list._recs = [];
      return;
    }
    list.innerHTML = recs.map((r, i) => `
      <button type="button" class="rec-card" data-rec="${i}" style="animation-delay:${i * 40}ms">
        ${coverHtml(r, "cover", "clay")}
        <div class="book-meta">
          <h3>${escapeHtml(r.title)}</h3>
          <p class="author">${escapeHtml(r.author || "")}</p>
        </div>
      </button>
    `).join("");
    list._recs = recs;
    recs.forEach((r, i) => {
      if (r.coverUrl) return;
      findCover(r).then((url) => {
        if (token !== recToken || !url) return;
        r.coverUrl = url;
        const img = list.querySelector(`[data-rec="${i}"] img`);
        paintCover(img, url);
      });
    });
  }

  function openRecDetail(r) {
    const genres = (r.genres || []).join(" · ");
    const age = bestFor(r.ageMinMonths, r.ageMaxMonths);
    const body = $("#detail-body");
    body._rec = r;
    body.innerHTML = `
      ${coverHtml(r, "detail-cover", "clay")}
      <h3 class="detail-title">${escapeHtml(r.title)}</h3>
      <p class="detail-author">${escapeHtml(r.author || "")}</p>
      ${r.blurb ? `<p class="detail-blurb">${escapeHtml(r.blurb)}</p>` : ""}
      ${genres ? `<p class="detail-line">${escapeHtml(genres)}</p>` : ""}
      ${age ? `<p class="detail-line">${escapeHtml(age)}</p>` : ""}
      <a class="detail-link" href="${bookSearchLink(r.title, r.author)}" target="_blank" rel="noopener noreferrer">View on Open Library</a>
      <div class="detail-actions">
        <button type="button" class="btn btn-primary btn-block" id="rec-add">Add to shelf</button>
      </div>
    `;
    if (!r.coverUrl) {
      findCover(r).then((url) => {
        if (body._rec !== r || !url) return;
        r.coverUrl = url;
        paintCover(body.querySelector("img"), url);
      });
    }
    openSheet("sheet-detail");
  }

  function addRecToShelf(r) {
    state.books.push({
      id: uid(),
      title: r.title,
      author: r.author || "",
      language: r.language || "en",
      genres: r.genres || [],
      ageMinMonths: r.ageMinMonths ?? null,
      ageMaxMonths: r.ageMaxMonths ?? null,
      isbn: null,
      notes: "",
      favorite: false,
      coverUrl: r.coverUrl || null,
      addedAt: new Date().toISOString()
    });
    save();
    toast("Added to the shelf");
    closeSheets();
    renderRecs();
  }

  /* —— Detail —— */
  function openDetail(id) {
    const b = state.books.find((x) => x.id === id);
    if (!b) return;
    const body = $("#detail-body");
    const langLabel = { en: "English", vi: "Vietnamese", bilingual: "Bilingual", other: "Other" }[b.language] || b.language;
    body.innerHTML = `
      ${coverHtml(b, "detail-cover")}
      <h3 class="detail-title" id="detail-title">${escapeHtml(b.title)}</h3>
      <p class="detail-author">${escapeHtml(b.author || "Unknown author")}</p>
      <div class="book-tags" style="justify-content:center;margin-bottom:12px">
        <span class="tag">${escapeHtml(langLabel)}</span>
        ${(b.genres || []).map((g) => `<span class="tag">${escapeHtml(g)}</span>`).join("")}
      </div>
      ${b.isbn ? `<p class="detail-line">ISBN ${escapeHtml(b.isbn)}</p>` : ""}
      ${b.notes ? `<p class="detail-blurb">${escapeHtml(b.notes)}</p>` : ""}
      <div class="detail-actions">
        <button type="button" class="btn btn-secondary btn-block" data-detail-fav="${escapeHtml(b.id)}">${b.favorite ? "♥ Favorited" : "♡ Mark favorite"}</button>
        <button type="button" class="btn btn-secondary btn-block" data-detail-edit="${escapeHtml(b.id)}">Edit</button>
        <button type="button" class="btn btn-danger btn-block" data-detail-delete="${escapeHtml(b.id)}">Remove from shelf</button>
      </div>
    `;
    openSheet("sheet-detail");
  }

  /* —— Add / edit form —— */
  function fillGenrePicks(selected = []) {
    const box = $("#genre-picks");
    const set = new Set(selected);
    box.innerHTML = GENRES.map((g) =>
      `<button type="button" class="genre-pick${set.has(g) ? " on" : ""}" data-genre="${escapeHtml(g)}">${escapeHtml(g)}</button>`
    ).join("");
  }

  function openAddForm(prefill = {}, opts = {}) {
    editingId = opts.editingId || null;
    $("#add-title").textContent = editingId ? "Edit book" : "Add a book";
    $("#book-title").value = prefill.title || "";
    $("#book-author").value = prefill.author || "";
    $("#book-language").value = prefill.language || "en";
    $("#book-age-min").value = prefill.ageMinMonths ?? "";
    $("#book-age-max").value = prefill.ageMaxMonths ?? "";
    $("#book-isbn").value = prefill.isbn || "";
    $("#book-notes").value = prefill.notes || "";
    const fav = !!prefill.favorite;
    const sw = $("#book-favorite");
    sw.classList.toggle("on", fav);
    sw.setAttribute("aria-pressed", fav ? "true" : "false");
    fillGenrePicks(prefill.genres || []);
    openAddForm._coverUrl = prefill.coverUrl || null;

    const banner = $("#lookup-banner");
    if (opts.lookupFailed) {
      banner.hidden = false;
      banner.textContent = "Couldn't look that up.";
    } else {
      banner.hidden = true;
    }
    openSheet("sheet-add");
    setTimeout(() => $("#book-title").focus(), 420);
  }

  function readForm() {
    const genres = $$("#genre-picks .genre-pick.on").map((el) => el.dataset.genre);
    const ageMin = $("#book-age-min").value;
    const ageMax = $("#book-age-max").value;
    return {
      title: $("#book-title").value.trim(),
      author: $("#book-author").value.trim(),
      language: $("#book-language").value,
      genres,
      ageMinMonths: ageMin === "" ? null : Number(ageMin),
      ageMaxMonths: ageMax === "" ? null : Number(ageMax),
      isbn: $("#book-isbn").value.trim() || null,
      notes: $("#book-notes").value.trim(),
      favorite: $("#book-favorite").classList.contains("on"),
      coverUrl: openAddForm._coverUrl || null
    };
  }

  function saveBookFromForm() {
    const data = readForm();
    if (!data.title) {
      toast("Title is required");
      $("#book-title").focus();
      return;
    }
    if (editingId) {
      const book = state.books.find((b) => b.id === editingId);
      if (book) Object.assign(book, data);
      toast("Book updated");
    } else {
      state.books.push({
        id: uid(),
        ...data,
        addedAt: new Date().toISOString()
      });
      toast("Added to the shelf");
    }
    save();
    closeSheets();
    setView("shelf");
    renderShelf();
  }

  /* —— ISBN lookup —— */
  function mapSubjectsToGenres(subjects = []) {
    const text = subjects.join(" ").toLowerCase();
    const found = new Set();
    const rules = [
      [/board/, "Board book"],
      [/picture/, "Picture book"],
      [/animal|bear|zoo|cat|dog|bird/, "Animals"],
      [/bedtime|sleep|goodnight|night/, "Bedtime"],
      [/family|mother|father|parent|baby/, "Family"],
      [/feel|emotion|love/, "Feelings"],
      [/nature|garden|tree|rain|snow|season/, "Nature"],
      [/food|eat|hungry|fruit|vegetable/, "Food"],
      [/truck|train|car|vehicle|bus/, "Vehicles"],
      [/adventure|hunt|journey/, "Adventure"],
      [/friend/, "Friendship"],
      [/rhyme|nursery|poem/, "Nursery rhymes"],
      [/folk|fairy|legend/, "Folk tales"],
      [/count|number/, "Counting"],
      [/alphabet|letter|abc/, "Letters"],
      [/play|peek/, "Play"],
      [/vietnam/, "Vietnamese"],
      [/bilingual/, "Bilingual"]
    ];
    rules.forEach(([re, g]) => { if (re.test(text)) found.add(g); });
    if (!found.size) found.add("Picture book");
    return [...found].filter((g) => GENRES.includes(g));
  }

  async function lookupIsbn(isbn) {
    const clean = String(isbn).replace(/[^0-9Xx]/g, "");
    let result = { title: "", author: "", isbn: clean, coverUrl: null, genres: [], language: "en" };

    // Open Library
    try {
      const r = await fetch(`https://openlibrary.org/isbn/${encodeURIComponent(clean)}.json`);
      if (r.ok) {
        const data = await r.json();
        result.title = data.title || "";
        if (Array.isArray(data.authors) && data.authors.length) {
          // authors are refs; try search instead for names
        }
        if (Array.isArray(data.subjects)) {
          result.genres = mapSubjectsToGenres(data.subjects.map(String));
        }
        result.coverUrl = `https://covers.openlibrary.org/b/isbn/${clean}-L.jpg`;
      }
    } catch { /* ignore */ }

    try {
      const r2 = await fetch(`https://openlibrary.org/search.json?isbn=${encodeURIComponent(clean)}`);
      if (r2.ok) {
        const data = await r2.json();
        const doc = (data.docs || [])[0];
        if (doc) {
          result.title = result.title || doc.title || "";
          if (Array.isArray(doc.author_name) && doc.author_name.length) {
            result.author = doc.author_name.join(", ");
          }
          if (Array.isArray(doc.subject)) {
            result.genres = mapSubjectsToGenres(doc.subject);
          }
          if (doc.language && doc.language.includes("vie")) result.language = "vi";
          result.coverUrl = result.coverUrl || `https://covers.openlibrary.org/b/isbn/${clean}-L.jpg`;
        }
      }
    } catch { /* ignore */ }

    if (!result.title) {
      try {
        const r3 = await fetch(`https://www.googleapis.com/books/v1/volumes?q=isbn:${encodeURIComponent(clean)}`);
        if (r3.ok) {
          const data = await r3.json();
          const info = data.items && data.items[0] && data.items[0].volumeInfo;
          if (info) {
            result.title = info.title || "";
            result.author = (info.authors || []).join(", ");
            result.genres = mapSubjectsToGenres([...(info.categories || []), info.description || ""]);
            if (info.imageLinks) {
              result.coverUrl = (info.imageLinks.thumbnail || info.imageLinks.smallThumbnail || "").replace("http:", "https:");
            }
            if (info.language === "vi") result.language = "vi";
          }
        }
      } catch { /* ignore */ }
    }

    const useful = !!(result.title && result.title.trim());
    return { useful, book: result };
  }

  async function handleScannedCode(code) {
    const now = Date.now();
    if (code === lastScanned && now < scanCooldownUntil) return;
    lastScanned = code;
    scanCooldownUntil = now + 3500;
    stopScanner();
    const status = $("#scan-status");
    status.hidden = false;
    status.classList.remove("error");
    status.textContent = "Looking up…";
    toast("Code captured");
    let lookup;
    try {
      lookup = await lookupIsbn(code);
    } catch {
      lookup = { useful: false, book: { isbn: code, title: "", author: "", genres: [], language: "en", coverUrl: null } };
    }
    if (lookup.useful) {
      openAddForm(lookup.book, { lookupOk: true });
    } else {
      openAddForm({ isbn: String(code).replace(/[^0-9Xx]/g, ""), language: "en" }, { lookupFailed: true });
    }
    $("#scan-status").hidden = true;
    $("#scan-status").textContent = "";
  }

  /* —— Scanner —— */
  function showScanOff() {
    scanDenied = true;
    scanStarting = false;
    const status = $("#scan-status");
    status.hidden = false;
    status.classList.add("error");
    status.textContent = "Camera is off.";
  }

  function permissionDenied(err) {
    const name = err && err.name;
    return name === "NotAllowedError" || name === "PermissionDeniedError" || name === "SecurityError";
  }

  async function startScanner() {
    if (scanController || scanStarting) return;
    if (currentView !== "scan") return;
    scanStarting = true;
    scanDenied = false;
    const status = $("#scan-status");
    status.hidden = true;
    status.classList.remove("error");
    status.textContent = "";

    const hasDetector = typeof window.BarcodeDetector === "function";
    if (hasDetector) {
      try {
        const supported = await BarcodeDetector.getSupportedFormats();
        if (currentView !== "scan") { scanStarting = false; return; }
        const formats = ["ean_13", "ean_8", "upc_a", "upc_e"].filter((f) => supported.includes(f));
        if (!formats.length) throw new Error("No barcode formats");
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" } },
          audio: false
        });
        if (currentView !== "scan") {
          stream.getTracks().forEach((t) => t.stop());
          scanStarting = false;
          return;
        }
        const video = $("#scan-video");
        video.hidden = false;
        $("#qr-reader").hidden = true;
        video.srcObject = stream;
        await video.play();
        if (currentView !== "scan") {
          stream.getTracks().forEach((tr) => tr.stop());
          video.srcObject = null;
          scanStarting = false;
          return;
        }
        const detector = new BarcodeDetector({ formats });
        let alive = true;
        scanController = {
          stop() {
            alive = false;
            stream.getTracks().forEach((t) => t.stop());
            video.srcObject = null;
          }
        };
        scanStarting = false;
        const tick = async () => {
          if (!alive) return;
          try {
            if (video.readyState >= 2) {
              const codes = await detector.detect(video);
              if (codes && codes[0] && codes[0].rawValue) {
                await handleScannedCode(codes[0].rawValue);
                return;
              }
            }
          } catch { /* keep going */ }
          requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
        return;
      } catch (err) {
        console.warn("BarcodeDetector path failed", err);
        const video = $("#scan-video");
        if (video && video.srcObject) {
          video.srcObject.getTracks().forEach((tr) => tr.stop());
          video.srcObject = null;
        }
        if (permissionDenied(err)) {
          showScanOff();
          return;
        }
      }
    }

    try {
      await loadHtml5Qrcode();
      if (currentView !== "scan") { scanStarting = false; return; }
      $("#scan-video").hidden = true;
      const reader = $("#qr-reader");
      reader.hidden = false;
      reader.innerHTML = "";
      const html5QrCode = new Html5Qrcode("qr-reader");
      await html5QrCode.start(
        { facingMode: "environment" },
        { fps: 8, qrbox: { width: 240, height: 140 }, aspectRatio: 0.75 },
        (decoded) => handleScannedCode(decoded),
        () => {}
      );
      if (currentView !== "scan") {
        html5QrCode.stop().catch(() => {});
        scanStarting = false;
        return;
      }
      scanController = {
        stop() {
          html5QrCode.stop().catch(() => {});
          html5QrCode.clear();
        }
      };
      scanStarting = false;
    } catch (err) {
      console.warn(err);
      showScanOff();
    }
  }

  function stopScanner() {
    scanStarting = false;
    if (scanController) {
      try { scanController.stop(); } catch { /* ignore */ }
      scanController = null;
    }
  }

  function loadHtml5Qrcode() {
    if (window.Html5Qrcode) return Promise.resolve();
    return new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = "https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js";
      s.onload = () => resolve();
      s.onerror = () => reject(new Error("Failed to load html5-qrcode"));
      document.head.appendChild(s);
    });
  }

  /* —— Profile / export —— */
  function openProfile() {
    $("#profile-name").value = state.profile.displayName || "Bé";
    $("#profile-birthday").value = state.profile.birthday || "2025-01-15";
    $("#profile-age").textContent = formatAge(childAgeMonths());
    openSheet("sheet-profile");
  }

  function saveProfile() {
    state.profile.displayName = $("#profile-name").value.trim() || "Bé";
    state.profile.birthday = $("#profile-birthday").value || "2025-01-15";
    save();
    toast("Profile saved");
    closeSheets();
    renderShelf();
    if (currentView === "foryou") renderRecs();
  }

  function exportJson() {
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `little-shelf-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
    toast("Export downloaded");
  }

  function importJson(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const data = JSON.parse(reader.result);
        if (!data || !Array.isArray(data.books)) throw new Error("bad");
        state.books = data.books;
        if (data.profile) {
          state.profile.displayName = data.profile.displayName || state.profile.displayName;
          state.profile.birthday = data.profile.birthday || state.profile.birthday;
        }
        save();
        toast("Library imported");
        closeSheets();
        renderShelf();
        renderGenres();
        renderRecs();
      } catch {
        toast("Could not read that JSON file");
      }
    };
    reader.readAsText(file);
  }

  /* —— Events —— */
  function bind() {
    $$(".tab").forEach((t) => t.addEventListener("click", () => setView(t.dataset.view)));
    $$("[data-goto]").forEach((b) => b.addEventListener("click", () => setView(b.dataset.goto)));
    $("#empty-add-manual").addEventListener("click", () => openAddForm({ language: "vi" }, { manual: true }));
    $("#add-manual").addEventListener("click", () => openAddForm({ language: "vi" }, { manual: true }));
    $("#open-profile").addEventListener("click", openProfile);
    $("#welcome-enter").addEventListener("click", () => closeWelcome(true));
    $("#welcome-replay").addEventListener("click", () => {
      closeSheets();
      openWelcome();
    });
    $("#sheet-backdrop").addEventListener("click", closeSheets);
    $$("[data-close-sheet]").forEach((b) => b.addEventListener("click", closeSheets));
    $("#profile-save").addEventListener("click", saveProfile);
    $("#export-json").addEventListener("click", exportJson);
    $("#import-json").addEventListener("click", () => $("#import-file").click());
    $("#import-file").addEventListener("change", (e) => {
      const f = e.target.files && e.target.files[0];
      if (f) importJson(f);
      e.target.value = "";
    });
    $("#save-book").addEventListener("click", saveBookFromForm);
    $("#book-favorite").addEventListener("click", (e) => {
      const btn = e.currentTarget;
      const on = !btn.classList.contains("on");
      btn.classList.toggle("on", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
    $("#genre-picks").addEventListener("click", (e) => {
      const btn = e.target.closest(".genre-pick");
      if (!btn) return;
      btn.classList.toggle("on");
    });
    $("#shelf-search").addEventListener("input", (e) => {
      shelfFilter.q = e.target.value;
      renderShelf();
    });
    $("#shelf-filters").addEventListener("click", (e) => {
      const chip = e.target.closest("[data-chip]");
      if (!chip) return;
      const key = chip.dataset.chip;
      if (key === "all") {
        shelfFilter.favorites = false;
        shelfFilter.language = "all";
      } else if (key === "fav") {
        shelfFilter.favorites = !shelfFilter.favorites;
      } else {
        shelfFilter.language = shelfFilter.language === key ? "all" : key;
      }
      renderShelf();
    });
    $("#shelf-list").addEventListener("click", (e) => {
      const heart = e.target.closest("[data-heart]");
      if (heart) {
        e.stopPropagation();
        toggleFavorite(heart.dataset.heart, heart);
        return;
      }
      const card = e.target.closest(".book-card");
      if (card) openDetail(card.dataset.id);
    });
    $("#shelf-list").addEventListener("keydown", (e) => {
      if (e.key !== "Enter" && e.key !== " ") return;
      const card = e.target.closest(".book-card");
      if (card) { e.preventDefault(); openDetail(card.dataset.id); }
    });
    $("#genre-grid").addEventListener("click", (e) => {
      const card = e.target.closest("[data-genre]");
      if (!card) return;
      shelfFilter.genre = card.dataset.genre;
      shelfFilter.favorites = false;
      shelfFilter.language = "all";
      setView("shelf");
      // show a temporary chip note via search placeholder
      toast(`Showing ${card.dataset.genre}`);
      renderShelf();
      // add genre clear via resetting when All is tapped — also inject genre chip state visually by filtering list
    });
    // Clear genre filter when choosing All
    const origShelfFilters = $("#shelf-filters");
    origShelfFilters.addEventListener("click", (e) => {
      const chip = e.target.closest("[data-chip]");
      if (chip && chip.dataset.chip === "all") shelfFilter.genre = "all";
    });

    $("#rec-list").addEventListener("click", (e) => {
      const card = e.target.closest("[data-rec]");
      if (!card) return;
      const recs = $("#rec-list")._recs || [];
      const r = recs[Number(card.dataset.rec)];
      if (r) openRecDetail(r);
    });

    $("#detail-body").addEventListener("click", (e) => {
      if (e.target.closest("#rec-add")) {
        const r = $("#detail-body")._rec;
        if (r) addRecToShelf(r);
        return;
      }
      const fav = e.target.closest("[data-detail-fav]");
      if (fav) { toggleFavorite(fav.dataset.detailFav); return; }
      const edit = e.target.closest("[data-detail-edit]");
      if (edit) {
        const b = state.books.find((x) => x.id === edit.dataset.detailEdit);
        if (b) openAddForm(b, { editingId: b.id });
        return;
      }
      const del = e.target.closest("[data-detail-delete]");
      if (del) {
        pendingDeleteId = del.dataset.detailDelete;
        const b = state.books.find((x) => x.id === pendingDeleteId);
        $("#confirm-text").textContent = b
          ? `Remove “${b.title}” from the shelf on this device?`
          : "Remove this book from the shelf on this device?";
        openSheet("sheet-confirm");
      }
    });
    $("#confirm-delete").addEventListener("click", () => {
      if (!pendingDeleteId) return;
      state.books = state.books.filter((b) => b.id !== pendingDeleteId);
      pendingDeleteId = null;
      save();
      closeSheets();
      toast("Removed");
      renderShelf();
      renderGenres();
      renderRecs();
    });

    $("#scan-status").addEventListener("click", () => {
      if (!$("#scan-status").classList.contains("error")) return;
      scanDenied = false;
      startScanner();
    });

    window.addEventListener("resize", updateTabIndicator);
    window.addEventListener("orientationchange", () => setTimeout(updateTabIndicator, 200));
  }


  /* —— First-visit welcome —— */
  const WELCOME_KEY = "little-library-welcome";
  function openWelcome() {
    const welcome = $("#welcome");
    const enter = $("#welcome-enter");
    if (!welcome) return;
    const bits = welcome.querySelectorAll(".welcome-emoji, .welcome-wordmark, .welcome-line, .welcome-enter");
    welcome.classList.remove("open");
    welcome.hidden = false;
    welcome.style.transition = "none";
    bits.forEach((el) => { el.style.transition = "none"; });
    void welcome.offsetWidth;
    welcome.style.removeProperty("transition");
    bits.forEach((el) => { el.style.removeProperty("transition"); });
    requestAnimationFrame(() => {
      welcome.classList.add("open");
      setTimeout(() => {
        if (welcome.classList.contains("open")) enter.focus({ preventScroll: true });
      }, 820);
    });
  }
  function closeWelcome(persist) {
    const welcome = $("#welcome");
    if (!welcome) return;
    if (persist) {
      try { localStorage.setItem(WELCOME_KEY, "1"); } catch (err) {}
    }
    welcome.classList.remove("open");
    setTimeout(() => {
      if (!welcome.classList.contains("open")) welcome.hidden = true;
    }, 320);
  }
  function maybeWelcome() {
    let seen = false;
    try { seen = localStorage.getItem(WELCOME_KEY) === "1"; } catch (err) {}
    if (!seen) openWelcome();
  }

  /* —— Boot —— */
  function boot() {
    bind();
    fillGenrePicks([]);
    setView("shelf");
    renderShelf();
    requestAnimationFrame(updateTabIndicator);
    maybeWelcome();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
