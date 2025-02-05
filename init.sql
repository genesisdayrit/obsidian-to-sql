CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE SCHEMA IF NOT EXISTS local;
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
CREATE INDEX IF NOT EXISTS idx_file_path ON local.notes(file_path);
CREATE INDEX IF NOT EXISTS idx_title ON local.notes(title);
CREATE INDEX IF NOT EXISTS idx_path_metadata ON local.notes USING gin (path_metadata);
CREATE INDEX IF NOT EXISTS idx_properties ON local.notes USING gin (properties);
