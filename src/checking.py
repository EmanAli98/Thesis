import os

MOJIBAKE_MARKERS = ["Ã", "â€™", "â€œ", "â€", "�"]

def peek_at_file(
    filepath: str,
    delimiter: str = "\t",
    is_musicbrainz: bool = False,
    n_lines: int = 50,
):
    print(f"--- Checking {os.path.basename(filepath)} ---")
    try:
        with open(filepath, "r", encoding="utf-8", errors="strict") as f:
            bad_count = 0
            seen_null = False
            seen_mojibake = False

            first = f.readline().rstrip("\n")
            cols_first = first.split(delimiter)
            expected_cols = len(cols_first)

            print("✅ Successfully read first line.")
            print(f"📊 Column Count (line 1): {expected_cols}")

            # Quick scan next lines for column-count consistency and bad markers
            for i in range(2, n_lines + 1):
                line = f.readline()
                if not line:
                    break
                line = line.rstrip("\n")
                cols = line.split(delimiter)

                if len(cols) != expected_cols:
                    bad_count += 1
                    if bad_count <= 3:
                        print(f"⚠️ Column mismatch at line {i}: got {len(cols)} expected {expected_cols}")

                if "\\N" in cols:
                    seen_null = True

                if any(m in line for m in MOJIBAKE_MARKERS):
                    seen_mojibake = True

            if is_musicbrainz:
                if seen_null:
                    print("⚠️ Found '\\N' (Postgres NULLs) - set nullstr='\\\\N' in DuckDB.")
                else:
                    print("ℹ️ No '\\N' found in first scanned lines (still set nullstr='\\\\N' anyway).")
            else:
                # Show header preview (and whether it contains literal quotes)
                preview = cols_first[:6]
                print(f"Preview of first 6 columns: {preview}")
                if any(c.startswith('"') and c.endswith('"') for c in cols_first):
                    print('⚠️ Header fields are quoted (e.g., "artist"). Consider stripping quotes on read.')

            if seen_mojibake:
                print("⚠️ Possible mojibake detected (Ã / â€™ / �). Text may be corrupted even if UTF-8 decodes.")

            if bad_count == 0:
                print(f"✅ Column count consistent for first {min(n_lines, i)} lines.")
            else:
                print(f"⚠️ Found {bad_count} column-count mismatches in first {n_lines} lines.")

    except UnicodeDecodeError:
        print("❌ ENCODING ERROR: This file is not UTF-8. We need to fix the encoding.")
    except FileNotFoundError:
        print(f"❌ FILE NOT FOUND: Could not find {filepath}. Please check the path.")
    print("\n")

# 1. Sanity check the MusicBrainz Release table (using your exact nested path)

peek_at_file(
    "C:/Users/User/OneDrive/Desktop/Eman_Thesis/data_raw/musicbrainz/mbdump/mbdump/release",
    is_musicbrainz=True,
)
# 2. Sanity check the CDS dataset

peek_at_file(
    "C:/Users/User/OneDrive/Desktop/Eman_Thesis/data_raw/hpi_cd/cds_clean.tsv",
    is_musicbrainz=False,
)
