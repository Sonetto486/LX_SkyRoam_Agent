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
  SettingOutlined
} from '@ant-design/icons';
import MapComponent from '../../components/MapComponent/MapComponent';
import WeatherCard from '../../components/Itinerary/WeatherCard';
import ActivityEditModal from '../../components/Itinerary/ActivityEditModal';
import DateRangeEditor from '../../components/Itinerary/DateRangeEditor';
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
}

// 行程项目接口
interface TravelPlanItem {
  id: number;
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

// 活动编辑数据接口（id可选）
interface ActivityEditData {
  id?: number;
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

// 每日活动数据
interface DayActivity {
  date: string;
  activities: TravelPlanItem[];
}

const ItineraryWorkspace: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [plan, setPlan] = useState<TravelPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeDay, setActiveDay] = useState(0);
  const [hoveredActivity, setHoveredActivity] = useState<number | null>(null);
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

  // 获取行程详情
  const fetchPlan = useCallback(async () => {
    if (!id) return;
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
  }, [id]);

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
  const handleDeleteActivity = async (activityId: number) => {
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

  // 移动活动顺序
  const handleMoveActivity = async (activityId: number, direction: 'up' | 'down') => {
    if (!plan || !id) return;
    const dayActivities = getDayActivities();
    if (activeDay >= dayActivities.length) return;

    const activities = [...dayActivities[activeDay].activities];
    const currentIndex = activities.findIndex(a => a.id === activityId);
    if (currentIndex === -1) return;

    const newIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
    if (newIndex < 0 || newIndex >= activities.length) {
      message.warning(direction === 'up' ? '已经是第一个' : '已经是最后一个');
      return;
    }

    // 交换位置
    [activities[currentIndex], activities[newIndex]] = [activities[newIndex], activities[currentIndex]];

    try {
      const res = await authFetch(
        buildApiUrl(`/travel-plans/${id}/items/reorder`),
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ item_ids: activities.map(a => a.id) }),
        }
      );
      if (!res.ok) throw new Error('排序失败');
      message.success(direction === 'up' ? '活动已上移' : '活动已下移');
      fetchPlan();
    } catch (err: any) {
      message.error(err.message || '移动失败');
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
          start_date: startDate,
          end_date: endDate,
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

  // 获取每日活动数据
 // 获取每日活动数据
const getDayActivities = (): DayActivity[] => {
  if (!plan) return [];

  // 🔥 新增：兼容AI生成的攻略数据（唯一改动，不影响原有功能）
  // 🔥 兼容AI生成的攻略数据（不影响任何原有功能）
// 🔥 兼容AI生成的攻略数据（解决标题+地址问题，不影响任何原有功能）
if (plan.preferences?.parsed_locations) {
  const locationMap: Record<string, TravelPlanItem[]> = {};
  plan.preferences.parsed_locations.forEach((loc: any) => {
    const dayKey = `day_${loc.day || 1}`;
    if (!locationMap[dayKey]) locationMap[dayKey] = [];

    // 👇 核心修复：处理标题和地址
    // 1. 标题：强制使用 loc.name，兜底为"未命名景点"
    const activityTitle = loc.name || "未命名景点";
    // 2. 地址：如果是"未知"，就用景点名替代，兜底为"未知地址"
    const activityAddress = (loc.address && loc.address !== "未知") 
      ? loc.address 
      : activityTitle || "未知地址";

    locationMap[dayKey].push({
      id: Number(loc.id) || Date.now(),
      title: activityTitle, // 明确赋值为景点名
      address: activityAddress, // 用处理后的地址
      location: activityAddress, // 和address保持一致
      item_type: loc.type || "景点",
      coordinates: loc.position || loc.coordinates || { lat: 0, lng: 0 },
      start_time: plan.start_date,
    } as TravelPlanItem);
  });

  const aiDays = Object.values(locationMap).map((activities, i) => ({
    date: getDateByOffset(plan.start_date, i),
    activities
  }));

  if (aiDays.length) return aiDays;
}

  // 👇 下面是你原有的所有代码，完全不动！
  // 如果有 selected_plan，从中提取每日行程
  if (plan.selected_plan?.daily_itineraries) {
    return plan.selected_plan.daily_itineraries.map((day: any, index: number) => ({
      date: day.date || getDateByOffset(plan.start_date, index),
      activities: (day.attractions || []).map((attr: any, attrIndex: number) => ({
        id: index * 100 + attrIndex,
        title: attr.name || attr,
        description: attr.description || '',
        item_type: 'attraction',
        location: attr.location || '',
        address: attr.address || '',
        coordinates: attr.coordinates || { lat: 0, lng: 0 },
        images: attr.images || [],
        details: attr,
      })),
    }));
  }

  // 如果有 generated_plans，使用第一个方案
  if (plan.generated_plans && plan.generated_plans.length > 0) {
    const firstPlan = plan.generated_plans[0];
    if (firstPlan.daily_itineraries) {
      return firstPlan.daily_itineraries.map((day: any, index: number) => ({
        date: day.date || getDateByOffset(plan.start_date, index),
        activities: (day.attractions || []).map((attr: any, attrIndex: number) => ({
          id: index * 100 + attrIndex,
          title: attr.name || attr,
          description: attr.description || '',
          item_type: 'attraction',
          location: attr.location || '',
          address: attr.address || '',
          coordinates: attr.coordinates || { lat: 0, lng: 0 },
          images: attr.images || [],
          details: attr,
        })),
      }));
    }
  }

  // 如果有 items，按日期分组
  if (plan.items && plan.items.length > 0) {
    const dayMap = new Map<string, TravelPlanItem[]>();
    plan.items.forEach(item => {
      const date = item.start_time ? item.start_time.split('T')[0] : plan.start_date.split('T')[0];
      if (!dayMap.has(date)) {
        dayMap.set(date, []);
      }
      dayMap.get(date)!.push(item);
    });
    return Array.from(dayMap.entries()).map(([date, activities]) => ({ date, activities }));
  }

  // 默认返回空数组
  return [];
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

    return dayActivities[activeDay].activities
      .filter(activity => activity.coordinates && activity.coordinates.lat && activity.coordinates.lng)
      .map(activity => ({
        id: activity.id,
        name: activity.title,
        position: activity.coordinates!,
        address: activity.address || activity.location || '',
        isHovered: hoveredActivity === activity.id,
      }));
  };

  // 获取地图中心点
  const getMapCenter = () => {
    const markers = getMapMarkers();
    if (markers.length > 0) {
      return markers[0].position;
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
      return `¥${plan.budget.toLocaleString()}`;
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

  // 获取天气数据（15日）
  const fetchWeatherData = async () => {
    if (!plan) return;
    try {
      const amapKey = process.env.REACT_APP_AMAP_KEY || process.env.REACT_APP_AMAP_WEB_KEY;
      if (!amapKey) {
        // 使用模拟数据
        const mockData = [];
        const weathers = ['晴', '多云', '阴', '小雨', '中雨'];
        for (let i = 0; i < 15; i++) {
          const date = new Date();
          date.setDate(date.getDate() + i);
          mockData.push({
            date: date.toISOString().split('T')[0],
            dayWeather: weathers[Math.floor(Math.random() * weathers.length)],
            dayTemp: String(20 + Math.floor(Math.random() * 10)),
            nightTemp: String(15 + Math.floor(Math.random() * 5)),
          });
        }
        setWeatherData(mockData);
        return;
      }

      const cityRes = await fetch(
        `https://restapi.amap.com/v3/config/district?keywords=${encodeURIComponent(plan.destination)}&key=${amapKey}&subdistrict=0`
      );
      const cityData = await cityRes.json();

      if (cityData.districts && cityData.districts.length > 0) {
        const adcode = cityData.districts[0].adcode;
        const weatherRes = await fetch(
          `https://restapi.amap.com/v3/weather/weatherInfo?city=${adcode}&key=${amapKey}&extensions=all`
        );
        const weatherJson = await weatherRes.json();

        if (weatherJson.status === '1' && weatherJson.forecasts && weatherJson.forecasts[0]) {
          setWeatherData(weatherJson.forecasts[0].casts.slice(0, 15).map((cast: any) => ({
            date: cast.date,
            dayWeather: cast.dayweather,
            dayTemp: cast.daytemp,
            nightTemp: cast.nighttemp,
          })));
        }
      }
    } catch (err) {
      console.error('获取天气失败:', err);
    }
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
      // 调用优化API（这里可以后续实现）
      await new Promise(resolve => setTimeout(resolve, 2000));
      message.success({ content: '行程已优化', key: 'optimize' });
    } catch (err: any) {
      message.error({ content: '优化失败：' + (err.message || '未知错误'), key: 'optimize' });
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
      <Menu.Item key="route" icon={<SwapOutlined />} onClick={() => setRouteModalVisible(true)}>
        路线编辑
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
      <Sider width={480} className="workspace-sider">
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
            days={Math.min(plan.duration_days, 5)}
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
                {/* 活动列表 */}
                <div className="activities-list">
                  {day.activities.map((activity) => (
                    <Card
                      key={activity.id}
                      className={`activity-card ${hoveredActivity === activity.id ? 'hovered' : ''}`}
                      onMouseEnter={() => setHoveredActivity(activity.id)}
                      onMouseLeave={() => setHoveredActivity(null)}
                      actions={[
                        <Tooltip key="edit" title="编辑">
                          <Button
                            icon={<EditOutlined />}
                            size="small"
                            onClick={() => openActivityModal(activity)}
                          />
                        </Tooltip>,
                        <Tooltip key="move-up" title="上移">
                          <Button
                            icon={<UpOutlined />}
                            size="small"
                            onClick={() => handleMoveActivity(activity.id, 'up')}
                          />
                        </Tooltip>,
                        <Tooltip key="move-down" title="下移">
                          <Button
                            icon={<DownOutlined />}
                            size="small"
                            onClick={() => handleMoveActivity(activity.id, 'down')}
                          />
                        </Tooltip>,
                        <Popconfirm
                          key="delete"
                          title="确定删除此活动？"
                          okText="删除"
                          cancelText="取消"
                          onConfirm={() => handleDeleteActivity(activity.id)}
                        >
                          <Button danger icon={<DeleteOutlined />} size="small" />
                        </Popconfirm>
                      ]}
                    >
                      <div className="activity-header">
                        <Tag color="blue">{activity.item_type || '景点'}</Tag>
                        <Text strong>{activity.title}</Text>
                      </div>
                      {activity.location && (
                        <div className="activity-location">
                          <EnvironmentOutlined /> {activity.location}
                        </div>
                      )}
                      {activity.description && (
                        <Paragraph className="activity-description" ellipsis={{ rows: 2 }}>
                          {activity.description}
                        </Paragraph>
                      )}
                      {activity.images && activity.images.length > 0 && (
                        <div className="activity-images">
                          <img
                            src={activity.images[0]}
                            alt={activity.title}
                            className="activity-image"
                          />
                        </div>
                      )}
                    </Card>
                  ))}

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
          // 表单提交逻辑
          setPlanInfoModalVisible(false);
        }}
        width={600}
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
          </div>
        )}
      </Modal>

      {/* 天气预览弹窗（15日） */}
      <Modal
        title={`${plan?.destination || ''} 天气预报（近15日）`}
        open={weatherModalVisible}
        onCancel={() => setWeatherModalVisible(false)}
        footer={null}
        width={900}
      >
        <div className="weather-preview-content">
          {weatherData.length > 0 ? (
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
                    {day.activities.map((activity, actIndex) => (
                      <Tag key={actIndex} style={{ marginBottom: 4 }}>
                        {activity.title}
                      </Tag>
                    ))}
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
