import React, { useState, useEffect } from 'react';
import { Card, Tag, Space, Typography, Divider, Button } from 'antd';
import { HomeOutlined, CarOutlined, CoffeeOutlined, CameraOutlined, ClockCircleOutlined } from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;

const TestDataExtraction: React.FC = () => {
  const [planData, setPlanData] = useState<any>(null);
  const [extractedData, setExtractedData] = useState<any[]>([]);

  useEffect(() => {
    // 从本地JSON文件加载数据
    fetch('/贵阳市 4天旅行计划.json')
      .then(res => res.json())
      .then(data => {
        setPlanData(data);
        extractData(data);
      })
      .catch(err => console.error('加载数据失败:', err));
  }, []);

  const extractData = (data: any) => {
    if (!data.generated_plans || !data.generated_plans[0]) {
      console.log('没有generated_plans数据');
      return;
    }

    const plan = data.generated_plans[0];
    const results: any[] = [];

    plan.daily_itineraries.forEach((day: any, dayIndex: number) => {
      const dayActivities: any[] = [];

      console.log(`处理第${dayIndex + 1}天:`, day);

      // 1. 提取住宿信息
      if (dayIndex === 0 && plan.hotel) {
        console.log('添加住宿信息:', plan.hotel);
        dayActivities.push({
          type: 'hotel',
          title: plan.hotel.name,
          icon: <HomeOutlined />,
          color: 'purple',
          data: plan.hotel
        });
      }

      // 2. 提取交通信息
      if (day.transportation && day.transportation.primary_routes) {
        console.log('添加交通信息:', day.transportation);
        day.transportation.primary_routes.forEach((route: any) => {
          dayActivities.push({
            type: 'transport',
            title: route.name || route.route,
            icon: <CarOutlined />,
            color: 'cyan',
            data: route
          });
        });
      }

      // 3. 提取日程
      if (day.schedule) {
        console.log('添加日程:', day.schedule.length, '项');
        day.schedule.forEach((item: any) => {
          const isMeal = item.activity?.includes('餐');
          dayActivities.push({
            type: isMeal ? 'meal' : 'schedule',
            title: item.activity,
            icon: isMeal ? <CoffeeOutlined /> : <ClockCircleOutlined />,
            color: isMeal ? 'orange' : 'green',
            data: item
          });
        });
      }

      // 4. 提取餐饮
      if (day.meals) {
        console.log('添加餐饮:', day.meals.length, '项');
        day.meals.forEach((meal: any) => {
          const exists = dayActivities.find(a => a.title?.includes(meal.type));
          if (!exists) {
            dayActivities.push({
              type: 'meal',
              title: `${meal.type} - ${meal.restaurant_name}`,
              icon: <CoffeeOutlined />,
              color: 'orange',
              data: meal
            });
          }
        });
      }

      // 5. 提取景点
      if (day.attractions) {
        console.log('添加景点:', day.attractions.length, '项');
        day.attractions.forEach((attr: any) => {
          const exists = dayActivities.find(a => a.title?.includes(attr.name));
          if (!exists) {
            dayActivities.push({
              type: 'attraction',
              title: attr.name,
              icon: <CameraOutlined />,
              color: 'blue',
              data: attr
            });
          }
        });
      }

      results.push({
        day: day.day,
        date: day.date,
        activities: dayActivities
      });
    });

    console.log('提取完成，总共', results.length, '天');
    setExtractedData(results);
  };

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <Title level={2}>数据提取测试页面</Title>

      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {extractedData.map((day, index) => (
          <Card key={index} title={`Day ${day.day} - ${day.date}`}>
            <Space direction="vertical" style={{ width: '100%' }}>
              {day.activities.map((activity: any, idx: number) => (
                <Card
                  key={idx}
                  size="small"
                  style={{ borderLeft: `4px solid ${activity.color}` }}
                >
                  <Space>
                    <Tag color={activity.color}>{activity.icon} {activity.type}</Tag>
                    <Text strong>{activity.title}</Text>
                  </Space>
                  <Divider style={{ margin: '8px 0' }} />
                  <pre style={{ fontSize: 12, margin: 0 }}>
                    {JSON.stringify(activity.data, null, 2)}
                  </pre>
                </Card>
              ))}
            </Space>
          </Card>
        ))}
      </Space>

      <Divider />

      <Card title="原始数据">
        <pre style={{ fontSize: 10, maxHeight: 400, overflow: 'auto' }}>
          {JSON.stringify(planData, null, 2)}
        </pre>
      </Card>
    </div>
  );
};

export default TestDataExtraction;