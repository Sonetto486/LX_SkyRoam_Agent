import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button, Card, Col, Empty, Rate, Row, Spin, Tag, Typography, message } from 'antd';
import { ArrowLeftOutlined, EnvironmentOutlined, GlobalOutlined, ClockCircleOutlined, StarOutlined } from '@ant-design/icons';
import { buildApiUrl } from '../../config/api';
import './PlaceDetailPage.css';

const { Title, Paragraph } = Typography;

interface PlaceDetailResponse {
  type: 'destinations' | 'attractions';
  id: number;
  name: string;
  coverImage?: string | null;
  summary?: string | null;
  destination?: {
    country?: string;
    city?: string;
    region?: string;
    latitude?: number | null;
    longitude?: number | null;
    timezone?: string | null;
    highlights?: string[];
    bestTimeToVisit?: string | null;
    popularityScore?: number;
    safetyScore?: number | null;
    costLevel?: string | null;
    images?: string[];
    videos?: string[];
  };
  attraction?: {
    category?: string;
    description?: string | null;
    address?: string | null;
    latitude?: number | null;
    longitude?: number | null;
    openingHours?: string | null;
    ticketPrice?: number | null;
    currency?: string | null;
    rating?: number | null;
    reviewCount?: number | null;
    features?: string | null;
    accessibility?: string | null;
    contactInfo?: string | null;
    website?: string | null;
    images?: string[];
  };
  relatedAttractions?: Array<{
    id: number;
    name: string;
    category?: string;
    description?: string | null;
    address?: string | null;
    rating?: number | null;
    reviewCount?: number | null;
    image?: string | null;
  }>;
}

