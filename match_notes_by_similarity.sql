-- Function: match_notes_by_similarity
-- Description: This function retrieves relevant note sections based on a similarity search
-- using a vector embedding and allows optional filtering by folder path.

CREATE OR REPLACE FUNCTION match_notes_by_similarity(
    query_embedding VECTOR(1536),      -- Input: The embedding vector generated from the user's question
    match_threshold FLOAT,             -- Input: Minimum similarity threshold (only sections with similarity above this)
    match_count INT,                   -- Input: Maximum number of results to return
    folder_path TEXT DEFAULT NULL      -- Input: Optional folder path to filter results
) 
RETURNS TABLE (
    section_id UUID,                   -- Output: ID of the matched section
    note_id UUID,                      -- Output: ID of the parent note
    raw_content TEXT,                  -- Output: The matched content
    section_type TEXT,                 -- Output: Whether it's a title or content
    section_order INT,                 -- Output: Order within the note
    note_title TEXT,                   -- Output: Title of the note
    note_path TEXT,                    -- Output: Path of the note
    similarity FLOAT                   -- Output: Similarity score
) 
LANGUAGE SQL AS $$
    SELECT 
        ne.id AS section_id,
        ne.note_id,
        ne.raw_content,
        ne.type AS section_type,
        ne.section_order,
        n.title AS note_title,
        n.file_path AS note_path,
        1 - (ne.embedding <-> query_embedding) AS similarity
    FROM 
        local.note_embeddings ne
    JOIN 
        local.notes n ON ne.note_id = n.id
    WHERE 
        -- Apply similarity threshold
        (1 - (ne.embedding <-> query_embedding)) > match_threshold
        
        -- Apply folder filter if provided
        AND (
            folder_path IS NULL 
            OR 
            n.file_path LIKE (folder_path || '%')
        )
    ORDER BY 
        similarity DESC
    LIMIT 
        LEAST(match_count, 200);
$$;

-- Test function exists
SELECT proname, proargtypes, prosrc 
FROM pg_proc 
WHERE proname = 'match_notes_by_similarity';
