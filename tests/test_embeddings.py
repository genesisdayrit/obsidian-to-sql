import os
import re
import json
import psycopg2
import tiktoken
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters
DB_PARAMS = {
    'dbname': os.getenv('POSTGRES_DB'),
    'user': os.getenv('POSTGRES_USER'),
    'password': os.getenv('POSTGRES_PASSWORD'),
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432')
}

# OpenAI API Key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# Global tokenizer
ENCODING_MODEL = "cl100k_base"  # Model used by Claude/OpenAI
tokenizer = tiktoken.get_encoding(ENCODING_MODEL)

def connect_to_db():
    """Create a new database connection using psycopg2."""
    return psycopg2.connect(**DB_PARAMS)

def get_random_note():
    """Retrieves a single random note from the local.notes table."""
    conn = connect_to_db()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT 
                id, file_path, title, content
            FROM local.notes
            ORDER BY RANDOM()
            LIMIT 1
        """)
        
        row = cur.fetchone()
        
        if row:
            note = {
                'id': row[0],
                'file_path': row[1],
                'title': row[2],
                'content': row[3]
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

def count_words(text):
    """Count the number of words in a text string."""
    if not text:
        return 0
    # Split by whitespace and count non-empty strings
    return len([word for word in re.split(r'\s+', text) if word])

def count_characters(text):
    """Count the number of characters in a text string."""
    if not text:
        return 0
    return len(text)

def count_tokens(text, tokenizer=tokenizer):
    """Count the number of tokens in a text string using tiktoken."""
    if not text:
        return 0
    tokens = tokenizer.encode(text)
    return len(tokens)

def generate_embedding(text):
    """Generate an embedding for the text using OpenAI's API."""
    if not text:
        return None
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    
    return response.data[0].embedding

def chunk_text_by_tokens(text, target_chunk_size=1000, tokenizer=tokenizer):
    """
    Chunk text based on token count with smart handling of sizes.
    Avoids creating very small chunks at the end.
    
    Args:
        text (str): The text to chunk
        target_chunk_size (int): Target size of each chunk in tokens
        tokenizer: The tokenizer to use
        
    Returns:
        list: A list of text chunks
    """
    if not text:
        return []
    
    # Encode the full text
    tokens = tokenizer.encode(text)
    total_tokens = len(tokens)
    
    # If the text is smaller than the target, return as single chunk
    if total_tokens <= target_chunk_size:
        return [text]
    
    # Determine number of chunks and actual chunk size
    # If we have a small remainder, redistribute tokens more evenly
    n_chunks = (total_tokens + target_chunk_size - 1) // target_chunk_size  # Ceiling division
    
    # Check if the last chunk would be too small (less than 40% of target)
    last_chunk_size = total_tokens % target_chunk_size
    if 0 < last_chunk_size < (target_chunk_size * 0.4):
        # Redistribute to avoid small final chunk
        n_chunks = max(1, total_tokens // target_chunk_size)  # At least 1 chunk
        chunk_size = total_tokens // n_chunks
    else:
        chunk_size = target_chunk_size
    
    chunks = []
    for i in range(0, total_tokens, chunk_size):
        # Get the token span for this chunk
        chunk_tokens = tokens[i:min(i + chunk_size, total_tokens)]
        # Decode back to text
        chunk_text = tokenizer.decode(chunk_tokens)
        chunks.append(chunk_text)
    
    return chunks

def process_title(note):
    """Create embedding for the title and store it."""
    if not note or not note['title']:
        return
    
    title = note['title']
    
    # Calculate counts
    word_count = count_words(title)
    character_count = count_characters(title)
    token_count = count_tokens(title)
    
    # Generate embedding
    embedding = generate_embedding(title)
    
    if not embedding:
        print("Failed to generate title embedding.")
        return
    
    # Store in database
    conn = connect_to_db()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO local.note_embeddings (
                note_id, type, raw_content, embedding, 
                section_order, word_count, character_count, token_count
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            note['id'],
            'title',
            title,
            embedding,
            0,  # section_order (0 for title)
            word_count,
            character_count,
            token_count
        ))
        
        embedding_id = cur.fetchone()[0]
        conn.commit()
        
        print(f"Title Embedding: {embedding_id}")
        print(f"- Title: {title}")
        print(f"- Word Count: {word_count}")
        print(f"- Character Count: {character_count}")
        print(f"- Token Count: {token_count}")
        
    except Exception as e:
        conn.rollback()
        print(f"Error storing title embedding: {e}")
    finally:
        cur.close()
        conn.close()

def process_content(note):
    """Chunk the content, create embeddings, and store them."""
    if not note or not note['content']:
        return
    
    content = note['content']
    
    # Chunk the content
    chunks = chunk_text_by_tokens(content)
    print(f"Content chunked into {len(chunks)} parts")
    
    # Process each chunk
    for i, chunk in enumerate(chunks):
        # Calculate counts
        word_count = count_words(chunk)
        character_count = count_characters(chunk)
        token_count = count_tokens(chunk)
        
        # Generate embedding
        embedding = generate_embedding(chunk)
        
        if not embedding:
            print(f"Failed to generate embedding for chunk {i+1}.")
            continue
        
        # Store in database
        conn = connect_to_db()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                INSERT INTO local.note_embeddings (
                    note_id, type, raw_content, embedding, 
                    section_order, word_count, character_count, token_count
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                note['id'],
                'content',
                chunk,
                embedding,
                i + 1,  # section_order (1-based for content chunks)
                word_count,
                character_count,
                token_count
            ))
            
            embedding_id = cur.fetchone()[0]
            conn.commit()
            
            print(f"Chunk {i+1} Embedding: {embedding_id}")
            print(f"- Section Order: {i+1}")
            print(f"- Word Count: {word_count}")
            print(f"- Character Count: {character_count}")
            print(f"- Token Count: {token_count}")
            print(f"- Preview: {chunk[:50]}...")
            
        except Exception as e:
            conn.rollback()
            print(f"Error storing chunk {i+1} embedding: {e}")
        finally:
            cur.close()
            conn.close()

def main():
    """Main function to process a random note."""
    print("Retrieving a random note...")
    note = get_random_note()
    
    if note:
        print(f"Processing note: {note['title']}")
        print(f"Path: {note['file_path']}")
        print("=" * 50)
        
        print("Processing title...")
        process_title(note)
        print("-" * 50)
        
        print("Processing content...")
        process_content(note)
        print("=" * 50)
        
        print("Note processing complete!")
    else:
        print("No notes were found.")

if __name__ == "__main__":
    main()
