import React, { useState, useMemo } from 'react';
import { Card, Form, Input, Select, DatePicker, Button, Space, message, Divider, Row, Col } from 'antd';
import { CalendarOutlined, UserOutlined, EnvironmentOutlined, ClockCircleOutlined, SaveOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import './PlanGeneratorPage.css';
import MapComponent from '../../components/MapComponent/MapComponent';

const { Option } = Select;
const { RangePicker } = DatePicker;

const PlanGeneratorPage: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [generatedPlan, setGeneratedPlan] = useState<any>(null);

  const handleGenerate = async (values: any) => {
    setLoading(true);
    try {
      // 根据日期范围自动计算天数
      const durationDays = values.dateRange[1].diff(values.dateRange[0], 'days') + 1;

      // 模拟API调用
      setTimeout(() => {
        // 模拟生成的旅行计划
        const plan = {
          id: 'plan-123',
          title: `${values.destination} ${durationDays}天旅行计划`,
          destination: values.destination,
          days: durationDays,
          people: values.people,
          budget: values.budget,
          startDate: values.dateRange[0].format('YYYY-MM-DD'),
          endDate: values.dateRange[1].format('YYYY-MM-DD'),
          itinerary: [
            {
              day: 1,
              activities: [
                {
                  time: '09:00',
                  activity: '抵达目的地',
                  location: values.destination,
                  description: '抵达机场/车站，前往酒店办理入住'
                },
                {
                  time: '14:00',
                  activity: '城市观光',
                  location: `${values.destination}市中心`,
                  description: '游览城市主要景点'
                }
              ]
            },
            {
              day: 2,
              activities: [
                {
                  time: '08:00',
                  activity: '景点游览',
                  location: `${values.destination}著名景点`,
                  description: '参观当地著名景点'
                },
                {
                  time: '15:00',
                  activity: '购物体验',
                  location: `${values.destination}购物区`,
                  description: '体验当地购物文化'
                }
              ]
            }
          ]
        };
        setGeneratedPlan(plan);
        message.success('旅行计划生成成功！');
      }, 2000);
    } catch (error) {
      message.error('生成旅行计划失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleSavePlan = () => {
    // 保存计划的逻辑
    message.success('计划保存成功！');
  };

  return (
    <div className="plan-generator-page">
      <div className="page-header">
        <h1>一键生成旅行计划</h1>
        <p>输入您的旅行需求，AI 将为您生成个性化的旅行计划</p>
      </div>

      <Card className="generator-form-card">
        <Form
          form={form}
          layout="vertical"
          onFinish={handleGenerate}
        >
          <Form.Item
            name="destination"
            label="目的地"
            rules={[{ required: true, message: '请输入目的地' }]}
          >
            <Input placeholder="例如：北京、上海、三亚" prefix={<EnvironmentOutlined />} />
          </Form.Item>

          <Form.Item
            name="dateRange"
            label="旅行日期"
            rules={[{ required: true, message: '请选择旅行日期' }]}
          >
            <RangePicker
              style={{ width: '100%' }}
              prefix={<CalendarOutlined />}
              disabledDate={(current) => {
                // 禁止选择今天之前的日期
                return current && current < dayjs().startOf('day');
              }}
            />
          </Form.Item>

          <Form.Item
            name="people"
            label="出行人数"
            rules={[{ required: true, message: '请选择出行人数' }]}
          >
            <Select placeholder="选择出行人数" style={{ width: '100%' }} prefix={<UserOutlined />}>
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(person => (
                <Option key={person} value={person}>{person}人</Option>
              ))}
              <Option key="10+" value="10+">十人及以上</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="budget"
            label="预算范围"
            rules={[{ required: true, message: '请选择预算范围' }]}
          >
            <Select placeholder="选择预算范围" style={{ width: '100%' }}>
              <Option value="low">经济型（&lt; 3000元/人）</Option>
              <Option value="medium">舒适型（3000-8000元/人）</Option>
              <Option value="high">豪华型（&gt; 8000元/人）</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="interests"
            label="兴趣偏好"
          >
            <Select
              mode="multiple"
              placeholder="选择您的兴趣偏好"
              style={{ width: '100%' }}
            >
              <Option value="sightseeing">观光游览</Option>
              <Option value="food">美食探索</Option>
              <Option value="shopping">购物</Option>
              <Option value="culture">文化体验</Option>
              <Option value="adventure">冒险活动</Option>
              <Option value="relaxation">休闲度假</Option>
            </Select>
          </Form.Item>

          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit" 
              block 
              size="large"
              loading={loading}
              icon={<ClockCircleOutlined />}
            >
              生成旅行计划
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {generatedPlan && (
        <Card className="generated-plan-card" title={generatedPlan.title}>
          <div className="plan-summary">
            <Space size="large">
              <span><CalendarOutlined /> {generatedPlan.days}天</span>
              <span><UserOutlined /> {generatedPlan.people}人</span>
              <span><EnvironmentOutlined /> {generatedPlan.destination}</span>
              <span>日期：{generatedPlan.startDate} 至 {generatedPlan.endDate}</span>
            </Space>
          </div>

          <Divider>行程安排</Divider>

          <Row gutter={16}>
            <Col span={10}>
              <div className="itinerary-details">
                {generatedPlan.itinerary.map((day: any) => (
                  <div key={day.day} className="day-section">
                    <h3>Day {day.day}</h3>
                    {day.activities.map((activity: any, index: number) => (
                      <Card key={index} className="activity-card">
                        <div className="activity-time">{activity.time}</div>
                        <div className="activity-content">
                          <h4>{activity.activity}</h4>
                          <p className="activity-location">{activity.location}</p>
                          <p className="activity-description">{activity.description}</p>
                        </div>
                      </Card>
                    ))}
                  </div>
                ))}
              </div>
            </Col>
            <Col span={14}>
              <div className="map-section">
                <MapComponent
                  markers={[]}
                  center={{ lat: 31.2304, lng: 121.4737 }}
                  zoom={12}
                />
              </div>
            </Col>
          </Row>

          <div className="plan-actions">
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSavePlan}
            >
              保存到我的行程
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
};

export default PlanGeneratorPage;