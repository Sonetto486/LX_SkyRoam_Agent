import React from 'react';
import { Card, Timeline, Tag, Typography, Space, Collapse } from 'antd';
import {
  ClockCircleOutlined,
  EnvironmentOutlined,
  DollarOutlined,
  BulbOutlined,
  CarOutlined,
  CoffeeOutlined,
  CameraOutlined
} from '@ant-design/icons';

const { Text, Paragraph } = Typography;
const { Panel } = Collapse;

interface ScheduleItem {
  time?: string;
  activity?: string;
  location?: string;
  description?: string;
  cost?: number;
  tips?: string;
  transport_note?: string;
}

interface DayScheduleSectionProps {
  schedule: ScheduleItem[];
}

const DayScheduleSection: React.FC<DayScheduleSectionProps> = ({ schedule }) => {
  if (!schedule || schedule.length === 0) return null;

  // 判断活动类型
  const getActivityType = (item: ScheduleItem): { icon: any; color: string; label: string } => {
    if (item.activity?.includes('餐') || item.activity?.includes('早餐') || item.activity?.includes('午餐') || item.activity?.includes('晚餐')) {
      return { icon: <CoffeeOutlined />, color: 'orange', label: '餐饮' };
    }
    if (item.activity?.includes('景点') || item.activity?.includes('游览') || item.activity?.includes('参观')) {
      return { icon: <CameraOutlined />, color: 'blue', label: '景点' };
    }
    return { icon: <ClockCircleOutlined />, color: 'green', label: '活动' };
  };

  return (
    <Card title="📅 今日日程" style={{ marginBottom: 16 }}>
      <Timeline
        items={schedule.map((item, index) => {
          const type = getActivityType(item);

          return {
            key: index,
            dot: type.icon,
            children: (
              <div>
                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                  <Space>
                    <Tag color={type.color}>{type.label}</Tag>
                    <Text strong>{item.activity}</Text>
                    {item.time && <Text type="secondary">{item.time}</Text>}
                  </Space>

                  {item.location && (
                    <div style={{ paddingLeft: 8 }}>
                      <EnvironmentOutlined style={{ marginRight: 4, color: '#8c8c8c' }} />
                      <Text>{item.location}</Text>
                    </div>
                  )}

                  {item.cost && (
                    <div style={{ paddingLeft: 8 }}>
                      <DollarOutlined style={{ marginRight: 4, color: '#52c41a' }} />
                      <Text type="warning">¥{item.cost}</Text>
                    </div>
                  )}

                  {(item.description || item.tips || item.transport_note) && (
                    <Collapse ghost style={{ marginTop: 8 }}>
                      <Panel header="查看详情" key="1">
                        {item.description && (
                          <Paragraph style={{ margin: '4px 0' }}>
                            {item.description}
                          </Paragraph>
                        )}
                        {item.transport_note && (
                          <Paragraph style={{ margin: '4px 0', color: '#13c2c2' }}>
                            <CarOutlined /> {item.transport_note}
                          </Paragraph>
                        )}
                        {item.tips && (
                          <Paragraph style={{ margin: '4px 0', color: '#52c41a' }}>
                            <BulbOutlined /> {item.tips}
                          </Paragraph>
                        )}
                      </Panel>
                    </Collapse>
                  )}
                </Space>
              </div>
            ),
          };
        })}
      />
    </Card>
  );
};

export default DayScheduleSection;