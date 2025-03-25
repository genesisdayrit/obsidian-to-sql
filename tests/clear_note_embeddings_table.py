import os
import psycopg2
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

def connect_to_db():
    """Create a new database connection using psycopg2."""
    return psycopg2.connect(**DB_PARAMS)

def clean_embeddings():
    """Delete all records from the note_embeddings table."""
    conn = connect_to_db()
    cur = conn.cursor()
    
    try:
        # Get count before deletion
        cur.execute("SELECT COUNT(*) FROM local.note_embeddings")
        count_before = cur.fetchone()[0]
        
        # Delete all records
        cur.execute("DELETE FROM local.note_embeddings")
        
        # Commit the transaction
        conn.commit()
        
        print(f"Successfully deleted {count_before} embedding records from local.note_embeddings")
        print("The table is now empty and ready for fresh data.")
        
    except Exception as e:
        conn.rollback()
        print(f"Error cleaning embeddings table: {e}")
    finally:
        cur.close()
        conn.close()

def main():
    """Main function to clean the embeddings table."""
    print("Preparing to clean note embeddings table...")
    
    # Confirmation prompt
    confirm = input("Are you sure you want to delete ALL embeddings? This cannot be undone. (y/n): ")
    
    if confirm.lower() in ('y', 'yes'):
        clean_embeddings()
    else:
        print("Operation cancelled. No records were deleted.")

if __name__ == "__main__":
    main()
