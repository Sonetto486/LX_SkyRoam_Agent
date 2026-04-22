import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Button, Row, Col, Typography, message, Spin, Tag, Rate, Badge } from 'antd';
import { ArrowLeftOutlined, EnvironmentOutlined } from '@ant-design/icons';
import { buildApiUrl } from '../../config/api';
import './TopicDetailPage.css';

const { Title, Paragraph } = Typography;

interface Place {
  id: number;
  type: string;
  name: string;
  description: string;
  highlight: string;
  image: string;
  rating: number;
  isKeyPoint: boolean;
}

interface TopicDetail {
  id: number;
  title: string;
  image: string;
  tags: string[];
  description: string;
  places: Place[];
}

const TopicDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const [topic, setTopic] = useState<TopicDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTopicDetail = async () => {
      try {
        const res = await fetch(buildApiUrl(`/topics/${id}`));
        if (!res.ok) {
          throw new Error('网络请求错误');
        }
        const data = await res.json();
        setTopic(data);
      } catch (err: any) {
        message.error('获取专题详情失败：' + err.message);
      } finally {
        setLoading(false);
      }
    };
    if (id) {
      fetchTopicDetail();
    }
  }, [id]);

  if (loading) {
    return (
      <div className="topic-detail-loading">
        <Spin size="large" tip="正在加载专题内容..." />
      </div>
    );
  }

  if (!topic) {
    return <div className="topic-detail-error">专题不存在或已被删除</div>;
  }

  return (
    <div className="topic-detail-container">
      {/* 头部大封面 */}
      <div 
        className="topic-detail-header" 
        style={{ backgroundImage: `linear-gradient(rgba(0,0,0,0.3), rgba(0,0,0,0.8)), url(${topic.image})` }}
      >
        <div className="topic-detail-header-content">
          <Button 
            className="back-btn" 
            type="link" 
            icon={<ArrowLeftOutlined />} 
            onClick={() => navigate(-1)}
          >
            返回发现页
          </Button>
          <div className="header-tags">
            {topic.tags.map((tag, idx) => (
              <Tag key={idx} color="blue">{tag}</Tag>
            ))}
          </div>
          <Title style={{ color: 'white', marginTop: 16, marginBottom: 8 }}>{topic.title}</Title>
          <Paragraph style={{ color: 'rgba(255,255,255,0.85)', fontSize: 16, maxWidth: 600 }}>
            {topic.description}
          </Paragraph>
        </div>
      </div>

      {/* 具体景点瀑布流展示 */}
      <div className="topic-detail-content">
        <Title level={3} style={{ marginBottom: 24 }}>包含的推荐地点</Title>
        <Row gutter={[24, 24]}>
          {topic.places.map((place) => (
            <Col xs={24} sm={12} lg={8} key={`${place.type}-${place.id}`}>
              <Badge.Ribbon text={place.isKeyPoint ? "核心必去" : ""} color="volcano" style={{ display: place.isKeyPoint ? 'block' : 'none' }}>
                <Card 
                  hoverable
                  className="place-card"
                  cover={
                    <div className="place-image-wrapper">
                      <img alt={place.name} src={place.image} className="place-image" />
                      <div className="place-type-badge">
                        <EnvironmentOutlined /> {place.type === 'destinations' ? '目的地' : '景点'}
                      </div>
                    </div>
                  }
                >
                  <Title level={4} className="place-title">{place.name}</Title>
                  <Rate disabled defaultValue={place.rating} allowHalf className="place-rating" />
                  
                  <div className="place-highlight">
                    <strong>💡 亮点: </strong> {place.highlight}
                  </div>
                  
                  <Paragraph ellipsis={{ rows: 3 }} className="place-desc">
                    {place.description}
                  </Paragraph>
                </Card>
              </Badge.Ribbon>
            </Col>
          ))}
        </Row>
      </div>
    </div>
  );
};

export default TopicDetailPage;