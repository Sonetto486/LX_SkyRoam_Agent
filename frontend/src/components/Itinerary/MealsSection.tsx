import React, { useState } from 'react';
import { Card, List, Tag, Button, Space, Typography, Collapse, Rate } from 'antd';
import {
  CoffeeOutlined,
  EnvironmentOutlined,
  DollarOutlined,
  PhoneOutlined,
  BulbOutlined,
  DownOutlined,
  RightOutlined,
  EyeOutlined
} from '@ant-design/icons';

const { Text, Paragraph } = Typography;
const { Panel } = Collapse;

interface Meal {
  type: string;
  time?: string;
  restaurant_name: string;
  cuisine?: string;
  recommended_dishes?: string[];
  estimated_cost?: number;
  booking_tips?: string;
  address?: string;
}

interface MealsSectionProps {
  meals: Meal[];
  onViewDetail?: (index: number) => void;
}

const MealsSection: React.FC<MealsSectionProps> = ({ meals, onViewDetail }) => {
  const [expanded, setExpanded] = useState(false);

  if (!meals || meals.length === 0) return null;

  const displayMeals = expanded ? meals : meals.slice(0, 3);

  return (
    <Card
      title="🍽️ 餐饮推荐"
      extra={
        meals.length > 3 && (
          <Button
            type="link"
            size="small"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? '收起' : `查看全部 ${meals.length} 家`}
            {expanded ? <DownOutlined /> : <RightOutlined />}
          </Button>
        )
      }
      style={{ marginBottom: 16 }}
    >
      <List
        dataSource={displayMeals}
        renderItem={(meal, index) => (
          <List.Item style={{ border: 'none', padding: '8px 0' }}>
            <Card
              size="small"
              style={{ width: '100%', borderLeft: '4px solid #fa8c16' }}
            >
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                  <Space>
                    <Tag color="orange">{meal.type}</Tag>
                    <Text strong>{meal.restaurant_name}</Text>
                  </Space>
                  {onViewDetail && (
                    <Button
                      type="link"
                      size="small"
                      icon={<EyeOutlined />}
                      onClick={() => onViewDetail(index)}
                    >
                      详情
                    </Button>
                  )}
                </Space>

                {meal.time && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    ⏰ {meal.time}
                  </Text>
                )}

                {meal.cuisine && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    🍴 {meal.cuisine}
                  </Text>
                )}

                {meal.estimated_cost && (
                  <Text type="warning" strong>
                    <DollarOutlined /> ¥{meal.estimated_cost}
                  </Text>
                )}

                {(meal.recommended_dishes || meal.address || meal.booking_tips) && (
                  <Collapse ghost>
                    <Panel header="查看详情" key="1">
                      {meal.recommended_dishes && meal.recommended_dishes.length > 0 && (
                        <div style={{ marginBottom: 8 }}>
                          <Text strong>推荐菜品：</Text>
                          <div style={{ marginTop: 4 }}>
                            {meal.recommended_dishes.map((dish, idx) => (
                              <Tag key={idx} color="orange" style={{ margin: '2px' }}>
                                {dish}
                              </Tag>
                            ))}
                          </div>
                        </div>
                      )}

                      {meal.address && (
                        <Paragraph style={{ margin: '4px 0' }}>
                          <EnvironmentOutlined style={{ marginRight: 4 }} />
                          {meal.address}
                        </Paragraph>
                      )}

                      {meal.booking_tips && (
                        <Paragraph style={{ margin: '4px 0', color: '#52c41a' }}>
                          <BulbOutlined style={{ marginRight: 4 }} />
                          {meal.booking_tips}
                        </Paragraph>
                      )}
                    </Panel>
                  </Collapse>
                )}
              </Space>
            </Card>
          </List.Item>
        )}
      />
    </Card>
  );
};

export default MealsSection;