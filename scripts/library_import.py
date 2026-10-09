#!/usr/bin/env python3
"""Little Library shelf data: spreadsheet / CSV -> docs/library/shelf.json (+ shared n:point store).

Source of truth: data/library/books.csv (one row per book, edit it in any spreadsheet app).

  python3 scripts/library_import.py                       # books.csv -> docs/library/shelf.json
  python3 scripts/library_import.py --xlsx Books.xlsx     # re-import the spreadsheet into books.csv first
  python3 scripts/library_import.py --pull                # copy what phones added/edited into books.csv first
  python3 scripts/library_import.py --push                # also publish to the shared store every phone reads

--push keeps books that exist only in the shared store (added on a phone) and adds them to
books.csv, so nothing added in the app is lost. Use --replace to publish books.csv exactly.
"""
import argparse
import csv
import io
import json
import re
import sys
import unicodedata
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "library" / "books.csv"
SHELF_JSON = ROOT / "docs" / "library" / "shelf.json"
COVERS_DIR = ROOT / "docs" / "library" / "covers"
SHARED_URL = "https://api.npoint.io/251111f67ba434bad0bb"

COLUMNS = ["id", "title", "author", "language", "genres", "favorite", "isbn", "cover", "link", "notes", "added_at"]
LANGUAGES = {
    "english": "en", "en": "en",
    "vietnamese": "vi", "vi": "vi",
    "english + vietnamese": "bilingual", "vietnamese + english": "bilingual",
    "english + spanish": "bilingual", "bilingual": "bilingual",
    "spanish": "other", "other": "other",
}
NO_AUTHOR = {"none credited", "none", "unknown", ""}


def slugify(text):
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:60].rstrip("-") or "book"


def norm_title(t):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(t or "")).strip().lower())


def isbn10_to_13(code):
    code = code.upper()
    if not re.fullmatch(r"\d{9}[\dX]", code):
        return ""
    total = sum((10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(code))
    if total % 11:
        return ""
    core = "978" + code[:9]
    check = (10 - sum((1 if i % 2 == 0 else 3) * int(c) for i, c in enumerate(core)) % 10) % 10
    return core + str(check)


def isbn_from_link(link):
    """Amazon book pages use the ISBN-10 as the /dp/ id. Only trust it when the checksum is valid."""
    m = re.search(r"amazon\.[a-z.]+/(?:.*/)?dp/([0-9X]{10})(?:[/?]|$)", link or "", re.I)
    return isbn10_to_13(m.group(1)) if m else ""


def read_csv():
    if not CSV_PATH.exists():
        return []
    with CSV_PATH.open(newline="", encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f) if (r.get("title") or "").strip()]


def write_csv(rows):
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") or "" for c in COLUMNS})


def unique_id(base, taken):
    slug, n = base, 2
    while slug in taken:
        slug, n = f"{base}-{n}", n + 1
    taken.add(slug)
    return slug


def save_cover(data, book_id):
    from PIL import Image
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.thumbnail((400, 400))
    out = COVERS_DIR / f"{book_id}.jpg"
    img.save(out, "JPEG", quality=78, optimize=True, progressive=True)
    return f"covers/{book_id}.jpg"


def import_xlsx(path):
    """Spreadsheet 'Books' sheet -> books.csv. Keeps ids/favorites of rows already in books.csv (matched by title)."""
    import openpyxl
    wb = openpyxl.load_workbook(path)
    ws = wb["Books"] if "Books" in wb.sheetnames else wb.worksheets[0]
    header = [str(c.value or "").strip().lower() for c in ws[1]]
    col = {name: i for i, name in enumerate(header)}
    for need in ("title",):
        if need not in col:
            sys.exit(f"Spreadsheet has no '{need}' column. Found: {header}")

    images = {}
    for img in getattr(ws, "_images", []):
        images.setdefault(img.anchor._from.row + 1, img)  # 1-based sheet row

    existing = {norm_title(r["title"]): r for r in read_csv()}
    taken = set()
    rows, seen, warnings = [], {}, []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def cell(row, name):
        i = col.get(name)
        v = row[i].value if i is not None and i < len(row) else None
        return str(v).strip() if v is not None else ""

    for r_idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
        title = cell(row, "title")
        if not title:
            continue
        key = norm_title(title)
        link = cell(row, "link")
        if key in seen:
            warnings.append(f"Possible duplicate: sheet row {r_idx} '{title}' repeats row {seen[key]}. Kept both.")
        seen[key] = r_idx
        prev = existing.get(key, {})
        book_id = prev.get("id") or slugify(title)
        book_id = unique_id(book_id, taken)

        lang_raw = cell(row, "language")
        language = LANGUAGES.get(lang_raw.lower(), "")
        if lang_raw and not language:
            warnings.append(f"Row {r_idx} '{title}': unknown language '{lang_raw}', left blank.")
        author = cell(row, "author")
        if author.lower() in NO_AUTHOR:
            author = ""
        genre = cell(row, "genre")

        cover = prev.get("cover", "")
        if r_idx in images:
            cover = save_cover(images[r_idx]._data(), book_id)
        rows.append({
            "id": book_id,
            "title": title,
            "author": author,
            "language": language,
            "genres": genre,
            "favorite": prev.get("favorite", ""),
            "isbn": cell(row, "isbn") or prev.get("isbn") or isbn_from_link(link),
            "cover": cover,
            "link": link,
            "notes": cell(row, "notes"),
            "added_at": prev.get("added_at") or now,
        })
    dropped = [r["title"] for k, r in existing.items() if k not in seen]
    if dropped:
        warnings.append("In books.csv but not in the spreadsheet (removed from books.csv): " + "; ".join(dropped))
    write_csv(rows)
    return rows, warnings


