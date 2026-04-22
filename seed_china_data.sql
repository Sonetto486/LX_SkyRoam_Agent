DO $$
DECLARE
  topic_beijing bigint;
  topic_shanghai bigint;
  topic_hangzhou bigint;
  topic_east bigint;
BEGIN
  INSERT INTO topic (name, intro, cover_url, region, continent)
  VALUES
    ('北京皇城中轴线', '从天安门到故宫，串联北京最经典的皇城历史轴线。', 'https://picsum.photos/seed/beijing_axis/800/600', '中国', 'asia')
  RETURNING id INTO topic_beijing;

  INSERT INTO topic (name, intro, cover_url, region, continent)
  VALUES
    ('上海外滩摩登夜游', '白天看城市天际线，夜晚看黄浦江灯火与百年建筑。', 'https://picsum.photos/seed/shanghai_bund/800/600', '中国', 'asia')
  RETURNING id INTO topic_shanghai;

  INSERT INTO topic (name, intro, cover_url, region, continent)
  VALUES
    ('杭州西湖慢生活', '围绕西湖展开的慢节奏城市漫游，适合轻松度假。', 'https://picsum.photos/seed/hangzhou_westlake/800/600', '中国', 'asia')
  RETURNING id INTO topic_hangzhou;

  INSERT INTO topic (name, intro, cover_url, region, continent)
  VALUES
    ('中国华东经典三城游', '北京、上海、杭州三城连线，适合第一次来中国的旅行者。', 'https://picsum.photos/seed/east_china/800/600', '中国', 'asia')
  RETURNING id INTO topic_east;

  INSERT INTO topic_place (topic_id, related_type, related_id, is_key_point, highlight_info, order_index)
  VALUES
    (topic_beijing, 'destinations', 1, true, '【首选目的地】北京最适合作为皇城线的起点。', 1),
    (topic_beijing, 'attractions', 1, true, '天安门广场是北京城市记忆的核心。', 2),
    (topic_beijing, 'attractions', 2, true, '故宫博物院建议预留半天慢慢逛。', 3),

    (topic_shanghai, 'destinations', 2, true, '【首选目的地】上海适合用夜景打开城市想象。', 1),
    (topic_shanghai, 'attractions', 3, true, '外滩夜景是上海最经典的城市封面。', 2),

    (topic_hangzhou, 'destinations', 5, true, '【首选目的地】杭州西湖适合慢下来感受城市气质。', 1),
    (topic_hangzhou, 'attractions', 4, true, '西湖是杭州最值得留出整天的地方。', 2),

    (topic_east, 'destinations', 1, true, '北京代表历史厚度，适合作为华东/华北连线起点。', 1),
    (topic_east, 'destinations', 2, false, '上海代表现代都市感，是必经一站。', 2),
    (topic_east, 'destinations', 5, false, '杭州代表江南韵味，适合作为收尾城市。', 3);

  INSERT INTO travel_plans (
    title, description, destination, start_date, end_date, duration_days,
    status, is_public, public_at, user_id, created_at, updated_at, is_active, score
  )
  VALUES
    ('北京4日文化之旅', '沿着中轴线、胡同、博物馆和传统园林感受北京的厚重历史。', '北京, 中国', '2026-09-01', '2026-09-04', 4, 'completed', true, NOW(), 1, NOW(), NOW(), true, 4.8),
    ('上海3日都市漫游', '从外滩到老街区，感受上海摩登与烟火气并存的城市节奏。', '上海, 中国', '2026-09-10', '2026-09-12', 3, 'completed', true, NOW(), 1, NOW(), NOW(), true, 4.7),
    ('杭州2日西湖慢游', '用两天围绕西湖、茶园和老街，体验杭州松弛的江南氛围。', '杭州, 中国', '2026-09-20', '2026-09-21', 2, 'completed', true, NOW(), 1, NOW(), NOW(), true, 4.6),
    ('华东5日经典连线游', '北京、上海、杭州三城连线，兼顾历史、现代与江南风景。', '北京, 上海, 杭州', '2026-10-01', '2026-10-05', 5, 'completed', true, NOW(), 1, NOW(), NOW(), true, 4.9);
END $$;
