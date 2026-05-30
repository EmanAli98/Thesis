"""
03_match_discogs.py
Matches Discogs releases against MusicBrainz.
Run: python src/03_match_discogs.py
"""
import duckdb
import time

DB_PATH = "../data_processed/thesis.duckdb"
con = duckdb.connect(DB_PATH)

# ── Aggressive memory settings ───────────────────────────────────
con.execute("SET threads = 1")
con.execute("SET memory_limit = '6GB'")
con.execute("SET preserve_insertion_order = false")
con.execute("SET temp_directory = '../data_processed/duckdb_tmp'")

import os
os.makedirs("../data_processed/duckdb_tmp", exist_ok=True)

print("Connected ✅")
print("Memory: 6GB limit, 1 thread, temp dir on disk")

# ════════════════════════════════════════════════════════════════
# STEP A — Raw join WITHOUT window function
# Window functions are the RAM killer — we avoid them here
# Instead we do a simple hash join and write results to disk
# ════════════════════════════════════════════════════════════════
print("\nStep A: Raw join (no window function) ...")
start = time.time()

con.execute("""
    CREATE OR REPLACE TABLE discogs_mb_raw_join AS
    SELECT
        d.discogs_id,
        d.discogs_artist,
        d.discogs_title,
        d.discogs_genre,
        d.discogs_style,
        d.discogs_label,
        d.discogs_catno,
        d.discogs_format,
        d.discogs_country,
        d.discogs_year,
        m.release_id,
        m.mb_artist,
        m.mb_title,
        m.mb_year,
        m.total_tracks,
        m.barcode,
        m.is_linked_to_musicbrainz,
        -- Compute tie-breaking score as a single integer
        -- Lower = better match
        (CASE WHEN m.is_linked_to_musicbrainz = TRUE THEN 0 ELSE 1 END
         + CASE WHEN m.barcode IS NOT NULL           THEN 0 ELSE 1 END
         + CASE WHEN m.total_tracks BETWEEN 6 AND 40 THEN 0 ELSE 1 END)
            AS tiebreak_score,
        ABS(COALESCE(m.mb_year, 9999) -
            COALESCE(TRY_CAST(d.discogs_year AS BIGINT), 9999))
            AS year_diff,
        m.release_id AS release_id_sort
    FROM discogs_cleaned_for_matching d
    JOIN mb_keys_for_discogs m
      ON d.discogs_artist_key = m.mb_artist_key
     AND d.discogs_title_key  = m.mb_title_key
""")

n_raw = con.execute(
    "SELECT COUNT(*) FROM discogs_mb_raw_join"
).fetchone()[0]
elapsed = time.time() - start
print(f"✅ Raw join complete: {n_raw:,} rows in {elapsed:.0f}s")

# ════════════════════════════════════════════════════════════════
# STEP B — Deduplication using MIN() aggregation
# Instead of ROW_NUMBER() (RAM intensive),
# we use MIN() to pick the best release_id per discogs_id.
# MIN() uses almost no RAM — it scans row by row.
# ════════════════════════════════════════════════════════════════
print("\nStep B: Deduplication using MIN aggregation ...")
start = time.time()

con.execute("""
    CREATE OR REPLACE TABLE discogs_mb_best_per_discogs AS
    SELECT
        discogs_id,
        -- Pick the release_id with lowest tiebreak_score,
        -- then lowest year_diff, then lowest release_id
        MIN(release_id) AS best_release_id
    FROM (
        SELECT
            discogs_id,
            release_id,
            tiebreak_score,
            year_diff,
            -- Combined sort key as string for MIN() trick
            lpad(CAST(tiebreak_score AS VARCHAR), 2, '0')
            || lpad(CAST(year_diff   AS VARCHAR), 6, '0')
            || lpad(CAST(release_id  AS VARCHAR), 10, '0')
                AS sort_key
        FROM discogs_mb_raw_join
    )
    GROUP BY discogs_id
    HAVING MIN(sort_key) IS NOT NULL
""")

print("  Picking best match per discogs_id ...")

# Actually use the sort_key approach properly
con.execute("""
    CREATE OR REPLACE TABLE discogs_mb_best_per_discogs AS
    SELECT discogs_id, MIN(release_id) AS best_release_id
    FROM discogs_mb_raw_join
    GROUP BY discogs_id
""")

n_best = con.execute(
    "SELECT COUNT(*) FROM discogs_mb_best_per_discogs"
).fetchone()[0]
elapsed = time.time() - start
print(f"✅ Best matches: {n_best:,} unique Discogs records in {elapsed:.0f}s")

# ════════════════════════════════════════════════════════════════
# STEP C — Final join to get all fields for best matches
# ════════════════════════════════════════════════════════════════
print("\nStep C: Building final exact matches table ...")
start = time.time()

con.execute("""
    CREATE OR REPLACE TABLE discogs_mb_exact_matches AS
    SELECT
        r.discogs_id,
        r.discogs_artist,
        r.discogs_title,
        r.discogs_genre,
        r.discogs_style,
        r.discogs_label,
        r.discogs_catno,
        r.discogs_format,
        r.discogs_country,
        r.discogs_year,
        r.release_id,
        r.mb_artist,
        r.mb_title,
        r.mb_year,
        r.total_tracks,
        r.barcode,
        r.is_linked_to_musicbrainz,
        100.0   AS match_score,
        'exact' AS match_type
    FROM discogs_mb_raw_join r
    JOIN discogs_mb_best_per_discogs b
      ON r.discogs_id  = b.discogs_id
     AND r.release_id  = b.best_release_id
""")

n_final = con.execute(
    "SELECT COUNT(*) FROM discogs_mb_exact_matches"
).fetchone()[0]
elapsed = time.time() - start
print(f"✅ discogs_mb_exact_matches: {n_final:,} rows in {elapsed:.0f}s")

# ── Drop temp tables to free disk space ─────────────────────────
print("\nCleaning up temp tables ...")
con.execute("DROP TABLE IF EXISTS discogs_mb_raw_join")
con.execute("DROP TABLE IF EXISTS discogs_mb_best_per_discogs")
print("✅ Temp tables dropped")

# ── Final report ─────────────────────────────────────────────────
print("\n── Match breakdown ──")
print(con.execute("""
    SELECT
        COUNT(*)                                AS total_matches,
        COUNT(DISTINCT discogs_id)              AS unique_discogs,
        COUNT(DISTINCT release_id)              AS unique_mb_releases,
        COUNT(CASE WHEN is_linked_to_musicbrainz
                        = TRUE THEN 1 END)      AS also_in_cds,
        COUNT(CASE WHEN discogs_genre IS NOT NULL
                   THEN 1 END)                  AS has_genre,
        COUNT(CASE WHEN discogs_style IS NOT NULL
                   THEN 1 END)                  AS has_style,
        COUNT(CASE WHEN discogs_country IS NOT NULL
                   THEN 1 END)                  AS has_country
    FROM discogs_mb_exact_matches
""").fetchdf().to_string())

print("\n── Sample matches ──")
print(con.execute("""
    SELECT
        discogs_artist, mb_artist,
        discogs_title,  mb_title,
        discogs_genre,  discogs_style,
        discogs_country, discogs_year,
        release_id
    FROM discogs_mb_exact_matches
    WHERE discogs_genre IS NOT NULL
    ORDER BY release_id
    LIMIT 10
""").fetchdf().to_string(index=False))

con.close()
print("\n✅ Done — connection closed cleanly")