"""
热门景点图片预置脚本
从 Wikimedia Commons 获取热门景点真实图片并写入数据库

使用方法:
    python backend/scripts/preset_attraction_images.py
"""

import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from loguru import logger

from app.core.database import get_async_session_local
from app.models.attraction_detail import AttractionDetail
from app.tools.wikimedia_service import wikimedia_service
from app.tools.unsplash_service import unsplash_service


# 热门景点列表（10个城市，约160个景点）
HOT_ATTRACTIONS = {
    "北京": [
        {"name": "故宫博物院", "english": "Forbidden City"},
        {"name": "天安门广场", "english": "Tiananmen Square"},
        {"name": "八达岭长城", "english": "Badaling Great Wall"},
        {"name": "颐和园", "english": "Summer Palace"},
        {"name": "天坛", "english": "Temple of Heaven"},
        {"name": "圆明园", "english": "Old Summer Palace"},
        {"name": "北海公园", "english": "Beihai Park"},
        {"name": "南锣鼓巷", "english": "Nanluoguxiang"},
        {"name": "什刹海", "english": "Shichahai"},
        {"name": "国家体育场", "english": "National Stadium Beijing"},
        {"name": "国家游泳中心", "english": "National Aquatics Center"},
        {"name": "北京动物园", "english": "Beijing Zoo"},
        {"name": "景山公园", "english": "Jingshan Park"},
        {"name": "恭王府", "english": "Prince Kung's Mansion"},
        {"name": "雍和宫", "english": "Yonghe Temple"},
        {"name": "国子监", "english": "Imperial College"},
        {"name": "香山公园", "english": "Fragrant Hills Park"},
        {"name": "明十三陵", "english": "Ming Tombs"},
        {"name": "慕田峪长城", "english": "Mutianyu Great Wall"},
        {"name": "798艺术区", "english": "798 Art Zone"},
    ],
    "上海": [
        {"name": "外滩", "english": "The Bund Shanghai"},
        {"name": "东方明珠广播电视塔", "english": "Oriental Pearl Tower"},
        {"name": "上海环球金融中心", "english": "Shanghai World Financial Center"},
        {"name": "金茂大厦", "english": "Jin Mao Tower"},
        {"name": "上海中心大厦", "english": "Shanghai Tower"},
        {"name": "豫园", "english": "Yu Garden Shanghai"},
        {"name": "城隍庙", "english": "City God Temple Shanghai"},
        {"name": "南京路步行街", "english": "Nanjing Road Shanghai"},
        {"name": "人民广场", "english": "People's Square Shanghai"},
        {"name": "上海博物馆", "english": "Shanghai Museum"},
        {"name": "田子坊", "english": "Tianzifang"},
        {"name": "新天地", "english": "Xintiandi"},
        {"name": "静安寺", "english": "Jing'an Temple"},
        {"name": "龙华寺", "english": "Longhua Temple"},
        {"name": "上海迪士尼乐园", "english": "Shanghai Disney Resort"},
        {"name": "上海野生动物园", "english": "Shanghai Wild Animal Park"},
        {"name": "上海科技馆", "english": "Shanghai Science and Technology Museum"},
        {"name": "朱家角古镇", "english": "Zhujiajiao"},
    ],
    "杭州": [
        {"name": "西湖风景名胜区", "english": "West Lake Hangzhou"},
        {"name": "灵隐寺", "english": "Lingyin Temple"},
        {"name": "雷峰塔", "english": "Leifeng Pagoda"},
        {"name": "三潭印月", "english": "Three Pools Mirroring the Moon"},
        {"name": "断桥残雪", "english": "Broken Bridge West Lake"},
        {"name": "苏堤春晓", "english": "Su Causeway West Lake"},
        {"name": "白堤", "english": "Bai Causeway West Lake"},
        {"name": "岳王庙", "english": "Yue Fei Temple"},
        {"name": "千岛湖", "english": "Qiandao Lake"},
        {"name": "宋城", "english": "Songcheng"},
        {"name": "西溪湿地", "english": "Xixi Wetland"},
        {"name": "龙井茶园", "english": "Longjing Tea Village"},
    ],
    "成都": [
        {"name": "宽窄巷子", "english": "Kuanzhai Alley"},
        {"name": "锦里", "english": "Jinli Ancient Street"},
        {"name": "武侯祠", "english": "Wuhou Shrine"},
        {"name": "杜甫草堂", "english": "Du Fu Thatched Cottage"},
        {"name": "大熊猫繁育研究基地", "english": "Giant Panda Breeding Research Base"},
        {"name": "春熙路", "english": "Chunxi Road"},
        {"name": "太古里", "english": "Taikoo Li Chengdu"},
        {"name": "青城山", "english": "Qingcheng Mountain"},
        {"name": "都江堰", "english": "Dujiangyan Irrigation System"},
        {"name": "人民公园", "english": "People's Park Chengdu"},
        {"name": "文殊院", "english": "Wenshu Monastery"},
        {"name": "锦江", "english": "Jinjiang River"},
    ],
    "西安": [
        {"name": "秦始皇兵马俑博物馆", "english": "Terracotta Army"},
        {"name": "大雁塔", "english": "Big Wild Goose Pagoda"},
        {"name": "小雁塔", "english": "Small Wild Goose Pagoda"},
        {"name": "西安城墙", "english": "Xi'an City Wall"},
        {"name": "钟楼", "english": "Bell Tower Xi'an"},
        {"name": "鼓楼", "english": "Drum Tower Xi'an"},
        {"name": "回民街", "english": "Muslim Quarter Xi'an"},
        {"name": "华清池", "english": "Huaqing Pool"},
        {"name": "大唐芙蓉园", "english": "Tang Paradise"},
        {"name": "陕西历史博物馆", "english": "Shaanxi History Museum"},
        {"name": "大明宫遗址", "english": "Daming Palace"},
        {"name": "碑林博物馆", "english": "Forest of Steles"},
    ],
    "南京": [
        {"name": "中山陵", "english": "Sun Yat-sen Mausoleum"},
        {"name": "明孝陵", "english": "Ming Xiaoling Tomb"},
        {"name": "夫子庙", "english": "Confucius Temple Nanjing"},
        {"name": "秦淮河", "english": "Qinhuai River"},
        {"name": "总统府", "english": "Presidential Palace Nanjing"},
        {"name": "玄武湖", "english": "Xuanwu Lake"},
        {"name": "紫金山", "english": "Purple Mountain Nanjing"},
        {"name": "南京博物院", "english": "Nanjing Museum"},
        {"name": "侵华日军南京大屠杀遇难同胞纪念馆", "english": "Nanjing Massacre Memorial Hall"},
        {"name": "鸡鸣寺", "english": "Jiming Temple"},
        {"name": "瞻园", "english": "Zhan Garden"},
        {"name": "老门东", "english": "Laomendong"},
    ],
    "苏州": [
        {"name": "拙政园", "english": "Humble Administrator's Garden"},
        {"name": "留园", "english": "Lingering Garden"},
        {"name": "狮子林", "english": "Lion Grove Garden"},
        {"name": "寒山寺", "english": "Hanshan Temple"},
        {"name": "虎丘", "english": "Tiger Hill Suzhou"},
        {"name": "苏州博物馆", "english": "Suzhou Museum"},
        {"name": "平江路", "english": "Pingjiang Road"},
        {"name": "山塘街", "english": "Shantang Street"},
        {"name": "周庄古镇", "english": "Zhouzhuang"},
        {"name": "同里古镇", "english": "Tongli"},
        {"name": "金鸡湖", "english": "Jinji Lake"},
        {"name": "网师园", "english": "Net Master Garden"},
    ],
    "厦门": [
        {"name": "鼓浪屿", "english": "Gulangyu Island"},
        {"name": "南普陀寺", "english": "Nanputuo Temple"},
        {"name": "厦门大学", "english": "Xiamen University"},
        {"name": "曾厝垵", "english": "Zengcuo'an"},
        {"name": "环岛路", "english": "Island Ring Road Xiamen"},
        {"name": "胡里山炮台", "english": "Hulishan Fortress"},
        {"name": "中山路步行街", "english": "Zhongshan Road Xiamen"},
        {"name": "集美学村", "english": "Jimei School Village"},
        {"name": "日光岩", "english": "Sunlight Rock"},
        {"name": "菽庄花园", "english": "Shuzhuang Garden"},
        {"name": "皓月园", "english": "Haoyue Park"},
        {"name": "钢琴博物馆", "english": "Piano Museum Gulangyu"},
    ],
    "重庆": [
        {"name": "洪崖洞", "english": "Hongya Cave"},
        {"name": "解放碑步行街", "english": "Jiefangbei Pedestrian Street"},
        {"name": "磁器口古镇", "english": "Ciqikou Ancient Town"},
        {"name": "长江索道", "english": "Yangtze River Cableway"},
        {"name": "武隆天生三桥", "english": "Wulong Karst"},
        {"name": "大足石刻", "english": "Dazu Rock Carvings"},
        {"name": "南山一棵树观景台", "english": "Nanshan Tree View Platform"},
        {"name": "朝天门", "english": "Chaotianmen"},
        {"name": "李子坝轻轨站", "english": "Liziba Station"},
        {"name": "人民大礼堂", "english": "Great Hall of the People Chongqing"},
        {"name": "三峡博物馆", "english": "Three Gorges Museum"},
        {"name": "白公馆", "english": "Baigongguan"},
    ],
    "广州": [
        {"name": "广州塔", "english": "Canton Tower"},
        {"name": "陈家祠", "english": "Chen Clan Ancestral Hall"},
        {"name": "沙面", "english": "Shamian Island"},
        {"name": "白云山", "english": "Baiyun Mountain"},
        {"name": "越秀公园", "english": "Yuexiu Park"},
        {"name": "中山纪念堂", "english": "Sun Yat-sen Memorial Hall"},
        {"name": "长隆野生动物世界", "english": "Chimelong Safari Park"},
        {"name": "长隆欢乐世界", "english": "Chimelong Paradise"},
        {"name": "北京路步行街", "english": "Beijing Road Guangzhou"},
        {"name": "珠江夜游", "english": "Pearl River Night Cruise"},
        {"name": "圣心大教堂", "english": "Sacred Heart Cathedral Guangzhou"},
        {"name": "石室圣心大教堂", "english": "Sacred Heart Cathedral Guangzhou"},
    ],
}


