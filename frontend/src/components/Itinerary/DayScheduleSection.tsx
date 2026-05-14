import React, { useState } from 'react';
import { Card, Timeline, Tag, Typography, Space, Collapse, Button, Tooltip, Popconfirm } from 'antd';
import {
  ClockCircleOutlined,
  EnvironmentOutlined,
  DollarOutlined,
  BulbOutlined,
  CarOutlined,
  CoffeeOutlined,
  CameraOutlined,
  EditOutlined,
  DeleteOutlined
} from '@ant-design/icons';
import './DayScheduleSection.css';

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
  priority?: string; // 'must' | 'optional' | 'backup'
}

interface DayScheduleSectionProps {
  schedule: ScheduleItem[];
  onEdit?: (index: number) => void;
  onDelete?: (index: number) => void;
}

const DayScheduleSection: React.FC<DayScheduleSectionProps> = ({
  schedule,
  onEdit,
  onDelete
}) => {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

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

  // 获取优先级标签
  const getPriorityTag = (priority?: string) => {
    if (!priority) return null;
    switch (priority) {
      case 'must':
        return <Tag color="red">必去</Tag>;
      case 'optional':
        return <Tag color="blue">可选</Tag>;
      case 'backup':
        return <Tag color="default">备选</Tag>;
      default:
        return null;
    }
  };

  // 构建时间轴项
  const buildTimelineItems = () => {
    return schedule.map((item, index) => {
      const type = getActivityType(item);

      return {
        key: index,
        dot: type.icon,
        children: (
          <div
            className="schedule-item-wrapper"
            onMouseEnter={() => setHoveredIndex(index)}
            onMouseLeave={() => setHoveredIndex(null)}
          >
            <div className="schedule-item-content">
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Space>
                  <Tag color={type.color}>{type.label}</Tag>
                  <Text strong>{item.activity}</Text>
                  {item.time && <Text type="secondary">{item.time}</Text>}
                  {getPriorityTag(item.priority)}
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

            {/* 操作按钮（hover显示） */}
            {(onEdit || onDelete) && (
              <div className={`schedule-item-actions ${hoveredIndex === index ? 'visible' : ''}`}>
                {onEdit && (
                  <Tooltip title="编辑">
                    <Button
                      type="text"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        onEdit(index);
                      }}
                    />
                  </Tooltip>
                )}
                {onDelete && (
                  <Popconfirm
                    title="确定删除此活动？"
                    okText="删除"
                    cancelText="取消"
                    onConfirm={(e) => {
                      e?.stopPropagation();
                      onDelete(index);
                    }}
                  >
                    <Tooltip title="删除">
                      <Button
                        type="text"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </Tooltip>
                  </Popconfirm>
                )}
              </div>
            )}
          </div>
        ),
      };
    });
  };

  return (
    <Card title="📅 今日日程" style={{ marginBottom: 16 }}>
      <Timeline items={buildTimelineItems()} />
    </Card>
  );
};

export default DayScheduleSection;