import React, { useEffect, useState } from 'react';
import { Typography, Row, Col, Card, Spin, message, Input, Button } from 'antd';
import { ArrowLeftOutlined, SearchOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

import { authFetch } from '../../utils/auth';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';

const { Title, Paragraph } = Typography;

const TopicsPage: React.FC = () => {
  const [topics, setTopics] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchValue, setSearchValue] = useState('');
  const navigate = useNavigate();

  const fetchTopics = async (keyword = '') => {
    setLoading(true);
    try {
      let url = buildApiUrl('/topics');
      if (keyword) {
        url += `?keyword=${encodeURIComponent(keyword)}`;
      }
      const resp = await authFetch(url);
      if (!resp.ok) throw new Error('Failed to fetch topics');
      const data = await resp.json();
      const sourceData = Array.isArray(data) ? data : data.topics || data.items || [];
      const mappedTopics = sourceData.map((topic: any) => ({
        id: topic.id,
        title: topic.title || topic.name || '未命名专题',
        image_url: topic.image || topic.cover_url || topic.cover_image_url || 'https://picsum.photos/seed/' + topic.id + '/800/600',
        tags: topic.tags || [topic.continent || topic.region || '未分类'],
        description: topic.description || topic.intro || '暂无描述'
      }));
      setTopics(mappedTopics);
    } catch (e) {
      message.error({ content: '获取专题列表失败', key: 'fetchTopicsError' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTopics();
  }, []);

  const handleSearch = (value: string) => {
    setSearchValue(value);
    fetchTopics(value);
  };

  return (
    <div className="topics-page">
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
          <Title level={2} style={{ margin: 0 }}>探索全部精选专题</Title>
          <Input.Search
            placeholder="搜索专题..."
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
            {topics.length > 0 ? (
              topics.map(t => (
                <Col xs={24} sm={12} md={8} lg={6} key={t.id}>
                  <Card className="topic-card" bodyStyle={{ padding: 0, overflow: 'hidden' }}>
                    <div className="topic-image" style={{ height: '200px', overflow: 'hidden', position: 'relative' }}>
                      <img alt={t.title} src={t.image_url} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                      <div className="topic-tags" style={{ position: 'absolute', bottom: '10px', left: '10px' }}>
                        {t.tags && t.tags.map((tag: string, idx: number) => (
                          <span key={idx} className="topic-tag" style={{ background: 'rgba(0,0,0,0.6)', color: '#fff', padding: '2px 8px', borderRadius: '4px', marginRight: '5px', fontSize: '12px' }}>{tag}</span>
                        ))}
                      </div>
                    </div>
                    <div className="topic-content" style={{ padding: '16px' }}>
                      <Title level={4} className="topic-title" style={{ margin: '0 0 8px 0', fontSize: '16px' }}>{t.title}</Title>
                      <Paragraph className="topic-desc" ellipsis={{ rows: 2 }} style={{ color: '#666', fontSize: '13px', marginBottom: '16px' }}>{t.description}</Paragraph>
                      <Button type="primary" onClick={() => navigate(`/topics/${t.id}`)}>
                        查看详情
                      </Button>
                    </div>
                  </Card>
                </Col>
              ))
            ) : (
              <Col span={24}>
                <div style={{ textAlign: 'center', padding: '40px 0', color: '#888' }}>
                  未找到相关专题
                </div>
              </Col>
            )}
          </Row>
        )}
      </div>
    </div>
  );
};

export default TopicsPage;
