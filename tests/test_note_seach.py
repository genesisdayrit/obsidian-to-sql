import os
import json
import psycopg2
import psycopg2.extras
import tiktoken
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

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

# Debug mode
DEBUG = True

def connect_to_db():
    """Create a new database connection using psycopg2."""
    return psycopg2.connect(**DB_PARAMS)

def generate_embedding(text: str) -> List[float]:
    """
    Generate an embedding for the text using OpenAI's API.
    
    Args:
        text (str): The text to generate an embedding for
        
    Returns:
        list: The embedding vector
    """
    if not text:
        raise ValueError("Cannot generate embedding for empty text")
    
    if DEBUG:
        print(f"Generating embedding for: '{text}'")
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    
    embedding = response.data[0].embedding
    
    if DEBUG:
        print(f"Embedding size: {len(embedding)} dimensions")
        print(f"First 5 values: {embedding[:5]}")
    
    return embedding

def adaptive_search_notes(
    query_text: str, 
    initial_threshold: float = 0.8,
    min_threshold: float = 0.3,
    threshold_step: float = 0.1,
    min_results: int = 1,
    max_results: int = 5,
    folder_path: Optional[str] = None,
    debug: bool = DEBUG
) -> Dict[str, Any]:
    """
    Search notes using semantic similarity with adaptive thresholds.
    Progressively lowers threshold until minimum results are found.
    
    Args:
        query_text (str): The user's natural language query
        initial_threshold (float): Starting similarity threshold (0-1)
        min_threshold (float): Minimum threshold to try before giving up
        threshold_step (float): How much to decrease threshold each attempt
        min_results (int): Minimum number of results to aim for
        max_results (int): Maximum number of results to return
        folder_path (str, optional): Folder path to restrict search
        debug (bool): Whether to output detailed debug information
        
    Returns:
        dict: Results and debug information
    """
    # Generate embedding for the query text
    query_embedding = generate_embedding(query_text)
    
    # Connect to database
    conn = connect_to_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    debug_info = {
        "query": query_text,
        "attempted_thresholds": [],
        "total_candidates_checked": 0,
        "timing": {}
    }
    
    # Create a direct SQL query
    sql_query = """
    SELECT 
        ne.id AS section_id,
        ne.note_id,
        ne.raw_content,
        ne.type AS section_type,
        ne.section_order,
        n.title AS note_title,
        n.file_path AS note_path,
        1 - (ne.embedding <-> %s::vector(1536)) AS similarity
    FROM 
        local.note_embeddings ne
    JOIN 
        local.notes n ON ne.note_id = n.id
    """
    
    # Parameters for the query
    params = [query_embedding]
    
    try:
        # First, get all potential candidates to analyze
        candidates_query = sql_query + """
        ORDER BY 
            1 - (ne.embedding <-> %s::vector(1536)) DESC
        LIMIT 50
        """
        
        candidate_params = params.copy()
        candidate_params.append(query_embedding)
        
        if debug:
            print("Fetching top 50 candidates for analysis...")
        
        cur.execute(candidates_query, candidate_params)
        all_candidates = [dict(row) for row in cur.fetchall()]
        debug_info["total_candidates_checked"] = len(all_candidates)
        
        if debug:
            print(f"Found {len(all_candidates)} candidates")
            if all_candidates:
                print("\nTop 5 candidate similarities:")
                for i, cand in enumerate(all_candidates[:5]):
                    print(f"  {i+1}. {cand['similarity']:.4f}: {cand['note_title']} - {cand['raw_content'][:50]}...")
        
        # Try different thresholds until we get enough results
        current_threshold = initial_threshold
        final_results = []
        
        while current_threshold >= min_threshold:
            debug_info["attempted_thresholds"].append(current_threshold)
            
            if debug:
                print(f"\nTrying threshold: {current_threshold:.2f}")
            
            # Filter candidates by current threshold
            threshold_results = [r for r in all_candidates if r["similarity"] >= current_threshold]
            
            if debug:
                print(f"  Found {len(threshold_results)} results at this threshold")
            
            if len(threshold_results) >= min_results:
                final_results = threshold_results[:max_results]
                if debug:
                    print(f"  Success! Found {len(final_results)} results")
                break
            
            # Lower threshold and try again
            current_threshold -= threshold_step
        
        # If we've tried all thresholds and still don't have enough results
        if not final_results and all_candidates:
            if debug:
                print("\nFell back to returning best available results regardless of threshold")
            final_results = all_candidates[:max_results]
        
        return {
            "results": final_results,
            "final_threshold": current_threshold,
            "debug_info": debug_info
        }
        
    except Exception as e:
        error_msg = f"Error searching notes: {e}"
        print(error_msg)
        return {"results": [], "error": error_msg, "debug_info": debug_info}
    finally:
        cur.close()
        conn.close()

