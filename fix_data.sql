-- 插入日本相关目的地
INSERT INTO destinations (id, name, country, city, region, latitude, longitude, description, popularity_score) 
VALUES 
(20, '东京', '日本', '东京', '关东', 35.6895, 139.6917, '繁华的现代都市与传统文化交织', 4.9),
(21, '京都', '日本', '京都', '关西', 35.0116, 135.7681, '千年古都，遍布神社与寺庙', 4.8),
(22, '北海道', '日本', '札幌', '北海道', 43.0618, 141.3545, '自然风光与顶级海鲜的宝库', 4.7),
(23, '大阪', '日本', '大阪', '关西', 34.6937, 135.5023, '天下厨房，关西的热情与活力', 4.8)
ON CONFLICT (id) DO NOTHING;

-- 插入对应的景点
INSERT INTO attractions (id, name, category, description, destination_id, rating, images)
VALUES 
(201, '浅草寺', '文化/历史', '东京都内最古老的寺庙，雷门是其标志。', 20, 4.6, '["https://picsum.photos/seed/sensoji/800/600"]'),
(202, '上野公园', '公园/自然', '著名的赏樱圣地，内有众多博物馆。', 20, 4.7, '["https://picsum.photos/seed/ueno/800/600"]'),
(203, '秋叶原', '娱乐/购物', '御宅族文化圣地，电子产品和动漫天堂。', 20, 4.5, '["https://picsum.photos/seed/akihabara/800/600"]'),
(204, '清水寺', '文化/历史', '京都最古老的寺院，清水舞台享有盛名。', 21, 4.8, '["https://picsum.photos/seed/kiyomizu/800/600"]'),
(205, '伏见稻荷大社', '文化/历史', '以千本鸟居闻名的京都地标。', 21, 4.9, '["https://picsum.photos/seed/fushimi/800/600"]'),
(206, '小樽运河', '景观/自然', '充满复古浪漫风情的北海道运河。', 22, 4.6, '["https://picsum.photos/seed/otaru/800/600"]'),
(207, '富良野花田', '公园/自然', '夏季绚丽的薰衣草花海。', 22, 4.8, '["https://picsum.photos/seed/furano/800/600"]'),
(208, '日本环球影城(USJ)', '主题公园', '集结好莱坞大片与日本动漫的主题乐园。', 23, 4.9, '["https://picsum.photos/seed/usj_park/800/600"]'),
(209, '大阪城公园', '文化/历史', '拥有壮丽天守阁的历史公园。', 23, 4.7, '["https://picsum.photos/seed/osaka_castle/800/600"]')
ON CONFLICT (id) DO NOTHING;

-- 修正所有序列号计数器
SELECT setval('destinations_id_seq', (SELECT MAX(id) FROM destinations));
SELECT setval('attractions_id_seq', (SELECT MAX(id) FROM attractions));

-- 彻底清理原有的 topic_place 数据关联并重启 ID
TRUNCATE TABLE topic_place RESTART IDENTITY CASCADE;

-- 重新根据专题插入精准的 topic_place 关联数据

-- 专题 1: 东京季
INSERT INTO topic_place (topic_id, related_type, related_id, is_key_point, highlight_info, order_index) VALUES 
(1, 'destinations', 20, true, '【首选目的地】这里是这趟行程的大本营。', 1),
(1, 'attractions', 201, true, '雷门是经典打卡点，建议穿着和服拍摄！', 2),
(1, 'attractions', 202, true, '樱花季千万不容错过的上野恩赐公园。', 3),
(1, 'attractions', 203, false, '逛完公园可以顺道去感受一下二次元文化。', 4);

-- 专题 2: 京都古寺巡礼
INSERT INTO topic_place (topic_id, related_type, related_id, is_key_point, highlight_info, order_index) VALUES 
(2, 'destinations', 21, true, '【首选目的地】千年古都，静心之旅的起点。', 1),
(2, 'attractions', 204, true, '清水舞台的日落绝美，请把行程留在傍晚。', 2),
(2, 'attractions', 205, true, '千本鸟居建议一早前往避开人潮。', 3);

-- 专题 3: 北海道美食之旅
INSERT INTO topic_place (topic_id, related_type, related_id, is_key_point, highlight_info, order_index) VALUES 
(3, 'destinations', 22, true, '【首选目的地】雪国风光，海鲜天堂。', 1),
(3, 'attractions', 206, true, '感受玻璃工艺与浪漫运河结合的双重情调。', 2),
(3, 'attractions', 207, false, '若是夏季出行，这是北海道的精髓。', 3);

-- 专题 4: 大阪环球影城
INSERT INTO topic_place (topic_id, related_type, related_id, is_key_point, highlight_info, order_index) VALUES 
(4, 'destinations', 23, true, '【首选目的地】极具关西热情的城市。', 1),
(4, 'attractions', 208, true, '提前购买快速票！马里奥园区是最火爆的。', 2),
(4, 'attractions', 209, false, '在刺激的过山车后，感受一下历史气息。', 3);