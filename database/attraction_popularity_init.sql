-- Attraction Popularity Table
-- Stores popularity ranking data from third-party platforms

-- Create popularity table
CREATE TABLE IF NOT EXISTS attraction_popularity (
    id SERIAL PRIMARY KEY,
    attraction_id INTEGER REFERENCES poi_attractions(id) ON DELETE CASCADE,
    name_zh VARCHAR(200) NOT NULL,
    city_zh VARCHAR(100) NOT NULL,
    popularity_rank INTEGER DEFAULT 9999,
    popularity_score FLOAT DEFAULT 0.0,
    source VARCHAR(50) DEFAULT 'manual',
    monthly_visitors INTEGER DEFAULT 0,
    tags VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create unique index
CREATE UNIQUE INDEX IF NOT EXISTS idx_attraction_popularity_unique
ON attraction_popularity(city_zh, name_zh);

-- Create city index
CREATE INDEX IF NOT EXISTS idx_attraction_popularity_city
ON attraction_popularity(city_zh);

-- Create rank index
CREATE INDEX IF NOT EXISTS idx_attraction_popularity_rank
ON attraction_popularity(popularity_rank ASC);

-- Create score index
CREATE INDEX IF NOT EXISTS idx_attraction_popularity_score
ON attraction_popularity(popularity_score DESC);
