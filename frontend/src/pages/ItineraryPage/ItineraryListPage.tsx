import React, { useState, useEffect } from 'react';
import { Card, Button, Space, Tag, Typography, Empty, Spin, Row, Col } from 'antd';
import { 
  CalendarOutlined, 
  EnvironmentOutlined, 
  UserOutlined, 
  EditOutlined, 
  DeleteOutlined,
  PlusOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import './ItineraryListPage.css';

const { Title, Paragraph } = Typography;

interface Itinerary {
  id: string;
  title: string;
  destination: string;
  startDate: string;
  endDate: string;
  days: number;
  activities: number;
  members: string[];
  image: string;
  status: 'draft' | 'active' | 'completed';
}

const ItineraryListPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [itineraries, setItineraries] = useState<Itinerary[]>([]);

  // 模拟数据加载
  useEffect(() => {
    const fetchItineraries = async () => {
      setLoading(true);
      // 模拟 API 调用
      setTimeout(() => {
        setItineraries([
          {
            id: '1',
            title: '东京5日游',
            destination: '东京, 日本',
            startDate: '2026-05-01',
            endDate: '2026-05-05',
            days: 5,
            activities: 15,
            members: ['user1', 'user2', 'user3'],
            image: 'https://picsum.photos/seed/tokyo1/800/600',
            status: 'active'
          },
          {
            id: '2',
            title: '巴黎浪漫之旅',
            destination: '巴黎, 法国',
            startDate: '2026-06-10',
            endDate: '2026-06-14',
            days: 4,
            activities: 12,
            members: ['user1', 'user2'],
            image: 'https://picsum.photos/seed/paris/800/600',
            status: 'draft'
          },
          {
            id: '3',
            title: '纽约都市探索',
            destination: '纽约, 美国',
            startDate: '2026-07-20',
            endDate: '2026-07-25',
            days: 5,
            activities: 18,
            members: ['user1', 'user2', 'user3', 'user4'],
            image: 'https://picsum.photos/seed/newyork/800/600',
            status: 'active'
          },
          {
            id: '4',
            title: '悉尼海滩度假',
            destination: '悉尼, 澳大利亚',
            startDate: '2026-08-05',
            endDate: '2026-08-10',
            days: 5,
            activities: 10,
            members: ['user1'],
            image: 'https://picsum.photos/seed/sydney/800/600',
            status: 'completed'
          }
        ]);
        setLoading(false);
      }, 1000);
    };

    fetchItineraries();
  }, []);

  const getStatusTag = (status: string) => {
    switch (status) {
      case 'draft':
        return <Tag color="blue">草稿</Tag>;
      case 'active':
        return <Tag color="green">进行中</Tag>;
      case 'completed':
        return <Tag color="gray">已完成</Tag>;
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
        <Spin size="large" />
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
          onClick={() => navigate('/itineraries/new')}
        >
          创建新行程
        </Button>
      </div>

      {/* 行程列表 */}
      {itineraries.length === 0 ? (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
          <Empty description="还没有创建行程">
            <Button 
              type="primary" 
              icon={<PlusOutlined />}
              onClick={() => navigate('/itineraries/new')}
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
                  <div className="itinerary-card-image">
                    <img src={itinerary.image} alt={itinerary.title} />
                    <div className="itinerary-card-status">
                      {getStatusTag(itinerary.status)}
                    </div>
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
                  <Button 
                    key="delete" 
                    danger 
                    icon={<DeleteOutlined />}
                  >
                    删除
                  </Button>
                ]}
              >
                <div className="itinerary-card-content">
                  <Title level={4}>{itinerary.title}</Title>
                  <div className="itinerary-card-meta">
                    <Space>
                      <Space>
                        <EnvironmentOutlined />
                        <span>{itinerary.destination}</span>
                      </Space>
                      <Space>
                        <CalendarOutlined />
                        <span>{itinerary.days}天</span>
                      </Space>
                    </Space>
                  </div>
                  <Paragraph>
                    {itinerary.startDate} - {itinerary.endDate}
                  </Paragraph>
                  <div className="itinerary-card-members">
                    <Space>
                      <UserOutlined />
                      <span>{itinerary.members.length}人</span>
                      <div className="member-avatars">
                        {itinerary.members.slice(0, 3).map((member, index) => (
                          <div 
                            key={index} 
                            className="member-avatar"
                            style={{ 
                              left: `${index * 20}px`,
                              backgroundColor: `hsl(${index * 60}, 70%, 60%)`
                            }}
                          >
                            {member.charAt(0).toUpperCase()}
                          </div>
                        ))}
                        {itinerary.members.length > 3 && (
                          <div className="member-avatar more">
                            +{itinerary.members.length - 3}
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
