import os
import re
import psycopg2
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters from environment variables
DB_PARAMS = {
    'dbname': os.getenv('POSTGRES_DB'),
    'user': os.getenv('POSTGRES_USER'),
    'password': os.getenv('POSTGRES_PASSWORD'),
    'host': os.getenv('POSTGRES_HOST'),
    'port': os.getenv('POSTGRES_PORT')
}

def connect_to_db():
    return psycopg2.connect(**DB_PARAMS)

def ensure_schema_exists():
    conn = connect_to_db()
    conn.autocommit = True  # Important for schema creation
    cur = conn.cursor()
    
    try:
        # Create schema and table if they don't exist
        with open('init.sql', 'r') as file:
            init_sql = file.read()
            cur.execute(init_sql)
        print("Schema and table initialized successfully")
    except Exception as e:
        print(f"Error initializing schema: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def get_file_times(file_path):
    stats = os.stat(file_path)
    created_at = datetime.fromtimestamp(stats.st_ctime).astimezone(timezone.utc)
    modified_at = datetime.fromtimestamp(stats.st_mtime).astimezone(timezone.utc)
    return created_at, modified_at

def extract_title(content, file_path):
    header_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if header_match:
        return header_match.group(1).strip()
    return Path(file_path).stem

def sync_notes(obsidian_path):
    conn = connect_to_db()
    cur = conn.cursor()
    
    try:
        # Walk through the Obsidian vault directory
        for root, _, files in os.walk(obsidian_path):
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    relative_path = str(Path(file_path).relative_to(obsidian_path))
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        title = extract_title(content, file_path)
                        created_at, modified_at = get_file_times(file_path)
                        
                        cur.execute("""
                            INSERT INTO local.notes (file_path, title, content, file_created_at, file_modified_at, sync_modified_at)
                            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (file_path) DO UPDATE 
                            SET title = EXCLUDED.title,
                                content = EXCLUDED.content,
                                file_modified_at = EXCLUDED.file_modified_at,
                                sync_modified_at = CURRENT_TIMESTAMP
                        """, (relative_path, title, content, created_at, modified_at))
                        
                        conn.commit()  # Commit after each file
                        print(f"Synced: {relative_path} (Title: {title})")
                    except Exception as e:
                        conn.rollback()  # Rollback on error
                        print(f"Error processing {file_path}: {e}")
                        continue
    finally:
        cur.close()
        conn.close()

def main():
    obsidian_path = os.getenv('OBSIDIAN_PATH')
    if not obsidian_path:
        print("Error: OBSIDIAN_PATH not set in environment variables")
        return
    
    if not os.path.exists(obsidian_path):
        print(f"Error: Path {obsidian_path} does not exist")
        return
    
    print("Ensuring schema exists...")
    ensure_schema_exists()
    
    print("Starting sync...")
    sync_notes(obsidian_path)
    print("Sync completed!")

if __name__ == "__main__":
    main()
