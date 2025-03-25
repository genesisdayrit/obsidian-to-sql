import os
import json
import psycopg2
import tiktoken
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
    """Create a new database connection using psycopg2."""
    return psycopg2.connect(**DB_PARAMS)

def get_random_note():
    """
    Retrieves a single random note from the local.notes table.
    Returns the note as a dictionary.
    """
    conn = connect_to_db()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT 
                id, file_path, title, content, properties, 
                path_metadata, file_created_at, file_modified_at, sync_modified_at
            FROM local.notes
            ORDER BY RANDOM()
            LIMIT 1
        """)
        
        row = cur.fetchone()
        
        if row:
            # Create a dictionary from the row
            note = {
                'id': row[0],
                'file_path': row[1],
                'title': row[2],
                'content': row[3],
                'properties': row[4],
                'path_metadata': row[5],
                'file_created_at': row[6],
                'file_modified_at': row[7],
                'sync_modified_at': row[8]
            }
            
            return note
        else:
            return None
            
    except Exception as e:
        print(f"Error retrieving random note: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def count_tokens(text, model="cl100k_base"):
    """
    Count the number of tokens in a text string using tiktoken.
    
    Args:
        text (str): The text to count tokens for
        model (str): The encoding to use, default is cl100k_base (used by Claude)
    
    Returns:
        int: Number of tokens
    """
    if not text:
        return 0
        
    encoder = tiktoken.get_encoding(model)
    tokens = encoder.encode(text)
    return len(tokens)

def format_note_display(note):
    """Format note for display with key information."""
    if not note:
        return "No notes found in the database."
    
    # Format timestamps for display
    created_at = note['file_created_at'].strftime('%Y-%m-%d %H:%M:%S UTC') if note['file_created_at'] else 'N/A'
    modified_at = note['file_modified_at'].strftime('%Y-%m-%d %H:%M:%S UTC') if note['file_modified_at'] else 'N/A'
    
    # Format path metadata
    path_info = ""
    if note['path_metadata']:
        path_data = note['path_metadata'] if isinstance(note['path_metadata'], dict) else json.loads(note['path_metadata'])
        directories = path_data.get('directories', [])
        if directories:
            path_info = f"Folder: {'/'.join(directories)}"
        else:
            path_info = "Folder: (root)"
    
    # Format properties if they exist
    properties_info = ""
    if note['properties'] and note['properties'] != 'null':
        properties = note['properties'] if isinstance(note['properties'], dict) else json.loads(note['properties'])
        if properties:
            properties_info = "\n\nProperties:\n" + "\n".join([f"- {k}: {v}" for k, v in properties.items()])
    
    # Count tokens
    title_tokens = count_tokens(note['title'])
    content_tokens = count_tokens(note['content'])
    total_tokens = title_tokens + content_tokens
    
    # Prepare a display with truncated content if very long
    content_preview = note['content']
    if len(content_preview) > 500:
        content_preview = content_preview[:500] + "...\n[Content truncated]"
    
    return f"""
Random Note: {note['title']}
{'=' * (13 + len(note['title']))}
ID: {note['id']}
Path: {note['file_path']}
{path_info}
Created: {created_at}
Modified: {modified_at}

Token Counts:
- Title: {title_tokens} tokens
- Content: {content_tokens} tokens
- Total: {total_tokens} tokens

{content_preview}
{properties_info}
"""

def main():
    """Main function to get and display a random note."""
    print("Retrieving a random note...")
    note = get_random_note()
    
    if note:
        formatted_display = format_note_display(note)
        print(formatted_display)
        
        # Print token counts separately as well for easier data collection
        title_tokens = count_tokens(note['title'])
        content_tokens = count_tokens(note['content'])
        total_tokens = title_tokens + content_tokens
        
        print("\nToken Summary:")
        print(f"Title:   {title_tokens:,} tokens")
        print(f"Content: {content_tokens:,} tokens")
        print(f"Total:   {total_tokens:,} tokens")
    else:
        print("No notes were found or there was an error retrieving a note.")

if __name__ == "__main__":
    main()
