import os
import re
import psycopg2
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters from environment variables
DB_PARAMS = {
    'dbname': os.getenv('POSTGRES_DB'),
    'user': os.getenv('POSTGRES_USER'),
    'password': os.getenv('POSTGRES_PASSWORD'),
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432')
}

def connect_to_db():
    """Create and return a new database connection."""
    return psycopg2.connect(**DB_PARAMS)

def get_headers(content):
    """
    Returns a list of tuples for each Markdown header found in the content.
    Each tuple contains (header_start_position, header_text).
    """
    headers = []
    header_pattern = re.compile(r'^(#{1,6})\s*(.+)$', re.MULTILINE)
    for match in header_pattern.finditer(content):
        headers.append((match.start(), match.group(2).strip()))
    return headers

def get_section_for_pos(headers, pos):
    """
    Given a list of headers (with their positions) and a position,
    returns the header text of the header immediately preceding that position.
    Defaults to "No Section" if none is found.
    """
    section = "No Section"
    for h_start, h_text in headers:
        if h_start <= pos:
            section = h_text
        else:
            break
    return section

def extract_relationships(content):
    """
    Extract relationships from the note content.
    
    Returns a list of dictionaries with:
      - target_title: cleaned title of the related note.
      - context: snippet (50 characters before and after the link).
      - section: the Markdown header above the link (or "No Section").
      - match_start: position of the link (for internal reference)
    """
    relationships = []
    headers = get_headers(content)
    pattern = re.compile(r'\[\[([^\]]+)\]\]')
    
    for match in pattern.finditer(content):
        raw_link = match.group(1)
        # Remove alias (after '|') and section specifier (after '#')
        cleaned = raw_link.split('|')[0].split('#')[0].strip()
        if not cleaned:
            continue

        # Capture 50 characters before and after the link for context
        start_context = max(0, match.start() - 50)
        end_context = min(len(content), match.end() + 50)
        context_snippet = content[start_context:end_context].replace('\n', ' ').strip()
        
        # Determine section based on nearest preceding header
        section = get_section_for_pos(headers, match.start())
        
        relationships.append({
            'target_title': cleaned,
            'context': context_snippet,
            'section': section,
            'match_start': match.start()
        })
    return relationships

def lookup_note_id(cur, column, value):
    """
    Look up a note in local.notes by a given column (e.g., 'title'),
    using a case-insensitive match. Returns the note's UUID if found.
    """
    query = f"SELECT id FROM local.notes WHERE LOWER({column}) = LOWER(%s) LIMIT 1"
    cur.execute(query, (value,))
    result = cur.fetchone()
    return result[0] if result else None

def get_note_by_title(cur, note_title):
    """
    Look up a note in local.notes by title (case-insensitive) and return the note's id and content.
    """
    query = "SELECT id, content FROM local.notes WHERE LOWER(title) = LOWER(%s) LIMIT 1"
    cur.execute(query, (note_title,))
    result = cur.fetchone()
    return result if result else None

def insert_relationship(cur, start_node_id, end_node_id, relationship_type, context, section):
    """
    Inserts a relationship record into local.relationships.
    Assumes the relationship id is a UUID generated by the database.
    """
    insert_sql = """
    INSERT INTO local.relationships (
        start_node_id, end_node_id, relationship_type, context, section, created_at, updated_at
    ) VALUES (
        %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    )
    """
    cur.execute(insert_sql, (start_node_id, end_node_id, relationship_type, context, section))

def main():
    # Prompt for the note title (as stored in local.notes)
    note_title = input("Enter the note title (as stored in local.notes): ").strip()
    
    # Connect to the database
    conn = connect_to_db()
    cur = conn.cursor()
    
    try:
        # Look up the source note by title
        source_note = get_note_by_title(cur, note_title)
        if not source_note:
            print(f"Source note with title '{note_title}' not found in local.notes. Please sync the note first.")
            return
        
        start_node_id, content = source_note
        
        # Ensure we have content to process
        if not content:
            print(f"No content found for note '{note_title}'.")
            return

        # Extract relationships from the note content
        rels = extract_relationships(content)
        if not rels:
            print("No relationships found in this note.")
            return
        
        inserted = 0
        for rel in rels:
            target_title = rel['target_title']
            context = rel['context']
            section = rel['section']
            
            # Look up target note by title (case-insensitive)
            end_node_id = lookup_note_id(cur, 'title', target_title)
            if not end_node_id:
                print(f"Warning: Target note '{target_title}' not found in local.notes. Skipping relationship insertion.")
                continue
            
            # Insert the relationship with default relationship_type "default"
            insert_relationship(cur, start_node_id, end_node_id, "default", context, section)
            inserted += 1
        
        conn.commit()
        print(f"Inserted {inserted} relationships into local.relationships.")
        
    except Exception as e:
        conn.rollback()
        print(f"Error processing relationships: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()