def row_to_book(r):
    return {
        "id": r["id"].strip(),
        "title": r["title"].strip(),
        "author": (r.get("author") or "").strip(),
        "language": (r.get("language") or "").strip() or "en",
        "genres": [g.strip() for g in (r.get("genres") or "").split(";") if g.strip()],
        "ageMinMonths": None,
        "ageMaxMonths": None,
        "isbn": (r.get("isbn") or "").strip() or None,
        "notes": (r.get("notes") or "").strip(),
        "favorite": (r.get("favorite") or "").strip().lower() in {"1", "yes", "true", "y", "x"},
        "coverUrl": (r.get("cover") or "").strip() or None,
        "link": (r.get("link") or "").strip() or None,
        "addedAt": (r.get("added_at") or "").strip() or None,
    }


def book_to_row(b):
    return {
        "id": b.get("id", ""),
        "title": b.get("title", ""),
        "author": b.get("author") or "",
        "language": b.get("language") or "",
        "genres": "; ".join(b.get("genres") or []),
        "favorite": "yes" if b.get("favorite") else "",
        "isbn": b.get("isbn") or "",
        "cover": b.get("coverUrl") or "",
        "link": b.get("link") or "",
        "notes": b.get("notes") or "",
        "added_at": b.get("addedAt") or "",
    }


def fetch_shared():
    req = urllib.request.Request(SHARED_URL, headers={"Accept": "application/json", "User-Agent": "little-library-import"})
    with urllib.request.urlopen(req, timeout=20) as res:
        data = json.load(res)
    return data.get("books") or []


def push_shared(books):
    body = json.dumps({"books": books}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(SHARED_URL, data=body, method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "little-library-import"})
    with urllib.request.urlopen(req, timeout=30) as res:
        if res.status >= 300:
            sys.exit(f"Shared store answered {res.status}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xlsx", help="re-import this spreadsheet into data/library/books.csv")
    ap.add_argument("--pull", action="store_true", help="replace books.csv with the shared store (what the phones see)")
    ap.add_argument("--push", action="store_true", help="publish to the shared store every phone reads")
    ap.add_argument("--replace", action="store_true", help="with --push: drop books that are only in the shared store")
    args = ap.parse_args()

    warnings = []
    if args.pull:
        live = fetch_shared()
        write_csv([book_to_row(b) for b in live])
        print(f"Pulled {len(live)} books from the shared store into {CSV_PATH.relative_to(ROOT)}")
    if args.xlsx:
        rows, warnings = import_xlsx(args.xlsx)
        print(f"Imported {len(rows)} rows from {args.xlsx}")

    rows = read_csv()
    ids = set()
    for r in rows:
        if not (r.get("id") or "").strip():
            r["id"] = slugify(r["title"])
        r["id"] = unique_id(r["id"].strip(), ids)
    write_csv(rows)
    books = [row_to_book(r) for r in rows]

    if args.push and not args.replace:
        live = fetch_shared()
        extra = [b for b in live if b.get("id") not in ids]
        if extra:
            print("Kept books that were only in the shared store:", "; ".join(b.get("title", "?") for b in extra))
            books += extra
            write_csv([book_to_row(b) for b in books])

    SHELF_JSON.write_text(json.dumps({"books": books}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(books)} books to {SHELF_JSON.relative_to(ROOT)}")
    if args.push:
        push_shared(books)
        print(f"Published {len(books)} books to the shared store")
    for w in warnings:
        print("NOTE:", w)


if __name__ == "__main__":
    main()
