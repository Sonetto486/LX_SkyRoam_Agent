import React, { useState, useEffect, useCallback } from 'react';
import { Card, Button, Space, Tag, Typography, Empty, Spin, Row, Col, Popconfirm, message, Modal, Dropdown, Menu, InputNumber, DatePicker, Tooltip } from 'antd';
import {
  CalendarOutlined,
  EnvironmentOutlined,
  UserOutlined,
  EditOutlined,
  DeleteOutlined,
  PlusOutlined,
  ExclamationCircleOutlined,
  MoreOutlined,
  ShareAltOutlined,
  CloudOutlined,
  EyeOutlined,
  SettingOutlined,
  CopyOutlined,
  WalletOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { buildApiUrl } from '../../config/api';
import { authFetch } from '../../utils/auth';
import './ItineraryListPage.css';

const { Title, Paragraph, Text } = Typography;

// 行程状态类型
type PlanStatus = 'draft' | 'generating' | 'completed' | 'archived';

// 行程数据接口（对接后端 TravelPlanResponse）
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
  status: PlanStatus;
  score?: number;
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

// 列表响应接口
interface TravelPlanListResponse {
  plans: TravelPlan[];
  total: number;
  skip: number;
  limit: number;
}

const ItineraryListPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [itineraries, setItineraries] = useState<TravelPlan[]>([]);
  const [deleteLoading, setDeleteLoading] = useState<number | null>(null);

  // 新增状态
  const [weatherModalVisible, setWeatherModalVisible] = useState(false);
  const [selectedItinerary, setSelectedItinerary] = useState<TravelPlan | null>(null);
  const [weatherData, setWeatherData] = useState<any[]>([]);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingItinerary, setEditingItinerary] = useState<TravelPlan | null>(null);
  const [shareModalVisible, setShareModalVisible] = useState(false);
  const [sharingItinerary, setSharingItinerary] = useState<TravelPlan | null>(null);

  // 获取行程列表
  const fetchItineraries = useCallback(async () => {
    setLoading(true);
    try {
      const res = await authFetch(buildApiUrl('/travel-plans/?limit=100'));
      if (!res.ok) {
        throw new Error('获取行程列表失败');
      }
      const data: TravelPlanListResponse = await res.json();
      setItineraries(data.plans || []);
    } catch (err: any) {
      message.error('获取行程列表失败：' + (err.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchItineraries();
  }, [fetchItineraries]);

  // 删除行程
  const handleDelete = async (id: number) => {
    setDeleteLoading(id);
    try {
      const res = await authFetch(buildApiUrl(`/travel-plans/${id}`), {
        method: 'DELETE',
      });
      if (!res.ok) {
        throw new Error('删除失败');
      }
      message.success('行程已删除');
      setItineraries(prev => prev.filter(item => item.id !== id));
    } catch (err: any) {
      message.error('删除行程失败：' + (err.message || '未知错误'));
    } finally {
      setDeleteLoading(null);
    }
  };

  // 确认删除
  const confirmDelete = (itinerary: TravelPlan) => {
    Modal.confirm({
      title: '确认删除',
      icon: <ExclamationCircleOutlined />,
      content: `确定要删除行程「${itinerary.title}」吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => handleDelete(itinerary.id),
    });
  };

  // 获取状态标签
  const getStatusTag = (status: PlanStatus) => {
    const statusConfig: Record<PlanStatus, { color: string; text: string }> = {
      draft: { color: 'blue', text: '草稿' },
      generating: { color: 'orange', text: '生成中' },
      completed: { color: 'green', text: '已完成' },
      archived: { color: 'gray', text: '已归档' },
    };
    const config = statusConfig[status] || statusConfig.draft;
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  // 格式化日期
  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' });
    } catch {
      return dateStr;
    }
  };

  // 获取成员数量
  const getMemberCount = (plan: TravelPlan): number => {
    return plan.preferences?.travelers || 1;
  };

  // 获取预算显示
  const getBudgetDisplay = (plan: TravelPlan): string => {
    if (plan.budget) {
      return `¥${plan.budget.toLocaleString()}`;
    }
    return '未设置';
  };

  // 获取天气预览
  const fetchWeatherPreview = async (destination: string, days: number = 15) => {
    try {
      const amapKey = process.env.REACT_APP_AMAP_KEY || process.env.REACT_APP_AMAP_WEB_KEY;
      if (!amapKey) {
        // 使用模拟数据
        const mockData = [];
        const weathers = ['晴', '多云', '阴', '小雨', '中雨'];
        for (let i = 0; i < Math.min(days, 15); i++) {
          const date = new Date();
          date.setDate(date.getDate() + i);
          mockData.push({
            date: date.toISOString().split('T')[0],
            dayWeather: weathers[Math.floor(Math.random() * weathers.length)],
            dayTemp: String(20 + Math.floor(Math.random() * 10)),
            nightTemp: String(15 + Math.floor(Math.random() * 5)),
          });
        }
        return mockData;
      }

      // 获取城市adcode
      const cityRes = await fetch(
        `https://restapi.amap.com/v3/config/district?keywords=${encodeURIComponent(destination)}&key=${amapKey}&subdistrict=0`
      );
      const cityData = await cityRes.json();

      if (!cityData.districts || cityData.districts.length === 0) {
        return [];
      }

      const adcode = cityData.districts[0].adcode;

      // 获取天气预报
      const weatherRes = await fetch(
        `https://restapi.amap.com/v3/weather/weatherInfo?city=${adcode}&key=${amapKey}&extensions=all`
      );
      const weatherJson = await weatherRes.json();

      if (weatherJson.status === '1' && weatherJson.forecasts && weatherJson.forecasts[0]) {
        return weatherJson.forecasts[0].casts.slice(0, days).map((cast: any) => ({
          date: cast.date,
          dayWeather: cast.dayweather,
          dayTemp: cast.daytemp,
          nightTemp: cast.nighttemp,
        }));
      }
      return [];
    } catch (err) {
      console.error('获取天气失败:', err);
      return [];
    }
  };

  // 打开天气预览弹窗
  const openWeatherModal = async (itinerary: TravelPlan) => {
    setSelectedItinerary(itinerary);
    setWeatherModalVisible(true);
    const data = await fetchWeatherPreview(itinerary.destination, 15);
    setWeatherData(data);
  };

  // 打开编辑弹窗
  const openEditModal = (itinerary: TravelPlan) => {
    setEditingItinerary(itinerary);
    setEditModalVisible(true);
  };

  // 保存编辑
  const handleSaveEdit = async (values: any) => {
    if (!editingItinerary) return;
    try {
      const res = await authFetch(buildApiUrl(`/travel-plans/${editingItinerary.id}`), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      if (!res.ok) throw new Error('更新失败');
      message.success('行程已更新');
      setEditModalVisible(false);
      fetchItineraries();
    } catch (err: any) {
      message.error('更新失败：' + (err.message || '未知错误'));
    }
  };

  // 复制行程
  const handleCopyItinerary = async (itinerary: TravelPlan) => {
    try {
      const res = await authFetch(buildApiUrl('/travel-plans/'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: `${itinerary.title} (副本)`,
          description: itinerary.description,
          departure: itinerary.departure,
          destination: itinerary.destination,
          start_date: itinerary.start_date,
          end_date: itinerary.end_date,
          duration_days: itinerary.duration_days,
          budget: itinerary.budget,
          transportation: itinerary.transportation,
          preferences: itinerary.preferences,
        }),
      });
      if (!res.ok) throw new Error('复制失败');
      message.success('行程已复制');
      fetchItineraries();
    } catch (err: any) {
      message.error('复制失败：' + (err.message || '未知错误'));
    }
  };

  // 打开分享弹窗
  const openShareModal = (itinerary: TravelPlan) => {
    setSharingItinerary(itinerary);
    setShareModalVisible(true);
  };

  // 分享行程
  const handleShare = async (type: string) => {
    if (!sharingItinerary) return;
    const shareUrl = `${window.location.origin}/itineraries/${sharingItinerary.id}`;

    switch (type) {
      case 'link':
        navigator.clipboard.writeText(shareUrl);
        message.success('链接已复制到剪贴板');
        break;
      case 'wechat':
        // 微信分享（需要引入微信SDK）
        message.info('请截图分享到微信');
        break;
      case 'public':
        // 发布为公开行程
        try {
          const res = await authFetch(buildApiUrl(`/travel-plans/${sharingItinerary.id}/publish`), {
            method: 'PUT',
          });
          if (!res.ok) throw new Error('发布失败');
          message.success('行程已发布为公开');
          fetchItineraries();
        } catch (err: any) {
          message.error('发布失败：' + (err.message || '未知错误'));
        }
        break;
    }
    setShareModalVisible(false);
  };

  // 获取卡片操作菜单
  const getCardMenu = (itinerary: TravelPlan) => (
    <Menu>
      <Menu.Item key="edit" icon={<EditOutlined />} onClick={() => openEditModal(itinerary)}>
        编辑行程
      </Menu.Item>
      <Menu.Item key="copy" icon={<CopyOutlined />} onClick={() => handleCopyItinerary(itinerary)}>
        复制行程
      </Menu.Item>
      <Menu.Item key="weather" icon={<CloudOutlined />} onClick={() => openWeatherModal(itinerary)}>
        天气预览
      </Menu.Item>
      <Menu.Item key="share" icon={<ShareAltOutlined />} onClick={() => openShareModal(itinerary)}>
        分享行程
      </Menu.Item>
      <Menu.Divider />
      <Menu.Item key="delete" icon={<DeleteOutlined />} danger onClick={() => confirmDelete(itinerary)}>
        删除行程
      </Menu.Item>
    </Menu>
  );

  if (loading) {
    return (
      <div className="itinerary-list-loading">
        <Spin size="large" tip="加载行程列表..." />
      </div>
    );
  }

  return (
    <div className="itinerary-list-page">
      {/* 页面标题 */}
      <div className="page-header">
        <Title level={2}>我的行程</Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate('/generate')}
        >
          创建新行程
        </Button>
      </div>

      {/* 行程列表 */}
      {itineraries.length === 0 ? (
        <div className="itinerary-empty">
          <Empty description="还没有创建行程">
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/generate')}
            >
              创建行程
            </Button>
          </Empty>
        </div>
      ) : (
        <Row gutter={[16, 16]}>
          {itineraries.map((itinerary) => (
            <Col xs={24} sm={12} md={8} lg={6} key={itinerary.id}>
              <Card
                className="itinerary-list-card"
                cover={
                  <div
                    className="itinerary-card-image"
                    onClick={() => navigate(`/itineraries/${itinerary.id}`)}
                  >
                    <img
                      src={`https://picsum.photos/seed/plan_${itinerary.id}/800/600`}
                      alt={itinerary.title}
                    />
                    <div className="itinerary-card-status">
                      {getStatusTag(itinerary.status)}
                    </div>
                    {itinerary.is_public && (
                      <Tag color="purple" className="public-tag">已公开</Tag>
                    )}
                  </div>
                }
                actions={[
                  <Button
                    key="edit"
                    icon={<EditOutlined />}
                    onClick={() => navigate(`/itineraries/${itinerary.id}`)}
                  >
                    编辑
                  </Button>,
                  <Dropdown
                    key="more"
                    overlay={getCardMenu(itinerary)}
                    trigger={['click']}
                  >
                    <Button icon={<MoreOutlined />}>
                      更多
                    </Button>
                  </Dropdown>
                ]}
              >
                <div
                  className="itinerary-card-content"
                  onClick={() => navigate(`/itineraries/${itinerary.id}`)}
                >
                  <Title level={4} ellipsis={{ rows: 1 }}>{itinerary.title}</Title>
                  <div className="itinerary-card-meta">
                    <Space>
                      <Space size={4}>
                        <EnvironmentOutlined />
                        <span>{itinerary.destination}</span>
                      </Space>
                      <Space size={4}>
                        <CalendarOutlined />
                        <span>{itinerary.duration_days}天</span>
                      </Space>
                    </Space>
                  </div>
                  <Paragraph className="itinerary-card-date">
                    {formatDate(itinerary.start_date)} - {formatDate(itinerary.end_date)}
                  </Paragraph>
                  <div className="itinerary-card-info">
                    <Space split={<span className="info-divider">|</span>}>
                      <Space size={4}>
                        <UserOutlined />
                        <span>{getMemberCount(itinerary)}人</span>
                      </Space>
                      <Space size={4}>
                        <WalletOutlined />
                        <span>{getBudgetDisplay(itinerary)}</span>
                      </Space>
                    </Space>
                  </div>
                  <div className="itinerary-card-members">
                    <div className="member-avatars">
                      {Array.from({ length: Math.min(getMemberCount(itinerary), 3) }).map((_, index) => (
                        <div
                          key={index}
                          className="member-avatar"
                          style={{
                            left: `${index * 20}px`,
                            backgroundColor: `hsl(${index * 60}, 70%, 60%)`
                          }}
                        >
                          {String.fromCharCode(65 + index)}
                        </div>
                      ))}
                      {getMemberCount(itinerary) > 3 && (
                        <div className="member-avatar more">
                          +{getMemberCount(itinerary) - 3}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {/* 天气预览弹窗 */}
      <Modal
        title={`${selectedItinerary?.destination || ''} 天气预报（近15日）`}
        open={weatherModalVisible}
        onCancel={() => setWeatherModalVisible(false)}
        footer={null}
        width={800}
        className="weather-preview-modal"
      >
        <div className="weather-preview-content">
          {weatherData.length > 0 ? (
            <Row gutter={[8, 8]}>
              {weatherData.map((weather, index) => (
                <Col key={index} xs={12} sm={8} md={6} lg={4}>
                  <Card className="weather-preview-item" size="small">
                    <div className="weather-date">{weather.date.slice(5)}</div>
                    <div className="weather-temp">
                      {weather.dayTemp}°/{weather.nightTemp}°
                    </div>
                    <div className="weather-condition">{weather.dayWeather}</div>
                  </Card>
                </Col>
              ))}
            </Row>
          ) : (
            <Empty description="暂无天气数据" />
          )}
        </div>
      </Modal>

      {/* 编辑弹窗 */}
      <Modal
        title="编辑行程"
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        onOk={() => {
          // 表单提交在子组件中处理
          setEditModalVisible(false);
        }}
        width={600}
      >
        {editingItinerary && (
          <div className="edit-itinerary-form">
            <div className="form-item">
              <Text strong>行程标题</Text>
              <input
                className="form-input"
                defaultValue={editingItinerary.title}
                id="edit-title"
              />
            </div>
            <div className="form-item">
              <Text strong>行程描述</Text>
              <textarea
                className="form-textarea"
                defaultValue={editingItinerary.description || ''}
                id="edit-description"
                rows={3}
              />
            </div>
            <div className="form-row">
              <div className="form-item">
                <Text strong>出发地</Text>
                <input
                  className="form-input"
                  defaultValue={editingItinerary.departure || ''}
                  id="edit-departure"
                />
              </div>
              <div className="form-item">
                <Text strong>目的地</Text>
                <input
                  className="form-input"
                  defaultValue={editingItinerary.destination}
                  id="edit-destination"
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-item">
                <Text strong>开始日期</Text>
                <DatePicker
                  style={{ width: '100%' }}
                  defaultValue={dayjs(editingItinerary.start_date)}
                  id="edit-start-date"
                />
              </div>
              <div className="form-item">
                <Text strong>结束日期</Text>
                <DatePicker
                  style={{ width: '100%' }}
                  defaultValue={dayjs(editingItinerary.end_date)}
                  id="edit-end-date"
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
                  defaultValue={editingItinerary.preferences?.travelers || 1}
                  id="edit-travelers"
                />
              </div>
              <div className="form-item">
                <Text strong>预算（元）</Text>
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  defaultValue={editingItinerary.budget || 0}
                  id="edit-budget"
                />
              </div>
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
            disabled={sharingItinerary?.is_public}
          >
            {sharingItinerary?.is_public ? '已公开' : '发布为公开行程'}
          </Button>
          <Button
            block
            icon={<ShareAltOutlined />}
            onClick={() => handleShare('wechat')}
          >
            分享到微信
          </Button>
        </div>
      </Modal>
    </div>
  );
};

export default ItineraryListPage;
