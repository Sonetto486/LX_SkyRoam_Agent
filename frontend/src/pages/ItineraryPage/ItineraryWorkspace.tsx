import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout, Tabs, Card, Button, Space, Tooltip, Empty, Spin, Typography, Tag, message, Popconfirm, Modal, Dropdown, Menu, Input, InputNumber, DatePicker, Select, Image } from 'antd';
import {
  EditOutlined,
  SyncOutlined,
  CarOutlined,
  SaveOutlined,
  PlusOutlined,
  EnvironmentOutlined,
  CalendarOutlined,
  UserOutlined,
  DeleteOutlined,
  ArrowLeftOutlined,
  ShareAltOutlined,
  UpOutlined,
  DownOutlined,
  MoreOutlined,
  CameraOutlined,
  ClockCircleOutlined,
  InfoCircleOutlined,
  CloudOutlined,
  WalletOutlined,
  CopyOutlined,
  EyeOutlined,
  SwapOutlined,
  SettingOutlined,
  HomeOutlined,
  CoffeeOutlined
} from '@ant-design/icons';
import MapComponent from '../../components/MapComponent/MapComponent';
import WeatherCard from '../../components/Itinerary/WeatherCard';
import ActivityEditModal from '../../components/Itinerary/ActivityEditModal';
import DateRangeEditor from '../../components/Itinerary/DateRangeEditor';
import RouteSegment from '../../components/Itinerary/RouteSegment';
import EnhancedActivityCard from '../../components/Itinerary/EnhancedActivityCard';
import HotelSection from '../../components/Itinerary/HotelSection';
import TransportSection from '../../components/Itinerary/TransportSection';
import DayScheduleSection from '../../components/Itinerary/DayScheduleSection';
import MealsSection from '../../components/Itinerary/MealsSection';
import AttractionsSection from '../../components/Itinerary/AttractionsSection';
import { buildApiUrl } from '../../config/api';
import { authFetch } from '../../utils/auth';
import './ItineraryWorkspace.css';

const { Content, Sider } = Layout;
const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;
const { Option } = Select;

// 行程数据接口
interface TravelPlan {
  id: number;
  title: string;
  description?: string;
  departure?: string;
  destination: string;
  start_date: string;
  end_date: string;
  duration_days: number;
  budget?: number;
  transportation?: string;
  preferences?: {
    travelers?: number;
    ageGroups?: string[];
    foodPreferences?: string[];
    dietaryRestrictions?: string[];
      parsed_locations?: Array<{
      id?: string | number;
      day: number;
      name: string;
      address?: string;
      position?: { lat: number; lng: number };
    }>;
  };
  status: string;
  score?: number;
  generated_plans?: any[];
  selected_plan?: any;
  is_public: boolean;
  items?: TravelPlanItem[];
  // 新增字段
  cities?: string[];
  members?: Array<{ name: string; role: string; avatar?: string }>;
  packing_list?: Array<{ name: string; category: string; checked: boolean }>;
  travel_mode?: string;
  tags?: string[];
}

// 行程项目接口
interface TravelPlanItem {
  id: number | string;
  title: string;
  description?: string;
  item_type: string;
  start_time?: string;
  end_time?: string;
  duration_hours?: number;
  location?: string;
  address?: string;
  coordinates?: { lat: number; lng: number };
  details?: any;
  images?: string[];
  // 新增字段用于增强显示
  time?: string;
  cost?: number;
  tips?: string;
  transport_note?: string;
}

// 活动编辑数据接口（id可选）
interface ActivityEditData {
  id?: number | string;
  title: string;
  description?: string;
  item_type: string;
  start_time?: string;
  end_time?: string;
  duration_hours?: number;
  location?: string;
  address?: string;
  coordinates?: { lat: number; lng: number };
  details?: any;
  images?: string[];
}

// 每日活动数据（优化版：分组结构）
interface DayActivity {
  date: string;
  hotel?: any;  // 住宿信息（仅第一天）
  transportation?: any;  // 交通信息
  schedule: any[];  // 日程时间轴
  meals: any[];  // 餐饮推荐（去重）
  attractions: any[];  // 景点列表（去重）
  daily_tips?: string[];  // 每日提示
  estimated_cost?: number;  // 每日预算
}

