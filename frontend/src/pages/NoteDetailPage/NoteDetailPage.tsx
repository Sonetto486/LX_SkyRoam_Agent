import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Typography, Button, Space, Card, Tag, Spin, Result, Divider, Image } from 'antd';
import { ArrowLeftOutlined, EnvironmentOutlined, StarOutlined, RocketOutlined, CoffeeOutlined, InsuranceOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { authFetch } from '../../utils/auth';
import './NoteDetailPage.css';

const { Title, Paragraph, Text } = Typography;

interface NoteDetail {
  id: number;
  title: string;
  destination: string;
  image_url: string;
  transport_info?: string;
  accommodation_info?: string;
  must_visit_spots?: string;
  food_recommendations?: string;
  practical_tips?: string;
  travel_feelings?: string;
}

const NoteDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [note, setNote] = useState<NoteDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchNoteDetail = async () => {
      setLoading(true);
      try {
        const response = await authFetch(`/notes/${id}`);
        if (response.ok) {
          const data = await response.json();
          setNote(data);
        }
      } catch (error) {
        console.error('获取笔记详情失败:', error);
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchNoteDetail();
    }
  }, [id]);

  if (loading) {
    return <div className="loading-container"><Spin size="large" tip="加载灵感详情..." /></div>;
  }

  if (!note) {
    return (
      <Result
        status="404"
        title="笔记未找到"
        subTitle="对不起，您查看的旅行灵感不存在或已被删除。"
        extra={<Button type="primary" onClick={() => navigate('/inspiration')}>返回灵感墙</Button>}
      />
    );
  }

  return (
    <div className="note-detail-page">
      <div className="detail-container">
        <Button 
          type="link" 
          icon={<ArrowLeftOutlined />} 
          onClick={() => navigate(-1)}
          className="back-link"
        >
          返回
        </Button>

        <div className="detail-header">
          <div className="header-image-container">
            <Image src={note.image_url} alt={note.title} className="main-image" />
          </div>
          <div className="header-info">
            <Title level={1} className="note-title">{note.title}</Title>
            <Space className="note-meta">
              <Tag color="blue" icon={<EnvironmentOutlined />}>{note.destination}</Tag>
              <Tag color="gold" icon={<StarOutlined />}>精选灵感</Tag>
            </Space>
          </div>
        </div>

        <div className="detail-content">
          <div className="content-main">
            {note.travel_feelings && (
              <section className="detail-section">
                <Title level={3}><RocketOutlined /> 旅行感悟</Title>
                <div className="section-body card-style">
                  <Paragraph className="content-text">{note.travel_feelings}</Paragraph>
                </div>
              </section>
            )}

            {note.must_visit_spots && (
              <section className="detail-section">
                <Title level={3}><EnvironmentOutlined /> 必打卡景点</Title>
                <div className="section-body">
                  <Paragraph className="content-text">{note.must_visit_spots}</Paragraph>
                </div>
              </section>
            )}

            <div className="grid-sections">
              {note.transport_info && (
                <section className="detail-section">
                  <Title level={4}><RocketOutlined /> 交通攻略</Title>
                  <Paragraph className="content-text secondary">{note.transport_info}</Paragraph>
                </section>
              )}

              {note.accommodation_info && (
                <section className="detail-section">
                  <Title level={4}><CoffeeOutlined /> 住宿建议</Title>
                  <Paragraph className="content-text secondary">{note.accommodation_info}</Paragraph>
                </section>
              )}

              {note.food_recommendations && (
                <section className="detail-section">
                  <Title level={4}><InsuranceOutlined /> 美食推荐</Title>
                  <Paragraph className="content-text secondary">{note.food_recommendations}</Paragraph>
                </section>
              )}
            </div>

            {note.practical_tips && (
              <Card className="tips-card" title={<span><InfoCircleOutlined /> 小贴士</span>}>
                <Paragraph className="content-text">{note.practical_tips}</Paragraph>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default NoteDetailPage;
