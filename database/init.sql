-- 数据库初始化脚本
-- 创建必要的扩展和初始数据

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 创建中文全文搜索配置（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'chinese') THEN
        CREATE TEXT SEARCH CONFIGURATION chinese (
            COPY = english
        );
        -- 简化的中文全文搜索配置
        ALTER TEXT SEARCH CONFIGURATION chinese
        ALTER MAPPING FOR asciiword, asciihword, hword_asciipart, word, hword, hword_part
        WITH simple;
    END IF;
END $$;

-- =============================================
-- 基础表结构
-- =============================================

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    full_name VARCHAR(100),
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    preferences TEXT,
    travel_history TEXT,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 目的地表
CREATE TABLE IF NOT EXISTS destinations (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    country VARCHAR(50) NOT NULL,
    city VARCHAR(50) NOT NULL,
    region VARCHAR(50),
    latitude DECIMAL(10, 6) NOT NULL,
    longitude DECIMAL(10, 6) NOT NULL,
    description TEXT,
    highlights TEXT,
    best_time_to_visit VARCHAR(100),
    popularity_score DECIMAL(3, 1),
    safety_score DECIMAL(3, 1),
    cost_level VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(name, country)
);

-- 景点表
CREATE TABLE IF NOT EXISTS attractions (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    address VARCHAR(255),
    latitude DECIMAL(10, 6),
    longitude DECIMAL(10, 6),
    opening_hours TEXT,
    ticket_price DECIMAL(10, 2),
    currency VARCHAR(10),
    rating DECIMAL(3, 1),
    review_count INTEGER,
    features TEXT,
    accessibility TEXT,
    contact_info TEXT,
    images TEXT,
    website VARCHAR(255),
    destination_id BIGINT REFERENCES destinations(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(name, destination_id)
);

-- 餐厅表
CREATE TABLE IF NOT EXISTS restaurants (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    cuisine_type VARCHAR(50) NOT NULL,
    description TEXT,
    address VARCHAR(255),
    latitude DECIMAL(10, 6),
    longitude DECIMAL(10, 6),
    opening_hours TEXT,
    price_range VARCHAR(50),
    rating DECIMAL(3, 1),
    review_count INTEGER,
    features TEXT,
    contact_info TEXT,
    menu_highlights TEXT,
    images TEXT,
    website VARCHAR(255),
    destination_id BIGINT REFERENCES destinations(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(name, destination_id)
);

-- 活动类型表
CREATE TABLE IF NOT EXISTS activity_types (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    category VARCHAR(50),
    duration_range TEXT,
    difficulty_level VARCHAR(20),
    age_restriction TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =============================================
-- 行程相关表
-- =============================================

-- 1. trip 行程主表
-- 负责人：人员1（创建行程-基础入口与地点添加）
-- 功能：创建行程、行程名称/天数/日期/备注/成员
-- =============================================
CREATE TABLE IF NOT EXISTS trip (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    days INT NOT NULL DEFAULT 1,
    start_date DATE,
    end_date DATE,
    remark TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trip_user_id ON trip(user_id);
CREATE INDEX IF NOT EXISTS idx_trip_created_at ON trip(created_at);


-- =============================================
-- 2. trip_day 行程天表
-- 负责人：人员1（创建行程-基础入口与地点添加）
-- 功能：天数切换、日期顺承、修改日期天数
-- =============================================
CREATE TABLE IF NOT EXISTS trip_day (
    id BIGSERIAL PRIMARY KEY,
    trip_id BIGINT NOT NULL REFERENCES trip(id) ON DELETE CASCADE,
    day_index INT NOT NULL,
    date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(trip_id, day_index)
);

CREATE INDEX IF NOT EXISTS idx_trip_day_trip_id ON trip_day(trip_id);


-- =============================================
-- 3. trip_item 行程内地点/活动/交通项
-- 负责人：人员1（创建行程-基础入口与地点添加）
-- 功能：添加地点/活动/交通、顺序调整、编辑路线、交通方式/时间
-- =============================================
CREATE TABLE IF NOT EXISTS trip_item (
    id BIGSERIAL PRIMARY KEY,
    trip_day_id BIGINT NOT NULL REFERENCES trip_day(id) ON DELETE CASCADE,
    item_type VARCHAR(20) NOT NULL, -- attraction/restaurant/activity/transport
    related_type VARCHAR(20), -- 关联类型：attractions/restaurants/destinations
    related_id BIGINT, -- 关联ID：对应attractions.id等
    name VARCHAR(100) NOT NULL, -- 冗余字段，方便快速显示
    order_index INT NOT NULL,
    start_time TIME,
    end_time TIME,
    transport_type VARCHAR(20), -- walk/bike/drive/bus
    transport_duration INT, -- 交通时长（分钟）
    remark TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trip_item_trip_day_id ON trip_item(trip_day_id);
CREATE INDEX IF NOT EXISTS idx_trip_item_order ON trip_item(trip_day_id, order_index);


-- =============================================
-- 4. favorite 收藏表
-- 负责人：人员5（行程计划-行程编辑+个人中心）
-- 功能：收藏地点、已收藏地点、批量收藏
-- =============================================
CREATE TABLE IF NOT EXISTS favorite (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    related_type VARCHAR(20) NOT NULL, -- attractions/restaurants/destinations
    related_id BIGINT NOT NULL,
    remark TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, related_type, related_id)
);

CREATE INDEX IF NOT EXISTS idx_favorite_user_id ON favorite(user_id);


-- =============================================
-- 5. checkin 点亮/打卡表
-- 负责人：人员5（行程计划-行程编辑+个人中心）
-- 功能：点亮地点、收藏/点亮总览
-- =============================================
CREATE TABLE IF NOT EXISTS checkin (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    related_type VARCHAR(20) NOT NULL, -- attractions/restaurants/destinations
    related_id BIGINT NOT NULL,
    mood VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_checkin_user_id ON checkin(user_id);
CREATE INDEX IF NOT EXISTS idx_checkin_created_at ON checkin(created_at);


-- =============================================
-- 6. footprint 用户足迹表
-- 负责人：人员5（行程计划-行程编辑+个人中心）
-- 功能：添加足迹、总览国家/城市/照片/心情、个人行程地图
-- =============================================
CREATE TABLE IF NOT EXISTS footprint (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    country VARCHAR(50) NOT NULL,
    city VARCHAR(50) NOT NULL,
    record_date DATE NOT NULL,
    mood VARCHAR(50),
    remark TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_footprint_user_id ON footprint(user_id);
CREATE INDEX IF NOT EXISTS idx_footprint_date ON footprint(record_date);


-- =============================================
-- 7. photo 图片表
-- 负责人：人员5（行程计划-行程编辑+个人中心）
-- 功能：添加图片、地点照片、图片空间
-- =============================================
CREATE TABLE IF NOT EXISTS photo (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    related_type VARCHAR(20) NOT NULL, -- trip/trip_item/checkin/footprint
    related_id BIGINT NOT NULL,
    photo_url VARCHAR(255) NOT NULL,
    remark TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_photo_user_id ON photo(user_id);
CREATE INDEX IF NOT EXISTS idx_photo_related ON photo(related_type, related_id);


-- =============================================
-- 8. topic 专题表
-- 负责人：人员4（行程计划-专题推荐与行程总览）
-- 功能：精选专题、搜索专题、切换区域
-- =============================================
CREATE TABLE IF NOT EXISTS topic (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    intro TEXT,
    cover_url VARCHAR(255),
    region VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_topic_region ON topic(region);
CREATE INDEX IF NOT EXISTS idx_topic_search ON topic USING gin(to_tsvector('chinese', name || ' ' || intro));


-- =============================================
-- 9. topic_place 专题地点表
-- 负责人：人员4（行程计划-专题推荐与行程总览）
-- 功能：专题地点地图模式、划重点、批量收藏
-- =============================================
CREATE TABLE IF NOT EXISTS topic_place (
    id BIGSERIAL PRIMARY KEY,
    topic_id BIGINT NOT NULL REFERENCES topic(id) ON DELETE CASCADE,
    related_type VARCHAR(20) NOT NULL, -- attractions/restaurants/destinations
    related_id BIGINT NOT NULL,
    is_key_point BOOLEAN NOT NULL DEFAULT FALSE,
    highlight_info TEXT,
    order_index INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_topic_place_topic_id ON topic_place(topic_id);
CREATE INDEX IF NOT EXISTS idx_topic_place_order ON topic_place(topic_id, order_index);


-- =============================================
-- 10. ai_task AI任务表
-- 负责人：人员3（创建行程-路线优化与智能创建）
-- 功能：一键规划路线、文本/截图识别、智能导入
-- =============================================
CREATE TABLE IF NOT EXISTS ai_task (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_type VARCHAR(30) NOT NULL, -- text_ocr/screenshot_ocr/plan_route/import_places
    input_content TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending/processing/completed/failed
    output_trip_id BIGINT REFERENCES trip(id) ON DELETE SET NULL,
    error_msg TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_task_user_id ON ai_task(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_task_status ON ai_task(status);

-- =============================================
-- 索引创建
-- =============================================

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_destinations_name ON destinations(name);
CREATE INDEX IF NOT EXISTS idx_destinations_country ON destinations(country);
CREATE INDEX IF NOT EXISTS idx_destinations_popularity ON destinations(popularity_score);

CREATE INDEX IF NOT EXISTS idx_attractions_destination_id ON attractions(destination_id);
CREATE INDEX IF NOT EXISTS idx_attractions_category ON attractions(category);
CREATE INDEX IF NOT EXISTS idx_attractions_rating ON attractions(rating);

CREATE INDEX IF NOT EXISTS idx_restaurants_destination_id ON restaurants(destination_id);
CREATE INDEX IF NOT EXISTS idx_restaurants_cuisine_type ON restaurants(cuisine_type);
CREATE INDEX IF NOT EXISTS idx_restaurants_rating ON restaurants(rating);

-- 创建全文搜索索引
CREATE INDEX IF NOT EXISTS idx_destinations_search ON destinations USING gin(to_tsvector('chinese', name || ' ' || description));
CREATE INDEX IF NOT EXISTS idx_attractions_search ON attractions USING gin(to_tsvector('chinese', name || ' ' || description));
CREATE INDEX IF NOT EXISTS idx_restaurants_search ON restaurants USING gin(to_tsvector('chinese', name || ' ' || description));

-- =============================================
-- 初始数据插入
-- =============================================

-- 创建初始用户数据
INSERT INTO users (username, email, full_name, hashed_password, is_verified, created_at, updated_at) 
VALUES 
('admin', 'admin@lxai.com', '系统管理员', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8f8f8f8f8f', true, NOW(), NOW()),
('demo_user', 'demo@lxai.com', '演示用户', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8f8f8f8f8f', true, NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

-- 创建初始目的地数据
INSERT INTO destinations (name, country, city, region, latitude, longitude, description, highlights, best_time_to_visit, popularity_score, safety_score, cost_level, created_at, updated_at)
VALUES 
('北京', '中国', '北京', '华北', 39.9042, 116.4074, '中华人民共和国的首都，历史文化名城', '["天安门广场", "故宫", "长城", "颐和园"]', '春季和秋季', 9.5, 9.0, 'medium', NOW(), NOW()),
('上海', '中国', '上海', '华东', 31.2304, 121.4737, '中国最大的经济中心城市', '["外滩", "东方明珠", "豫园", "南京路"]', '春季和秋季', 9.2, 8.8, 'high', NOW(), NOW()),
('广州', '中国', '广州', '华南', 23.1291, 113.2644, '广东省省会，岭南文化中心', '["珠江夜游", "陈家祠", "白云山", "上下九"]', '冬季和春季', 8.8, 8.5, 'medium', NOW(), NOW()),
('深圳', '中国', '深圳', '华南', 22.5431, 114.0579, '中国改革开放的前沿城市', '["世界之窗", "欢乐谷", "大梅沙", "华强北"]', '全年', 8.5, 8.7, 'high', NOW(), NOW()),
('杭州', '中国', '杭州', '华东', 30.2741, 120.1551, '人间天堂，西湖美景', '["西湖", "灵隐寺", "雷峰塔", "千岛湖"]', '春季和秋季', 9.0, 8.9, 'medium', NOW(), NOW())
ON CONFLICT (name, country) DO NOTHING;

-- 创建初始景点数据
INSERT INTO attractions (name, category, description, address, latitude, longitude, opening_hours, ticket_price, currency, rating, review_count, features, accessibility, contact_info, images, website, destination_id, created_at, updated_at)
VALUES 
('天安门广场', '历史建筑', '中华人民共和国的象征', '北京市东城区天安门广场', 39.9042, 116.4074, '{"周一": "全天开放", "周二": "全天开放", "周三": "全天开放", "周四": "全天开放", "周五": "全天开放", "周六": "全天开放", "周日": "全天开放"}', 0, 'CNY', 4.7, 12580, '["免费参观", "历史意义", "拍照圣地"]', '["无障碍通道", "轮椅租赁"]', '{"电话": "010-65132277"}', '["https://example.com/tiananmen1.jpg", "https://example.com/tiananmen2.jpg"]', 'https://www.tiananmen.org.cn', 1, NOW(), NOW()),
('故宫博物院', '博物馆', '明清两代的皇家宫殿', '北京市东城区景山前街4号', 39.9163, 116.3972, '{"周一": "08:30-17:00", "周二": "08:30-17:00", "周三": "08:30-17:00", "周四": "08:30-17:00", "周五": "08:30-17:00", "周六": "08:30-17:00", "周日": "08:30-17:00"}', 60, 'CNY', 4.8, 9876, '["世界文化遗产", "古建筑", "文物展览"]', '["无障碍通道", "语音导览"]', '{"电话": "010-85007421"}', '["https://example.com/gugong1.jpg", "https://example.com/gugong2.jpg"]', 'https://www.dpm.org.cn', 1, NOW(), NOW()),
('外滩', '观光景点', '上海的标志性景观', '上海市黄浦区中山东一路', 31.2397, 121.4994, '{"周一": "全天开放", "周二": "全天开放", "周三": "全天开放", "周四": "全天开放", "周五": "全天开放", "周六": "全天开放", "周日": "全天开放"}', 0, 'CNY', 4.6, 15678, '["免费参观", "夜景美丽", "历史建筑"]', '["无障碍通道"]', '{"电话": "021-63213579"}', '["https://example.com/waitan1.jpg", "https://example.com/waitan2.jpg"]', 'https://www.shanghai.gov.cn', 2, NOW(), NOW()),
('西湖', '自然景观', '人间天堂的美景', '浙江省杭州市西湖区', 30.2741, 120.1551, '{"周一": "全天开放", "周二": "全天开放", "周三": "全天开放", "周四": "全天开放", "周五": "全天开放", "周六": "全天开放", "周日": "全天开放"}', 0, 'CNY', 4.9, 23456, '["免费参观", "自然美景", "文化底蕴"]', '["无障碍通道", "游船服务"]', '{"电话": "0571-87969691"}', '["https://example.com/xihu1.jpg", "https://example.com/xihu2.jpg"]', 'https://www.hangzhou.gov.cn', 5, NOW(), NOW())
ON CONFLICT (name, destination_id) DO NOTHING;

-- 创建初始餐厅数据
INSERT INTO restaurants (name, cuisine_type, description, address, latitude, longitude, opening_hours, price_range, rating, review_count, features, contact_info, menu_highlights, images, website, destination_id, created_at, updated_at)
VALUES 
('全聚德烤鸭店', '北京菜', '百年老字号烤鸭店', '北京市东城区前门大街30号', 39.9042, 116.4074, '{"周一": "11:00-22:00", "周二": "11:00-22:00", "周三": "11:00-22:00", "周四": "11:00-22:00", "周五": "11:00-22:00", "周六": "11:00-22:00", "周日": "11:00-22:00"}', '人均 ¥200-¥300', 4.5, 5678, '["传统老字号", "适合聚餐", "有包间"]', '{"电话": "010-65112418", "地址": "北京市东城区前门大街30号"}', '["北京烤鸭", "炸酱面", "豆汁"]', '["https://example.com/quanjude1.jpg", "https://example.com/quanjude2.jpg"]', 'https://www.quanjude.com.cn', 1, NOW(), NOW()),
('小笼包店', '上海菜', '正宗上海小笼包', '上海市黄浦区南京东路123号', 31.2304, 121.4737, '{"周一": "10:00-22:00", "周二": "10:00-22:00", "周三": "10:00-22:00", "周四": "10:00-22:00", "周五": "10:00-22:00", "周六": "10:00-22:00", "周日": "10:00-22:00"}', '人均 ¥40-¥60', 4.3, 3456, '["传统小吃", "价格实惠", "外卖服务"]', '{"电话": "021-63212345", "地址": "上海市黄浦区南京东路123号"}', '["小笼包", "生煎包", "糖醋排骨"]', '["https://example.com/xiaolongbao1.jpg", "https://example.com/xiaolongbao2.jpg"]', 'https://www.xiaolongbao.com', 2, NOW(), NOW()),
('粤菜馆', '粤菜', '正宗广东菜', '广东省广州市天河区珠江新城', 23.1291, 113.2644, '{"周一": "11:00-23:00", "周二": "11:00-23:00", "周三": "11:00-23:00", "周四": "11:00-23:00", "周五": "11:00-23:00", "周六": "11:00-23:00", "周日": "11:00-23:00"}', '人均 ¥150-¥250', 4.7, 7890, '["正宗粤菜", "环境优雅", "服务周到"]', '{"电话": "020-12345678", "地址": "广东省广州市天河区珠江新城"}', '["白切鸡", "叉烧", "煲仔饭"]', '["https://example.com/yuecai1.jpg", "https://example.com/yuecai2.jpg"]', 'https://www.yuecai.com', 3, NOW(), NOW())
ON CONFLICT (name, destination_id) DO NOTHING;

-- 创建初始活动类型数据
INSERT INTO activity_types (name, description, category, duration_range, difficulty_level, age_restriction, created_at, updated_at)
VALUES 
('观光游览', '参观景点和地标建筑', 'cultural', '{"min": 2, "max": 8}', 'easy', '{"min": 0, "max": 100}', NOW(), NOW()),
('户外运动', '登山、徒步等户外活动', 'outdoor', '{"min": 4, "max": 12}', 'medium', '{"min": 8, "max": 65}', NOW(), NOW()),
('文化体验', '博物馆、艺术馆参观', 'cultural', '{"min": 1, "max": 6}', 'easy', '{"min": 0, "max": 100}', NOW(), NOW()),
('美食体验', '品尝当地特色美食', 'food', '{"min": 1, "max": 3}', 'easy', '{"min": 0, "max": 100}', NOW(), NOW()),
('购物娱乐', '购物和娱乐活动', 'entertainment', '{"min": 2, "max": 6}', 'easy', '{"min": 0, "max": 100}', NOW(), NOW())
ON CONFLICT (name) DO NOTHING;