const ItineraryWorkspace: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [plan, setPlan] = useState<TravelPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeDay, setActiveDay] = useState(0);
  const [hoveredActivity, setHoveredActivity] = useState<number | string | null>(null);
  const [saving, setSaving] = useState(false);

  // 编辑弹窗状态
  const [activityModalVisible, setActivityModalVisible] = useState(false);
  const [editingActivity, setEditingActivity] = useState<ActivityEditData | null>(null);
  const [dateEditorVisible, setDateEditorVisible] = useState(false);

  // 新增状态
  const [planInfoModalVisible, setPlanInfoModalVisible] = useState(false);
  const [routeModalVisible, setRouteModalVisible] = useState(false);
  const [shareModalVisible, setShareModalVisible] = useState(false);
  const [weatherModalVisible, setWeatherModalVisible] = useState(false);
  const [weatherData, setWeatherData] = useState<any[]>([]);
  const [overviewModalVisible, setOverviewModalVisible] = useState(false);
  const [routeSegments, setRouteSegments] = useState<any[]>([]); // 路线段信息

  // 获取行程详情
  const fetchPlan = useCallback(async () => {
    if (!id) return;

    // Handle "new" case - create a new empty plan
    if (id === "new") {
      setLoading(true);
      try {
        const res = await authFetch(buildApiUrl('/travel-plans/new'), {
          method: 'POST',
        });
        if (!res.ok) {
          throw new Error('创建行程失败');
        }
        const data: TravelPlan = await res.json();
        // Redirect to the new plan's workspace
        navigate(`/itineraries/${data.id}`, { replace: true });
        return;
      } catch (err: any) {
        message.error('创建行程失败：' + (err.message || '未知错误'));
        navigate('/itineraries', { replace: true });
      } finally {
        setLoading(false);
      }
      return;
    }

    setLoading(true);
    try {
      const res = await authFetch(buildApiUrl(`/travel-plans/${id}`));
      if (!res.ok) {
        throw new Error('获取行程详情失败');
      }
      const data: TravelPlan = await res.json();
      setPlan(data);
    } catch (err: any) {
      message.error('获取行程详情失败：' + (err.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  }, [id, navigate]);

  useEffect(() => {
    fetchPlan();
  }, [fetchPlan]);

  // 保存行程
  const handleSave = async () => {
    if (!plan) return;
    setSaving(true);
    try {
      // 这里可以调用更新API保存当前状态
      message.success('行程已保存');
    } catch (err: any) {
      message.error('保存失败：' + (err.message || '未知错误'));
    } finally {
      setSaving(false);
    }
  };

  // 打开活动编辑弹窗
  const openActivityModal = (activity?: TravelPlanItem | ActivityEditData) => {
    setEditingActivity(activity || null);
    setActivityModalVisible(true);
  };

  // 保存活动
  const handleSaveActivity = async (activity: ActivityEditData) => {
    if (!plan || !id) return;
    try {
      if (activity.id) {
        // 更新现有活动
        const res = await authFetch(
          buildApiUrl(`/travel-plans/${id}/items/${activity.id}`),
          {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(activity),
          }
        );
        if (!res.ok) throw new Error('更新活动失败');
        message.success('活动已更新');
      } else {
        // 添加新活动
        const res = await authFetch(
          buildApiUrl(`/travel-plans/${id}/items`),
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(activity),
          }
        );
        if (!res.ok) throw new Error('添加活动失败');
        message.success('活动已添加');
      }
      fetchPlan();
    } catch (err: any) {
      message.error(err.message || '操作失败');
      throw err;
    }
  };

  // 删除活动
  const handleDeleteActivity = async (activityId: number | string) => {
    if (!plan || !id) return;
    try {
      const res = await authFetch(
        buildApiUrl(`/travel-plans/${id}/items/${activityId}`),
        { method: 'DELETE' }
      );
      if (!res.ok) throw new Error('删除失败');
      message.success('活动已删除');
      fetchPlan();
    } catch (err: any) {
      message.error(err.message || '删除失败');
    }
  };

  // 移动活动顺序（景点上移下移）
  const handleMoveActivity = async (activityId: number | string, direction: 'up' | 'down') => {
    if (!plan || !id) return;

    try {
      // 获取当前景点的时间
      const currentItem = plan.items?.find(item => item.id === activityId);
      if (!currentItem || !currentItem.start_time) {
        message.warning('无法移动此景点');
        return;
      }

      // 获取同一天的所有景点
      const currentDate = currentItem.start_time.split('T')[0];
      const sameDayItems = plan.items?.filter(item =>
        item.item_type === 'attraction' &&
        item.start_time &&
        item.start_time.split('T')[0] === currentDate
      ).sort((a, b) => {
        if (!a.start_time || !b.start_time) return 0;
        return new Date(a.start_time).getTime() - new Date(b.start_time).getTime();
      });

      if (!sameDayItems || sameDayItems.length < 2) {
        message.warning('景点数量不足，无法移动');
        return;
      }

      // 找到当前景点在列表中的位置
      const currentIndex = sameDayItems.findIndex(item => item.id === activityId);

      // 计算目标位置
      const targetIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;

      if (targetIndex < 0 || targetIndex >= sameDayItems.length) {
        message.warning('无法移动到该位置');
        return;
      }

      // 交换时间
      const targetItem = sameDayItems[targetIndex];

      // 更新两个景点的时间
      await authFetch(
        buildApiUrl(`/travel-plans/${id}/items/${activityId}`),
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            start_time: targetItem.start_time
          }),
        }
      );

      await authFetch(
        buildApiUrl(`/travel-plans/${id}/items/${targetItem.id}`),
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            start_time: currentItem.start_time
          }),
        }
      );

      message.success(`景点已${direction === 'up' ? '上移' : '下移'}`);
      fetchPlan();
    } catch (err: any) {
      message.error('移动失败：' + (err.message || '未知错误'));
    }
  };

  // 更新日期
  const handleUpdateDateRange = async (startDate: string, endDate: string, durationDays: number) => {
    if (!plan || !id) return;
    try {
      const res = await authFetch(buildApiUrl(`/travel-plans/${id}`), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_date: `${startDate}T00:00:00`,
          end_date: `${endDate}T23:59:59`,
          duration_days: durationDays,
        }),
      });
      if (!res.ok) throw new Error('更新失败');
      message.success('日期已更新');
      fetchPlan();
    } catch (err: any) {
      throw err;
    }
  };

  // 获取每日活动数据（增强版：包含住宿、餐饮、交通、日程等所有信息）
