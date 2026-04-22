async def _parse_text_to_itineraries(text_plan: str, destination: str, days: int, start_date: datetime) -> List[Dict[str, Any]]:
    """将文本计划解析为结构化的行程数据"""
    try:
        import re
        from datetime import datetime, timedelta

        itineraries = []

        # 使用正则表达式解析文本中的日期和活动
        # 匹配模式 "Day 1:", "第一天:", "D1:" 等格式
        day_patterns = [
            r'(?:第(\d+)天|Day\s*(\d+)|D(\d+)|day\s*(\d+))[:\s]*',
            r'(\d+)月(\d+)日[:\s]*'  # 日期格式
        ]

        # 按行分割文本
        lines = text_plan.split('\n')
        current_day = 0
        current_activities = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检查是否是新的一天
            day_match = None
            for pattern in day_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    # 保存前一天的内容
                    if current_activities and current_day > 0:
                        itinerary = _create_day_itinerary(current_day, start_date, destination, current_activities)
                        itineraries.append(itinerary)

                    # 获取天数
                    day_num = 0
                    for group in match.groups():
                        if group and group.isdigit():
                            day_num = int(group)
                            break

                    current_day = day_num
                    current_activities = []
                    break

            # 如果是活动行，则进行解析
            if current_day > 0 and not day_match:
                activity = _parse_activity_line(line)
                if activity:
                    current_activities.append(activity)

        # 保存最后一天的内容
        if current_activities and current_day > 0:
            itinerary = _create_day_itinerary(current_day, start_date, destination, current_activities)
            itineraries.append(itinerary)

        # 如果没有解析到任何行程，则创建默认行程
        if not itineraries:
            for day in range(1, days + 1):
                itinerary = _create_default_day_itinerary(day, start_date, destination)
                itineraries.append(itinerary)

        # 按天数排序
        itineraries.sort(key=lambda x: x['day'])

        return itineraries

    except Exception as e:
        logger.error(f"解析文本计划失败: {e}")
        # 返回默认行程
        itineraries = []
        for day in range(1, days + 1):
            itinerary = _create_default_day_itinerary(day, start_date, destination)
            itineraries.append(itinerary)
        return itineraries