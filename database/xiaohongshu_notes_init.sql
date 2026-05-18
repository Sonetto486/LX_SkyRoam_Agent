-- Create xiaohongshu_notes table for storing pre-imported data

CREATE TABLE IF NOT EXISTS xiaohongshu_notes (
    id SERIAL PRIMARY KEY,
    note_id VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(500),
    description TEXT,
    img_urls JSON DEFAULT '[]',
    tag_list JSON DEFAULT '[]',
    liked_count INTEGER DEFAULT 0,
    location VARCHAR(200),
    destination VARCHAR(100) NOT NULL,
    relevance_score FLOAT DEFAULT 0.0,
    url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster queries by destination
CREATE INDEX IF NOT EXISTS idx_xiaohongshu_destination ON xiaohongshu_notes(destination);

-- Create index for relevance score
CREATE INDEX IF NOT EXISTS idx_xiaohongshu_relevance ON xiaohongshu_notes(relevance_score DESC);