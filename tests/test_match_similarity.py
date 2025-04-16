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

# Global tokenizer (make sure this matches your embedding model)
ENCODING_MODEL = "cl100k_base"
tokenizer = tiktoken.get_encoding(ENCODING_MODEL)

def connect_to_db():
    """Create a new database connection using psycopg2."""
    return psycopg2.connect(**DB_PARAMS)

def generate_embedding(text: str) -> List[float]:
    """
    Generate an embedding for the text using OpenAI's API.
    
    Args:
        text (str): The text to generate an embedding for.
        
    Returns:
        list: The embedding vector.
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
    debug: bool = DEBUG
) -> Dict[str, Any]:
    """
    Search notes from local.note_embeddings_test using semantic similarity with adaptive thresholds.
    Both the raw distance and the similarity (1 - distance) scores are returned.
    
    Args:
        query_text (str): The user's natural language query.
        initial_threshold (float): Starting similarity threshold (0-1).
        min_threshold (float): Minimum threshold to try before giving up.
        threshold_step (float): How much to decrease threshold each attempt.
        min_results (int): Minimum number of results to aim for.
        max_results (int): Maximum number of results to return.
        debug (bool): Whether to output detailed debug information.
        
    Returns:
        dict: Results and debug information.
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
    
    # Build the SQL query using the test embeddings table.
    # We compute both the raw distance and the similarity score.
    sql_query = """
    SELECT 
        ne.id AS section_id,
        ne.note_id,
        ne.raw_content,
        ne.type AS section_type,
        ne.section_order,
        (ne.embedding <-> %s::vector(1536)) AS distance,
        1 - (ne.embedding <-> %s::vector(1536)) AS similarity
    FROM 
        local.note_embeddings_test ne
    """
    
    # Build candidate query: fetch top 50 candidates ordered by similarity (i.e. 1 - distance)
    candidates_query = sql_query + """
    ORDER BY 
        1 - (ne.embedding <-> %s::vector(1536)) DESC
    LIMIT 50
    """
    
    # We need to supply the query_embedding three times:
    #   * Once for distance in SELECT,
    #   * Once for similarity in SELECT,
    #   * Once for the ORDER BY clause.
    candidate_params = [query_embedding, query_embedding, query_embedding]
    
    try:
        if debug:
            print("Fetching top 50 candidates for analysis from local.note_embeddings_test...")
        
        cur.execute(candidates_query, candidate_params)
        all_candidates = [dict(row) for row in cur.fetchall()]
        debug_info["total_candidates_checked"] = len(all_candidates)
        
        if debug:
            print(f"Found {len(all_candidates)} candidates")
            if all_candidates:
                print("\nTop 5 candidate scores:")
                for i, cand in enumerate(all_candidates[:5]):
                    print(f"  {i+1}. Similarity: {cand['similarity']:.4f}, Distance: {cand['distance']:.4f}")
        
        # Adaptive thresholding: lower threshold until at least min_results are found.
        current_threshold = initial_threshold
        final_results = []
        
        while current_threshold >= min_threshold:
            debug_info["attempted_thresholds"].append(current_threshold)
            
            if debug:
                print(f"\nTrying threshold: {current_threshold:.2f}")
            
            # Filter candidates based on similarity threshold.
            threshold_results = [r for r in all_candidates if r["similarity"] >= current_threshold]
            
            if debug:
                print(f"  Found {len(threshold_results)} results at this threshold")
            
            if len(threshold_results) >= min_results:
                final_results = threshold_results[:max_results]
                if debug:
                    print(f"  Success! Returning {len(final_results)} results")
                break
            
            current_threshold -= threshold_step
        
        # If no threshold produced enough results, fall back to best available candidates.
        if not final_results and all_candidates:
            if debug:
                print("\nFell back to returning best available results regardless of threshold")
            final_results = all_candidates[:max_results]
        
        return {
            "results": final_results,
            "final_threshold": current_threshold,
            "debug_info": debug_info,
            "all_candidates": all_candidates  # Optionally include all candidates for debug info
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
    Format search results for display, including both similarity and raw distance scores.
    
    Args:
        search_response (dict): The response from adaptive_search_notes().
        show_debug (bool): Whether to include debug information.
        
    Returns:
        str: Formatted results as text.
    """
    results = search_response.get("results", [])
    debug_info = search_response.get("debug_info", {})
    final_threshold = search_response.get("final_threshold", 0)
    
    if not results:
        output = "No matching notes found."
        if show_debug and "error" in search_response:
            output += f"\nError: {search_response['error']}"
        return output
    
    output = "Search Results:\n" + "=" * 50 + "\n\n"
    
    for i, result in enumerate(results, 1):
        similarity_percent = round(result['similarity'] * 100, 1)
        distance = result['distance']
        content = result['raw_content']
        if len(content) > 300:
            content = content[:297] + "..."
        
        output += f"Result #{i} - Similarity: {similarity_percent}% match (Distance: {distance:.4f})\n"
        output += f"Section Type: {result['section_type'].capitalize()} | Section Order: {result['section_order']}\n\n"
        output += f"{content}\n\n"
        output += "-" * 50 + "\n\n"
    
    if show_debug:
        output += f"\nDEBUG INFO:\n{'-' * 40}\n"
        output += f"Query: '{debug_info.get('query', '')}'\n"
        output += f"Final threshold used: {final_threshold:.2f}\n"
        output += f"Thresholds tried: {', '.join([f'{t:.2f}' for t in debug_info.get('attempted_thresholds', [])])}\n"
        output += f"Total candidates analyzed: {debug_info.get('total_candidates_checked', 0)}\n"
    
    return output

def main():
    """Interactive search interface for the test note embeddings."""
    print("Adaptive Test Note Search System (using local.note_embeddings_test)")
    print("=" * 50)
    
    while True:
        query = input("\nEnter your search query (or 'q' to quit): ")
        if query.lower() in ('q', 'quit', 'exit'):
            break
        
        count_input = input("Number of results to show (default: 3): ")
        try:
            max_results = int(count_input) if count_input else 3
        except ValueError:
            max_results = 3
        
        print("\nSearching test note embeddings...")
        search_response = adaptive_search_notes(
            query_text=query,
            initial_threshold=0.8,
            min_threshold=0.3,
            threshold_step=0.1,
            min_results=1,
            max_results=max_results,
            debug=DEBUG
        )
        
        print("\n" + format_search_results(search_response, show_debug=DEBUG))

if __name__ == "__main__":
    main()

