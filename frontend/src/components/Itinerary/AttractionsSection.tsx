import React, { useState, useEffect } from 'react';
import { Card, List, Tag, Button, Space, Typography, Collapse, Rate, message, Spin } from 'antd';
import {
  CameraOutlined,
  EnvironmentOutlined,
  StarOutlined,
  DownOutlined,
  RightOutlined,
  CarOutlined,
  ClockCircleOutlined,
  DollarOutlined,
  SwapOutlined,
  CheckCircleOutlined
} from '@ant-design/icons';
import { authFetch } from '../../utils/auth';

const { Text, Paragraph } = Typography;
const { Panel } = Collapse;

interface Attraction {
  name: string;
  type?: string;
  score?: number;
  address?: string;
  description?: string;
  coordinates?: { lat: number; lng: number };
  inSchedule?: boolean; // 是否已在日程中
}

interface RouteSegment {
  from: string;
  to: string;
  distance?: number;
  duration?: number;
  mode?: string;
  cost?: number;
}

interface AttractionsSectionProps {
  attractions: Attraction[];
  hotelAddress?: string;
  hotelCoordinates?: { lat: number; lng: number };
  planId?: number;
  dayDate?: string;
  onRouteOptimized?: (segments: RouteSegment[]) => void;
}

const AttractionsSection: React.FC<AttractionsSectionProps> = ({
  attractions,
  hotelAddress,
  hotelCoordinates,
  planId,
  dayDate,
  onRouteOptimized
}) => {
  const [routeSegments, setRouteSegments] = useState<RouteSegment[]>([]);
  const [loading, setLoading] = useState(false);
  const [optimized, setOptimized] = useState(false);

  useEffect(() => {
    // 重置优化状态
    setOptimized(false);
    setRouteSegments([]);
  }, [attractions]);

  const handleOptimizeRoute = async () => {
    if (!planId) {
      message.warning('无法获取行程ID');
      return;
    }

    setLoading(true);
    try {
      // 调用后端路径优化API
      const response = await authFetch(`/travel-plans/${planId}/optimize-route`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          date: dayDate,
          start_point: hotelCoordinates ? {
            name: '酒店',
            coordinates: hotelCoordinates
          } : null,
        }),
      });

      if (!response.ok) {
        throw new Error('路径优化失败');
      }

      const data = await response.json();

      console.log('路线优化返回数据:', data);
      console.log('route_segments:', data.route_segments);

      if (data.route_segments && data.route_segments.length > 0) {
        setRouteSegments(data.route_segments);
        setOptimized(true);
        message.success(`路径优化完成，共 ${data.route_segments.length} 个路段`);

        if (onRouteOptimized) {
          onRouteOptimized(data.route_segments);
        }
      } else {
        message.info('没有可优化的路径');
      }
    } catch (error: any) {
      console.error('路径优化失败:', error);
      message.error(error.message || '路径优化失败');
    } finally {
      setLoading(false);
    }
  };

  if (!attractions || attractions.length === 0) return null;

  return (
    <Card
      title={
        <Space>
          <CameraOutlined />
          <span>景点列表</span>
          <Tag color="blue">{attractions.length} 个景点</Tag>
          {optimized && <Tag color="success" icon={<CheckCircleOutlined />}>已优化</Tag>}
        </Space>
      }
      extra={
        <Button
          type="primary"
          size="small"
          icon={<SwapOutlined />}
          onClick={handleOptimizeRoute}
          loading={loading}
          disabled={optimized}
        >
          {optimized ? '已优化' : '路线优化'}
        </Button>
      }
      style={{ marginBottom: 16 }}
    >
      {/* 显示起点（酒店） */}
      {hotelAddress && (
        <Card size="small" style={{ marginBottom: 8, backgroundColor: '#f6ffed' }}>
          <Space>
            <Tag color="green">起点</Tag>
            <Text strong>酒店</Text>
            <Text type="secondary">{hotelAddress}</Text>
          </Space>
        </Card>
      )}

      {/* 景点列表 */}
      <List
        dataSource={attractions}
        renderItem={(attraction, index) => (
          <div key={index}>
            {/* 景点卡片 */}
            <List.Item style={{ border: 'none', padding: '8px 0' }}>
              <Card
                size="small"
                hoverable
                style={{ width: '100%', borderLeft: '4px solid #1890ff' }}
              >
                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                  <Space>
                    <Tag color="blue">{index + 1}</Tag>
                    <Text strong>{attraction.name}</Text>
                    {attraction.inSchedule && (
                      <Tag color="green" style={{ fontSize: 10 }}>已在日程</Tag>
                    )}
                  </Space>

                  {attraction.type && (
                    <Tag color="blue" style={{ marginTop: 4 }}>{attraction.type}</Tag>
                  )}

                  {attraction.score && (
                    <Space style={{ marginTop: 4 }}>
                      <StarOutlined style={{ color: '#faad14' }} />
                      <Text>{attraction.score} 分</Text>
                    </Space>
                  )}

                  {attraction.address && (
                    <Paragraph style={{ margin: '4px 0', fontSize: 12, color: '#8c8c8c' }}>
                      <EnvironmentOutlined style={{ marginRight: 4 }} />
                      {attraction.address}
                    </Paragraph>
                  )}

                  {attraction.description && (
                    <Collapse ghost>
                      <Panel header="查看详情" key="1">
                        <Paragraph style={{ margin: 0 }}>
                          {attraction.description}
                        </Paragraph>
                      </Panel>
                    </Collapse>
                  )}
                </Space>
              </Card>
            </List.Item>

            {/* 显示到下一个景点的路线信息 */}
            {index < attractions.length - 1 && routeSegments[index] && (
              <Card
                size="small"
                style={{
                  margin: '4px 0 8px 0',
                  backgroundColor: '#e6f7ff',
                  border: '1px dashed #1890ff'
                }}
              >
                <Space split={<Text type="secondary">→</Text>} size={8}>
                  <Text type="secondary">
                    <CarOutlined /> {routeSegments[index].mode || '打车'}
                  </Text>
                  {routeSegments[index].duration && (
                    <Text type="secondary">
                      <ClockCircleOutlined /> {routeSegments[index].duration}分钟
                    </Text>
                  )}
                  {routeSegments[index].distance && (
                    <Text type="secondary">
                      <EnvironmentOutlined /> {routeSegments[index].distance}公里
                    </Text>
                  )}
                  {routeSegments[index].cost && (
                    <Text type="warning">
                      <DollarOutlined /> ¥{routeSegments[index].cost}
                    </Text>
                  )}
                </Space>
              </Card>
            )}
          </div>
        )}
      />

      {/* 显示终点（返回酒店） */}
      {hotelAddress && attractions.length > 0 && optimized && (
        <Card size="small" style={{ marginTop: 8, backgroundColor: '#fff7e6' }}>
          <Space>
            <Tag color="orange">终点</Tag>
            <Text strong>返回酒店</Text>
            <Text type="secondary">{hotelAddress}</Text>
          </Space>
        </Card>
      )}
    </Card>
  );
};

export default AttractionsSection;