import React from 'react';
import { Space, Typography } from 'antd';
import {
  CarOutlined,
  ArrowDownOutlined
} from '@ant-design/icons';

const { Text } = Typography;

interface RouteSegmentProps {
  from: string;
  to: string;
  distance: number;  // km
  duration: number;  // minutes
  mode: 'walking' | 'driving' | 'transit';
}

const RouteSegment: React.FC<RouteSegmentProps> = ({
  from,
  to,
  distance,
  duration,
  mode
}) => {
  const getModeIcon = () => {
    switch (mode) {
      case 'walking':
        return <span style={{ fontSize: '16px', color: '#52c41a' }}>🚶</span>;
      case 'driving':
        return <CarOutlined style={{ fontSize: '16px', color: '#1890ff' }} />;
      case 'transit':
        return <span style={{ fontSize: '16px', color: '#faad14' }}>🚌</span>;
      default:
        return <span style={{ fontSize: '16px', color: '#8c8c8c' }}>🚌</span>;
    }
  };

  const getModeLabel = () => {
    switch (mode) {
      case 'walking':
        return '步行';
      case 'driving':
        return '驾车';
      case 'transit':
        return '公交/骑行';
      default:
        return '未知';
    }
  };

  const formatDuration = (minutes: number) => {
    if (minutes < 60) {
      return `${minutes}分钟`;
    }
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}小时${mins}分钟` : `${hours}小时`;
  };

  return (
    <div style={{
      padding: '8px 16px',
      margin: '4px 0',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      borderRadius: '8px',
      border: '1px solid rgba(102, 126, 234, 0.3)',
      boxShadow: '0 2px 8px rgba(102, 126, 234, 0.2)'
    }}>
      <Space direction="vertical" size={4} style={{ width: '100%' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ArrowDownOutlined style={{ fontSize: '12px', color: '#ffffff' }} />
          <Text style={{ fontSize: '12px', color: '#ffffff', opacity: 0.9 }}>
            {from} → {to}
          </Text>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {getModeIcon()}
          <Text strong style={{ fontSize: '13px', color: '#ffffff' }}>
            {getModeLabel()}
          </Text>
          <Text style={{ fontSize: '12px', color: '#ffffff', opacity: 0.85 }}>
            {distance.toFixed(1)}公里
          </Text>
          <Text style={{ fontSize: '12px', color: '#ffffff', opacity: 0.85 }}>
            约{formatDuration(duration)}
          </Text>
        </div>
      </Space>
    </div>
  );
};

export default RouteSegment;
