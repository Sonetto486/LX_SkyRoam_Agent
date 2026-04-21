-- =====================================================
-- 1. 行程表 (trip) - 合并原trip、trip_action、schedule
-- =====================================================
CREATE TABLE `trip` (
    `trip_id` INT NOT NULL AUTO_INCREMENT COMMENT '行程ID，主键',
    `trip_name` VARCHAR(100) NOT NULL COMMENT '行程名称',
    `days` INT DEFAULT 0 COMMENT '天数',
    `item_count` INT DEFAULT 0 COMMENT '物品数量',
    `member_count` INT DEFAULT 1 COMMENT '成员数量',
    `trip_description` TEXT COMMENT '行程说明',
    `trip_remark` TEXT COMMENT '行程备注',
    `trip_summary` TEXT COMMENT '行程总结',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `user_id` INT NOT NULL COMMENT '所属用户ID',
    
    -- 原trip_action表字段
    `action_type` VARCHAR(50) COMMENT '操作类型（一键优化、修改日期天数、修改日期顺承、顺序调整、编辑路线、添加全行程、添加至行程、创建为旅行程）',
    `action_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    
    -- 原schedule表字段
    `start_date` DATE COMMENT '往返开始时间',
    `end_date` DATE COMMENT '往返结束时间',
    `real_time` TIME COMMENT '实时时间',
    `day_index` INT DEFAULT 1 COMMENT '天数切换（当前第几天）',
    `weather_forecast` JSON COMMENT '天气预报（近5日，存储JSON格式）',
    
    PRIMARY KEY (`trip_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_action_time` (`action_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='行程表（合并行程、操作记录、日程）';

-- =====================================================
-- 2. 地点表 (location) - 合并原location、media、service_facility
-- =====================================================
CREATE TABLE `location` (
    `location_id` INT NOT NULL AUTO_INCREMENT COMMENT '地点ID，主键',
    `location_name` VARCHAR(100) NOT NULL COMMENT '地点名称',
    `address` VARCHAR(255) COMMENT '地址',

--  新增经纬度信息，用于前端地图打点和高德路线规划
    `latitude` DECIMAL(10, 7) COMMENT '纬度 (如：39.909187)',
    `longitude` DECIMAL(10, 7) COMMENT '经度 (如：116.397451)',

    `description` TEXT COMMENT '地点简介',
    `location_type` VARCHAR(50) COMMENT '地点类型',
    `open_time` VARCHAR(100) COMMENT '开放时间',
    `phone` VARCHAR(20) COMMENT '电话',
    `website` VARCHAR(255) COMMENT '网址',
    `is_favorite` TINYINT(1) DEFAULT 0 COMMENT '是否收藏（0-否，1-是）',
    `is_highlight` TINYINT(1) DEFAULT 0 COMMENT '是否点亮（0-否，1-是）',
    `added_by` VARCHAR(50) COMMENT '添加方式（搜索/智能导入/推荐站点等）',
    
    --原media表字段优化为一个JSON数组，兼容一个地点有多张图片的情况
    `media_images` JSON COMMENT '图片列表数组，每个元素包含 url, type, upload_time',
    
    -- 原service_facility表字段（支持多个设施，用JSON存储）
    `facilities` JSON COMMENT '服务设施列表（如：["停车场","卫生间","餐厅"]）',
    
    PRIMARY KEY (`location_id`),
    INDEX `idx_location_name` (`location_name`),
    INDEX `idx_is_favorite` (`is_favorite`),
    INDEX `idx_is_highlight` (`is_highlight`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='地点表（合并地点、媒体、服务设施）';

-- =====================================================
-- 3. 地点与行程关联表 (trip_location)
-- =====================================================
CREATE TABLE `trip_location` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键',
    `trip_id` INT NOT NULL COMMENT '行程ID',
    `location_id` INT NOT NULL COMMENT '地点ID',
    `day_index` INT DEFAULT 1 COMMENT '第几天',
    `order_index` INT DEFAULT 0 COMMENT '顺序',
    `is_stopover` TINYINT(1) DEFAULT 0 COMMENT '是否为停靠站（0-否，1-是）',
    `is_planned` TINYINT(1) DEFAULT 0 COMMENT '是否为待规划地点（0-否，1-是）',
    PRIMARY KEY (`id`),
    INDEX `idx_trip_id` (`trip_id`),
    INDEX `idx_location_id` (`location_id`),
    UNIQUE KEY `uk_trip_location` (`trip_id`, `location_id`, `day_index`, `order_index`),
    FOREIGN KEY (`trip_id`) REFERENCES `trip`(`trip_id`) ON DELETE CASCADE,
    FOREIGN KEY (`location_id`) REFERENCES `location`(`location_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='地点与行程关联表';

-- =====================================================
-- 4. 交通表 (transport)
-- =====================================================
CREATE TABLE `transport` (
    `transport_id` INT NOT NULL AUTO_INCREMENT COMMENT '交通ID，主键',
    `from_location_id` INT NOT NULL COMMENT '起点地点ID',
    `to_location_id` INT NOT NULL COMMENT '终点地点ID',
    `mode` ENUM('步行', '驾车', '公共交通') NOT NULL COMMENT '交通方式',
    `distance` VARCHAR(50) COMMENT '距离（如：2.5km）',
    `duration` VARCHAR(50) COMMENT '耗时（如：15分钟）',
    `is_peak_season` TINYINT(1) DEFAULT 0 COMMENT '是否为旺季交通工具（0-否，1-是）',
    `route_path` TEXT COMMENT '地图路径显示（可存JSON或坐标串）',
    PRIMARY KEY (`transport_id`),
    INDEX `idx_from_location` (`from_location_id`),
    INDEX `idx_to_location` (`to_location_id`),
    FOREIGN KEY (`from_location_id`) REFERENCES `location`(`location_id`) ON DELETE CASCADE,
    FOREIGN KEY (`to_location_id`) REFERENCES `location`(`location_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='交通表';

-- =====================================================
-- 5. 用户个人表 (user)
-- =====================================================
CREATE TABLE `user` (
    `user_id` INT NOT NULL AUTO_INCREMENT COMMENT '用户ID，主键',
    `username` VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    `password` VARCHAR(255) NOT NULL COMMENT '密码（加密存储）',
    `email` VARCHAR(100) COMMENT '邮箱',
    `favorite_locations` JSON COMMENT '已收藏地点（存储地点ID列表）',
    `highlighted_locations` JSON COMMENT '点亮地点（存储地点ID列表）',
    `special_focus` JSON COMMENT '特别关注（存储地点ID或专题ID）',
    `photo_mood` TEXT COMMENT '照片心情',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
    PRIMARY KEY (`user_id`),
    INDEX `idx_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户个人表';

-- =====================================================
-- 6. 专题与推荐表 (topic)
-- =====================================================
CREATE TABLE `topic` (
    `topic_id` INT NOT NULL AUTO_INCREMENT COMMENT '专题ID，主键',
    `topic_name` VARCHAR(100) NOT NULL COMMENT '专题名称',
    `location_ids` JSON COMMENT '关联地点ID列表（存储JSON数组）',
    `is_featured` TINYINT(1) DEFAULT 0 COMMENT '是否为精选专题（0-否，1-是）',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`topic_id`),
    INDEX `idx_is_featured` (`is_featured`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专题与推荐表';

-- =====================================================
-- 7. 目的地搜索表 (destination_search)
-- =====================================================
CREATE TABLE `destination_search` (
    `search_id` INT NOT NULL AUTO_INCREMENT COMMENT '搜索ID，主键',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `region` VARCHAR(50) COMMENT '切换区域（如：亚洲/欧洲）',
    `keyword` VARCHAR(100) NOT NULL COMMENT '目的地搜索关键词',
    `search_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '搜索时间',
    PRIMARY KEY (`search_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_keyword` (`keyword`),
    INDEX `idx_search_time` (`search_time`),
    FOREIGN KEY (`user_id`) REFERENCES `user`(`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='目的地搜索表';