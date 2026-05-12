-- This is English version,because of UTF-8 encoding issues

-- RAG Vector Database Init Script
-- PostgreSQL + pgvector

-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create main table for travel notes
CREATE TABLE IF NOT EXISTS xhs_notes (
    id SERIAL PRIMARY KEY,
    destination VARCHAR(100) NOT NULL,
    transport_info TEXT,
    accommodation_info TEXT,
    must_visit_spots TEXT,
    food_recommendations TEXT,
    practical_tips TEXT,
    travel_feelings TEXT,
    source_type VARCHAR(50) DEFAULT 'excel',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create chunks table with vector column
CREATE TABLE IF NOT EXISTS xhs_note_chunks (
    id SERIAL PRIMARY KEY,
    note_id INTEGER NOT NULL REFERENCES xhs_notes(id) ON DELETE CASCADE,
    chunk_type VARCHAR(50),
    chunk_text TEXT NOT NULL,
    embedding vector(1024),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Create HNSW index for fast similarity search
CREATE INDEX IF NOT EXISTS xhs_note_chunks_embedding_idx
ON xhs_note_chunks USING hnsw (embedding vector_cosine_ops);