const getDayActivities = (): DayActivity[] => {
  if (!plan) return [];

  console.log('getDayActivities called, plan:', plan);
  console.log('plan.items:', plan.items);
  console.log('plan.selected_plan:', plan.selected_plan);
  console.log('plan.generated_plans:', plan.generated_plans);

  // 优先使用items数据（数据库中的实际数据，会被优化功能更新）
  // 只有当items为空时才使用JSON数据
  if (plan.items && plan.items.length > 0) {
    console.log('优先使用 items 数据（数据库实际数据）');
    const dayMap = new Map<string, TravelPlanItem[]>();
    plan.items.forEach(item => {
      const date = item.start_time ? item.start_time.split('T')[0] : plan.start_date.split('T')[0];
      if (!dayMap.has(date)) {
        dayMap.set(date, []);
      }
      dayMap.get(date)!.push(item);
    });

    // 如果有selected_plan，用它来补充住宿、餐饮、交通等丰富信息
    const richData = plan.selected_plan?.daily_itineraries || plan.generated_plans?.[0]?.daily_itineraries;
    const totalDays = richData?.length || 0;

    // 按日期排序，确保天数顺序正确，并转换为新的结构
    return Array.from(dayMap.entries())
      .sort(([dateA], [dateB]) => dateA.localeCompare(dateB))
      .map(([date, items], dayIndex) => {
        // 从richData中查找当天的补充信息
        const dayRichData = richData?.find((day: any) => day.date === date);

        // 判断是否需要显示交通信息
        // 只过滤掉跨城市的出发/返程交通（如北京到三亚的航班）
        // 保留旅游城市内部的交通信息（如三亚市内的公交、打车）
        const shouldShowTransport = (() => {
          if (!dayRichData?.transportation) return false;

          // 检查是否是跨城市交通
          const transport = dayRichData.transportation;
          const stage = transport.stage;

          // 如果明确标记为出发或返程阶段，则不显示
          if (stage === 'departure' || stage === 'return') {
            return false;
          }

          // 检查交通路线是否包含跨城市关键词
          const primaryRoutes = transport.primary_routes || [];
          for (const route of primaryRoutes) {
            const routeName = route.name || route.route || '';
            // 如果包含"到"字且涉及出发地，可能是跨城市交通
            if (routeName.includes('到') && (
              routeName.includes('北京') ||
              routeName.includes('上海') ||
              routeName.includes('广州') ||
              routeName.includes('深圳')
            )) {
              // 检查是否是旅游城市内部的交通
              const destination = plan.destination || '';
              if (!routeName.includes(destination)) {
                return false;
              }
            }
          }

          return true;
        })();

        return {
          date,
          // 住宿信息（从richData获取）
          hotel: plan.selected_plan?.hotel || plan.generated_plans?.[0]?.hotel || null,
          // 交通信息（过滤跨城市交通）
          transportation: shouldShowTransport ? dayRichData?.transportation : null,
          // 日程时间轴（从richData获取）
          schedule: dayRichData?.schedule || [],
          // 餐饮推荐（从richData获取）
          meals: dayRichData?.meals || [],
          // 景点列表（从items获取，这是关键！）
          attractions: items.filter(item => item.item_type === 'attraction').map(item => ({
            id: item.id,  // 添加id字段，用于路线匹配
            name: item.title,
            address: item.address,
            coordinates: item.coordinates,
            type: item.details?.type,
            score: item.details?.score,
            description: item.description,
          })),
          // 每日提示（从richData获取）
          daily_tips: dayRichData?.daily_tips || [],
          // 每日预算（从richData获取）
          estimated_cost: dayRichData?.estimated_cost || 0,
        };
      });
  }

  // 如果items为空，才使用JSON数据（AI生成的静态数据）
  if (plan.selected_plan?.daily_itineraries) {
    console.log('items为空，使用 selected_plan 数据');
    return extractRichDailyItineraries(plan.selected_plan);
  }

  if (plan.generated_plans && plan.generated_plans.length > 0) {
    console.log('items为空，使用 generated_plans 数据');
    const firstPlan = plan.generated_plans[0];
    if (firstPlan.daily_itineraries) {
      return extractRichDailyItineraries(firstPlan);
    }
  }

  // 兼容智能导入的 parsed_locations
  if (plan.preferences?.parsed_locations) {
    const locationMap: Record<string, TravelPlanItem[]> = {};
    plan.preferences.parsed_locations.forEach((loc: any) => {
      const dayKey = `day_${loc.day || 1}`;
      if (!locationMap[dayKey]) locationMap[dayKey] = [];

      const activityTitle = loc.name || "未命名景点";
      const activityAddress = (loc.address && loc.address !== "未知")
        ? loc.address
        : activityTitle || "未知地址";

      locationMap[dayKey].push({
        id: Number(loc.id) || Date.now(),
        title: activityTitle,
        address: activityAddress,
        location: activityAddress,
        item_type: loc.type || "景点",
        coordinates: loc.position || loc.coordinates || { lat: 0, lng: 0 },
        start_time: plan.start_date,
      } as TravelPlanItem);
    });

    const aiDays = Object.values(locationMap).map((activities, i) => ({
      date: getDateByOffset(plan.start_date, i),
      hotel: null,
      transportation: null,
      schedule: activities.map(item => ({
        time: undefined,
        activity: item.title,
        location: item.location || item.address,
        description: undefined,
      })),
      meals: [],
      attractions: activities.filter(item => item.item_type === 'attraction' || item.item_type === '景点').map(item => ({
        name: item.title,
        address: item.address,
        coordinates: item.coordinates,
      })),
      daily_tips: [],
      estimated_cost: 0,
    }));

    if (aiDays.length) return aiDays;
  }

  // 默认返回空数组
  return [];
};

  // 新增：从生成方案中提取丰富的每日行程数据（优化版：智能去重）
  const extractRichDailyItineraries = (planData: any): DayActivity[] => {
    if (!planData.daily_itineraries || !plan) return [];

    console.log('Extracting rich daily itineraries from planData:', planData);

    const totalDays = planData.daily_itineraries.length;

    return planData.daily_itineraries.map((day: any, dayIndex: number) => {
      const date = day.date || getDateByOffset(plan.start_date, dayIndex);

      console.log(`Processing day ${dayIndex}:`, day);

      // 判断是否需要显示交通信息
      // 只过滤掉跨城市的出发/返程交通，保留旅游城市内部的交通
      const shouldShowTransport = (() => {
        if (!day.transportation) return false;

        const stage = day.transportation.stage;

        // 如果明确标记为出发或返程阶段，则不显示
        if (stage === 'departure' || stage === 'return') {
          return false;
        }

        // 检查交通路线是否包含跨城市关键词
        const primaryRoutes = day.transportation.primary_routes || [];
        for (const route of primaryRoutes) {
          const routeName = route.name || route.route || '';
          // 如果包含"到"字且涉及主要城市，可能是跨城市交通
          if (routeName.includes('到') && (
            routeName.includes('北京') ||
            routeName.includes('上海') ||
            routeName.includes('广州') ||
            routeName.includes('深圳')
          )) {
            // 检查是否是旅游城市内部的交通
            const destination = plan.destination || '';
            if (!routeName.includes(destination)) {
              return false;
            }
          }
        }

        return true;
      })();

      // 返回分组数据结构
      return {
        date,
        // 住宿信息（所有天都可以访问，用于路径优化）
        hotel: planData.hotel || null,
        // 交通信息（过滤跨城市交通）
        transportation: shouldShowTransport ? day.transportation : null,
        // 日程时间轴（所有活动）
        schedule: day.schedule || [],
        // 餐饮推荐（去重）
        meals: extractMealsWithDedup(day.meals, day.schedule),
        // 景点列表（去重）
        attractions: extractAttractionsWithDedup(day.attractions, day.schedule),
        // 每日提示
        daily_tips: day.daily_tips || [],
        // 每日预算
        estimated_cost: day.estimated_cost || 0,
      };
    });
  };

  // 新增：提取餐饮信息并去重
  const extractMealsWithDedup = (meals: any[], schedule: any[]): any[] => {
    if (!meals) return [];

    return meals.filter(meal => {
      // 检查 schedule 中是否已有相同时间的餐饮
      const existsInSchedule = schedule?.some(item =>
        item.time === meal.time &&
        (item.activity?.includes(meal.type) || item.activity?.includes('餐'))
      );

      if (existsInSchedule) {
        console.log(`Skipping duplicate meal: ${meal.type} at ${meal.time}`);
      }

      return !existsInSchedule;
    });
  };

  // 新增：提取景点信息（保留所有景点，标记是否在schedule中）
  const extractAttractionsWithDedup = (attractions: any[], schedule: any[]): any[] => {
    if (!attractions) return [];

    // 返回所有景点，但标记是否已在schedule中提到
    return attractions.map(attr => {
      const existsInSchedule = schedule?.some(item =>
        item.location?.includes(attr.name) || item.activity?.includes(attr.name)
      );

      return {
        ...attr,
        inSchedule: existsInSchedule, // 标记是否已在日程中
      };
    });
  };

  // 根据偏移量计算日期
  const getDateByOffset = (startDate: string, offset: number): string => {
    const date = new Date(startDate);
    date.setDate(date.getDate() + offset);
    return date.toISOString().split('T')[0];
  };

  // 格式化日期显示
  const formatDateDisplay = (dateStr: string) => {
    const date = new Date(dateStr);
    return `${date.getMonth() + 1}月${date.getDate()}日`;
  };

  // 准备地图标记数据
  const getMapMarkers = () => {
    const dayActivities = getDayActivities();
    if (dayActivities.length === 0 || activeDay >= dayActivities.length) return [];

    const day = dayActivities[activeDay];
    const markers: any[] = [];

    // 从景点中提取坐标
    if (day.attractions) {
      day.attractions.forEach((attr: any) => {
        if (attr.coordinates && attr.coordinates.lat && attr.coordinates.lng) {
          markers.push({
            id: attr.id || attr.name,  // 优先使用id，如果没有则使用name
            name: attr.name,
            position: attr.coordinates,
            address: attr.address || '',
            isHovered: false,
          });
        }
      });
    }

    // 从住宿中提取坐标（仅作为标注点，不参与路线规划）
    if (day.hotel && day.hotel.coordinates) {
      markers.push({
        id: 'hotel',
        name: day.hotel.name,
        position: day.hotel.coordinates,
        address: day.hotel.address || '',
        isHovered: false,
        isHotel: true,  // 标记为酒店，不参与路线绘制
      });
    }

    return markers;
  };

  // 获取地图中心点
  const getMapCenter = () => {
    const markers = getMapMarkers();
    if (markers.length > 0) {
      return markers[0].position;
    }

    // 如果没有标记点，使用目的地城市的坐标
    if (plan?.destination) {
      // 常见城市坐标映射
      const cityCoordinates: Record<string, { lat: number; lng: number }> = {
        '北京': { lat: 39.9042, lng: 116.4074 },
        '上海': { lat: 31.2304, lng: 121.4737 },
        '广州': { lat: 23.1291, lng: 113.2644 },
        '深圳': { lat: 22.5431, lng: 114.0579 },
        '成都': { lat: 30.5728, lng: 104.0668 },
        '杭州': { lat: 30.2741, lng: 120.1551 },
        '西安': { lat: 34.3416, lng: 108.9398 },
        '重庆': { lat: 29.4316, lng: 106.9123 },
        '武汉': { lat: 30.5928, lng: 114.3055 },
        '南京': { lat: 32.0603, lng: 118.7969 },
        '天津': { lat: 39.0842, lng: 117.2009 },
        '苏州': { lat: 31.2989, lng: 120.5853 },
        '郑州': { lat: 34.7466, lng: 113.6254 },
        '长沙': { lat: 28.2282, lng: 112.9388 },
        '青岛': { lat: 36.0671, lng: 120.3826 },
        '大连': { lat: 38.9140, lng: 121.6147 },
        '厦门': { lat: 24.4798, lng: 118.0894 },
        '昆明': { lat: 25.0389, lng: 102.7183 },
        '三亚': { lat: 18.2528, lng: 109.5120 },
        '贵阳': { lat: 26.6470, lng: 106.6302 },
        '桂林': { lat: 25.2744, lng: 110.2900 },
        '丽江': { lat: 26.8721, lng: 100.2297 },
        '拉萨': { lat: 29.6500, lng: 91.1000 },
      };

      // 尝试匹配城市名
      const cityName = plan.destination.replace('市', '');
      if (cityCoordinates[cityName]) {
        return cityCoordinates[cityName];
      }

      // 如果城市不在列表中，尝试模糊匹配
      for (const [city, coords] of Object.entries(cityCoordinates)) {
        if (plan.destination.includes(city)) {
          return coords;
        }
      }
    }

    // 默认返回北京坐标
    return { lat: 39.9042, lng: 116.4074 };
  };

  // 获取成员数量
  const getMemberCount = (): number => {
    return plan?.preferences?.travelers || 1;
  };

  // 获取预算显示
  const getBudgetDisplay = (): string => {
    if (plan?.budget) {
      // 将预算数值转换为类型显示
      if (plan.budget <= 3000) {
        return '经济型（< 3000元/人）';
      } else if (plan.budget <= 8000) {
        return '舒适型（3000-8000元/人）';
      } else {
        return '豪华型（> 8000元/人）';
      }
    }
    return '未设置';
  };

  // 打开行程信息编辑弹窗
  const openPlanInfoModal = () => {
    setPlanInfoModalVisible(true);
  };

  // 保存行程信息
  const handleSavePlanInfo = async (values: any) => {
    if (!plan) return;
    try {
      const res = await authFetch(buildApiUrl(`/travel-plans/${plan.id}`), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      if (!res.ok) throw new Error('更新失败');
      message.success('行程信息已更新');
      setPlanInfoModalVisible(false);
      fetchPlan();
    } catch (err: any) {
      message.error('更新失败：' + (err.message || '未知错误'));
    }
  };

  // 获取天气数据（智能判断日期）
  const fetchWeatherData = async () => {
    if (!plan) return;

    // 确保至少显示7天，或者行程天数（取较大值）
    const days = Math.max(7, plan.duration_days);

    try {
      // 调用后端天气API，传递旅行日期
      const res = await fetch(buildApiUrl(`/weather?city=${encodeURIComponent(plan.destination)}&days=${days}&travel_date=${encodeURIComponent(plan.start_date)}`));

      if (!res.ok) {
        // 使用模拟数据
        setWeatherData(generateMockWeatherFromStart(plan.start_date, days));
        return;
      }

      const data = await res.json();

      if (data.forecast && data.forecast.length > 0) {
        setWeatherData(data.forecast.map((cast: any) => ({
          date: cast.date,
          dayWeather: cast.dayweather,
          dayTemp: cast.daytemp,
          nightTemp: cast.nighttemp,
          dateMode: data.date_mode,
          dateReason: data.date_reason,
        })));
      } else {
        // 无数据时使用模拟数据
        setWeatherData(generateMockWeatherFromStart(plan.start_date, days));
      }
    } catch (err) {
      console.error('获取天气失败:', err);
      // 失败时使用模拟数据
      setWeatherData(generateMockWeatherFromStart(plan.start_date, days));
    }
  };

  // 生成从指定日期开始的模拟天气数据
  const generateMockWeatherFromStart = (startDate: string, count: number) => {
    const mockData = [];
    const weathers = ['晴', '多云', '阴', '小雨', '中雨'];
    const start = new Date(startDate);

    for (let i = 0; i < count; i++) {
      const date = new Date(start);
      date.setDate(date.getDate() + i);
      mockData.push({
        date: date.toISOString().split('T')[0],
        dayWeather: weathers[Math.floor(Math.random() * weathers.length)],
        dayTemp: String(20 + Math.floor(Math.random() * 10)),
        nightTemp: String(15 + Math.floor(Math.random() * 5)),
      });
    }
    return mockData;
  };

  // 打开天气弹窗
  const openWeatherModal = () => {
    fetchWeatherData();
    setWeatherModalVisible(true);
  };

  // 一键优化行程
  const handleOptimize = async () => {
    if (!plan) return;
    message.loading({ content: '正在优化行程...', key: 'optimize' });
    try {
      const res = await authFetch(buildApiUrl(`/travel-plans/${plan.id}/optimize`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fill_coordinates: true,
          balance_schedule: true
        })
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || '优化失败');
      }
      const data = await res.json();
      const stats = data.stats || {};
      const filledCount = stats.coordinates_filled || 0;
      const movedCount = stats.items_moved || 0;

      message.success({
        content: `优化完成：填充${filledCount}个景点坐标，移动${movedCount}个景点`,
        key: 'optimize',
        duration: 3
      });

      // 刷新行程数据以显示更新后的地图标记
      fetchPlan();
    } catch (err: any) {
      message.error({ content: '优化失败：' + (err.message || '未知错误'), key: 'optimize' });
    }
  };

  // 路线优化
  const handleRouteOptimize = async () => {
    if (!plan) return;
    message.loading({ content: '正在优化路线...', key: 'route-optimize' });
    try {
      const res = await authFetch(buildApiUrl(`/travel-plans/${plan.id}/optimize-route`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || '路线优化失败');
      }
      const data = await res.json();

      // 保存路线段信息（按天分组）
      if (data.optimized_days && data.optimized_days.length > 0) {
        setRouteSegments(data.optimized_days);
      }

      const stats = data.stats || {};
      const totalDistance = stats.total_distance || 0;
      const totalDuration = stats.total_duration || 0;
      const daysOptimized = stats.days_optimized || 0;

      // 检查是否已经最优
      if (data.already_optimized) {
        message.info({
          content: '路线已经是最优，无需优化',
          key: 'route-optimize',
          duration: 3
        });
      } else {
        message.success({
          content: `路线优化完成：优化${daysOptimized}天，总距离${totalDistance.toFixed(1)}公里，约${Math.round(totalDuration / 60)}小时`,
          key: 'route-optimize',
          duration: 4
        });
      }

      // 刷新行程数据以显示更新后的路线
      fetchPlan();
    } catch (err: any) {
      message.error({ content: '路线优化失败：' + (err.message || '未知错误'), key: 'route-optimize' });
    }
  };

  // 导出行程
  const handleExport = async (format: string) => {
    if (!plan) return;
    try {
      const res = await authFetch(buildApiUrl(`/travel-plans/${plan.id}/export?format=${format}`));
      if (!res.ok) throw new Error('导出失败');

      if (format === 'json') {
        const data = await res.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${plan.title}.json`;
        a.click();
        URL.revokeObjectURL(url);
      } else if (format === 'html') {
        const html = await res.text();
        const blob = new Blob([html], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${plan.title}.html`;
        a.click();
        URL.revokeObjectURL(url);
      }
      message.success('导出成功');
    } catch (err: any) {
      message.error('导出失败：' + (err.message || '未知错误'));
    }
  };

  // 分享行程
  const handleShare = async (type: string) => {
    if (!plan) return;
    const shareUrl = `${window.location.origin}/itineraries/${plan.id}`;

    switch (type) {
      case 'link':
        navigator.clipboard.writeText(shareUrl);
        message.success('链接已复制到剪贴板');
        break;
      case 'public':
        try {
          const res = await authFetch(buildApiUrl(`/travel-plans/${plan.id}/publish`), {
            method: 'PUT',
          });
          if (!res.ok) throw new Error('发布失败');
          message.success('行程已发布为公开');
          fetchPlan();
        } catch (err: any) {
          message.error('发布失败：' + (err.message || '未知错误'));
        }
        break;
    }
    setShareModalVisible(false);
  };

  // 获取地图控制菜单
  const getMapControlMenu = () => (
    <Menu>
      <Menu.Item key="route" icon={<SwapOutlined />} onClick={handleRouteOptimize}>
        路线优化
      </Menu.Item>
      <Menu.Item key="optimize" icon={<SyncOutlined />} onClick={handleOptimize}>
        一键优化
      </Menu.Item>
      <Menu.Item key="weather" icon={<CloudOutlined />} onClick={openWeatherModal}>
        天气预览
      </Menu.Item>
      <Menu.Item key="overview" icon={<InfoCircleOutlined />} onClick={() => setOverviewModalVisible(true)}>
        行程概览
      </Menu.Item>
      <Menu.Divider />
      <Menu.Item key="export-json" icon={<CopyOutlined />} onClick={() => handleExport('json')}>
        导出JSON
      </Menu.Item>
      <Menu.Item key="export-html" icon={<CopyOutlined />} onClick={() => handleExport('html')}>
        导出HTML
      </Menu.Item>
    </Menu>
  );

  // 获取分享菜单
  const getShareMenu = () => (
    <Menu>
      <Menu.Item key="link" icon={<CopyOutlined />} onClick={() => handleShare('link')}>
        复制链接
      </Menu.Item>
      <Menu.Item key="public" icon={<EyeOutlined />} onClick={() => handleShare('public')} disabled={plan?.is_public}>
        {plan?.is_public ? '已公开' : '发布为公开'}
      </Menu.Item>
    </Menu>
  );

  if (loading) {
    return (
      <div className="workspace-loading">
        <Spin size="large" tip="加载行程详情..." />
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="workspace-error">
        <Empty description="行程不存在或无权访问">
          <Button type="primary" onClick={() => navigate('/itineraries')}>
            返回行程列表
          </Button>
        </Empty>
      </div>
    );
  }

  const dayActivities = getDayActivities();

  return (
    <Layout className="workspace-layout">
      {/* 左半屏：信息流面板 */}
      <Sider width={600} className="workspace-sider">
        {/* 顶部看板 */}
        <div className="workspace-header">
          <Button
            type="link"
            className="back-btn"
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/itineraries')}
          >
            返回列表
          </Button>

          <div className="itinerary-info">
            <Title level={2} className="itinerary-title">{plan.title}</Title>
            <div className="itinerary-meta">
              <Space size={16}>
                <Space size={4}>
                  <EnvironmentOutlined />
                  <span>{plan.destination}</span>
                </Space>
                <Space size={4}>
                  <CalendarOutlined />
                  <span>{plan.duration_days}天</span>
                </Space>
                <Space size={4}>
                  <UserOutlined />
                  <span>{getMemberCount()}人</span>
                </Space>
                <Space size={4}>
                  <WalletOutlined />
                  <span>{getBudgetDisplay()}</span>
                </Space>
              </Space>
            </div>
            <div className="itinerary-date">
              {formatDateDisplay(plan.start_date)} - {formatDateDisplay(plan.end_date)}
              <Button
                type="link"
                size="small"
                icon={<EditOutlined />}
                onClick={() => setDateEditorVisible(true)}
                style={{ marginLeft: 8 }}
              >
                编辑日期
              </Button>
              <Button
                type="link"
                size="small"
                icon={<SettingOutlined />}
                onClick={openPlanInfoModal}
                style={{ marginLeft: 8 }}
              >
                编辑信息
              </Button>
            </div>
            {plan.description && (
              <Paragraph className="itinerary-desc" ellipsis={{ rows: 2 }}>
                {plan.description}
              </Paragraph>
            )}
            <div className="itinerary-actions">
              <Button size="small" icon={<CloudOutlined />} onClick={openWeatherModal}>
                天气预览
              </Button>
              <Button size="small" icon={<InfoCircleOutlined />} onClick={() => setOverviewModalVisible(true)}>
                行程概览
              </Button>
            </div>
          </div>

          {/* 天气信息 */}
          <WeatherCard
            city={plan.destination}
            startDate={plan.start_date}
            days={Math.max(7, plan.duration_days)}
          />
        </div>

        {/* 天数标签页 */}
        {dayActivities.length > 0 ? (
          <Tabs
            activeKey={activeDay.toString()}
            onChange={(key) => setActiveDay(parseInt(key))}
            className="day-tabs"
            tabBarExtraContent={
              <Button size="small" icon={<PlusOutlined />} onClick={() => openActivityModal()}>
                添加活动
              </Button>
            }
          >
            {dayActivities.map((day, index) => (
              <Tabs.TabPane
                key={index}
                tab={
                  <Space size={4}>
                    <span className="day-label">Day {index + 1}</span>
                    <span className="day-date">{formatDateDisplay(day.date)}</span>
                  </Space>
                }
              >
                {/* 分类标签页 */}
                <div className="activities-list">
                  <Tabs
                    defaultActiveKey="schedule"
                    className="category-tabs"
                    size="small"
                  >
                    {/* 日程时间轴 */}
                    <Tabs.TabPane
                      key="schedule"
                      tab={
                        <Space size={4}>
                          <ClockCircleOutlined />
                          <span>今日日程</span>
                          {day.schedule && day.schedule.length > 0 && (
                            <Tag color="blue" style={{ marginLeft: 4 }}>{day.schedule.length}</Tag>
                          )}
                        </Space>
                      }
                    >
                      {day.schedule && day.schedule.length > 0 ? (
                        <DayScheduleSection
                          schedule={day.schedule}
                          onEdit={(index) => {
                            // 从schedule中找到对应的活动，转换为TravelPlanItem格式
                            const scheduleItem = day.schedule[index];
                            if (scheduleItem) {
                              // 尝试从items中找到匹配的活动
                              const matchingItem = plan.items?.find(item =>
                                item.title === scheduleItem.activity ||
                                item.location === scheduleItem.location
                              );

                              if (matchingItem) {
                                openActivityModal(matchingItem);
                              } else {
                                // 如果找不到，创建一个新的活动数据
                                openActivityModal({
                                  title: scheduleItem.activity || '',
                                  item_type: 'attraction',
                                  location: scheduleItem.location,
                                  description: scheduleItem.description,
                                  start_time: day.date,
                                  details: {
                                    cost: scheduleItem.cost,
                                    tips: scheduleItem.tips,
                                    transport_note: scheduleItem.transport_note,
                                    priority: scheduleItem.priority
                                  }
                                });
                              }
                            }
                          }}
                          onDelete={(index) => {
                            // 从schedule中找到对应的活动，尝试从items中删除
                            const scheduleItem = day.schedule[index];
                            if (scheduleItem) {
                              const matchingItem = plan.items?.find(item =>
                                item.title === scheduleItem.activity ||
                                item.location === scheduleItem.location
                              );

                              if (matchingItem && matchingItem.id) {
                                handleDeleteActivity(matchingItem.id);
                              } else {
                                message.warning('无法删除此活动：未找到对应的行程项');
                              }
                            }
                          }}
                        />
                      ) : (
                        <Empty description="暂无日程安排" style={{ padding: '40px 0' }} />
                      )}
                    </Tabs.TabPane>

                    {/* 景点列表 */}
                    <Tabs.TabPane
                      key="attractions"
                      tab={
                        <Space size={4}>
                          <CameraOutlined />
                          <span>景点列表</span>
                          {day.attractions && day.attractions.length > 0 && (
                            <Tag color="green" style={{ marginLeft: 4 }}>{day.attractions.length}</Tag>
                          )}
                        </Space>
                      }
                    >
                      {day.attractions && day.attractions.length > 0 ? (
                        <AttractionsSection
                          attractions={day.attractions}
                          hotelAddress={day.hotel?.address}
                          hotelCoordinates={day.hotel?.coordinates}
                          planId={plan?.id}
                          dayDate={day.date}
                          onRouteOptimized={(data) => {
                            // Handle route segments for map display
                            // data 包含 { date, route_segments, ordered_items }
                            console.log('收到路线优化数据:', data);
                            setRouteSegments(prev => {
                              const existing = prev.find(r => r.date === data.date);
                              if (existing) {
                                return prev.map(r => r.date === data.date ? data : r);
                              }
                              return [...prev, data];
                            });
                          }}
                          onEditAttraction={(index) => {
                            // 从attractions中找到对应的景点
                            const attraction = day.attractions[index];
                            if (attraction) {
                              // 尝试从items中找到匹配的景点
                              const matchingItem = plan.items?.find(item =>
                                item.title === attraction.name ||
                                item.address === attraction.address
                              );

                              if (matchingItem) {
                                openActivityModal(matchingItem);
                              } else {
                                // 如果找不到，创建一个新的活动数据
                                openActivityModal({
                                  title: attraction.name,
                                  item_type: 'attraction',
                                  location: attraction.address,
                                  address: attraction.address,
                                  coordinates: attraction.coordinates,
                                  description: attraction.description,
                                  start_time: day.date,
                                  details: {
                                    type: attraction.type,
                                    score: attraction.score,
                                    priority: attraction.priority
                                  }
                                });
                              }
                            }
                          }}
                          onDeleteAttraction={(index) => {
                            // 从attractions中找到对应的景点，尝试从items中删除
                            const attraction = day.attractions[index];
                            if (attraction) {
                              const matchingItem = plan.items?.find(item =>
                                item.title === attraction.name ||
                                item.address === attraction.address
                              );

                              if (matchingItem && matchingItem.id) {
                                handleDeleteActivity(matchingItem.id);
                              } else {
                                message.warning('无法删除此景点：未找到对应的行程项');
                              }
                            }
                          }}
                          onTogglePriority={(index, priority) => {
                            // 更新景点的优先级
                            const attraction = day.attractions[index];
                            if (attraction) {
                              const matchingItem = plan.items?.find(item =>
                                item.title === attraction.name ||
                                item.address === attraction.address
                              );

                              if (matchingItem && matchingItem.id) {
                                // 更新details中的priority
                                const updatedDetails = {
                                  ...(matchingItem.details || {}),
                                  priority: priority
                                };

                                handleSaveActivity({
                                  id: matchingItem.id,
                                  title: matchingItem.title,
                                  item_type: matchingItem.item_type,
                                  details: updatedDetails
                                } as any).catch(err => {
                                  message.error('更新优先级失败');
                                });
                              } else {
                                message.warning('无法更新优先级：未找到对应的行程项');
                              }
                            }
                          }}
                          onMoveAttraction={(index, direction) => {
                            // 移动景点顺序
                            const attraction = day.attractions[index];
                            if (attraction) {
                              const matchingItem = plan.items?.find(item =>
                                item.title === attraction.name ||
                                item.address === attraction.address
                              );

                              if (matchingItem && matchingItem.id) {
                                handleMoveActivity(matchingItem.id, direction);
                              } else {
                                message.warning('无法移动此景点：未找到对应的行程项');
                              }
                            }
                          }}
                        />
                      ) : (
                        <Empty description="暂无景点安排" style={{ padding: '40px 0' }} />
                      )}
                    </Tabs.TabPane>

                    {/* 住宿推荐 */}
                    <Tabs.TabPane
                      key="hotel"
                      tab={
                        <Space size={4}>
                          <HomeOutlined />
                          <span>住宿推荐</span>
                          {day.hotel && <Tag color="purple" style={{ marginLeft: 4 }}>1</Tag>}
                        </Space>
                      }
                    >
                      {day.hotel ? (
                        <HotelSection hotel={day.hotel} />
                      ) : (
                        <Empty description="暂无住宿推荐" style={{ padding: '40px 0' }} />
                      )}
                    </Tabs.TabPane>

                    {/* 交通信息 */}
                    <Tabs.TabPane
                      key="transport"
                      tab={
                        <Space size={4}>
                          <CarOutlined />
                          <span>交通信息</span>
                          {day.transportation && <Tag color="cyan" style={{ marginLeft: 4 }}>1</Tag>}
                        </Space>
                      }
                    >
                      {day.transportation ? (
                        <TransportSection transportation={day.transportation} />
                      ) : (
                        <Empty description="暂无交通信息" style={{ padding: '40px 0' }} />
                      )}
                    </Tabs.TabPane>

                    {/* 餐饮推荐 */}
                    <Tabs.TabPane
                      key="meals"
                      tab={
                        <Space size={4}>
                          <CoffeeOutlined />
                          <span>餐饮推荐</span>
                          {day.meals && day.meals.length > 0 && (
                            <Tag color="orange" style={{ marginLeft: 4 }}>{day.meals.length}</Tag>
                          )}
                        </Space>
                      }
                    >
                      {day.meals && day.meals.length > 0 ? (
                        <MealsSection meals={day.meals} />
                      ) : (
                        <Empty description="暂无餐饮推荐" style={{ padding: '40px 0' }} />
                      )}
                    </Tabs.TabPane>
                  </Tabs>

                  {/* 添加活动按钮 */}
                  <Button
                    type="dashed"
                    block
                    icon={<PlusOutlined />}
                    className="add-activity-btn"
                    onClick={() => openActivityModal()}
                  >
                    添加活动
                  </Button>
                </div>
              </Tabs.TabPane>
            ))}
          </Tabs>
        ) : (
          <div className="empty-activities">
            <Empty description="暂无行程安排">
              <Button type="primary" icon={<PlusOutlined />} onClick={() => openActivityModal()}>
                添加活动
              </Button>
            </Empty>
          </div>
        )}
      </Sider>

      {/* 右半屏：地图模式 */}
      <Content className="workspace-content">
        {/* 地图组件 */}
        <MapComponent
          markers={getMapMarkers()}
          center={getMapCenter()}
          zoom={12}
          viewMode="day"
          currentDay={activeDay + 1}
          routeSegments={routeSegments}
        />

        {/* 地图控制按钮 */}
        <div className="map-controls">
          <Dropdown overlay={getMapControlMenu()} trigger={['click']} placement="bottomRight">
            <Tooltip title="更多操作">
              <Button
                icon={<MoreOutlined />}
                className="map-control-btn"
              />
            </Tooltip>
          </Dropdown>
          <Tooltip title="显示交通工具">
            <Button
              icon={<CarOutlined />}
              className="map-control-btn"
            />
          </Tooltip>
          <Tooltip title="保存行程">
            <Button
              icon={<SaveOutlined />}
              className="map-control-btn primary"
              loading={saving}
              onClick={handleSave}
            />
          </Tooltip>
          <Dropdown overlay={getShareMenu()} trigger={['click']} placement="bottomRight">
            <Tooltip title="分享行程">
              <Button
                icon={<ShareAltOutlined />}
                className="map-control-btn success"
              />
            </Tooltip>
          </Dropdown>
        </div>
      </Content>

      {/* 活动编辑弹窗 */}
      <ActivityEditModal
        visible={activityModalVisible}
        activity={editingActivity}
        date={dayActivities[activeDay]?.date}
        startDate={plan?.start_date}
        endDate={plan?.end_date}
        onCancel={() => {
          setActivityModalVisible(false);
          setEditingActivity(null);
        }}
        onOk={handleSaveActivity}
      />

      {/* 日期编辑弹窗 */}
      <DateRangeEditor
        visible={dateEditorVisible}
        startDate={plan?.start_date}
        endDate={plan?.end_date}
        durationDays={plan?.duration_days}
        onCancel={() => setDateEditorVisible(false)}
        onOk={handleUpdateDateRange}
      />

      {/* 行程信息编辑弹窗 */}
      <Modal
        title="编辑行程信息"
        open={planInfoModalVisible}
        onCancel={() => setPlanInfoModalVisible(false)}
        onOk={() => {
          // 收集表单数据
          const title = (document.getElementById('plan-title') as HTMLInputElement)?.value;
          const description = (document.getElementById('plan-description') as HTMLTextAreaElement)?.value;
          const departure = (document.getElementById('plan-departure') as HTMLInputElement)?.value;
          const destination = (document.getElementById('plan-destination') as HTMLInputElement)?.value;
          const travelers = (document.getElementById('plan-travelers') as HTMLInputElement)?.value;
          const budget = (document.getElementById('plan-budget') as HTMLInputElement)?.value;
          const travelMode = (document.getElementById('plan-travel-mode') as HTMLSelectElement)?.value;

          handleSavePlanInfo({
            title,
            description,
            departure,
            destination,
            budget: budget ? parseFloat(budget) : undefined,
            travel_mode: travelMode,
            preferences: {
              ...plan?.preferences,
              travelers: travelers ? parseInt(travelers) : undefined,
            },
          });
        }}
        width={700}
      >
        {plan && (
          <div className="plan-info-form">
            <div className="form-item">
              <Text strong>行程标题</Text>
              <Input
                className="form-input"
                defaultValue={plan.title}
                id="plan-title"
              />
            </div>
            <div className="form-item">
              <Text strong>行程描述</Text>
              <TextArea
                className="form-textarea"
                defaultValue={plan.description || ''}
                id="plan-description"
                rows={3}
              />
            </div>
            <div className="form-row">
              <div className="form-item">
                <Text strong>出发地</Text>
                <Input
                  className="form-input"
                  defaultValue={plan.departure || ''}
                  id="plan-departure"
                />
              </div>
              <div className="form-item">
                <Text strong>目的地</Text>
                <Input
                  className="form-input"
                  defaultValue={plan.destination}
                  id="plan-destination"
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-item">
                <Text strong>出行人数</Text>
                <InputNumber
                  style={{ width: '100%' }}
                  min={1}
                  max={20}
                  defaultValue={plan.preferences?.travelers || 1}
                  id="plan-travelers"
                />
              </div>
              <div className="form-item">
                <Text strong>预算（元）</Text>
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  defaultValue={plan.budget || 0}
                  id="plan-budget"
                />
              </div>
            </div>
            <div className="form-item">
              <Text strong>出行方式</Text>
              <Select
                style={{ width: '100%' }}
                defaultValue={plan.travel_mode || 'flight'}
                id="plan-travel-mode"
                options={[
                  { value: 'flight', label: '飞机' },
                  { value: 'train', label: '火车' },
                  { value: 'car', label: '自驾' },
                  { value: 'bus', label: '大巴' },
                  { value: 'self_drive', label: '自驾游' },
                ]}
              />
            </div>
            {plan.cities && plan.cities.length > 0 && (
              <div className="form-item">
                <Text strong>途经城市</Text>
                <div style={{ marginTop: 8 }}>
                  {plan.cities.map((city, index) => (
                    <Tag key={index} color="blue" style={{ marginBottom: 4 }}>
                      {city}
                    </Tag>
                  ))}
                </div>
              </div>
            )}
            {plan.members && plan.members.length > 0 && (
              <div className="form-item">
                <Text strong>参与成员</Text>
                <div style={{ marginTop: 8 }}>
                  {plan.members.map((member, index) => (
                    <Tag key={index} color="green" style={{ marginBottom: 4 }}>
                      {member.name} ({member.role})
                    </Tag>
                  ))}
                </div>
              </div>
            )}
            {plan.tags && plan.tags.length > 0 && (
              <div className="form-item">
                <Text strong>行程标签</Text>
                <div style={{ marginTop: 8 }}>
                  {plan.tags.map((tag, index) => (
                    <Tag key={index} color="purple" style={{ marginBottom: 4 }}>
                      {tag}
                    </Tag>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* 天气预览弹窗 */}
      <Modal
        title={`${plan?.destination || ''} 天气预报`}
        open={weatherModalVisible}
        onCancel={() => setWeatherModalVisible(false)}
        footer={null}
        width={900}
      >
        <div className="weather-preview-content">
          {weatherData.length > 0 ? (
            <>
              <div style={{ marginBottom: 12, color: '#666' }}>
                行程日期：{plan?.start_date?.slice(0, 10)} 至 {plan?.end_date?.slice(0, 10)}（共 {plan?.duration_days} 天）
                {weatherData[0]?.dateReason && (
                  <div style={{ marginTop: 4, fontSize: 12 }}>
                    {weatherData[0]?.dateMode === 'travel_date' ? (
                      <span style={{ color: '#52c41a' }}>✓ 显示行程期间天气</span>
                    ) : (
                      <span style={{ color: '#1890ff' }}>显示近期天气：{weatherData[0]?.dateReason}</span>
                    )}
                  </div>
                )}
              </div>
              <div className="weather-grid">
                {weatherData.map((weather, index) => (
                  <Card key={index} className="weather-preview-item" size="small">
                    <div className="weather-date">{weather.date.slice(5)}</div>
                    <div className="weather-temp">
                      {weather.dayTemp}°/{weather.nightTemp}°
                    </div>
                    <div className="weather-condition">{weather.dayWeather}</div>
                  </Card>
                ))}
              </div>
            </>
          ) : (
            <Empty description="暂无天气数据" />
          )}
        </div>
      </Modal>

      {/* 行程概览弹窗 */}
      <Modal
        title="行程概览"
        open={overviewModalVisible}
        onCancel={() => setOverviewModalVisible(false)}
        footer={null}
        width={800}
      >
        {plan && (
          <div className="plan-overview">
            <div className="overview-header">
              <Title level={3}>{plan.title}</Title>
              <Paragraph>{plan.description}</Paragraph>
            </div>
            <div className="overview-stats">
              <Card>
                <Space direction="vertical" align="center">
                  <CalendarOutlined style={{ fontSize: 24, color: '#1890ff' }} />
                  <Text strong>{plan.duration_days}天</Text>
                  <Text type="secondary">行程天数</Text>
                </Space>
              </Card>
              <Card>
                <Space direction="vertical" align="center">
                  <UserOutlined style={{ fontSize: 24, color: '#52c41a' }} />
                  <Text strong>{getMemberCount()}人</Text>
                  <Text type="secondary">出行人数</Text>
                </Space>
              </Card>
              <Card>
                <Space direction="vertical" align="center">
                  <WalletOutlined style={{ fontSize: 24, color: '#faad14' }} />
                  <Text strong>{getBudgetDisplay()}</Text>
                  <Text type="secondary">预算</Text>
                </Space>
              </Card>
              <Card>
                <Space direction="vertical" align="center">
                  <EnvironmentOutlined style={{ fontSize: 24, color: '#722ed1' }} />
                  <Text strong>{plan.destination}</Text>
                  <Text type="secondary">目的地</Text>
                </Space>
              </Card>
            </div>
            <div className="overview-schedule">
              <Title level={4}>行程安排</Title>
              {getDayActivities().map((day, index) => (
                <Card key={index} size="small" style={{ marginBottom: 8 }}>
                  <Text strong>Day {index + 1} - {formatDateDisplay(day.date)}</Text>
                  <div style={{ marginTop: 8 }}>
                    {/* 显示日程 */}
                    {day.schedule && day.schedule.length > 0 && (
                      <div>
                        <Text type="secondary">日程：</Text>
                        {day.schedule.map((item, idx) => (
                          <Tag key={idx} style={{ marginBottom: 4 }}>
                            {item.activity}
                          </Tag>
                        ))}
                      </div>
                    )}
                    {/* 显示景点 */}
                    {day.attractions && day.attractions.length > 0 && (
                      <div style={{ marginTop: 4 }}>
                        <Text type="secondary">景点：</Text>
                        {day.attractions.map((attr, idx) => (
                          <Tag key={idx} color="blue" style={{ marginBottom: 4 }}>
                            {attr.name}
                          </Tag>
                        ))}
                      </div>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          </div>
        )}
      </Modal>

      {/* 分享弹窗 */}
      <Modal
        title="分享行程"
        open={shareModalVisible}
        onCancel={() => setShareModalVisible(false)}
        footer={null}
        width={400}
      >
        <div className="share-options">
          <Button
            block
            icon={<CopyOutlined />}
            onClick={() => handleShare('link')}
            style={{ marginBottom: 12 }}
          >
            复制链接
          </Button>
          <Button
            block
            icon={<EyeOutlined />}
            onClick={() => handleShare('public')}
            style={{ marginBottom: 12 }}
            disabled={plan?.is_public}
          >
            {plan?.is_public ? '已公开' : '发布为公开行程'}
          </Button>
        </div>
      </Modal>
    </Layout>
  );
};

export default ItineraryWorkspace;