async def preset_attraction_images():
    """预置热门景点图片"""
    async_session = get_async_session_local()

    total_count = 0
    success_count = 0
    wikimedia_count = 0
    unsplash_count = 0

    async with async_session() as db:
        for city, attractions in HOT_ATTRACTIONS.items():
            logger.info(f"开始处理城市: {city} ({len(attractions)} 个景点)")

            for attraction in attractions:
                name = attraction["name"]
                english = attraction.get("english", "")

                total_count += 1

                try:
                    # 1. 查询数据库是否存在该景点
                    query = select(AttractionDetail).where(
                        AttractionDetail.name == name,
                        AttractionDetail.city == city
                    )
                    result = await db.execute(query)
                    existing = result.scalar_one_or_none()

                    # 2. 从 Wikimedia 获取图片
                    image_url = await wikimedia_service.search_attraction_image(
                        attraction_name=name,
                        city=city,
                        english_name=english
                    )

                    image_source = "wikimedia"

                    # 3. 如果 Wikimedia 没有图片，使用 Unsplash 兜底
                    if not image_url:
                        image_url = unsplash_service.get_static_fallback_for_city(city)
                        image_source = "unsplash"
                        unsplash_count += 1
                        logger.warning(f"⚠️ {name}: Wikimedia 未找到，使用 Unsplash 兜底")
                    else:
                        wikimedia_count += 1

                    if image_url:
                        if existing:
                            # 更新现有记录
                            existing.image_url = image_url
                            existing.image_source = image_source
                            existing.verified = "verified"
                            logger.success(f"✅ 更新 {name}: {image_url[:60]}...")
                        else:
                            # 创建新记录
                            new_detail = AttractionDetail(
                                name=name,
                                destination=city,
                                city=city,
                                image_url=image_url,
                                image_source=image_source,
                                source="preset",
                                verified="verified",
                                match_priority=100
                            )
                            db.add(new_detail)
                            logger.success(f"✅ 新增 {name}: {image_url[:60]}...")

                        success_count += 1
                    else:
                        logger.error(f"❌ {name}: 未找到任何图片")

                    # 限流：每秒最多 1 个请求
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"❌ {name}: {e}")

        # 批量提交
        await db.commit()

        logger.info("=" * 50)
        logger.info(f"预置完成!")
        logger.info(f"  总景点数: {total_count}")
        logger.info(f"  成功数: {success_count}")
        logger.info(f"  Wikimedia 图片: {wikimedia_count}")
        logger.info(f"  Unsplash 兜底: {unsplash_count}")
        logger.info("=" * 50)


