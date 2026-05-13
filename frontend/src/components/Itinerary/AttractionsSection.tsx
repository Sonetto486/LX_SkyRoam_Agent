import React, { useState } from 'react';
import { Card, List, Tag, Button, Space, Typography, Collapse, Rate } from 'antd';
import {
  CameraOutlined,
  EnvironmentOutlined,
  StarOutlined,
  DownOutlined,
  RightOutlined
} from '@ant-design/icons';

const { Text, Paragraph } = Typography;
const { Panel } = Collapse;

interface Attraction {
  name: string;
  type?: string;
  score?: number;
  address?: string;
  description?: string;
  coordinates?: { lat: number; lng: number };
}

interface AttractionsSectionProps {
  attractions: Attraction[];
}

const AttractionsSection: React.FC<AttractionsSectionProps> = ({ attractions }) => {
  const [expanded, setExpanded] = useState(false);

  if (!attractions || attractions.length === 0) return null;

  const displayAttractions = expanded ? attractions : attractions.slice(0, 4);

  return (
    <Card
      title="📍 景点列表"
      extra={
        attractions.length > 4 && (
          <Button
            type="link"
            size="small"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? '收起' : `查看全部 ${attractions.length} 个`}
            {expanded ? <DownOutlined /> : <RightOutlined />}
          </Button>
        )
      }
      style={{ marginBottom: 16 }}
    >
      <List
        grid={{ gutter: 16, column: 2 }}
        dataSource={displayAttractions}
        renderItem={(attraction) => (
          <List.Item>
            <Card
              size="small"
              hoverable
              style={{ borderLeft: '4px solid #1890ff' }}
            >
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Text strong>{attraction.name}</Text>

                {attraction.type && (
                  <Tag color="blue">{attraction.type}</Tag>
                )}

                {attraction.score && (
                  <Space>
                    <StarOutlined style={{ color: '#faad14' }} />
                    <Text>{attraction.score} 分</Text>
                  </Space>
                )}

                {attraction.address && (
                  <Paragraph
                    ellipsis={{ rows: 1 }}
                    style={{ margin: 0, fontSize: 12, color: '#8c8c8c' }}
                  >
                    <EnvironmentOutlined style={{ marginRight: 4 }} />
                    {attraction.address}
                  </Paragraph>
                )}
              </Space>
            </Card>
          </List.Item>
        )}
      />
    </Card>
  );
};

export default AttractionsSection;