-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schema
CREATE SCHEMA IF NOT EXISTS local;

-- Create notes table
CREATE TABLE IF NOT EXISTS local.notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_path TEXT NOT NULL UNIQUE,
    title TEXT,
    content TEXT,
    properties JSONB, 
    path_metadata JSONB,
    file_created_at TIMESTAMP WITH TIME ZONE,
    file_modified_at TIMESTAMP WITH TIME ZONE,
    sync_modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indices for notes table
CREATE INDEX IF NOT EXISTS idx_file_path ON local.notes(file_path);
CREATE INDEX IF NOT EXISTS idx_title ON local.notes(title);
CREATE INDEX IF NOT EXISTS idx_path_metadata ON local.notes USING gin (path_metadata);
CREATE INDEX IF NOT EXISTS idx_properties ON local.notes USING gin (properties);

-- Create note_embeddings table for embeddings
CREATE TABLE IF NOT EXISTS local.note_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    note_id UUID NOT NULL REFERENCES local.notes(id) ON DELETE CASCADE,
    type TEXT NOT NULL, -- 'title' or 'content' to indicate what kind of content is embedded
    raw_content TEXT NOT NULL,
    embedding VECTOR(1536), -- Using 1536 dimensions for common embedding models
    section_order INT,
    word_count INT,
    character_count INT,
    token_count INT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indices for note_embeddings table
CREATE INDEX IF NOT EXISTS idx_note_embeddings_note_id ON local.note_embeddings(note_id);
CREATE INDEX IF NOT EXISTS idx_note_embeddings_type ON local.note_embeddings(type);

-- Create an HNSW index on the embeddings column for faster similarity searches
CREATE INDEX IF NOT EXISTS idx_note_embeddings_embedding_hnsw 
ON local.note_embeddings USING hnsw (embedding vector_cosine_ops);

-- Function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update the updated_at timestamp on note_embeddings
CREATE TRIGGER update_note_embeddings_updated_at
BEFORE UPDATE ON local.note_embeddings
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();
