import React, { useState, useEffect } from 'react';
import { Modal, Button, Spin, Typography, Tag, Space, Image, Collapse, Rate, message, Empty, Divider, Card } from 'antd';
import {
  EnvironmentOutlined,
  PhoneOutlined,
  ClockCircleOutlined,
  DollarOutlined,
  GlobalOutlined,
  StarOutlined,
  ReloadOutlined,
  BulbOutlined,
  HomeOutlined,
  CoffeeOutlined,
  CameraOutlined
} from '@ant-design/icons';
import { authFetch } from '../../utils/auth';
import { buildApiUrl } from '../../config/api';

const { Text, Paragraph, Title } = Typography;
const { Panel } = Collapse;

interface DetailModalProps {
  visible: boolean;
  type: 'attraction' | 'hotel' | 'meal';
  data: any;
  planId?: number;
  itemId?: number | string;
  onCancel: () => void;
  onDetailUpdated?: (detail: any) => void;
}

interface Review {
  content: string;
  rating?: number;
  visitor_type?: string;
  date?: string;
}

interface DetailInfo {
  name: string;
  city: string;
  address?: string;
  coordinates?: { lat: number; lng: number };
  description: string;
  images: Array<{ url: string; title?: string }>;
  rating?: number;
  opening_hours?: string;
  phone?: string;
  website?: string;
  facilities?: string[];
  ticket_price?: number;
  price_per_night?: number;
  average_cost?: number;
  price_note?: string;
  tips?: string[];
  recommended_dishes?: string[];
  cuisine?: string;
  star_rating?: number;
  check_in?: string;
  check_out?: string;
  source?: string;
  error?: string;
  reviews?: Review[];
  highlights?: string[];
  best_time?: string;
  duration?: string;
}

