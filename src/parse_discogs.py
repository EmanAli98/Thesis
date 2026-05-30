"""
parse_discogs.py - FIXED
The bug: elem.clear() on child elements destroyed their data
         before the parent <release> could read them.
Fix: only clear the release element itself after processing.
Run: python src/parse_discogs.py
"""
import gzip
import xml.etree.ElementTree as ET
import duckdb
import pandas as pd
import time
import os

GZ_PATH = "../data_raw/discogs/discogs_20260401_releases.xml.gz"
DB_PATH = "../data_processed/thesis.duckdb"

BATCH_SIZE   = 10_000
REPORT_EVERY = 100_000

size_gb = os.path.getsize(GZ_PATH) / (1024**3)
print(f"File: {GZ_PATH}")
print(f"Size: {size_gb:.2f} GB")

con = duckdb.connect(DB_PATH)
print("Connected to DuckDB ✅")

con.execute("""
    CREATE OR REPLACE TABLE discogs_releases_raw (
        discogs_id      INTEGER,
        discogs_artist  VARCHAR,
        discogs_title   VARCHAR,
        discogs_year    VARCHAR,
        discogs_country VARCHAR,
        discogs_genre   VARCHAR,
        discogs_style   VARCHAR,
        discogs_label   VARCHAR,
        discogs_catno   VARCHAR,
        discogs_format  VARCHAR,
        discogs_status  VARCHAR
    )
""")
print("✅ discogs_releases_raw table created (empty)")

def flush(con, batch):
    if not batch:
        return []
    df = pd.DataFrame(batch, columns=[
        "discogs_id", "discogs_artist", "discogs_title",
        "discogs_year", "discogs_country", "discogs_genre",
        "discogs_style", "discogs_label", "discogs_catno",
        "discogs_format", "discogs_status"
    ])
    con.register("_discogs_tmp", df)
    con.execute("INSERT INTO discogs_releases_raw SELECT * FROM _discogs_tmp")
    con.unregister("_discogs_tmp")
    return []

print(f"\nStreaming {GZ_PATH} ...")
print("This will take 30–60 minutes. Progress below:\n")

batch        = []
total_parsed = 0
total_saved  = 0
start        = time.time()

try:
    with gzip.open(GZ_PATH, "rb") as gz:
        # ── KEY FIX: track the root element so we can clear it
        # periodically to prevent memory buildup, WITHOUT destroying
        # child elements before the parent release is processed
        context = ET.iterparse(gz, events=("start", "end"))
        root    = None

        for event, elem in context:

            # Capture root on very first element
            if event == "start" and root is None:
                root = elem
                continue

            # Only process complete <release> elements
            if event != "end" or elem.tag != "release":
                continue  # ← FIX: NO elem.clear() here anymore

            total_parsed += 1

            # Status filter
            status = elem.get("status", "accepted").lower()
            if status == "deleted":
                elem.clear()
                if root is not None:
                    root.clear()
                continue

            release_id = elem.get("id")

            # ── Artist ───────────────────────────────────────
            artist = None
            artists_el = elem.find("artists")
            if artists_el is not None:
                first = artists_el.find("artist")
                if first is not None:
                    # Try <name> first, then <n> (older format)
                    for tag in ("name", "n"):
                        n = first.find(tag)
                        if n is not None and n.text:
                            artist = n.text.strip()
                            break

            # ── Title ────────────────────────────────────────
            title_el = elem.find("title")
            title = title_el.text.strip() if (
                title_el is not None and title_el.text) else None

            if not artist and not title:
                elem.clear()
                if root is not None:
                    root.clear()
                continue

            # ── Year ─────────────────────────────────────────
            year = None
            rel_el = elem.find("released")
            if rel_el is not None and rel_el.text:
                year = rel_el.text.strip().split("-")[0]

            # ── Country ──────────────────────────────────────
            country = None
            c_el = elem.find("country")
            if c_el is not None and c_el.text:
                country = c_el.text.strip()

            # ── Genre (first) ─────────────────────────────────
            genre = None
            genres_el = elem.find("genres")
            if genres_el is not None:
                g = genres_el.find("genre")
                if g is not None and g.text:
                    genre = g.text.strip()

            # ── Style (first — more specific than genre) ──────
            style = None
            styles_el = elem.find("styles")
            if styles_el is not None:
                s = styles_el.find("style")
                if s is not None and s.text:
                    style = s.text.strip()

            # ── Label + catalogue number ───────────────────────
            label = catno = None
            labels_el = elem.find("labels")
            if labels_el is not None:
                lbl = labels_el.find("label")
                if lbl is not None:
                    label = lbl.get("name", "").strip() or None
                    catno = lbl.get("catno", "").strip() or None

            # ── Format ────────────────────────────────────────
            fmt = None
            formats_el = elem.find("formats")
            if formats_el is not None:
                f = formats_el.find("format")
                if f is not None:
                    fmt = f.get("name", "").strip() or None

            batch.append((
                int(release_id) if release_id else None,
                artist, title, year, country,
                genre, style, label, catno, fmt, status
            ))
            total_saved += 1

            # ── FIX: clear element AND root to free memory ────
            elem.clear()
            if root is not None:
                root.clear()

            if len(batch) >= BATCH_SIZE:
                batch = flush(con, batch)

            if total_parsed % REPORT_EVERY == 0:
                n_db    = con.execute(
                    "SELECT COUNT(*) FROM discogs_releases_raw"
                ).fetchone()[0]
                elapsed = time.time() - start
                rate    = total_parsed / elapsed if elapsed > 0 else 0
                print(f"  Parsed {total_parsed:>9,} | "
                      f"Saved {n_db:>8,} | "
                      f"{rate:,.0f}/sec | "
                      f"{elapsed/60:.0f} min",
                      flush=True)

except Exception as e:
    print(f"\n⚠️  Error at release {total_parsed:,}: {e}")
    batch = flush(con, batch)

# Final flush
batch = flush(con, batch)

n_final = con.execute(
    "SELECT COUNT(*) FROM discogs_releases_raw"
).fetchone()[0]
elapsed = time.time() - start

print(f"""
── Streaming complete ──
  Total parsed   : {total_parsed:,}
  Saved to DB    : {n_final:,}
  Time elapsed   : {elapsed/60:.1f} minutes
""")

print("── Field coverage ──")
print(con.execute("""
    SELECT
        COUNT(*)                AS total,
        COUNT(discogs_artist)   AS has_artist,
        COUNT(discogs_title)    AS has_title,
        COUNT(discogs_year)     AS has_year,
        COUNT(discogs_country)  AS has_country,
        COUNT(discogs_genre)    AS has_genre,
        COUNT(discogs_style)    AS has_style,
        COUNT(discogs_label)    AS has_label,
        COUNT(discogs_catno)    AS has_catno,
        COUNT(discogs_format)   AS has_format
    FROM discogs_releases_raw
""").fetchdf().T.rename(columns={0: "count"}).to_string())

print("\n── Sample rows ──")
print(con.execute("""
    SELECT discogs_id, discogs_artist, discogs_title,
           discogs_genre, discogs_style, discogs_label,
           discogs_country, discogs_year
    FROM discogs_releases_raw
    WHERE discogs_genre IS NOT NULL
      AND discogs_style IS NOT NULL
    LIMIT 10
""").fetchdf().to_string(index=False))

con.close()
print("\n✅ Done — connection closed cleanly")