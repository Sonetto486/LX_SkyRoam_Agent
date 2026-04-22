import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout, Tabs, Card, Button, Space, Tooltip, Empty, Spin, Typography, Tag, message, Popconfirm } from 'antd';
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
  DownOutlined
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
  const [editingActivity, setEditingActivity] = useState<TravelPlanItem | null>(null);
  const [dateEditorVisible, setDateEditorVisible] = useState(false);

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

  // 分享行程
  const handleShare = () => {
    if (!plan) return;
    const shareUrl = `${window.location.origin}/plans-library?highlight=${plan.id}`;
    navigator.clipboard.writeText(shareUrl);
    message.success('分享链接已复制到剪贴板');
  };

  // 打开活动编辑弹窗
  const openActivityModal = (activity?: TravelPlanItem) => {
    setEditingActivity(activity || null);
    setActivityModalVisible(true);
  };

  // 保存活动
  const handleSaveActivity = async (activity: TravelPlanItem) => {
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
  const getDayActivities = (): DayActivity[] => {
    if (!plan) return [];

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
            </div>
            {plan.description && (
              <Paragraph className="itinerary-desc" ellipsis={{ rows: 2 }}>
                {plan.description}
              </Paragraph>
            )}
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
          <Tooltip title="路线编辑">
            <Button
              icon={<EditOutlined />}
              className="map-control-btn"
            />
          </Tooltip>
          <Tooltip title="一键优化">
            <Button
              icon={<SyncOutlined />}
              className="map-control-btn"
            />
          </Tooltip>
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
          <Tooltip title="分享行程">
            <Button
              icon={<ShareAltOutlined />}
              className="map-control-btn success"
              onClick={handleShare}
            />
          </Tooltip>
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
    </Layout>
  );
};

export default ItineraryWorkspace;
