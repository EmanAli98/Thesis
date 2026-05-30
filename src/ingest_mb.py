import duckdb

# 1. Connect to your database (using ../ since the script is inside the src/ folder)
db_path = '../data_processed/thesis.duckdb'
con = duckdb.connect(db_path)
print(f"Connected to {db_path}...")

# 2. Ingest the 14-column Release table safely
print("Importing the MusicBrainz 'release' table...")

con.execute("""
    CREATE OR REPLACE TABLE mb_release AS 
    SELECT * FROM read_csv(
        '../data_raw/musicbrainz/mbdump/mbdump/release',
        header = False,
        sep = '\t',
        nullstr = '\\N',
        quote = '',  -- MB uses raw tabs, no quotes around strings
        columns = {
            'id': 'INTEGER',
            'gid': 'VARCHAR',  -- Global ID (UUID)
            'name': 'VARCHAR', -- Release Title
            'artist_credit': 'INTEGER',
            'release_group': 'INTEGER',
            'status': 'INTEGER',
            'packaging': 'INTEGER',
            'language': 'INTEGER',
            'script': 'INTEGER',
            'barcode': 'VARCHAR',
            'comment': 'VARCHAR',
            'edits_pending': 'INTEGER',
            'quality': 'INTEGER',
            'last_updated': 'TIMESTAMP'
        }
    )
""")

print("✅ mb_release table created successfully!")

# 3. Prove that it worked!
print("\n--- First 5 rows of your new mb_release table ---")
print(con.execute("SELECT id, name, barcode, artist_credit FROM mb_release LIMIT 5").fetchdf())
print(con.execute("SELECT COUNT(*) AS n FROM mb_release").fetchdf())
print(con.execute("SELECT COUNT(*) AS null_artist_credit FROM mb_release WHERE artist_credit IS NULL").fetchdf())