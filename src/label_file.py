import os
import argparse

def main():
    ap = argparse.ArgumentParser()

    # Default paths relative to THIS file (src/label_file.py)
    here = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.normpath(os.path.join(here, "..", "data_processed", "match_validation_sample_v7.csv"))
    default_db = os.path.normpath(os.path.join(here, "..", "data_processed", "thesis.duckdb"))

    ap.add_argument(
        "--input",
        default=default_input,
        help=f"Path to labeled CSV (default: {default_input})",
    )
    ap.add_argument(
        "--mapping_db",
        default=default_db,
        help=f"Path to thesis.duckdb (default: {default_db})",
    )
    ap.add_argument(
        "--mapping_table",
        default="cds_to_mb_final_mapping_v7",
        help="DuckDB table name for full mapping weights",
    )
    ap.add_argument(
        "--weights_csv",
        default=None,
        help="Optional: CSV with columns match_type,n (if you don't want DuckDB).",
    )

    args = ap.parse_args()

