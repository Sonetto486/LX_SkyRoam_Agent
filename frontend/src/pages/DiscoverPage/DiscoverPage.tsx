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

  const [itineraryCards, setItineraryCards] = useState<ItineraryCard[]>([]);
  const [loadingItineraries, setLoadingItineraries] = useState(false);

  const visibleTopicCards = topicCards.slice(0, 4);
  const visibleItineraryCards = itineraryCards.slice(0, 4);

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

// 获取推荐行程列表
    const fetchItineraries = async () => {
      setLoadingItineraries(true);
      try {
        const qs = new URLSearchParams();
        if (searchValue) qs.append('keyword', searchValue);
        // 如果行程没有continent字段，这里就只传keyword
        
        const res = await fetch(buildApiUrl(`/travel-plans/public?${qs.toString()}`));
        if (!res.ok) {
          throw new Error('网络请求错误');
        }
        const responseData = await res.json();
        // 假设接口返回的是 { plans: [...] } 或数组，兼容处理
        const plans = Array.isArray(responseData) ? responseData : (responseData.plans || []);
        
        // 映射属性名称与格式
        const formattedPlans: ItineraryCard[] = plans.map((p: any) => ({
          id: p.id,
          title: p.title || p.name || '未命名行程',
          image: p.cover_image || p.image_url || `https://picsum.photos/seed/plan_${p.id}/800/600`,
          destination: p.destination || '未提供目的地',
          days: p.days || 3,
          activities: p.activities_count || 10,
          rating: p.rating || p.total_score || 4.5
        }));
        
        setItineraryCards(formattedPlans);
      } catch (err: any) {
        if(err.message !== "Failed to fetch") {
          message.error('获取推荐行程失败：' + err.message);
        }
      } finally {
        setLoadingItineraries(false);
      }
    };
    
    // 把上面的 fetchTopics 和 fetchItineraries 绑在一起
    const handleSearch = () => {
      fetchTopics();
      fetchItineraries();
    };

    useEffect(() => {
      handleSearch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
            onPressEnter={handleSearch}
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
          <Button type="primary" style={{ marginLeft: 16 }} onClick={handleSearch} loading={loadingTopics || loadingItineraries}>
            搜索
          </Button>
        </div>
      </div>

      {/* 精选专题 */}
      <div className="section">
        <div className="section-header">
          <Title level={3}>精选专题</Title>
          <Button type="link" onClick={() => navigate('/topics-library')}>查看全部</Button>
        </div>
        <Spin spinning={loadingTopics}>
          <Row gutter={[16, 16]}>
            {visibleTopicCards.map((topic) => (
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
          <Button type="link" onClick={() => navigate('/plans-library?tab=public')}>查看全部</Button>
        </div>
        <Spin spinning={loadingItineraries}><Row gutter={[16, 16]}>{visibleItineraryCards.map((itinerary) => (
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
                  <Button type="primary" size="small" style={{ marginTop: 16 }} onClick={() => navigate(`/itineraries/${itinerary.id}`)}>查看行程</Button>
                </div>
              </Card>
            </Col>
          ))}
        </Row></Spin></div></div>);};export default DiscoverPage;