async def test_single_attraction(name: str, city: str, english: str = ""):
    """测试单个景点的图片获取"""
    logger.info(f"测试景点: {name} ({city})")

    # 测试 Wikimedia
    image_url = await wikimedia_service.search_attraction_image(
        attraction_name=name,
        city=city,
        english_name=english
    )

    if image_url:
        logger.success(f"Wikimedia 图片: {image_url}")
    else:
        # 测试 Unsplash 兜底
        fallback = unsplash_service.get_static_fallback_for_city(city)
        logger.warning(f"使用 Unsplash 兜底: {fallback}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="预置热门景点图片")
    parser.add_argument("--test", action="store_true", help="测试模式（只测试几个景点）")
    parser.add_argument("--name", type=str, default="", help="测试单个景点名称")
    parser.add_argument("--city", type=str, default="", help="测试景点城市")
    parser.add_argument("--english", type=str, default="", help="测试景点英文名")

    args = parser.parse_args()

    if args.test:
        # 测试几个热门景点
        test_cases = [
            ("故宫博物院", "北京", "Forbidden City"),
            ("外滩", "上海", "The Bund Shanghai"),
            ("西湖风景名胜区", "杭州", "West Lake Hangzhou"),
            ("兵马俑", "西安", "Terracotta Army"),
        ]
        for name, city, english in test_cases:
            asyncio.run(test_single_attraction(name, city, english))
    elif args.name and args.city:
        asyncio.run(test_single_attraction(args.name, args.city, args.english))
    else:
        # 运行完整预置
        asyncio.run(preset_attraction_images())