def format_search_results(search_response: Dict[str, Any], show_debug: bool = DEBUG) -> str:
    """
    Format search results for display, including debug info if requested.
    
    Args:
        search_response (dict): The response from adaptive_search_notes()
        show_debug (bool): Whether to include debug information
        
    Returns:
        str: Formatted results as text
    """
    results = search_response.get("results", [])
    debug_info = search_response.get("debug_info", {})
    final_threshold = search_response.get("final_threshold", 0)
    
    if not results:
        output = "No matching notes found."
        if show_debug and "error" in search_response:
            output += f"\nError: {search_response['error']}"
        return output
    
    output = "Search Results:\n" + "="*50 + "\n\n"
    
    for i, result in enumerate(results, 1):
        # Format similarity as percentage
        similarity_percent = round(result['similarity'] * 100, 1)
        
        # Format the content (truncate if too long)
        content = result['raw_content']
        if len(content) > 300:
            content = content[:297] + "..."
        
        # Build the formatted result
        output += f"Result #{i} - {similarity_percent}% match\n"
        output += f"Note: {result['note_title']}\n"
        output += f"Path: {result['note_path']}\n"
        output += f"Type: {result['section_type'].capitalize()}\n\n"
        output += f"{content}\n\n"
        output += "-"*50 + "\n\n"
    
    # Add debug information if requested
    if show_debug:
        output += f"\nDEBUG INFO:\n{'-'*40}\n"
        output += f"Query: '{debug_info.get('query', '')}'\n"
        output += f"Final threshold used: {final_threshold:.2f}\n"
        output += f"Thresholds tried: {', '.join([f'{t:.2f}' for t in debug_info.get('attempted_thresholds', [])])}\n"
        output += f"Total candidates analyzed: {debug_info.get('total_candidates_checked', 0)}\n"
        
        # Show distribution of similarity scores
        if results:
            output += "\nSimilarity distribution of all candidates:\n"
            all_scores = [round(r['similarity'], 2) for r in search_response.get("all_candidates", results)]
            score_ranges = {}
            for score in all_scores:
                range_key = int(score * 10) / 10  # Group by 0.1 intervals
                score_ranges[range_key] = score_ranges.get(range_key, 0) + 1
            
            for score_range in sorted(score_ranges.keys(), reverse=True):
                count = score_ranges[score_range]
                output += f"  {score_range:.1f}-{score_range+0.1:.1f}: {count} results\n"
    
    return output

def main():
    """Interactive search interface with adaptive thresholds."""
    print("Adaptive Note Search System")
    print("==========================")
    
    while True:
        # Get search query
        query = input("\nEnter your search query (or 'q' to quit): ")
        if query.lower() in ('q', 'quit', 'exit'):
            break
        
        # Get optional folder filter
        folder = input("Filter by folder (optional, press Enter to skip): ")
        folder_path = folder if folder else None
        
        # Get result count
        count_input = input("Number of results to show (default: 3): ")
        try:
            max_results = int(count_input) if count_input else 3
        except ValueError:
            max_results = 3
        
        print("\nSearching notes...")
        search_response = adaptive_search_notes(
            query_text=query,
            initial_threshold=0.8,    # Start with high threshold
            min_threshold=0.3,        # Don't go below this threshold
            threshold_step=0.1,       # Lower by 0.1 each attempt
            min_results=1,            # Try to get at least 1 result
            max_results=max_results,  # User-specified max
            folder_path=folder_path,
            debug=DEBUG               # Enable detailed debugging
        )
        
        # Display results
        print("\n" + format_search_results(search_response, show_debug=DEBUG))

if __name__ == "__main__":
    main()
