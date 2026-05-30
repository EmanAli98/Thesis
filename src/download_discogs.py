"""
01_download_discogs.py
Downloads Discogs releases XML dump with auto-resume.
Run: python src/01_download_discogs.py
"""
import os
import time
import requests

RAW_DIR  = "../data_raw/discogs"
os.makedirs(RAW_DIR, exist_ok=True)

URL      = ("https://data.discogs.com/first?download=data%2F2026%2Fdiscogs_20260401_releases.xml.gz")
OUT_PATH = os.path.join(RAW_DIR, "discogs_20260401_releases.xml.gz")

HEADERS  = {
    "User-Agent": "Mozilla/5.0 (compatible; thesis-research/1.0)"
}

MAX_RETRIES = 10   # retry up to 10 times on connection drop
CHUNK_SIZE  = 512 * 1024  # 512 KB chunks (smaller = more stable)

# ── Check if partially downloaded ────────────────────────────────
existing_bytes = os.path.getsize(OUT_PATH) if os.path.exists(OUT_PATH) else 0
if existing_bytes > 0:
    print(f"Found partial download: {existing_bytes / (1024**3):.2f} GB")
    print("Will resume from where it stopped.\n")

# ── Get total file size ───────────────────────────────────────────
print("Checking file size ...")
head = requests.head(URL, headers=HEADERS, timeout=30)
total_bytes = int(head.headers.get("content-length", 0))
total_gb    = total_bytes / (1024**3)
print(f"Total size: {total_gb:.2f} GB\n")

if existing_bytes >= total_bytes and total_bytes > 0:
    print(f"✅ Already fully downloaded: {OUT_PATH}")
    raise SystemExit(0)

# ════════════════════════════════════════════════════════════════
# Download with auto-resume on connection drop
# ════════════════════════════════════════════════════════════════
start      = time.time()
attempt    = 0

while attempt < MAX_RETRIES:
    attempt += 1

    # Check how much we have already
    existing_bytes = os.path.getsize(OUT_PATH) if os.path.exists(OUT_PATH) else 0

    if existing_bytes >= total_bytes and total_bytes > 0:
        break  # fully downloaded

    # Set Range header to resume from current position
    headers = dict(HEADERS)
    if existing_bytes > 0:
        headers["Range"] = f"bytes={existing_bytes}-"
        print(f"Attempt {attempt}: Resuming from "
              f"{existing_bytes / (1024**3):.2f} GB ...")
    else:
        print(f"Attempt {attempt}: Starting download ...")

    try:
        response = requests.get(
            URL,
            headers  = headers,
            stream   = True,
            timeout  = (10, 60)  # (connect timeout, read timeout)
        )

        # 206 = partial content (resume), 200 = full download
        if response.status_code not in (200, 206):
            print(f"  ❌ HTTP {response.status_code} — stopping.")
            raise SystemExit(1)

        # Open file in append mode if resuming, write mode if fresh
        mode = "ab" if existing_bytes > 0 else "wb"
        downloaded = existing_bytes

        with open(OUT_PATH, mode) as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Progress
                    mb      = downloaded / (1024**2)
                    total_mb = total_bytes / (1024**2) if total_bytes else 0
                    elapsed = time.time() - start
                    speed   = (downloaded - existing_bytes) / (1024**2) / elapsed \
                              if elapsed > 0 else 0
                    pct     = (downloaded / total_bytes * 100) \
                              if total_bytes > 0 else 0
                    eta     = ((total_mb - mb) / speed / 60) \
                              if speed > 0 else 0
                    print(
                        f"  {pct:5.1f}%  |"
                        f"  {mb:,.0f}/{total_mb:,.0f} MB  |"
                        f"  {speed:.1f} MB/s  |"
                        f"  ETA {eta:.0f} min",
                        end="\r", flush=True
                    )

        print(f"\n  ✅ Attempt {attempt} complete.")
        break  # success — exit retry loop

    except (
        requests.exceptions.ChunkedEncodingError,
        requests.exceptions.ConnectionError,
        requests.exceptions.ReadTimeout
    ) as e:
        current_gb = os.path.getsize(OUT_PATH) / (1024**3) \
                     if os.path.exists(OUT_PATH) else 0
        print(f"\n  ⚠️  Connection dropped at {current_gb:.2f} GB: {e}")
        if attempt < MAX_RETRIES:
            wait = min(30, attempt * 5)
            print(f"  Waiting {wait}s then retrying "
                  f"({attempt}/{MAX_RETRIES}) ...")
            time.sleep(wait)
        else:
            print("  ❌ Max retries reached.")
            raise SystemExit(1)

# ── Final verification ────────────────────────────────────────────
final_size = os.path.getsize(OUT_PATH)
final_gb   = final_size / (1024**3)
elapsed    = time.time() - start

if total_bytes > 0 and final_size < total_bytes:
    missing_mb = (total_bytes - final_size) / (1024**2)
    print(f"\n⚠️  File may be incomplete: {final_gb:.2f} GB "
          f"({missing_mb:.0f} MB missing)")
    print("Re-run this script to resume.")
else:
    print(f"\n✅ Download complete: {final_gb:.2f} GB")
    print(f"📁 Saved: {os.path.abspath(OUT_PATH)}")
    print(f"⏱️  Total time: {elapsed/60:.1f} minutes")