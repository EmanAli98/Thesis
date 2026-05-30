import duckdb

# Connect to the persistent database file in your processed folder
# Script is in 'src/', so we go up one level to find 'data_processed'
db_path = '../data_processed/thesis.duckdb'
con = duckdb.connect(db_path)

print(f"Connected to {db_path}...")

# --- 1. INGEST ARTIST (19 Columns based on your Jupyter check) ---
print("Ingesting 'artist' table...")
con.execute("""
    CREATE OR REPLACE TABLE mb_artist AS 
    SELECT * FROM read_csv('../data_raw/musicbrainz/mbdump/mbdump/artist', 
    header=False, sep='\t', nullstr='\\N', quote='',
    columns={
        'id': 'INTEGER', 'gid': 'VARCHAR', 'name': 'VARCHAR', 'sort_name': 'VARCHAR',
        'begin_date_year': 'INTEGER', 'begin_date_month': 'INTEGER', 'begin_date_day': 'INTEGER',
        'end_date_year': 'INTEGER', 'end_date_month': 'INTEGER', 'end_date_day': 'INTEGER',
        'type': 'INTEGER', 'area': 'INTEGER', 'gender': 'INTEGER', 'comment': 'VARCHAR',
        'edits_pending': 'INTEGER', 'last_updated': 'TIMESTAMP', 'ended': 'BOOLEAN',
        'col18': 'VARCHAR', 'col19': 'VARCHAR' -- Placeholders for the extra columns found
    })
""")

# --- 2. INGEST ARTIST_CREDIT_NAME (5 Columns) ---
print("Ingesting 'artist_credit_name'...")
con.execute("""
    CREATE OR REPLACE TABLE mb_artist_credit_name AS 
    SELECT * FROM read_csv('../data_raw/musicbrainz/mbdump/mbdump/artist_credit_name', 
    header=False, sep='\t', nullstr='\\N', quote='',
    columns={
        'artist_credit': 'INTEGER', 'position': 'INTEGER', 
        'artist': 'INTEGER', 'name': 'VARCHAR', 'join_phrase': 'VARCHAR'
    })
""")

# --- 3. INGEST MEDIUM (9 Columns) ---
print("Ingesting 'medium' table...")
con.execute("""
    CREATE OR REPLACE TABLE mb_medium AS 
    SELECT * FROM read_csv('../data_raw/musicbrainz/mbdump/mbdump/medium', 
    header=False, sep='\t', nullstr='\\N', quote='',
    columns={
        'id': 'INTEGER', 'release': 'INTEGER', 'position': 'INTEGER', 
        'format': 'INTEGER', 'name': 'VARCHAR', 'edits_pending': 'INTEGER', 
        'last_updated': 'TIMESTAMP', 'track_count': 'INTEGER', 'release_group': 'INTEGER'
    })
""")

# --- 4. INGEST ARTIST_CREDIT (Standard 5 columns) ---
# We assume 5 columns here as it's the standard companion to artist_credit_name
print("Ingesting 'artist_credit'...")
con.execute("""
    CREATE OR REPLACE TABLE mb_artist_credit AS 
    SELECT * FROM read_csv('../data_raw/musicbrainz/mbdump/mbdump/artist_credit', 
    header=False, sep='\t', nullstr='\\N', quote='',
    columns={
        'id': 'INTEGER', 'name': 'VARCHAR', 'artist_count': 'INTEGER', 
        'ref_count': 'INTEGER', 'created': 'TIMESTAMP'
    })
""")

# --- 5. INGEST CLEAN CDS ---
print("Ingesting 'cds_clean.tsv'...")
con.execute("""
    CREATE OR REPLACE TABLE cds_clean AS 
    SELECT * FROM read_csv_auto('../data_raw/hpi_cd/cds_clean.tsv', header=True, sep='\t')
""")

print("✅ All tables ingested successfully without sniffing errors!")
con.close()