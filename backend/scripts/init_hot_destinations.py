"""
初始化100个热门城市数据
数据来源：参考携程、马蜂窝等平台的年度热门目的地榜单
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session
from app.models.hot_destination import HotDestination
from sqlalchemy import select
from loguru import logger


# 100个热门城市数据（按优先级排序）
HOT_DESTINATIONS_DATA = [
    # 第一梯队：顶级热门城市（优先级 1-20）
    {"city_name": "北京", "province": "北京", "region": "华北", "priority": 1, "tags": "历史文化,名胜古迹,美食"},
    {"city_name": "上海", "province": "上海", "region": "华东", "priority": 2, "tags": "都市风光,购物,美食"},
    {"city_name": "广州", "province": "广东", "region": "华南", "priority": 3, "tags": "美食,购物,历史文化"},
    {"city_name": "深圳", "province": "广东", "region": "华南", "priority": 4, "tags": "都市风光,科技,购物"},
    {"city_name": "杭州", "province": "浙江", "region": "华东", "priority": 5, "tags": "自然风光,历史文化,美食"},
    {"city_name": "成都", "province": "四川", "region": "西南", "priority": 6, "tags": "美食,休闲,历史文化"},
    {"city_name": "重庆", "province": "重庆", "region": "西南", "priority": 7, "tags": "美食,自然风光,都市"},
    {"city_name": "西安", "province": "陕西", "region": "西北", "priority": 8, "tags": "历史文化,名胜古迹,美食"},
    {"city_name": "南京", "province": "江苏", "region": "华东", "priority": 9, "tags": "历史文化,自然风光,美食"},
    {"city_name": "苏州", "province": "江苏", "region": "华东", "priority": 10, "tags": "园林,历史文化,美食"},
    {"city_name": "厦门", "province": "福建", "region": "华东", "priority": 11, "tags": "海滨,休闲,美食"},
    {"city_name": "三亚", "province": "海南", "region": "华南", "priority": 12, "tags": "海滨,度假,热带风光"},
    {"city_name": "青岛", "province": "山东", "region": "华东", "priority": 13, "tags": "海滨,啤酒,美食"},
    {"city_name": "昆明", "province": "云南", "region": "西南", "priority": 14, "tags": "春城,自然风光,民族风情"},
    {"city_name": "大理", "province": "云南", "region": "西南", "priority": 15, "tags": "古镇,自然风光,休闲"},
    {"city_name": "丽江", "province": "云南", "region": "西南", "priority": 16, "tags": "古镇,自然风光,民族风情"},
    {"city_name": "桂林", "province": "广西", "region": "华南", "priority": 17, "tags": "山水,自然风光,溶洞"},
    {"city_name": "张家界", "province": "湖南", "region": "华中", "priority": 18, "tags": "山水,自然风光,奇峰"},
    {"city_name": "长沙", "province": "湖南", "region": "华中", "priority": 19, "tags": "美食,历史文化,娱乐"},
    {"city_name": "武汉", "province": "湖北", "region": "华中", "priority": 20, "tags": "历史文化,美食,江河风光"},

    # 第二梯队：热门旅游城市（优先级 21-50）
    {"city_name": "天津", "province": "天津", "region": "华北", "priority": 21, "tags": "历史文化,美食,都市"},
    {"city_name": "沈阳", "province": "辽宁", "region": "东北", "priority": 22, "tags": "历史文化,美食,冰雪"},
    {"city_name": "大连", "province": "辽宁", "region": "东北", "priority": 23, "tags": "海滨,都市,美食"},
    {"city_name": "哈尔滨", "province": "黑龙江", "region": "东北", "priority": 24, "tags": "冰雪,欧式建筑,美食"},
    {"city_name": "长春", "province": "吉林", "region": "东北", "priority": 25, "tags": "冰雪,电影文化,都市"},
    {"city_name": "济南", "province": "山东", "region": "华东", "priority": 26, "tags": "泉水,历史文化,美食"},
    {"city_name": "烟台", "province": "山东", "region": "华东", "priority": 27, "tags": "海滨,葡萄酒,美食"},
    {"city_name": "威海", "province": "山东", "region": "华东", "priority": 28, "tags": "海滨,度假,宜居"},
    {"city_name": "郑州", "province": "河南", "region": "华中", "priority": 29, "tags": "历史文化,交通枢纽,美食"},
    {"city_name": "洛阳", "province": "河南", "region": "华中", "priority": 30, "tags": "历史文化,牡丹,石窟"},
    {"city_name": "开封", "province": "河南", "region": "华中", "priority": 31, "tags": "历史文化,古都,美食"},
    {"city_name": "太原", "province": "山西", "region": "华北", "priority": 32, "tags": "历史文化,古建筑,美食"},
    {"city_name": "石家庄", "province": "河北", "region": "华北", "priority": 33, "tags": "历史文化,交通枢纽"},
    {"city_name": "合肥", "province": "安徽", "region": "华东", "priority": 34, "tags": "历史文化,科技,美食"},
    {"city_name": "黄山", "province": "安徽", "region": "华东", "priority": 35, "tags": "山水,自然风光,徽派建筑"},
    {"city_name": "福州", "province": "福建", "region": "华东", "priority": 36, "tags": "历史文化,美食,海滨"},
    {"city_name": "泉州", "province": "福建", "region": "华东", "priority": 37, "tags": "历史文化,海上丝绸之路,美食"},
    {"city_name": "南昌", "province": "江西", "region": "华东", "priority": 38, "tags": "历史文化,红色旅游,美食"},
    {"city_name": "景德镇", "province": "江西", "region": "华东", "priority": 39, "tags": "陶瓷文化,历史文化"},
    {"city_name": "九江", "province": "江西", "region": "华东", "priority": 40, "tags": "庐山,自然风光,历史文化"},

    # 第三梯队：特色旅游城市（优先级 41-70）
    {"city_name": "贵阳", "province": "贵州", "region": "西南", "priority": 41, "tags": "避暑,民族风情,美食"},
    {"city_name": "遵义", "province": "贵州", "region": "西南", "priority": 42, "tags": "红色旅游,历史文化,美食"},
    {"city_name": "西双版纳", "province": "云南", "region": "西南", "priority": 43, "tags": "热带风光,民族风情,自然"},
    {"city_name": "香格里拉", "province": "云南", "region": "西南", "priority": 44, "tags": "高原风光,民族风情,自然"},
    {"city_name": "腾冲", "province": "云南", "region": "西南", "priority": 45, "tags": "温泉,火山,边境风情"},
    {"city_name": "北海", "province": "广西", "region": "华南", "priority": 46, "tags": "海滨,度假,美食"},
    {"city_name": "南宁", "province": "广西", "region": "华南", "priority": 47, "tags": "都市,美食,民族风情"},
    {"city_name": "海口", "province": "海南", "region": "华南", "priority": 48, "tags": "海滨,热带风光,美食"},
    {"city_name": "珠海", "province": "广东", "region": "华南", "priority": 49, "tags": "海滨,度假,宜居"},
    {"city_name": "佛山", "province": "广东", "region": "华南", "priority": 50, "tags": "美食,历史文化,功夫"},
    {"city_name": "东莞", "province": "广东", "region": "华南", "priority": 51, "tags": "都市,美食,购物"},
    {"city_name": "惠州", "province": "广东", "region": "华南", "priority": 52, "tags": "海滨,自然风光,美食"},
    {"city_name": "汕头", "province": "广东", "region": "华南", "priority": 53, "tags": "美食,海滨,历史文化"},
    {"city_name": "中山", "province": "广东", "region": "华南", "priority": 54, "tags": "历史文化,美食,宜居"},
    {"city_name": "江门", "province": "广东", "region": "华南", "priority": 55, "tags": "侨乡,历史文化,美食"},
    {"city_name": "兰州", "province": "甘肃", "region": "西北", "priority": 56, "tags": "美食,黄河,历史文化"},
    {"city_name": "敦煌", "province": "甘肃", "region": "西北", "priority": 57, "tags": "莫高窟,沙漠,历史文化"},
    {"city_name": "嘉峪关", "province": "甘肃", "region": "西北", "priority": 58, "tags": "长城,历史文化,沙漠"},
    {"city_name": "西宁", "province": "青海", "region": "西北", "priority": 59, "tags": "高原,民族风情,自然"},
    {"city_name": "银川", "province": "宁夏", "region": "西北", "priority": 60, "tags": "沙漠,湖泊,民族风情"},
    {"city_name": "乌鲁木齐", "province": "新疆", "region": "西北", "priority": 61, "tags": "民族风情,自然风光,美食"},
    {"city_name": "吐鲁番", "province": "新疆", "region": "西北", "priority": 62, "tags": "葡萄沟,火焰山,历史文化"},
    {"city_name": "喀什", "province": "新疆", "region": "西北", "priority": 63, "tags": "民族风情,历史文化,边境"},
    {"city_name": "伊犁", "province": "新疆", "region": "西北", "priority": 64, "tags": "草原,自然风光,民族风情"},
    {"city_name": "拉萨", "province": "西藏", "region": "西南", "priority": 65, "tags": "宗教文化,高原,历史文化"},
    {"city_name": "林芝", "province": "西藏", "region": "西南", "priority": 66, "tags": "桃花,自然风光,高原"},
    {"city_name": "日喀则", "province": "西藏", "region": "西南", "priority": 67, "tags": "珠峰,宗教文化,高原"},
    {"city_name": "呼和浩特", "province": "内蒙古", "region": "华北", "priority": 68, "tags": "草原,民族风情,美食"},
    {"city_name": "呼伦贝尔", "province": "内蒙古", "region": "华北", "priority": 69, "tags": "草原,自然风光,民族风情"},
    {"city_name": "鄂尔多斯", "province": "内蒙古", "region": "华北", "priority": 70, "tags": "沙漠,草原,民族风情"},

    # 第四梯队：其他热门城市（优先级 71-100）
    {"city_name": "无锡", "province": "江苏", "region": "华东", "priority": 71, "tags": "太湖,园林,美食"},
    {"city_name": "常州", "province": "江苏", "region": "华东", "priority": 72, "tags": "主题乐园,美食,宜居"},
    {"city_name": "南通", "province": "江苏", "region": "华东", "priority": 73, "tags": "江海风光,美食,宜居"},
    {"city_name": "扬州", "province": "江苏", "region": "华东", "priority": 74, "tags": "园林,美食,历史文化"},
    {"city_name": "镇江", "province": "江苏", "region": "华东", "priority": 75, "tags": "山水,历史文化,美食"},
    {"city_name": "徐州", "province": "江苏", "region": "华东", "priority": 76, "tags": "历史文化,美食,交通枢纽"},
    {"city_name": "温州", "province": "浙江", "region": "华东", "priority": 77, "tags": "山水,商业,美食"},
    {"city_name": "宁波", "province": "浙江", "region": "华东", "priority": 78, "tags": "海滨,历史文化,美食"},
    {"city_name": "绍兴", "province": "浙江", "region": "华东", "priority": 79, "tags": "水乡,历史文化,美食"},
    {"city_name": "嘉兴", "province": "浙江", "region": "华东", "priority": 80, "tags": "水乡,历史文化,美食"},
    {"city_name": "金华", "province": "浙江", "region": "华东", "priority": 81, "tags": "横店影视城,历史文化,美食"},
    {"city_name": "舟山", "province": "浙江", "region": "华东", "priority": 82, "tags": "海岛,佛教,海鲜"},
    {"city_name": "台州", "province": "浙江", "region": "华东", "priority": 83, "tags": "山海,美食,宜居"},
    {"city_name": "湖州", "province": "浙江", "region": "华东", "priority": 84, "tags": "太湖,古镇,美食"},
    {"city_name": "丽水", "province": "浙江", "region": "华东", "priority": 85, "tags": "山水,自然风光,摄影"},
    {"city_name": "衢州", "province": "浙江", "region": "华东", "priority": 86, "tags": "山水,历史文化,美食"},
    {"city_name": "三亚", "province": "海南", "region": "华南", "priority": 87, "tags": "海滨,度假,热带"},
    {"city_name": "万宁", "province": "海南", "region": "华南", "priority": 88, "tags": "海滨,冲浪,度假"},
    {"city_name": "文昌", "province": "海南", "region": "华南", "priority": 89, "tags": "航天,海滨,美食"},
    {"city_name": "琼海", "province": "海南", "region": "华南", "priority": 90, "tags": "博鳌,海滨,度假"},
    {"city_name": "保亭", "province": "海南", "region": "华南", "priority": 91, "tags": "热带雨林,温泉,度假"},
    {"city_name": "陵水", "province": "海南", "region": "华南", "priority": 92, "tags": "海滨,度假,美食"},
    {"city_name": "澄迈", "province": "海南", "region": "华南", "priority": 93, "tags": "长寿之乡,美食,宜居"},
    {"city_name": "儋州", "province": "海南", "region": "华南", "priority": 94, "tags": "历史文化,海滨,美食"},
    {"city_name": "东方", "province": "海南", "region": "华南", "priority": 95, "tags": "海滨,自然风光,美食"},
    {"city_name": "五指山", "province": "海南", "region": "华南", "priority": 96, "tags": "热带雨林,山地,民族风情"},
    {"city_name": "乐东", "province": "海南", "region": "华南", "priority": 97, "tags": "海滨,热带风光,美食"},
    {"city_name": "昌江", "province": "海南", "region": "华南", "priority": 98, "tags": "棋子湾,海滨,自然风光"},
    {"city_name": "白沙", "province": "海南", "region": "华南", "priority": 99, "tags": "热带雨林,茶园,自然风光"},
    {"city_name": "琼中", "province": "海南", "region": "华南", "priority": 100, "tags": "热带雨林,山地,民族风情"},
]


async def init_hot_destinations():
    """初始化热门城市数据"""
    async with async_session() as db:
        logger.info("开始初始化热门城市数据...")

        added_count = 0
        skipped_count = 0

        for city_data in HOT_DESTINATIONS_DATA:
            # 检查是否已存在
            query = select(HotDestination).where(HotDestination.city_name == city_data["city_name"])
            result = await db.execute(query)
            existing = result.scalar_one_or_none()

            if existing:
                logger.debug(f"城市已存在，跳过: {city_data['city_name']}")
                skipped_count += 1
                continue

            # 创建新记录
            hot_dest = HotDestination(
                city_name=city_data["city_name"],
                province=city_data.get("province"),
                region=city_data.get("region"),
                priority=city_data.get("priority", 100),
                tags=city_data.get("tags"),
                is_enabled=True,
                popularity_score=0.0,
                pre_generated_count=0
            )

            db.add(hot_dest)
            added_count += 1
            logger.debug(f"添加城市: {city_data['city_name']}")

        await db.commit()

        logger.info(f"热门城市初始化完成！新增: {added_count}, 跳过: {skipped_count}")
        return {"added": added_count, "skipped": skipped_count}


if __name__ == "__main__":
    result = asyncio.run(init_hot_destinations())
    print(f"初始化结果: {result}")
