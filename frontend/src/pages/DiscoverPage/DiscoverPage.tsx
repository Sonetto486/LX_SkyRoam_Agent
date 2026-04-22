import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Input, Select, Card, Button, Space, Row, Col, Tag, Typography, message, Spin } from 'antd';
import { SearchOutlined, StarOutlined, EnvironmentOutlined, CalendarOutlined } from '@ant-design/icons';
import { buildApiUrl } from '../../config/api';
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
  id: number;
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
  
  const [topicCards, setTopicCards] = useState<TopicCard[]>([]);
  const [loadingTopics, setLoadingTopics] = useState(true);

  // 抓取专题数据的独立函数，带上搜索和过滤参数
  const fetchTopics = async () => {
    setLoadingTopics(true);
    try {
      const qs = new URLSearchParams();
      if (searchValue) qs.append('keyword', searchValue);
      if (region && region !== 'all') qs.append('continent', region);
      
      const res = await fetch(buildApiUrl(`/topics?${qs.toString()}`));
      if (!res.ok) {
        throw new Error('网络请求错误');
      }
      const data = await res.json();
      setTopicCards(data);
    } catch (err: any) {
      if(err.message !== "Failed to fetch") {
        message.error('获取推荐专题失败：' + err.message);
      }
    } finally {
      setLoadingTopics(false);
    }
  };

  useEffect(() => {
    // 组件加载时先查一次全部
    fetchTopics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const itineraryCards: ItineraryCard[] = [
    {
      id: 1,
      title: '东京5日精华游',
      image: 'https://picsum.photos/seed/tokyo5/800/600',
      destination: '东京, 日本',
      days: 5,
      activities: 15,
      rating: 4.8
    },
    {
      id: 2,
      title: '关西7日文化之旅',
      image: 'https://picsum.photos/seed/kansai/800/600',
      destination: '大阪, 京都, 奈良',
      days: 7,
      activities: 20,
      rating: 4.9
    },
    {
      id: 3,
      title: '北海道冬季仙境',
      image: 'https://picsum.photos/seed/hokkaido2/800/600',
      destination: '札幌, 小樽, 函馆',
      days: 6,
      activities: 18,
      rating: 4.7
    },
    {
      id: 4,
      title: '冲绳海岛度假',
      image: 'https://picsum.photos/seed/okinawa/800/600',
      destination: '冲绳, 日本',
      days: 4,
      activities: 12,
      rating: 4.6
    }
  ];

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
            onPressEnter={fetchTopics}
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
          <Button type="primary" style={{ marginLeft: 16 }} onClick={fetchTopics} loading={loadingTopics}>
            搜索
          </Button>
        </div>
      </div>

      {/* 精选专题 */}
      <div className="section">
        <div className="section-header">
          <Title level={3}>精选专题</Title>
          <Button type="link">查看全部</Button>
        </div>
        <Spin spinning={loadingTopics}>
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
                    <Button type="primary" size="small" onClick={() => navigate(`/topic/${topic.id}`)}>
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
          <Button type="link">查看全部</Button>
        </div>
        <Row gutter={[16, 16]}>
          {itineraryCards.map((itinerary) => (
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
                  <Button type="primary" size="small" style={{ marginTop: 16 }}>
                    查看行程
                  </Button>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      </div>
    </div>
  );
};

export default DiscoverPage;
