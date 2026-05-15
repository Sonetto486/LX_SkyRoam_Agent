import React from 'react';
import { Card, Tag, Space, Typography, Collapse, Rate, Button } from 'antd';
import {
  HomeOutlined,
  EnvironmentOutlined,
  DollarOutlined,
  PhoneOutlined,
  StarOutlined,
  EyeOutlined
} from '@ant-design/icons';

const { Text, Paragraph } = Typography;
const { Panel } = Collapse;

interface Hotel {
  name: string;
  address?: string;
  rating?: number;
  star_rating?: number;
  star?: number;
  price_per_night?: number;
  price?: number;
  amenities?: string[];
  facilities?: string[];
  phone?: string;
  check_in?: string;
  check_out?: string;
  coordinates?: { lat: number; lng: number };
}

interface HotelSectionProps {
  hotel: Hotel;
  onViewDetail?: () => void;
}

const HotelSection: React.FC<HotelSectionProps> = ({ hotel, onViewDetail }) => {
  if (!hotel) return null;

  const starRating = hotel.star_rating || hotel.star || 5;
  const price = hotel.price_per_night || hotel.price;
  const amenities = hotel.amenities || hotel.facilities || [];

  return (
    <Card
      title="🏨 住宿推荐"
      extra={
        <Space>
          {onViewDetail && (
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={onViewDetail}
            >
              查看详情
            </Button>
          )}
          {hotel.phone && (
            <Button
              type="link"
              size="small"
              icon={<PhoneOutlined />}
              href={`tel:${hotel.phone}`}
            >
              联系酒店
            </Button>
          )}
        </Space>
      }
      style={{ marginBottom: 16 }}
    >
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <div>
          <Text strong style={{ fontSize: 16 }}>{hotel.name}</Text>
          <Space style={{ marginLeft: 8 }}>
            <Tag color="purple">
              <StarOutlined /> {starRating}星级
            </Tag>
            {hotel.rating && (
              <Tag color="gold">
                <StarOutlined /> {hotel.rating}分
              </Tag>
            )}
          </Space>
        </div>

        {hotel.address && (
          <Paragraph style={{ margin: 0 }}>
            <EnvironmentOutlined style={{ marginRight: 8, color: '#8c8c8c' }} />
            {hotel.address}
          </Paragraph>
        )}

        {price && (
          <Text type="warning" strong style={{ fontSize: 16 }}>
            <DollarOutlined style={{ marginRight: 8 }} />
            ¥{price}/晚
          </Text>
        )}

        {(hotel.check_in || hotel.check_out) && (
          <Space size={16}>
            {hotel.check_in && (
              <Text type="secondary">
                入住：{hotel.check_in}
              </Text>
            )}
            {hotel.check_out && (
              <Text type="secondary">
                退房：{hotel.check_out}
              </Text>
            )}
          </Space>
        )}

        {amenities.length > 0 && (
          <Collapse ghost>
            <Panel header="酒店设施" key="1">
              <div>
                {amenities.map((amenity, idx) => (
                  <Tag key={idx} color="purple" style={{ margin: '4px' }}>
                    {amenity}
                  </Tag>
                ))}
              </div>
            </Panel>
          </Collapse>
        )}
      </Space>
    </Card>
  );
};

export default HotelSection;