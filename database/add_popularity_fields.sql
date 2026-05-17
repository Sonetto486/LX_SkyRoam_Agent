-- 为已存在的 poi_attractions 表添加热度字段
-- 如果字段已存在会报错，可以忽略错误继续执行

-- 添加评分字段 (0-5分，来自高德API)
ALTER TABLE poi_attractions ADD COLUMN IF NOT EXISTS rating FLOAT DEFAULT 0.0;

-- 添加热度评分字段 (0-100分)
ALTER TABLE poi_attractions ADD COLUMN IF NOT EXISTS popularity_score FLOAT DEFAULT 0.0;

-- 创建热度索引
CREATE INDEX IF NOT EXISTS poi_attractions_rating_idx ON poi_attractions(rating DESC);
CREATE INDEX IF NOT EXISTS poi_attractions_popularity_idx ON poi_attractions(popularity_score DESC);

-- 添加注释
COMMENT ON COLUMN poi_attractions.rating IS '景点评分 (0-5分，来自高德API)';
COMMENT ON COLUMN poi_attractions.popularity_score IS '热度评分 (0-100分，rating * 20)';