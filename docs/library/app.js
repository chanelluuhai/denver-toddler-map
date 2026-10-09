(() => {
  "use strict";

  const STORAGE_KEY = "littleShelf.v1";
  const SEED_KEY = "littleShelf.sharedSeeded";
  // Public list. No account and no secret. Every phone reads and writes this same document.
  const SHARED_SHELF_URL = "https://api.npoint.io/251111f67ba434bad0bb";
  // Same categories as the Categories sheet in the book spreadsheet (data/library/books.csv).
  const GENRES = [
    "Feelings & Social Skills", "Animals & Nature", "Bedtime", "Stories & Picture Books",
    "Folk & Fairy Tales", "First Words & Concepts", "Songs & Nursery Rhymes",
    "Philosophy & Big Questions", "Family & Love", "Holidays & Celebrations",
    "Body & Health", "Activity & Play"
  ];

  // Genres on the shelf that are not in the list above (older books) still get a filter.
  function allGenres() {
    const extra = [];
    state.books.forEach((b) => (b.genres || []).forEach((g) => {
      if (!GENRES.includes(g) && !extra.includes(g)) extra.push(g);
    }));
    return GENRES.concat(extra);
  }

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
  let shelfFilter = { q: "", language: "all", genre: "all" };
  let editingId = null;
  let pendingDeleteId = null;
  let scanController = null;
  let scanStarting = false;
  let scanGeneration = 0;
  let lastScanned = "";
  let scanCooldownUntil = 0;
  let scanApplyToken = 0;

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
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (err) {}
  }

  function shelfFileUrl() {
    return new URL("shelf.json", document.baseURI).href.split("?")[0] + "?t=" + Date.now();
  }

  function normalizeBooks(list) {
    if (!Array.isArray(list)) return null;
    return list.filter((b) => b && typeof b === "object" && String(b.title || "").trim()).map((b) => ({
      id: b.id || uid(),
      title: String(b.title).trim(),
      author: b.author || "",
      language: b.language || "en",
      genres: Array.isArray(b.genres) ? b.genres.filter((g) => typeof g === "string") : [],
      ageMinMonths: b.ageMinMonths ?? null,
      ageMaxMonths: b.ageMaxMonths ?? null,
      isbn: b.isbn || null,
      notes: b.notes || "",
      favorite: !!b.favorite,
      checked: !!b.checked, // TEMP inventory
      checkedAt: b.checkedAt || null, // TEMP inventory
      coverUrl: b.coverUrl || null,
      link: b.link || null,
      addedAt: b.addedAt || null
    }));
  }

  function copyBooks(books) {
    return books.map((b) => Object.assign({}, b, { genres: (b.genres || []).slice() }));
  }

  let shelfRevision = 0;
  let publishTail = Promise.resolve();

  async function readShelfDocument(url) {
    const res = await fetch(url, {
      cache: "no-store",
      headers: { Accept: "application/json" }
    });
    if (!res.ok) throw new Error(String(res.status));
    const data = await res.json();
    const books = normalizeBooks(data && data.books);
    if (!books) throw new Error("bad shelf");
    return books;
  }

  async function pushSharedShelf(books) {
    const res = await fetch(SHARED_SHELF_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json"
      },
      body: JSON.stringify({ books }),
      cache: "no-store"
    });
    if (!res.ok) throw new Error(String(res.status));
  }

  function saveBooks() {
    save();
    const revision = ++shelfRevision;
    const books = copyBooks(state.books);
    publishTail = publishTail.then(async () => {
      if (revision !== shelfRevision) return;
      try {
        await pushSharedShelf(books);
      } catch (err) {
        toast("Saved on this phone only. The shared shelf did not update.");
      }
    }).catch(() => {});
  }

  function showShelfFromState() {
    if (currentView === "shelf") renderShelf();
    if (currentView === "favorites") renderFavorites();
  }

  async function refreshSharedShelf() {
    const revisionAtStart = shelfRevision;
    let live = null;
    try {
      live = await readShelfDocument(SHARED_SHELF_URL + "?t=" + Date.now());
    } catch (err) {
      live = null;
    }
    if (revisionAtStart !== shelfRevision) return;
    if (live) {
      let seeded = false;
      try { seeded = localStorage.getItem(SEED_KEY) === "1"; } catch (err) {}
      if (!seeded && live.length === 0 && state.books.length) {
        try { localStorage.setItem(SEED_KEY, "1"); } catch (err) {}
        saveBooks();
        return;
      }
      state.books = live;
      try { localStorage.setItem(SEED_KEY, "1"); } catch (err) {}
      save();
      showShelfFromState();
      return;
    }
    if (state.books.length) return;
    try {
      const fileBooks = await readShelfDocument(shelfFileUrl());
      if (revisionAtStart !== shelfRevision) return;
      state.books = fileBooks;
      save();
      showShelfFromState();
    } catch (err) {}
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
        return `<div class="${className}"><img src="${escapeHtml(book.coverUrl)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.onerror=null;this.src='icons/clay-book.png?v=20261004e';this.classList.add('is-clay')"></div>`;
      }
      return `<div class="${className}"><img src="${escapeHtml(book.coverUrl)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove();this.parentElement.innerHTML='<span class=cover-mono>${escapeHtml(monogram(book.title))}</span>'"/></div>`;
    }
    if (fallback === "clay") {
      return `<div class="${className}"><img src="icons/clay-book.png?v=20261004e" alt="" class="is-clay"></div>`;
    }
    return `<div class="${className}"><span class="cover-mono">${escapeHtml(monogram(book.title))}</span></div>`;
  }

  function heartSvg(on) {
    // Phosphor heart (fill / regular), same set as the dock
    if (on) {
      return `<svg viewBox="0 0 256 256" fill="currentColor" aria-hidden="true"><path d="M240,102c0,70-103.79,126.66-108.21,129a8,8,0,0,1-7.58,0C119.79,228.66,16,172,16,102A62.07,62.07,0,0,1,78,40c20.65,0,38.73,8.88,50,23.89C139.27,48.88,157.35,40,178,40A62.07,62.07,0,0,1,240,102Z"/></svg>`;
    }
    return `<svg viewBox="0 0 256 256" fill="currentColor" aria-hidden="true"><path d="M178,40c-20.65,0-38.73,8.88-50,23.89C116.73,48.88,98.65,40,78,40a62.07,62.07,0,0,0-62,62c0,70,103.79,126.66,108.21,129a8,8,0,0,0,7.58,0C136.21,228.66,240,172,240,102A62.07,62.07,0,0,0,178,40ZM128,214.8C109.74,204.16,32,155.69,32,102A46.06,46.06,0,0,1,78,56c19.45,0,35.78,10.36,42.6,27a8,8,0,0,0,14.8,0c6.82-16.67,23.15-27,42.6-27a46.06,46.06,0,0,1,46,46C224,155.61,146.24,204.15,128,214.8Z"/></svg>`;
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
    $$(".sheet.open").forEach((el) => {
      if (el.id === id) return;
      el.classList.remove("open");
      el.setAttribute("aria-hidden", "true");
    });
    if (id !== "sheet-add-menu") {
      stopScanner();
      resetAddMenu();
    }
    const sheet = document.getElementById(id);
    const backdrop = $("#sheet-backdrop");
    sheet.classList.add("open");
    sheet.setAttribute("aria-hidden", "false");
    backdrop.classList.add("open");
    if (id === "sheet-genres") renderGenreSheet();
  }

  function closeSheets() {
    $$(".sheet.open").forEach((el) => {
      el.classList.remove("open");
      el.setAttribute("aria-hidden", "true");
    });
    $("#sheet-backdrop").classList.remove("open");
    stopScanner();
    resetAddMenu();
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
    stopScanner();
    if (name === "shelf") renderShelf();
    if (name === "favorites") renderFavorites();
  }

  /* —— Shelf —— */
  function filteredBooks() {
    const q = shelfFilter.q.trim().toLowerCase();
    return state.books
      .filter((b) => {
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
      { key: "vi", label: "Vietnamese" },
      { key: "bilingual", label: "Bilingual" },
      { key: "en", label: "English" }
    ];
    row.innerHTML = chips.map((c) => {
      let active = false;
      if (c.key === "all") active = shelfFilter.language === "all";
      if (c.key === "vi") active = shelfFilter.language === "vi";
      if (c.key === "bilingual") active = shelfFilter.language === "bilingual";
      if (c.key === "en") active = shelfFilter.language === "en";
      return `<button type="button" class="chip${active ? " active" : ""}" data-chip="${c.key}">${c.label}</button>`;
    }).join("");
  }

  function renderShelf() {
    renderShelfFilters();
    renderInventoryCount(); // TEMP inventory
    renderGenreSheet();
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
    list.innerHTML = books.map((b) => bookCardHtml(b, { inventory: true })).join(""); // TEMP inventory
  }

  /* —— TEMP inventory: check off physical books. Remove this block, the check button in
     bookCardHtml, #inventory-count, the [data-check] handler, and .check-btn/.inventory-count CSS. —— */
  const CHECK_OFF_SVG = `<svg viewBox="0 0 256 256" fill="currentColor" aria-hidden="true"><path d="M173.66,98.34a8,8,0,0,1,0,11.32l-56,56a8,8,0,0,1-11.32,0l-24-24a8,8,0,0,1,11.32-11.32L112,148.69l50.34-50.35A8,8,0,0,1,173.66,98.34ZM232,128A104,104,0,1,1,128,24,104.11,104.11,0,0,1,232,128Zm-16,0a88,88,0,1,0-88,88A88.1,88.1,0,0,0,216,128Z"/></svg>`;
  const CHECK_ON_SVG = `<svg viewBox="0 0 256 256" fill="currentColor" aria-hidden="true"><path d="M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24Zm45.66,85.66-56,56a8,8,0,0,1-11.32,0l-24-24a8,8,0,0,1,11.32-11.32L112,148.69l50.34-50.35a8,8,0,0,1,11.32,11.32Z"/></svg>`;

  function checkBtnHtml(b) {
    return `<button type="button" class="check-btn${b.checked ? " on" : ""}" data-check="${escapeHtml(b.id)}" aria-label="${b.checked ? "Checked" : "Not checked"}" aria-pressed="${b.checked ? "true" : "false"}">${b.checked ? CHECK_ON_SVG : CHECK_OFF_SVG}</button>`;
  }

  function renderInventoryCount() {
    const el = $("#inventory-count");
    if (!el) return;
    const total = state.books.length;
    el.hidden = !total;
    el.textContent = `${state.books.filter((b) => b.checked).length} / ${total} checked`;
  }

  function toggleChecked(id, btn) {
    const book = state.books.find((b) => b.id === id);
    if (!book) return;
    book.checked = !book.checked;
    book.checkedAt = book.checked ? new Date().toISOString() : null;
    saveBooks(); // whole in-memory list, queued; only the newest revision is sent
    btn.classList.toggle("on", book.checked);
    btn.setAttribute("aria-pressed", book.checked ? "true" : "false");
    btn.setAttribute("aria-label", book.checked ? "Checked" : "Not checked");
    btn.innerHTML = book.checked ? CHECK_ON_SVG : CHECK_OFF_SVG;
    renderInventoryCount();
  }
  /* —— end TEMP inventory —— */

  function bookCardHtml(b, opts = {}) {
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
        <div class="card-actions">
          ${opts.inventory ? checkBtnHtml(b) : ""}
          <button type="button" class="heart-btn${b.favorite ? " on" : ""}" data-heart="${escapeHtml(b.id)}" aria-label="${b.favorite ? "Unfavorite" : "Favorite"}" aria-pressed="${b.favorite ? "true" : "false"}">
            ${heartSvg(!!b.favorite)}
          </button>
        </div>
      </article>`;
  }

  function toggleFavorite(id, btn) {
    const book = state.books.find((b) => b.id === id);
    if (!book) return;
    book.favorite = !book.favorite;
    saveBooks();
    if (btn) {
      btn.classList.toggle("on", book.favorite);
      btn.classList.remove("pop");
      void btn.offsetWidth;
      btn.classList.add("pop");
      btn.setAttribute("aria-pressed", book.favorite ? "true" : "false");
      btn.setAttribute("aria-label", book.favorite ? "Unfavorite" : "Favorite");
      btn.innerHTML = heartSvg(book.favorite);
    }
    // Keep the card in place on the shelf (no jump to the top); re-sort on the next render.
    // Only re-render the shelf when the tap came from elsewhere (e.g. the detail sheet).
    if (currentView === "shelf" && !btn) renderShelf();
    if (currentView === "favorites") renderFavorites();
    if ($("#sheet-detail").classList.contains("open")) openDetail(id);
  }

  function renderGenreSheet() {
    const list = $("#genre-sheet-list");
    if (!list) return;
    const items = [{ key: "all", label: "All", count: state.books.length }].concat(
      allGenres().map((g) => ({
        key: g,
        label: g,
        count: state.books.filter((b) => (b.genres || []).includes(g)).length
      }))
    );
    list.innerHTML = items.map((item) => {
      const on = item.key === "all" ? shelfFilter.genre === "all" : shelfFilter.genre === item.key;
      return `<button type="button" class="${on ? "on" : ""}" data-genre-filter="${escapeHtml(item.key)}"><span>${escapeHtml(item.label)}</span><span class="count">${item.count}</span></button>`;
    }).join("");
    const label = $("#genre-filter-label");
    const btn = $("#open-genre-filter");
    if (!label || !btn) return;
    if (shelfFilter.genre === "all") {
      label.hidden = true;
      label.textContent = "";
      btn.classList.remove("on");
      btn.setAttribute("aria-pressed", "false");
    } else {
      label.hidden = false;
      label.textContent = shelfFilter.genre;
      btn.classList.add("on");
      btn.setAttribute("aria-pressed", "true");
    }
  }

  /* —— Favorites —— */
  function renderFavorites() {
    const list = $("#fav-list");
    const empty = $("#fav-empty");
    const favs = state.books
      .filter((b) => b.favorite)
      .sort((a, b) => a.title.localeCompare(b.title));
    empty.hidden = favs.length > 0;
    list.innerHTML = favs.map((b) => bookCardHtml(b)).join("");
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
      ${/^https?:\/\//.test(b.link || "") ? `<a class="detail-link" href="${escapeHtml(b.link)}" target="_blank" rel="noopener noreferrer">Open store page</a>` : ""}
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
    box.innerHTML = allGenres().map((g) =>
      `<button type="button" class="genre-pick${set.has(g) ? " on" : ""}" data-genre="${escapeHtml(g)}">${escapeHtml(g)}</button>`
    ).join("");
  }

  function openAddForm(prefill = {}, opts = {}) {
    editingId = opts.editingId || null;
    openAddForm._scanToken = 0;
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
    } else if (opts.lookupPending) {
      banner.hidden = false;
      banner.textContent = "Looking up this barcode…";
    } else {
      banner.hidden = true;
      banner.textContent = "";
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
    saveBooks();
    closeSheets();
    setView("shelf");
    renderShelf();
  }

  /* —— ISBN lookup —— */
  function mapSubjectsToGenres(subjects = []) {
    const text = subjects.join(" ").toLowerCase();
    const found = new Set();
    const rules = [
      [/feel|emotion|kind|manners|social/, "Feelings & Social Skills"],
      [/animal|bear|zoo|cat|dog|bird|nature|garden|tree|insect/, "Animals & Nature"],
      [/bedtime|sleep|goodnight/, "Bedtime"],
      [/folk|fairy|legend|myth/, "Folk & Fairy Tales"],
      [/first words|alphabet|letter|abc|count|number|color|colour|shape|concept/, "First Words & Concepts"],
      [/rhyme|nursery|song|music/, "Songs & Nursery Rhymes"],
      [/philosoph/, "Philosophy & Big Questions"],
      [/family|mother|father|parent|love/, "Family & Love"],
      [/holiday|christmas|birthday|new year|halloween|easter/, "Holidays & Celebrations"],
      [/body|health|potty|toilet/, "Body & Health"],
      [/activity|play|game|sticker|puzzle/, "Activity & Play"]
    ];
    rules.forEach(([re, g]) => { if (re.test(text)) found.add(g); });
    if (!found.size) found.add("Stories & Picture Books");
    return [...found].filter((g) => GENRES.includes(g));
  }

  function fetchTimeout(url, ms) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), ms || 4000);
    return fetch(url, { signal: ctrl.signal }).finally(() => clearTimeout(timer));
  }

  async function lookupIsbn(isbn) {
    const clean = String(isbn).replace(/[^0-9Xx]/g, "");
    let result = { title: "", author: "", isbn: clean, coverUrl: null, genres: [], language: "en" };

    // Open Library
    try {
      const r = await fetchTimeout(`https://openlibrary.org/isbn/${encodeURIComponent(clean)}.json`);
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
      const r2 = await fetchTimeout(`https://openlibrary.org/search.json?isbn=${encodeURIComponent(clean)}`);
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
        const r3 = await fetchTimeout(`https://www.googleapis.com/books/v1/volumes?q=isbn:${encodeURIComponent(clean)}`);
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
    let clean = String(code || "").replace(/[^0-9Xx]/g, "");
    if (/^97[89]\d{10}/.test(clean)) clean = clean.slice(0, 13);
    if (clean.length < 8) return;
    const now = Date.now();
    if (clean === lastScanned && now < scanCooldownUntil) return;
    lastScanned = clean;
    scanCooldownUntil = now + 3500;
    const token = ++scanApplyToken;
    stopScanner();
    openAddForm({ isbn: clean, language: "en" }, { lookupPending: true });
    openAddForm._scanToken = token;
    let lookup;
    try {
      lookup = await lookupIsbn(clean);
    } catch {
      lookup = { useful: false, book: { isbn: clean, title: "", author: "", genres: [], language: "en", coverUrl: null } };
    }
    applyScanLookup(token, clean, lookup);
  }

  function applyScanLookup(token, clean, lookup) {
    if (token !== openAddForm._scanToken) return;
    if (editingId) return;
    const sheet = $("#sheet-add");
    if (!sheet || !sheet.classList.contains("open")) return;
    const isbnNow = String($("#book-isbn").value || "").replace(/[^0-9Xx]/g, "");
    if (isbnNow !== clean) return;
    const banner = $("#lookup-banner");
    const book = lookup && lookup.book;
    if (lookup && lookup.useful && book) {
      const titleEl = $("#book-title");
      if (!titleEl.value.trim() && book.title) titleEl.value = book.title;
      const authorEl = $("#book-author");
      if (!authorEl.value.trim() && book.author) authorEl.value = book.author;
      if (book.language && $("#book-language").value === "en" && book.language !== "en") {
        $("#book-language").value = book.language;
      }
      if (book.genres && book.genres.length && !$$("#genre-picks .genre-pick.on").length) {
        fillGenrePicks(book.genres);
      }
      if (book.coverUrl) openAddForm._coverUrl = book.coverUrl;
      if (banner) {
        banner.hidden = true;
        banner.textContent = "";
      }
      return;
    }
    if (banner) {
      banner.hidden = false;
      banner.textContent = "Couldn't look that up.";
    }
  }

  /* —— Scanner —— */
  function resetAddMenu() {
    const choices = $("#add-menu-choices");
    const title = $("#add-menu-title");
    if (choices) choices.hidden = false;
    if (title) title.textContent = "Add a book";
  }

  function permissionDenied(err) {
    const name = err && err.name;
    return name === "NotAllowedError" || name === "PermissionDeniedError" || name === "SecurityError";
  }

  function showCameraError(err) {
    scanStarting = false;
    const status = $("#scan-status");
    if (!status) return;
    status.hidden = false;
    status.classList.add("error");
    status.textContent = permissionDenied(err)
      ? "Camera is blocked. On iPhone, allow camera for this site in Settings."
      : "Camera isn't available.";
  }

  function hideScanScreen() {
    const screen = $("#scan-screen");
    if (screen) screen.hidden = true;
    const video = $("#scan-video");
    if (video) video.style.visibility = "";
    const status = $("#scan-status");
    if (!status) return;
    status.hidden = true;
    status.textContent = "";
    status.classList.remove("error");
  }

  function showScanScreen() {
    const screen = $("#scan-screen");
    const video = $("#scan-video");
    screen.hidden = false;
    video.style.visibility = "";
    const status = $("#scan-status");
    status.hidden = true;
    status.classList.remove("error");
    status.textContent = "";
    const sheet = $("#sheet-add-menu");
    if (sheet) {
      sheet.classList.remove("open");
      sheet.setAttribute("aria-hidden", "true");
    }
    const backdrop = $("#sheet-backdrop");
    if (backdrop) backdrop.classList.remove("open");
    resetAddMenu();
  }

  function prepareScanVideo(video) {
    video.playsInline = true;
    video.muted = true;
    video.autoplay = true;
    video.controls = false;
    video.setAttribute("playsinline", "");
    video.setAttribute("webkit-playsinline", "");
    video.setAttribute("muted", "");
    video.setAttribute("autoplay", "");
  }

  // Tap handler. getUserMedia runs in this turn, before any await, so iOS
  // still treats it as the button gesture.
  function beginScan() {
    stopScanner();
    loadZxing().catch(() => {});
    const generation = scanGeneration;
    const video = $("#scan-video");
    prepareScanVideo(video);
    showScanScreen();
    if (!navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== "function") {
      showCameraError(new Error("Camera isn't available."));
      return;
    }
    let streamPromise;
    try {
      streamPromise = navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false });
    } catch (err) {
      showCameraError(err);
      return;
    }
    const unlock = video.play();
    if (unlock && typeof unlock.catch === "function") unlock.catch(() => {});
    continueScan(streamPromise, generation);
  }

  async function continueScan(streamPromise, generation) {
    scanStarting = true;
    let stream;
    try {
      stream = await streamPromise;
    } catch (err) {
      scanStarting = false;
      if (generation !== scanGeneration) return;
      showCameraError(err);
      return;
    }
    if (generation !== scanGeneration || $("#scan-screen").hidden) {
      stream.getTracks().forEach((t) => t.stop());
      scanStarting = false;
      return;
    }
    const video = $("#scan-video");
    video.srcObject = stream;
    try { await video.play(); } catch (err) { /* muted inline video can still show frames */ }
    const alive = () => generation === scanGeneration && !$("#scan-screen").hidden;
    scanController = {
      stop() {
        stream.getTracks().forEach((t) => t.stop());
        if (video.srcObject) video.srcObject = null;
      }
    };
    scanStarting = false;
    if (!alive()) {
      stream.getTracks().forEach((t) => t.stop());
      return;
    }
    startLiveDetection(video, stream, alive);
  }

  function withTimeout(promise, ms) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("timeout")), ms);
      promise.then(
        (value) => { clearTimeout(timer); resolve(value); },
        (err) => { clearTimeout(timer); reject(err); }
      );
    });
  }

  let zxingPromise = null;
  function loadZxing() {
    if (window.ZXing && window.ZXing.MultiFormatReader) return Promise.resolve();
    if (zxingPromise) return zxingPromise;
    zxingPromise = new Promise((resolve, reject) => {
      const el = document.createElement("script");
      el.src = "zxing-0.21.3.min.js";
      el.onload = () => resolve();
      el.onerror = () => {
        zxingPromise = null;
        reject(new Error("Failed to load barcode decoder"));
      };
      document.head.appendChild(el);
    });
    return zxingPromise;
  }

  function makeZxingReader() {
    const Z = window.ZXing;
    const hints = new Map();
    hints.set(Z.DecodeHintType.POSSIBLE_FORMATS, [
      Z.BarcodeFormat.EAN_13,
      Z.BarcodeFormat.EAN_8,
      Z.BarcodeFormat.UPC_A,
      Z.BarcodeFormat.UPC_E,
      Z.BarcodeFormat.CODE_128,
      Z.BarcodeFormat.CODE_39,
      Z.BarcodeFormat.ITF,
      Z.BarcodeFormat.QR_CODE
    ]);
    hints.set(Z.DecodeHintType.TRY_HARDER, true);
    const reader = new Z.MultiFormatReader();
    reader.setHints(hints);
    return reader;
  }

  function decodeWithZxing(reader, canvas) {
    const Z = window.ZXing;
    const biners = [Z.HybridBinarizer, Z.GlobalHistogramBinarizer];
    for (const Biner of biners) {
      try {
        const src = new Z.HTMLCanvasElementLuminanceSource(canvas);
        const bitmap = new Z.BinaryBitmap(new Biner(src));
        const result = reader.decode(bitmap);
        reader.reset();
        const text = result && result.getText ? result.getText() : "";
        if (text) return text;
      } catch (err) {
        try { reader.reset(); } catch (e) { /* ignore */ }
      }
    }
    return "";
  }

  function drawScanFrame(video, canvas, ctx) {
    const vw = video.videoWidth;
    const vh = video.videoHeight;
    if (!vw || !vh) return false;
    const bandH = Math.max(80, Math.round(vh * 0.62));
    const sy = Math.max(0, Math.round((vh - bandH) / 2));
    const scale = Math.min(1, 960 / vw);
    const dw = Math.max(1, Math.round(vw * scale));
    const dh = Math.max(1, Math.round(bandH * scale));
    if (canvas.width !== dw) canvas.width = dw;
    if (canvas.height !== dh) canvas.height = dh;
    ctx.drawImage(video, 0, sy, vw, bandH, 0, 0, dw, dh);
    return true;
  }

  async function makeBarcodeDetector() {
    if (typeof window.BarcodeDetector !== "function") return null;
    let formats = ["ean_13", "ean_8", "upc_a", "upc_e", "code_128", "code_39", "itf", "qr_code"];
    try {
      const supported = await BarcodeDetector.getSupportedFormats();
      const filtered = formats.filter((f) => supported.includes(f));
      if (filtered.length) formats = filtered;
    } catch (err) { /* keep the ISBN formats */ }
    try {
      return new BarcodeDetector({ formats });
    } catch (err) {
      return null;
    }
  }

  function startLiveDetection(video, stream, alive) {
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    let detector = null;
    let nativeFailed = 0;
    let reader = null;
    let busy = false;
    let timer = 0;
    let stopped = false;

    const stopTracks = () => {
      stopped = true;
      if (timer) clearTimeout(timer);
      timer = 0;
      stream.getTracks().forEach((t) => t.stop());
      if (video.srcObject) video.srcObject = null;
    };
    scanController = { stop: stopTracks };

    const schedule = (ms) => {
      if (stopped || !alive()) return;
      timer = setTimeout(tick, ms);
    };

    makeBarcodeDetector().then((det) => {
      if (!stopped && alive()) detector = det;
    }).catch(() => {});

    loadZxing().then(() => {
      if (stopped || !alive() || !window.ZXing) return;
      try { reader = makeZxingReader(); } catch (err) { reader = null; }
    }).catch(() => {});

    async function tick() {
      timer = 0;
      if (stopped || !alive()) return;
      if (busy || video.readyState < 2 || !video.videoWidth) {
        schedule(100);
        return;
      }
      if (!drawScanFrame(video, canvas, ctx)) {
        schedule(100);
        return;
      }
      busy = true;
      let code = "";
      try {
        // ZXing reads the pixels directly. Native detect() on iOS often never
        // settles for a camera frame, so don't wait on it before decoding.
        if (reader) {
          code = decodeWithZxing(reader, canvas) || "";
        } else if (detector && nativeFailed < 8) {
          try {
            const codes = await withTimeout(detector.detect(canvas), 350);
            if (codes && codes[0] && codes[0].rawValue) code = String(codes[0].rawValue);
          } catch (err) {
            nativeFailed += 1;
          }
        }
      } finally {
        busy = false;
      }
      if (stopped || !alive()) return;
      if (code) {
        handleScannedCode(code);
        return;
      }
      schedule(70);
    }

    schedule(160);
  }

  function stopScanner() {
    scanStarting = false;
    scanGeneration += 1;
    if (scanController) {
      try { scanController.stop(); } catch (err) { /* ignore */ }
      scanController = null;
    }
    hideScanScreen();
  }

  /* —— Profile / export —— */
  let aboutOpen = false;
  let aboutTimer = 0;
  function openAbout() {
    $("#profile-name").value = state.profile.displayName || "Bé";
    $("#profile-birthday").value = state.profile.birthday || "2025-01-15";
    $("#profile-age").textContent = formatAge(childAgeMonths());
    closeSheets();
    aboutOpen = true;
    clearTimeout(aboutTimer);
    const drawer = $("#about-drawer");
    const backdrop = $("#about-backdrop");
    drawer.hidden = false;
    backdrop.hidden = false;
    drawer.classList.remove("open");
    backdrop.classList.remove("open");
    $("#open-about").setAttribute("aria-expanded", "true");
    drawer.classList.remove("settled");
    void drawer.offsetWidth;
    drawer.classList.add("open");
    backdrop.classList.add("open");
    const settle = (e) => {
      if (e.target !== drawer || e.propertyName !== "transform") return;
      drawer.removeEventListener("transitionend", settle);
      if (aboutOpen) drawer.classList.add("settled");
    };
    drawer.addEventListener("transitionend", settle);
    setTimeout(() => {
      if (aboutOpen) drawer.classList.add("settled");
    }, 520);
  }

  function closeAbout() {
    const drawer = $("#about-drawer");
    if (!aboutOpen && !drawer.classList.contains("open")) return;
    aboutOpen = false;
    drawer.classList.remove("settled");
    void drawer.offsetWidth;
    drawer.classList.remove("open");
    $("#about-backdrop").classList.remove("open");
    $("#open-about").setAttribute("aria-expanded", "false");
    clearTimeout(aboutTimer);
    aboutTimer = setTimeout(() => {
      if (!aboutOpen) {
        drawer.hidden = true;
        $("#about-backdrop").hidden = true;
      }
    }, 520);
  }

  function saveProfile() {
    state.profile.displayName = $("#profile-name").value.trim() || "Bé";
    const nextBirthday = $("#profile-birthday").value;
    if (/^\d{4}-\d{2}-\d{2}$/.test(nextBirthday)) {
      state.profile.birthday = nextBirthday;
    }
    save();
    toast("Profile saved");
    closeAbout();
    renderShelf();
    if (currentView === "favorites") renderFavorites();
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
        state.books = normalizeBooks(data.books) || [];
        if (data.profile) {
          state.profile.displayName = data.profile.displayName || state.profile.displayName;
          state.profile.birthday = data.profile.birthday || state.profile.birthday;
        }
        saveBooks();
        toast("Library imported");
        closeSheets();
        renderShelf();
        renderFavorites();
      } catch {
        toast("Could not read that JSON file");
      }
    };
    reader.readAsText(file);
  }

  /* —— Events —— */
  function bind() {
    $$(".tab").forEach((t) => t.addEventListener("click", () => setView(t.dataset.view)));
    $("#dock-plus").addEventListener("click", () => {
      stopScanner();
      resetAddMenu();
      openSheet("sheet-add-menu");
    });
    $("#menu-scan").addEventListener("click", beginScan);
    $("#empty-scan").addEventListener("click", beginScan);
    $("#menu-manual").addEventListener("click", () => openAddForm({ language: "vi" }, { manual: true }));
    $("#empty-add-manual").addEventListener("click", () => openAddForm({ language: "vi" }, { manual: true }));
    $("#open-about").addEventListener("click", openAbout);
    $("#about-close").addEventListener("click", closeAbout);
    $("#about-backdrop").addEventListener("click", closeAbout);
    $("#open-genre-filter").addEventListener("click", () => openSheet("sheet-genres"));
    $("#genre-sheet-list").addEventListener("click", (e) => {
      const btn = e.target.closest("[data-genre-filter]");
      if (!btn) return;
      shelfFilter.genre = btn.dataset.genreFilter;
      closeSheets();
      renderShelf();
    });
    $("#welcome-enter").addEventListener("click", () => closeWelcome(true));
    $("#welcome-replay").addEventListener("click", () => {
      closeAbout();
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
        shelfFilter.language = "all";
      } else {
        shelfFilter.language = shelfFilter.language === key ? "all" : key;
      }
      renderShelf();
    });
    ["#shelf-list", "#fav-list"].forEach((sel) => {
      $(sel).addEventListener("click", (e) => {
        const check = e.target.closest("[data-check]"); // TEMP inventory
        if (check) {
          e.stopPropagation();
          toggleChecked(check.dataset.check, check);
          return;
        }
        const heart = e.target.closest("[data-heart]");
        if (heart) {
          e.stopPropagation();
          toggleFavorite(heart.dataset.heart, heart);
          return;
        }
        const card = e.target.closest(".book-card");
        if (card) openDetail(card.dataset.id);
      });
      $(sel).addEventListener("keydown", (e) => {
        if (e.key !== "Enter" && e.key !== " ") return;
        if (e.target.closest("[data-heart], [data-check]")) return;
        const card = e.target.closest(".book-card");
        if (card) { e.preventDefault(); openDetail(card.dataset.id); }
      });
    });
    // Clear genre filter when choosing All
    const origShelfFilters = $("#shelf-filters");
    origShelfFilters.addEventListener("click", (e) => {
      const chip = e.target.closest("[data-chip]");
      if (chip && chip.dataset.chip === "all") shelfFilter.genre = "all";
    });

    $("#detail-body").addEventListener("click", (e) => {
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
          ? `Remove “${b.title}” from the shelf?`
          : "Remove this book from the shelf?";
        openSheet("sheet-confirm");
      }
    });
    $("#confirm-delete").addEventListener("click", () => {
      if (!pendingDeleteId) return;
      state.books = state.books.filter((b) => b.id !== pendingDeleteId);
      pendingDeleteId = null;
      saveBooks();
      closeSheets();
      toast("Removed");
      renderShelf();
      renderFavorites();
    });

    $("#scan-close").addEventListener("click", () => stopScanner());
    $("#scan-status").addEventListener("click", () => {
      if (!$("#scan-status").classList.contains("error")) return;
      beginScan();
    });

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
    refreshSharedShelf();
    maybeWelcome();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
