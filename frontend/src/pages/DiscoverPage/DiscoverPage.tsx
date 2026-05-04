import React, { useState, useEffect } from 'react';
import { Input, Select, Card, Button, Space, Row, Col, Tag, Typography, message, Spin, Empty } from 'antd';
import { SearchOutlined, StarOutlined, EnvironmentOutlined, CalendarOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { authFetch } from '../../utils/auth';
import { API_BASE_URL } from '../../config/api';
import './DiscoverPage.css';

const { Option } = Select;
const { Title, Paragraph } = Typography;

interface TopicCard {
  id: number;
  title: string;
  image: string;
  tags: string[];
  description: string;
}

interface ItineraryCard {
  id: number | string;
  title: string;
  image: string;
  destination: string;
  days: number;
  activities: number;
  rating: number;
}

const DiscoverPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchValue, setSearchValue] = useState('');
  const [region, setRegion] = useState('all');
  const [loading, setLoading] = useState(false);
  const [topicsLoading, setTopicsLoading] = useState(false);
  const [itineraries, setItineraries] = useState<ItineraryCard[]>([]);
  const [topicCards, setTopicCards] = useState<TopicCard[]>([]);

  // 拉取真实的公共旅行计划
  useEffect(() => {
    fetchPublicItineraries();
    fetchTopics();
  }, []);

  const fetchTopics = async () => {
    try {
      setTopicsLoading(true);
      const res = await authFetch(`/topics?keyword=${encodeURIComponent(searchValue)}&continent=${encodeURIComponent(region === 'all' ? '' : region)}`);
      const data = await res.json();
      const sourceData = Array.isArray(data) ? data : data.topics || data.items || [];
      const mappedTopics = sourceData.map((topic: any) => ({
        id: topic.id,
        title: topic.title || topic.name || '未命名专题',
        image: topic.image || topic.cover_url || topic.cover_image_url || 'https://picsum.photos/seed/' + topic.id + '/800/600',
        tags: topic.tags || [topic.continent || '未分类'],
        description: topic.description || topic.intro || ''
      }));
      setTopicCards(mappedTopics);
    } catch (error) {
      console.error('获取专题失败:', error);
      message.error({ content: '获取专题失败', key: 'fetchTopicsError' });
    } finally {
      setTopicsLoading(false);
    }
  };

  const handleSearch = () => {
    fetchTopics();
    fetchPublicItineraries();
  };

  const fetchPublicItineraries = async () => {
    try {
      setLoading(true);
      const response = await authFetch(`/travel-plans/public?keyword=${encodeURIComponent(searchValue)}`);
      const data = await response.json();
      if (data && data.plans) {
        const mappedItineraries = data.plans.map((plan: any) => ({
          id: plan.id,
          title: plan.title || '未命名行程',
          image: 'https://picsum.photos/seed/' + plan.id + '/800/600', // 暂用随机图
          destination: plan.destination || '未知目的地',
          days: plan.duration_days || 1,
          activities: plan.items ? plan.items.length : 15,
          rating: plan.score || 4.8
        }));
        setItineraries(mappedItineraries);
      }
    } catch (error) {
      console.error('获取推荐行程失败:', error);
      message.error({ content: '获取推荐行程失败，请刷新重试', key: 'fetchPlansError' });
    } finally {
      setLoading(false);
    }
  };

  const handleItineraryClick = (id: number | string) => {
    navigate(`/plans/${id}`);
  };

  const handleTopicClick = (id: number | string) => {
    navigate(`/topics/${id}`);
  };

  const handleViewAllTopics = () => {
    navigate('/topics');
  };

  const handleViewAllItineraries = () => {
    navigate('/public-plans');
  };

  return (
    <div className="discover-page">
      {/* 顶部搜索栏 */}
      <div className="search-section">
        <div className="search-container">
          <Input
            placeholder="搜索目的地、景点或行程"
            prefix={<SearchOutlined style={{ color: 'rgba(255, 255, 255, 0.6)' }} />}
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            style={{ 
              width: 480, 
              backgroundColor: 'rgba(255, 255, 255, 0.1)', 
              borderColor: 'rgba(255, 255, 255, 0.2)',
              color: '#716060ff'
            }}
          />
          <Select
            defaultValue="all"
            style={{ 
              width: 200, 
              marginLeft: 16, 
              backgroundColor: 'rgba(255, 255, 255, 0.1)', 
              borderColor: 'rgba(255, 255, 255, 0.2)',
              color: '#373131ff'
            }}
            onChange={setRegion}
          >
            <Option value="all" style={{ color: '#000' }}>全部区域</Option>
            <Option value="asia" style={{ color: '#000' }}>亚洲</Option>
            <Option value="europe" style={{ color: '#000' }}>欧洲</Option>
            <Option value="north-america" style={{ color: '#000' }}>北美洲</Option>
            <Option value="oceania" style={{ color: '#000' }}>大洋洲</Option>
          </Select>
          <Button type="primary" style={{ marginLeft: 16 }} onClick={handleSearch}>
            搜索
          </Button>
        </div>
      </div>

      {/* 精选专题 */}
      <div className="section">
        <div className="section-header">
          <Title level={3}>精选专题</Title>
          <Button type="link" onClick={handleViewAllTopics}>查看全部</Button>
        </div>
        <Spin spinning={topicsLoading}>
        <Row gutter={[16, 16]}>
          {topicCards.map((topic) => (
            <Col xs={24} sm={12} md={8} lg={6} key={topic.id}>
              <Card className="topic-card">
                <div className="topic-image">
                  <img src={topic.image} alt={topic.title} />
                </div>
                <div className="topic-content">
                  <div className="topic-tags">
                    {topic.tags.map((tag, index) => (
                      <Tag key={index}>{tag}</Tag>
                    ))}
                  </div>
                  <Title level={4}>{topic.title}</Title>
                  <p className="topic-description">{topic.description}</p>
                  <Button type="primary" size="small" onClick={() => handleTopicClick(topic.id)}>
                    查看详情
                  </Button>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
        </Spin>
      </div>

      {/* 推荐行程 */}
      <div className="section">
        <div className="section-header">
          <Title level={3}>推荐行程</Title>
          <Button type="link" onClick={handleViewAllItineraries}>查看全部</Button>
        </div>
        {loading ? (
           <div style={{ textAlign: 'center', padding: '50px 0' }}><Spin size="large" /></div>
        ) : itineraries.length > 0 ? (
          <Row gutter={[16, 16]}>
            {itineraries.map((itinerary) => (
              <Col xs={24} sm={12} md={8} lg={6} key={itinerary.id}>
                <Card className="itinerary-card">
                  <div className="itinerary-image">
                    <img src={itinerary.image} alt={itinerary.title} />
                  </div>
                  <div className="itinerary-content">
                    <Title level={4}>{itinerary.title}</Title>
                    <div className="itinerary-meta">
                      <Space>
                        <Space>
                          <EnvironmentOutlined />
                          <span>{itinerary.destination}</span>
                        </Space>
                        <Space>
                          <CalendarOutlined />
                          <span>{itinerary.days}天</span>
                        </Space>
                        <Space>
                          <StarOutlined />
                          <span>{itinerary.rating}</span>
                        </Space>
                      </Space>
                    </div>
                    <Button type="primary" size="small" style={{ marginTop: 16 }} onClick={() => handleItineraryClick(itinerary.id)}>
                      查看行程
                    </Button>
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        ) : (
          <Empty description="暂无推荐行程" />
        )}
      </div>
    </div>
  );
};

export default DiscoverPage;
