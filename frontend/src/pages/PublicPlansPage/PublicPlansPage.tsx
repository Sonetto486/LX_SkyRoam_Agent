import React, { useEffect, useState } from 'react';
import { Typography, Row, Col, Spin, message, Input, Button, Card, Tag } from 'antd';
import { ArrowLeftOutlined, SearchOutlined, EnvironmentOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { authFetch } from '../../utils/auth';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';

const { Title, Paragraph } = Typography;

const PublicPlansPage: React.FC = () => {
  const [plans, setPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchValue, setSearchValue] = useState('');
  const navigate = useNavigate();

  const fetchPlans = async (keyword = '') => {
    setLoading(true);
    try {
      let url = buildApiUrl(API_ENDPOINTS.TRAVEL_PLANS_PUBLIC);
      if (keyword) {
        url += `?keyword=${encodeURIComponent(keyword)}`;
      }
      const resp = await authFetch(url);
      if (!resp.ok) throw new Error('Failed to fetch public plans');
      const data = await resp.json();
      const sourceData = data.plans || data.items || [];
      const mappedPlans = sourceData.map((plan: any) => ({
        id: plan.id,
        title: plan.title || '未命名行程',
        image: 'https://picsum.photos/seed/' + plan.id + '/800/600',
        destination: plan.destination || '未知目的地',
        days: plan.duration_days || 1,
        activities: plan.items ? plan.items.length : 15,
        rating: plan.score || 4.8,
        description: plan.description
      }));
      setPlans(mappedPlans);
    } catch (e) {
      message.error({ content: '获取所有推荐行程失败', key: 'fetchPlansError' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlans();
  }, []);

  const handleSearch = (value: string) => {
    setSearchValue(value);
    fetchPlans(value);
  };

  return (
    <div className="public-plans-page">
      <div className="page-container" style={{ padding: '40px', maxWidth: '1200px', margin: '0 auto', minHeight: '100vh' }}>
        <Button 
          type="link" 
          icon={<ArrowLeftOutlined />} 
          onClick={() => navigate('/discover')}
          style={{ marginBottom: '20px', padding: 0 }}
        >
          返回发现页
        </Button>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <Title level={2} style={{ margin: 0 }}>查看推荐行程</Title>
          <Input.Search
            placeholder="搜索行程..."
            allowClear
            onSearch={handleSearch}
            style={{ width: 300 }}
            enterButton={<Button type="primary" icon={<SearchOutlined />}>搜索</Button>}
          />
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '50px' }}><Spin size="large" /></div>
        ) : (
          <Row gutter={[24, 24]}>
            {plans.length > 0 ? (
              plans.map(itinerary => (
                <Col xs={24} sm={12} md={8} lg={6} key={itinerary.id}>
                  <Card
                    hoverable
                    className="itinerary-card"
                    style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
                    bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column' }}
                      onClick={() => navigate(`/plans/${itinerary.id}`)}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                        <Title level={4} style={{ margin: 0, fontSize: '1.1rem' }} ellipsis={{ rows: 2 }}>
                          {itinerary.title}
                        </Title>
                      </div>
                      {itinerary.destination && (
                        <div style={{ marginBottom: 16 }}>
                          <Tag icon={<EnvironmentOutlined />} color="blue" style={{ marginBottom: 4 }}>
                            {itinerary.destination}
                          </Tag>
                      </div>
                    )}
                    <Paragraph ellipsis={{ rows: 3 }} type="secondary" style={{ flex: 1 }}>
                      {itinerary.description || '暂无简介，点击查看行程详情。'}
                    </Paragraph>
                    <div style={{ marginTop: 'auto', paddingTop: 16, borderTop: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', color: '#8c8c8c', fontSize: '0.85rem' }}>
                      <span>{itinerary.days} 天</span>
                      <span>1 组方案</span>
                    </div>
                  </Card>
                </Col>
              ))
            ) : (
              <Col span={24}>
                <div style={{ textAlign: 'center', padding: '40px 0', color: '#888' }}>
                  未找到相关行程
                </div>
              </Col>
            )}
          </Row>
        )}
      </div>
    </div>
  );
};

export default PublicPlansPage;