const DetailModal: React.FC<DetailModalProps> = ({
  visible,
  type,
  data,
  planId,
  itemId,
  onCancel,
  onDetailUpdated
}) => {
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<DetailInfo | null>(null);
  const [cached, setCached] = useState(false);

  useEffect(() => {
    if (visible && data) {
      // 初始化基本信息
      const initialDetail: DetailInfo = {
        name: data.name || data.title || data.restaurant_name || '',
        city: data.city || '',
        address: data.address,
        coordinates: data.coordinates,
        description: data.description || '',
        images: data.images || data.photos || [],
        rating: data.rating || data.score,
        opening_hours: data.opening_hours || '',
        phone: data.phone || '',
        website: data.website || '',
        facilities: data.facilities || [],
        price_note: data.price_note || data.cost || '',
        tips: [],
        source: '基本信息'
      };

      // 根据类型设置价格
      if (type === 'attraction') {
        initialDetail.ticket_price = data.ticket_price || data.price;
      } else if (type === 'hotel') {
        initialDetail.price_per_night = data.price_per_night || data.price;
        initialDetail.star_rating = data.star_rating || data.star;
        initialDetail.check_in = data.check_in || '14:00';
        initialDetail.check_out = data.check_out || '12:00';
      } else if (type === 'meal') {
        initialDetail.average_cost = data.average_cost || data.estimated_cost;
        initialDetail.cuisine = data.cuisine;
        initialDetail.recommended_dishes = data.recommended_dishes || [];
      }

      setDetail(initialDetail);
      setCached(false);
    }
  }, [visible, data, type]);

  const handleEnrichDetail = async () => {
    if (!planId) {
      message.warning('无法获取行程ID');
      return;
    }

    setLoading(true);
    try {
      let url = '';
      let body: any = {
        name: detail?.name,
        city: detail?.city || data?.city,
        address: detail?.address,
        coordinates: detail?.coordinates
      };

      // 根据类型选择不同的API端点
      if (itemId) {
        // 如果有itemId，使用项目详情端点
        url = buildApiUrl(`/travel-plans/${planId}/items/${itemId}/enrich-detail`);
      } else {
        // 否则使用通用端点
        if (type === 'attraction') {
          url = buildApiUrl(`/travel-plans/${planId}/enrich-attraction-detail`);
        } else if (type === 'hotel') {
          url = buildApiUrl(`/travel-plans/${planId}/enrich-hotel-detail`);
        } else {
          url = buildApiUrl(`/travel-plans/${planId}/enrich-meal-detail`);
          body.cuisine = detail?.cuisine;
        }
      }

      const response = await authFetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      if (!response.ok) {
        throw new Error('获取详情失败');
      }

      const result = await response.json();

      if (result.success && result.detail) {
        setDetail(result.detail);
        setCached(true);
        message.success('详情已更新');

        if (onDetailUpdated) {
          onDetailUpdated(result.detail);
        }
      } else {
        throw new Error(result.message || '获取详情失败');
      }
    } catch (error: any) {
      message.error(error.message || '获取详情失败');
    } finally {
      setLoading(false);
    }
  };

  const getTypeLabel = () => {
    switch (type) {
      case 'attraction':
        return '景点详情';
      case 'hotel':
        return '住宿详情';
      case 'meal':
        return '餐饮详情';
      default:
        return '详情';
    }
  };

  const getTypeIcon = () => {
    switch (type) {
      case 'attraction':
        return <CameraOutlined />;
      case 'hotel':
        return <HomeOutlined />;
      case 'meal':
        return <CoffeeOutlined />;
      default:
        return null;
    }
  };

  const renderPriceInfo = () => {
    if (!detail) return null;

    if (type === 'attraction') {
      return (
        <>
          {detail.ticket_price !== undefined && detail.ticket_price !== null && (
            <Space>
              <DollarOutlined style={{ color: '#faad14' }} />
              <Text strong style={{ color: '#faad14' }}>
                ¥{detail.ticket_price}
              </Text>
              {detail.price_note && (
                <Text type="secondary">({detail.price_note})</Text>
              )}
            </Space>
          )}
        </>
      );
    } else if (type === 'hotel') {
      return (
        <>
          {detail.price_per_night !== undefined && detail.price_per_night !== null && (
            <Space>
              <DollarOutlined style={{ color: '#faad14' }} />
              <Text strong style={{ color: '#faad14' }}>
                ¥{detail.price_per_night}/晚
              </Text>
            </Space>
          )}
          {detail.star_rating && (
            <Tag color="purple">
              <StarOutlined /> {detail.star_rating}星级
            </Tag>
          )}
        </>
      );
    } else if (type === 'meal') {
      return (
        <>
          {detail.average_cost !== undefined && detail.average_cost !== null && (
            <Space>
              <DollarOutlined style={{ color: '#faad14' }} />
              <Text strong style={{ color: '#faad14' }}>
                人均 ¥{detail.average_cost}
              </Text>
            </Space>
          )}
          {detail.cuisine && (
            <Tag color="orange">{detail.cuisine}</Tag>
          )}
        </>
      );
    }

    return null;
  };

  return (
    <Modal
      title={
        <Space>
          {getTypeIcon()}
          <span>{getTypeLabel()}</span>
          {detail?.name && <Text type="secondary">- {detail.name}</Text>}
        </Space>
      }
      open={visible}
      onCancel={onCancel}
      footer={[
        <Button key="close" onClick={onCancel}>
          关闭
        </Button>,
        <Button
          key="enrich"
          type="primary"
          icon={<ReloadOutlined />}
          loading={loading}
          onClick={handleEnrichDetail}
        >
          {cached ? '刷新信息' : '更新信息'}
        </Button>
      ]}
      width={700}
      destroyOnClose
    >
      <Spin spinning={loading}>
        {!detail ? (
          <Empty description="暂无数据" />
        ) : (
          <div>
            {/* 图片展示 */}
            {detail.images && detail.images.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <Image.PreviewGroup>
                  <Space size={8} wrap>
                    {detail.images.slice(0, 4).map((img, index) => (
                      <Image
                        key={index}
                        width={150}
                        height={100}
                        src={typeof img === 'string' ? img : img.url}
                        alt={typeof img === 'string' ? '' : img.title}
                        style={{ borderRadius: 8, objectFit: 'cover' }}
                        fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                      />
                    ))}
                  </Space>
                </Image.PreviewGroup>
              </div>
            )}

            {/* 基本信息 */}
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              {/* 名称和评分 */}
              <div>
                <Title level={4} style={{ marginBottom: 8 }}>{detail.name}</Title>
                <Space size={16}>
                  {detail.rating !== undefined && detail.rating !== null && (
                    <Space>
                      <StarOutlined style={{ color: '#faad14' }} />
                      <Rate disabled value={detail.rating} allowHalf style={{ fontSize: 14 }} />
                      <Text>{detail.rating}分</Text>
                    </Space>
                  )}
                  {renderPriceInfo()}
                </Space>
              </div>

              {/* 地址 */}
              {detail.address && (
                <Paragraph style={{ marginBottom: 0 }}>
                  <EnvironmentOutlined style={{ marginRight: 8, color: '#8c8c8c' }} />
                  {detail.address}
                </Paragraph>
              )}

              {/* 联系方式和营业时间 */}
              <Space size={24} wrap>
                {detail.phone && (
                  <Text>
                    <PhoneOutlined style={{ marginRight: 8 }} />
                    {detail.phone}
                  </Text>
                )}
                {detail.opening_hours && (
                  <Text>
                    <ClockCircleOutlined style={{ marginRight: 8 }} />
                    {detail.opening_hours}
                  </Text>
                )}
                {detail.website && (
                  <a href={detail.website} target="_blank" rel="noopener noreferrer">
                    <GlobalOutlined style={{ marginRight: 8 }} />
                    官网
                  </a>
                )}
              </Space>

              {/* 酒店特有信息 */}
              {type === 'hotel' && (detail.check_in || detail.check_out) && (
                <Space size={24}>
                  {detail.check_in && <Text type="secondary">入住：{detail.check_in}</Text>}
                  {detail.check_out && <Text type="secondary">退房：{detail.check_out}</Text>}
                </Space>
              )}

              <Divider style={{ margin: '12px 0' }} />

              {/* 介绍 */}
              {detail.description && (
                <div>
                  <Text strong>介绍</Text>
                  <Paragraph style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>
                    {detail.description}
                  </Paragraph>
                </div>
              )}

              {/* 景点亮点 */}
              {type === 'attraction' && detail.highlights && detail.highlights.length > 0 && (
                <div>
                  <Text strong><BulbOutlined style={{ marginRight: 8 }} />景点亮点</Text>
                  <div style={{ marginTop: 8 }}>
                    {detail.highlights.map((highlight, index) => (
                      <Tag key={index} color="green" style={{ marginBottom: 4 }}>
                        {highlight}
                      </Tag>
                    ))}
                  </div>
                </div>
              )}

              {/* 最佳游览时间和时长 */}
              {type === 'attraction' && (detail.best_time || detail.duration) && (
                <Space size={24} wrap>
                  {detail.best_time && (
                    <Text><ClockCircleOutlined style={{ marginRight: 8 }} />最佳游览时间：{detail.best_time}</Text>
                  )}
                  {detail.duration && (
                    <Text>建议游览时长：{detail.duration}</Text>
                  )}
                </Space>
              )}

              {/* 游客评价 */}
              {detail.reviews && detail.reviews.length > 0 && (
                <div>
                  <Text strong>游客评价</Text>
                  <div style={{ marginTop: 8 }}>
                    {detail.reviews.map((review, index) => (
                      <Card key={index} size="small" style={{ marginBottom: 8 }}>
                        <Space direction="vertical" size={4} style={{ width: '100%' }}>
                          <Space size={8}>
                            {review.rating && (
                              <Rate disabled value={review.rating} allowHalf style={{ fontSize: 12 }} />
                            )}
                            {review.visitor_type && (
                              <Tag color="blue">{review.visitor_type}</Tag>
                            )}
                            {review.date && (
                              <Text type="secondary" style={{ fontSize: 12 }}>{review.date}</Text>
                            )}
                          </Space>
                          <Text>{review.content}</Text>
                        </Space>
                      </Card>
                    ))}
                  </div>
                </div>
              )}

              {/* 推荐菜品（餐厅） */}
              {type === 'meal' && detail.recommended_dishes && detail.recommended_dishes.length > 0 && (
                <div>
                  <Text strong>推荐菜品</Text>
                  <div style={{ marginTop: 8 }}>
                    {detail.recommended_dishes.map((dish, index) => (
                      <Tag key={index} color="orange" style={{ marginBottom: 4 }}>
                        {dish}
                      </Tag>
                    ))}
                  </div>
                </div>
              )}

              {/* 设施 */}
              {detail.facilities && detail.facilities.length > 0 && (
                <div>
                  <Text strong>设施服务</Text>
                  <div style={{ marginTop: 8 }}>
                    {detail.facilities.map((facility, index) => (
                      <Tag key={index} color="blue" style={{ marginBottom: 4 }}>
                        {facility}
                      </Tag>
                    ))}
                  </div>
                </div>
              )}

              {/* 游览/住宿/用餐提示 */}
              {detail.tips && detail.tips.length > 0 && (
                <Collapse ghost>
                  <Panel header={<><BulbOutlined style={{ marginRight: 8 }} />实用提示</>} key="tips">
                    <ul style={{ margin: 0, paddingLeft: 20 }}>
                      {detail.tips.map((tip, index) => (
                        <li key={index}>
                          <Text>{tip}</Text>
                        </li>
                      ))}
                    </ul>
                  </Panel>
                </Collapse>
              )}

              {/* 数据来源 */}
              {detail.source && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  数据来源：{detail.source}
                </Text>
              )}
            </Space>
          </div>
        )}
      </Spin>
    </Modal>
  );
};

export default DetailModal;