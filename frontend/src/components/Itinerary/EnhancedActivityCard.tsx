import React, { useState } from 'react';
import { Card, Tag, Button, Space, Typography, Collapse, Descriptions, Badge, Rate, Divider, Tooltip, Popconfirm } from 'antd';
import {
  EnvironmentOutlined,
  ClockCircleOutlined,
  PhoneOutlined,
  DollarOutlined,
  StarOutlined,
  InfoCircleOutlined,
  CarOutlined,
  HomeOutlined,
  CoffeeOutlined,
  CameraOutlined,
  DownOutlined,
  RightOutlined,
  BulbOutlined,
  HeartOutlined,
  EditOutlined,
  UpOutlined,
  DownOutlined as MoveDownOutlined,
  DeleteOutlined
} from '@ant-design/icons';

const { Text, Paragraph, Title } = Typography;
const { Panel } = Collapse;

interface ActivityData {
  id: number | string;
  title: string;
  item_type: 'hotel' | 'restaurant' | 'attraction' | 'transport' | 'schedule';
  time?: string;
  location?: string;
  address?: string;
  description?: string;
  cost?: number;
  tips?: string;
  transport_note?: string;
  coordinates?: { lat: number; lng: number };
  images?: string[];

  // Hotel specific
  rating?: number;
  star_rating?: number;
  price_per_night?: number;
  amenities?: string[];
  facilities?: string[];
  phone?: string;
  check_in?: string;
  check_out?: string;

  // Restaurant specific
  cuisine?: string;
  recommended_dishes?: string[];
  booking_tips?: string;

  // Transport specific
  transport_type?: string;
  duration?: number;
  distance?: number;
  route?: string;
  usage_tips?: string[];

  // Attraction specific
  type?: string;
  score?: number;

  // Additional details
  details?: any;
}

interface EnhancedActivityCardProps {
  activity: ActivityData;
  isHovered?: boolean;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
  onEdit?: () => void;
  onMoveUp?: () => void;
  onMoveDown?: () => void;
  onDelete?: () => void;
}

