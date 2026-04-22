import React, { useState, useEffect, useCallback } from 'react';
import { Card, Button, Space, Tag, Typography, Empty, Spin, Row, Col, Popconfirm, message, Modal } from 'antd';
import {
  CalendarOutlined,
  EnvironmentOutlined,
  UserOutlined,
  EditOutlined,
  DeleteOutlined,
  PlusOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { buildApiUrl } from '../../config/api';
import { authFetch } from '../../utils/auth';
import './ItineraryListPage.css';

const { Title, Paragraph } = Typography;

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
                  <Popconfirm
                    key="delete"
                    title="确定删除此行程？"
                    onConfirm={() => handleDelete(itinerary.id)}
                    okText="删除"
                    cancelText="取消"
                  >
                    <Button
                      danger
                      icon={<DeleteOutlined />}
                      loading={deleteLoading === itinerary.id}
                    >
                      删除
                    </Button>
                  </Popconfirm>
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
                  <div className="itinerary-card-members">
                    <Space>
                      <UserOutlined />
                      <span>{getMemberCount(itinerary)}人</span>
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
                    </Space>
                  </div>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </div>
  );
};

export default ItineraryListPage;