const PlaceDetailPage: React.FC = () => {
  const { type, id } = useParams<{ type: 'destinations' | 'attractions'; id: string }>();
  const navigate = useNavigate();
  const [place, setPlace] = useState<PlaceDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPlace = async () => {
      try {
        setLoading(true);
        const res = await fetch(buildApiUrl(`/topics/places/${type}/${id}`));
        if (!res.ok) {
          throw new Error('网络请求错误');
        }
        const data = await res.json();
        setPlace(data);
      } catch (err: any) {
        message.error('获取地点详情失败：' + err.message);
      } finally {
        setLoading(false);
      }
    };

    if (type && id) {
      fetchPlace();
    }
  }, [type, id]);

  if (loading) {
    return (
      <div className="place-detail-loading">
        <Spin size="large" tip="正在加载地点详情..." />
      </div>
    );
  }

  if (!place) {
    return <div className="place-detail-error">地点不存在或已被删除</div>;
  }

  const coverImage = place.coverImage || (place.type === 'destinations' ? place.destination?.images?.[0] : place.attraction?.images?.[0]) || 'https://picsum.photos/seed/place-detail/1600/900';

  return (
    <div className="place-detail-container">
      <div className="place-detail-hero" style={{ backgroundImage: `linear-gradient(rgba(0,0,0,0.2), rgba(0,0,0,0.78)), url(${coverImage})` }}>
        <div className="place-detail-hero-inner">
          <Button type="link" className="back-link" icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
            返回上一页
          </Button>

          <div className="hero-tags">
            <Tag color="blue">{place.type === 'destinations' ? '目的地' : '景点'}</Tag>
            {place.type === 'destinations' ? <Tag color="geekblue">目的地详情</Tag> : <Tag color="volcano">景点详情</Tag>}
          </div>

          <Title level={1} style={{ color: '#fff', marginBottom: 8 }}>
            {place.name}
          </Title>
          <Paragraph style={{ color: 'rgba(255,255,255,0.86)', fontSize: 16, maxWidth: 760 }}>
            {place.summary}
          </Paragraph>
        </div>
      </div>

      <div className="place-detail-content">
        {place.type === 'destinations' && place.destination && (
          <>
            <Row gutter={[24, 24]} className="info-row">
              <Col xs={24} lg={16}>
                <Card className="info-card">
                  <Title level={3}>基础信息</Title>
                  <div className="info-grid">
                    <div><EnvironmentOutlined /> 国家：{place.destination.country || '-'}</div>
                    <div><EnvironmentOutlined /> 城市：{place.destination.city || '-'}</div>
                    <div><GlobalOutlined /> 区域：{place.destination.region || '-'}</div>
                    <div><ClockCircleOutlined /> 最佳访问期：{place.destination.bestTimeToVisit || '-'}</div>
                    <div><StarOutlined /> 热度分：{place.destination.popularityScore ?? '-'}</div>
                    <div>安全分：{place.destination.safetyScore ?? '-'}</div>
                    <div>消费水平：{place.destination.costLevel || '-'}</div>
                    <div>时区：{place.destination.timezone || '-'}</div>
                  </div>
                </Card>
              </Col>
              <Col xs={24} lg={8}>
                <Card className="info-card">
                  <Title level={4}>推荐亮点</Title>
                  <div className="chip-list">
                    {(place.destination.highlights || []).length > 0 ? (
                      place.destination.highlights!.map((item, idx) => <Tag key={idx}>{item}</Tag>)
                    ) : (
                      <Empty description="暂无亮点数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    )}
                  </div>
                </Card>
              </Col>
            </Row>

            <Card className="info-card" style={{ marginTop: 24 }}>
              <Title level={3}>周边推荐景点</Title>
              <Row gutter={[16, 16]}>
                {(place.relatedAttractions || []).map((item) => (
                  <Col xs={24} sm={12} lg={8} key={item.id}>
                    <Card hoverable className="mini-card" onClick={() => navigate(`/places/attractions/${item.id}`)}>
                      <div className="mini-card-image-wrap">
                        <img src={item.image || `https://picsum.photos/seed/attr_${item.id}/800/600`} alt={item.name} />
                      </div>
                      <Title level={5}>{item.name}</Title>
                      <div className="mini-meta">{item.category || '景点'} · {item.rating ?? '-'} 分</div>
                      <Paragraph ellipsis={{ rows: 2 }} className="mini-desc">{item.description}</Paragraph>
                      <Button type="link" style={{ paddingLeft: 0 }}>查看详情 →</Button>
                    </Card>
                  </Col>
                ))}
              </Row>
            </Card>
          </>
        )}

        {place.type === 'attractions' && place.attraction && (
          <Row gutter={[24, 24]}>
            <Col xs={24} lg={14}>
              <Card className="info-card">
                <Title level={3}>景点详情</Title>
                <div className="detail-list">
                  <div><strong>分类：</strong>{place.attraction.category || '-'}</div>
                  <div><strong>地址：</strong>{place.attraction.address || '-'}</div>
                  <div><strong>开放时间：</strong>{place.attraction.openingHours || '-'}</div>
                  <div><strong>门票价格：</strong>{place.attraction.ticketPrice != null ? `${place.attraction.ticketPrice} ${place.attraction.currency || ''}` : '-'}</div>
                  <div><strong>评分：</strong>{place.attraction.rating ?? '-'} / 5</div>
                  <div><strong>点评数：</strong>{place.attraction.reviewCount ?? '-'}</div>
                  <div><strong>联系方式：</strong>{place.attraction.contactInfo || '-'}</div>
                  <div><strong>官网：</strong>{place.attraction.website || '-'}</div>
                </div>
              </Card>
            </Col>
            <Col xs={24} lg={10}>
              <Card className="info-card">
                <Title level={3}>所属目的地</Title>
                <p>{place.destination?.name || '-'}</p>
                <p>{place.destination?.country || ''} {place.destination?.city ? `· ${place.destination.city}` : ''}</p>
                <p>{place.destination?.region || ''}</p>
              </Card>
              <Card className="info-card" style={{ marginTop: 24 }}>
                <Title level={4}>设施与提示</Title>
                <Paragraph>{place.attraction.features || '暂无设施信息'}</Paragraph>
                <Paragraph>{place.attraction.accessibility || '暂无无障碍信息'}</Paragraph>
              </Card>
            </Col>
          </Row>
        )}
      </div>
    </div>
  );
};

export default PlaceDetailPage;