const EnhancedActivityCard: React.FC<EnhancedActivityCardProps> = ({
  activity,
  isHovered,
  onMouseEnter,
  onMouseLeave,
  onEdit,
  onMoveUp,
  onMoveDown,
  onDelete
}) => {
  const [expanded, setExpanded] = useState(false);

  // Get icon and color based on type
  const getTypeStyle = () => {
    switch (activity.item_type) {
      case 'hotel':
        return { icon: <HomeOutlined />, color: 'purple', label: '住宿' };
      case 'restaurant':
        return { icon: <CoffeeOutlined />, color: 'orange', label: '餐饮' };
      case 'transport':
        return { icon: <CarOutlined />, color: 'cyan', label: '交通' };
      case 'attraction':
        return { icon: <CameraOutlined />, color: 'blue', label: '景点' };
      case 'schedule':
        return { icon: <ClockCircleOutlined />, color: 'green', label: '日程' };
      default:
        return { icon: <InfoCircleOutlined />, color: 'default', label: '活动' };
    }
  };

  const typeStyle = getTypeStyle();

  // Render core info (always visible)
  const renderCoreInfo = () => (
    <>
      <div className="activity-header">
        <Tag color={typeStyle.color}>{typeStyle.icon} {typeStyle.label}</Tag>
        <Text strong style={{ fontSize: '16px' }}>{activity.title}</Text>
      </div>

      <Space direction="vertical" size={8} style={{ width: '100%', marginTop: 12 }}>
        {/* Time */}
        {activity.time && (
          <div className="activity-detail-row">
            <ClockCircleOutlined style={{ color: '#8c8c8c', marginRight: 8 }} />
            <Text>{activity.time}</Text>
          </div>
        )}

        {/* Location */}
        {activity.location && (
          <div className="activity-detail-row">
            <EnvironmentOutlined style={{ color: '#8c8c8c', marginRight: 8 }} />
            <Text>{activity.location}</Text>
          </div>
        )}

        {/* Cost */}
        {activity.cost && (
          <div className="activity-detail-row">
            <DollarOutlined style={{ color: '#52c41a', marginRight: 8 }} />
            <Text type="warning" strong>¥{activity.cost}</Text>
          </div>
        )}

        {/* Rating for hotels/restaurants */}
        {activity.rating && (
          <div className="activity-detail-row">
            <StarOutlined style={{ color: '#faad14', marginRight: 8 }} />
            <Rate disabled defaultValue={activity.rating} style={{ fontSize: 14 }} />
            <Text style={{ marginLeft: 8 }}>{activity.rating} 分</Text>
          </div>
        )}

        {/* Star rating for hotels */}
        {activity.star_rating && (
          <div className="activity-detail-row">
            <StarOutlined style={{ color: '#722ed1', marginRight: 8 }} />
            <Text>{activity.star_rating} 星级酒店</Text>
          </div>
        )}

        {/* Price per night for hotels */}
        {activity.price_per_night && (
          <div className="activity-detail-row">
            <DollarOutlined style={{ color: '#52c41a', marginRight: 8 }} />
            <Text>¥{activity.price_per_night}/晚</Text>
          </div>
        )}

        {/* Transport type */}
        {activity.transport_type && (
          <div className="activity-detail-row">
            <CarOutlined style={{ color: '#13c2c2', marginRight: 8 }} />
            <Text>{activity.transport_type}</Text>
          </div>
        )}

        {/* Duration and distance for transport */}
        {(activity.duration || activity.distance) && (
          <div className="activity-detail-row">
            <ClockCircleOutlined style={{ color: '#8c8c8c', marginRight: 8 }} />
            <Text>
              {activity.duration && `${activity.duration}分钟`}
              {activity.duration && activity.distance && ' · '}
              {activity.distance && `${activity.distance}公里`}
            </Text>
          </div>
        )}

        {/* Cuisine type for restaurants */}
        {activity.cuisine && (
          <div className="activity-detail-row">
            <CoffeeOutlined style={{ color: '#fa8c16', marginRight: 8 }} />
            <Text>{activity.cuisine}</Text>
          </div>
        )}
      </Space>

      {/* Expand button */}
      <Button
        type="link"
        size="small"
        onClick={() => setExpanded(!expanded)}
        style={{ padding: '4px 0', marginTop: 8 }}
      >
        {expanded ? '收起详情' : '查看详情'} {expanded ? <DownOutlined /> : <RightOutlined />}
      </Button>
    </>
  );

  // Render expanded details
  const renderExpandedDetails = () => {
    if (!expanded) return null;

    return (
      <div className="activity-expanded-details" style={{ marginTop: 16 }}>
        <Divider style={{ margin: '12px 0' }} />

        {/* Description */}
        {activity.description && (
          <Paragraph style={{ margin: '8px 0' }}>
            <Text type="secondary">{activity.description}</Text>
          </Paragraph>
        )}

        {/* Transport note */}
        {activity.transport_note && (
          <div className="detail-section">
            <Text strong><CarOutlined /> 交通提示</Text>
            <Paragraph style={{ margin: '4px 0 12px 0', paddingLeft: 20 }}>
              {activity.transport_note}
            </Paragraph>
          </div>
        )}

        {/* Tips */}
        {activity.tips && (
          <div className="detail-section">
            <Text strong><BulbOutlined /> 小贴士</Text>
            <Paragraph style={{ margin: '4px 0 12px 0', paddingLeft: 20, color: '#52c41a' }}>
              {activity.tips}
            </Paragraph>
          </div>
        )}

        {/* Booking tips for restaurants */}
        {activity.booking_tips && (
          <div className="detail-section">
            <Text strong><HeartOutlined /> 预订提示</Text>
            <Paragraph style={{ margin: '4px 0 12px 0', paddingLeft: 20, color: '#fa8c16' }}>
              {activity.booking_tips}
            </Paragraph>
          </div>
        )}

        {/* Phone */}
        {activity.phone && (
          <div className="detail-section">
            <Text strong><PhoneOutlined /> 联系电话</Text>
            <Paragraph style={{ margin: '4px 0 12px 0', paddingLeft: 20 }}>
              <a href={`tel:${activity.phone}`}>{activity.phone}</a>
            </Paragraph>
          </div>
        )}

        {/* Address */}
        {activity.address && (
          <div className="detail-section">
            <Text strong><EnvironmentOutlined /> 详细地址</Text>
            <Paragraph style={{ margin: '4px 0 12px 0', paddingLeft: 20 }}>
              {activity.address}
            </Paragraph>
          </div>
        )}

        {/* Amenities/Facilities for hotels */}
        {(activity.amenities || activity.facilities) && (
          <div className="detail-section">
            <Text strong><HomeOutlined /> 酒店设施</Text>
            <div style={{ marginTop: 8, paddingLeft: 20 }}>
              <Space wrap>
                {(activity.amenities || activity.facilities || []).map((amenity, idx) => (
                  <Tag key={idx} color="purple">{amenity}</Tag>
                ))}
              </Space>
            </div>
          </div>
        )}

        {/* Recommended dishes for restaurants */}
        {activity.recommended_dishes && activity.recommended_dishes.length > 0 && (
          <div className="detail-section">
            <Text strong><CoffeeOutlined /> 推荐菜品</Text>
            <div style={{ marginTop: 8, paddingLeft: 20 }}>
              <Space wrap>
                {activity.recommended_dishes.map((dish: any, idx) => (
                  <Tag key={idx} color="orange">{typeof dish === 'string' ? dish : (dish?.name || '推荐菜')}</Tag>
                ))}
              </Space>
            </div>
          </div>
        )}

        {/* Usage tips for transport */}
        {activity.usage_tips && activity.usage_tips.length > 0 && (
          <div className="detail-section">
            <Text strong><BulbOutlined /> 出行提示</Text>
            <ul style={{ margin: '4px 0 12px 0', paddingLeft: 40 }}>
              {activity.usage_tips.map((tip, idx) => (
                <li key={idx}><Text>{tip}</Text></li>
              ))}
            </ul>
          </div>
        )}

        {/* Route info for transport */}
        {activity.route && (
          <div className="detail-section">
            <Text strong><CarOutlined /> 路线</Text>
            <Paragraph style={{ margin: '4px 0 12px 0', paddingLeft: 20 }}>
              {activity.route}
            </Paragraph>
          </div>
        )}

        {/* Check-in/out dates for hotels */}
        {(activity.check_in || activity.check_out) && (
          <div className="detail-section">
            <Text strong><ClockCircleOutlined /> 入住信息</Text>
            <Paragraph style={{ margin: '4px 0 12px 0', paddingLeft: 20 }}>
              {activity.check_in && `入住: ${activity.check_in}`}
              {activity.check_in && activity.check_out && ' · '}
              {activity.check_out && `退房: ${activity.check_out}`}
            </Paragraph>
          </div>
        )}

        {/* Attraction type */}
        {activity.type && (
          <div className="detail-section">
            <Text strong><CameraOutlined /> 景点类型</Text>
            <Paragraph style={{ margin: '4px 0 12px 0', paddingLeft: 20 }}>
              {activity.type}
            </Paragraph>
          </div>
        )}

        {/* Attraction score */}
        {activity.score && (
          <div className="detail-section">
            <Text strong><StarOutlined /> 评分</Text>
            <Paragraph style={{ margin: '4px 0 12px 0', paddingLeft: 20 }}>
              {activity.score} 分
            </Paragraph>
          </div>
        )}
      </div>
    );
  };

  return (
    <Card
      className={`enhanced-activity-card ${isHovered ? 'hovered' : ''}`}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      style={{ marginBottom: 12 }}
      actions={[
        <Tooltip key="edit" title="编辑">
          <Button
            icon={<EditOutlined />}
            size="small"
            onClick={(e) => {
              e.stopPropagation();
              onEdit?.();
            }}
          />
        </Tooltip>,
        <Tooltip key="move-up" title="上移">
          <Button
            icon={<UpOutlined />}
            size="small"
            onClick={(e) => {
              e.stopPropagation();
              onMoveUp?.();
            }}
          />
        </Tooltip>,
        <Tooltip key="move-down" title="下移">
          <Button
            icon={<MoveDownOutlined />}
            size="small"
            onClick={(e) => {
              e.stopPropagation();
              onMoveDown?.();
            }}
          />
        </Tooltip>,
        <Popconfirm
          key="delete"
          title="确定删除此活动？"
          okText="删除"
          cancelText="取消"
          onConfirm={(e) => {
            e?.stopPropagation();
            onDelete?.();
          }}
        >
          <Button
            danger
            icon={<DeleteOutlined />}
            size="small"
            onClick={(e) => e.stopPropagation()}
          />
        </Popconfirm>
      ]}
    >
      {renderCoreInfo()}
      {renderExpandedDetails()}
    </Card>
  );
};

export default EnhancedActivityCard;
