-- 预生成方案系统数据库表创建脚本
-- 执行此脚本创建 pre_generated_plans 和 hot_destinations 表

-- 创建预生成方案表
CREATE TABLE IF NOT EXISTS pre_generated_plans (
    id SERIAL PRIMARY KEY,

    -- 目的地信息
    destination_id INTEGER,
    destination_name VARCHAR(100) NOT NULL,

    -- 预生成方案核心数据
    plan_template JSONB NOT NULL,

    -- 匹配维度
    duration_days INTEGER NOT NULL,
    budget_level VARCHAR(20) NOT NULL,
    travel_preferences JSONB,
    age_groups JSONB,
    food_preferences JSONB,
    transportation_mode VARCHAR(50),

    -- 元数据
    popularity_score FLOAT DEFAULT 0.0,
    generation_version VARCHAR(20),
    data_sources JSONB,

    -- 状态管理
    status VARCHAR(20) DEFAULT 'active',
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,

    -- 统计信息
    match_count INTEGER DEFAULT 0,
    usage_count INTEGER DEFAULT 0,
    avg_rating FLOAT,

    -- 基础字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_pre_plans_destination ON pre_generated_plans(destination_name);
CREATE INDEX IF NOT EXISTS idx_pre_plans_duration ON pre_generated_plans(duration_days);
CREATE INDEX IF NOT EXISTS idx_pre_plans_budget ON pre_generated_plans(budget_level);
CREATE INDEX IF NOT EXISTS idx_pre_plans_status ON pre_generated_plans(status);
CREATE INDEX IF NOT EXISTS idx_pre_plans_expires ON pre_generated_plans(expires_at);

-- 创建热门城市表
CREATE TABLE IF NOT EXISTS hot_destinations (
    id SERIAL PRIMARY KEY,

    -- 基本信息
    city_name VARCHAR(100) NOT NULL UNIQUE,
    province VARCHAR(50),
    region VARCHAR(50),

    -- 热度指标
    popularity_score FLOAT DEFAULT 0.0,
    monthly_visitors INTEGER,
    search_volume INTEGER,

    -- 配置
    priority INTEGER DEFAULT 100,
    is_enabled BOOLEAN DEFAULT TRUE,

    -- 预生成状态
    pre_generated_count INTEGER DEFAULT 0,
    last_pre_generated_at TIMESTAMP,

    -- 城市坐标
    latitude FLOAT,
    longitude FLOAT,

    -- 城市特色标签
    tags VARCHAR(200),

    -- 基础字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_hot_dest_city ON hot_destinations(city_name);
CREATE INDEX IF NOT EXISTS idx_hot_dest_priority ON hot_destinations(priority);
CREATE INDEX IF NOT EXISTS idx_hot_dest_enabled ON hot_destinations(is_enabled);

-- 添加注释
COMMENT ON TABLE pre_generated_plans IS '预生成行程方案表，存储热门城市的预生成方案模板';
COMMENT ON TABLE hot_destinations IS '热门城市表，管理国内前100热门旅游城市';

COMMENT ON COLUMN pre_generated_plans.plan_template IS '完整的方案模板数据（JSON格式，不含具体日期）';
COMMENT ON COLUMN pre_generated_plans.duration_days IS '行程天数，用于匹配用户需求';
COMMENT ON COLUMN pre_generated_plans.budget_level IS '预算等级：economy(经济型), comfortable(舒适型), luxury(豪华型)';
COMMENT ON COLUMN pre_generated_plans.status IS '方案状态：active(活跃), deprecated(过期), updating(更新中)';
COMMENT ON COLUMN pre_generated_plans.expires_at IS '方案过期时间，默认30天';

COMMENT ON COLUMN hot_destinations.priority IS '预生成优先级，数值越小优先级越高';
COMMENT ON COLUMN hot_destinations.pre_generated_count IS '已预生成的方案数量';