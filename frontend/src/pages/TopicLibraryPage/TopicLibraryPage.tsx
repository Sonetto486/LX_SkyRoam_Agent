import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Col, Row, Spin, Tag, Typography, message } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { buildApiUrl } from '../../config/api';
import './TopicLibraryPage.css';

const { Title, Paragraph } = Typography;

interface TopicCard {
  id: number;
  title: string;
  image: string;
  tags: string[];
  description: string;
}

const TopicLibraryPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [topics, setTopics] = useState<TopicCard[]>([]);

  useEffect(() => {
    const fetchTopics = async () => {
      try {
        setLoading(true);
        const res = await fetch(buildApiUrl('/topics'));
        if (!res.ok) {
          throw new Error('网络请求错误');
        }
        const data = await res.json();
        setTopics(Array.isArray(data) ? data : []);
      } catch (err: any) {
        message.error('获取专题列表失败：' + err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchTopics();
  }, []);

  return (
    <div className="topic-library-page">
      <div className="topic-library-header">
        <Button type="link" icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} className="topic-library-back">
          返回上一页
        </Button>
        <Title level={2} style={{ margin: 0 }}>专题总览</Title>
      </div>

      <Spin spinning={loading}>
        <Row gutter={[16, 16]}>
          {topics.map((topic) => (
            <Col xs={24} sm={12} md={8} lg={6} key={topic.id}>
              <Card className="topic-library-card" hoverable onClick={() => navigate(`/topic/${topic.id}`)}>
                <div className="topic-library-image">
                  <img src={topic.image} alt={topic.title} />
                </div>
                <div className="topic-library-tags">
                  {topic.tags.map((tag) => (
                    <Tag key={tag}>{tag}</Tag>
                  ))}
                </div>
                <Title level={4}>{topic.title}</Title>
                <Paragraph ellipsis={{ rows: 3 }}>{topic.description}</Paragraph>
                <Button type="primary" size="small" onClick={(e) => { e.stopPropagation(); navigate(`/topic/${topic.id}`); }}>
                  查看详情
                </Button>
              </Card>
            </Col>
          ))}
        </Row>
      </Spin>
    </div>
  );
};

export default TopicLibraryPage;
