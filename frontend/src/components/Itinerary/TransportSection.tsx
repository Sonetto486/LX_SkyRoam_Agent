import React from 'react';
import { Card, List, Tag, Space, Typography, Collapse } from 'antd';
import {
  CarOutlined,
  ClockCircleOutlined,
  EnvironmentOutlined,
  DollarOutlined,
  BulbOutlined
} from '@ant-design/icons';

const { Text, Paragraph } = Typography;
const { Panel } = Collapse;

interface TransportRoute {
  type?: string;
  name?: string;
  route?: string;
  duration?: number;
  distance?: number;
  price?: number;
  usage_tips?: string[];
}

interface Transportation {
  primary_routes?: TransportRoute[];
  backup_routes?: TransportRoute[];
}

interface TransportSectionProps {
  transportation: Transportation;
}

const TransportSection: React.FC<TransportSectionProps> = ({ transportation }) => {
  if (!transportation || !transportation.primary_routes || transportation.primary_routes.length === 0) {
    return null;
  }

  return (
    <Card title="🚗 交通信息" style={{ marginBottom: 16 }}>
      <List
        dataSource={transportation.primary_routes}
        renderItem={(route) => (
          <List.Item style={{ border: 'none', padding: '8px 0' }}>
            <Card
              size="small"
              style={{ width: '100%', borderLeft: '4px solid #13c2c2' }}
            >
              <Space direction="vertical" size={8} style={{ width: '100%' }}>
                <Space>
                  <Tag color="cyan">{route.type || '交通'}</Tag>
                  <Text strong>{route.name || route.route}</Text>
                </Space>

                <Space size={16}>
                  {route.duration && (
                    <Text type="secondary">
                      <ClockCircleOutlined style={{ marginRight: 4 }} />
                      {route.duration}分钟
                    </Text>
                  )}

                  {route.distance && (
                    <Text type="secondary">
                      <EnvironmentOutlined style={{ marginRight: 4 }} />
                      {route.distance}公里
                    </Text>
                  )}

                  {route.price && (
                    <Text type="warning" strong>
                      <DollarOutlined style={{ marginRight: 4 }} />
                      ¥{route.price}
                    </Text>
                  )}
                </Space>

                {route.route && (
                  <Paragraph style={{ margin: 0, color: '#8c8c8c' }}>
                    路线：{route.route}
                  </Paragraph>
                )}

                {route.usage_tips && route.usage_tips.length > 0 && (
                  <Collapse ghost>
                    <Panel header="出行提示" key="1">
                      <ul style={{ margin: 0, paddingLeft: 20 }}>
                        {route.usage_tips.map((tip, idx) => (
                          <li key={idx}>
                            <Text>
                              <BulbOutlined style={{ marginRight: 4, color: '#52c41a' }} />
                              {tip}
                            </Text>
                          </li>
                        ))}
                      </ul>
                    </Panel>
                  </Collapse>
                )}
              </Space>
            </Card>
          </List.Item>
        )}
      />

      {transportation.backup_routes && transportation.backup_routes.length > 0 && (
        <Collapse ghost style={{ marginTop: 16 }}>
          <Panel header="备选方案" key="backup">
            <List
              dataSource={transportation.backup_routes}
              renderItem={(route) => (
                <List.Item style={{ border: 'none', padding: '4px 0' }}>
                  <Space>
                    <Tag>{route.type}</Tag>
                    <Text>{route.name || route.route}</Text>
                    {route.price && <Text type="warning">¥{route.price}</Text>}
                  </Space>
                </List.Item>
              )}
            />
          </Panel>
        </Collapse>
      )}
    </Card>
  );
};

export default TransportSection;