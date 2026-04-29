import React, { useState } from 'react';
import { Card, Form, Input, Select, DatePicker, Button, Space, message, Divider, Row, Col, Progress } from 'antd';
import { CalendarOutlined, UserOutlined, EnvironmentOutlined, ClockCircleOutlined, SaveOutlined, LoadingOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import './PlanGeneratorPage.css';
import MapComponent from '../../components/MapComponent/MapComponent';
import { buildApiUrl } from '../../config/api';
import { authFetch } from '../../utils/auth';

const { Option } = Select;
const { RangePicker } = DatePicker;

// 预算映射
const budgetMap: Record<string, number> = {
  low: 3000,
  medium: 6000,
  high: 10000,
};

const PlanGeneratorPage: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [generatedPlan, setGeneratedPlan] = useState<any>(null);
  const [planId, setPlanId] = useState<number | null>(null);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationStatus, setGenerationStatus] = useState<string>('');
  const navigate = useNavigate();

  // 轮询生成状态
  const pollGenerationStatus = async (id: number) => {
    try {
      const res = await authFetch(buildApiUrl(`/travel-plans/${id}/status`));
      if (!res.ok) {
        throw new Error('获取状态失败');
      }
      const data = await res.json();
      return data;
    } catch (error) {
      console.error('轮询状态失败:', error);
      return null;
    }
  };

  // 等待生成完成
  const waitForGeneration = async (id: number): Promise<boolean> => {
    const maxAttempts = 120; // 最多等待2分钟
    let attempts = 0;

    while (attempts < maxAttempts) {
      const status = await pollGenerationStatus(id);

      if (!status) {
        attempts++;
        await new Promise(resolve => setTimeout(resolve, 1000));
        continue;
      }

      setGenerationStatus(status.status);

      if (status.status === 'completed') {
        setGenerationProgress(100);
        return true;
      }

      if (status.status === 'failed') {
        return false;
      }

      // 更新进度
      const progress = Math.min(90, 10 + (attempts / maxAttempts) * 80);
      setGenerationProgress(Math.round(progress));

      attempts++;
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    return false;
  };

  const handleGenerate = async (values: any) => {
    setLoading(true);
    setGenerationProgress(0);
    setGenerationStatus('');
    setGeneratedPlan(null);
    setPlanId(null);

    try {
      // 根据日期范围自动计算天数
      const durationDays = values.dateRange[1].diff(values.dateRange[0], 'days') + 1;

      // 1. 创建旅行计划
      const createData = {
        title: `${values.destination} ${durationDays}天旅行计划`,
        destination: values.destination,
        start_date: values.dateRange[0].format('YYYY-MM-DD'),
        end_date: values.dateRange[1].format('YYYY-MM-DD'),
        duration_days: durationDays,
        budget: budgetMap[values.budget] || 5000,
        preferences: {
          travelers: typeof values.people === 'string' ? (values.people === '10+' ? 10 : parseInt(values.people) || 1) : values.people,
          interests: values.interests || [],
        },
      };

      setGenerationProgress(10);
      setGenerationStatus('创建计划中...');

      const createRes = await authFetch(buildApiUrl('/travel-plans/'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(createData),
      });

      if (!createRes.ok) {
        const errorData = await createRes.json().catch(() => ({}));
        throw new Error(errorData.detail || '创建计划失败');
      }

      const createdPlan = await createRes.json();
      const newPlanId = createdPlan.id;
      setPlanId(newPlanId);

      setGenerationProgress(20);
      setGenerationStatus('生成方案中...');

      // 2. 触发生成任务
      const generateRes = await authFetch(buildApiUrl(`/travel-plans/${newPlanId}/generate`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preferences: {
            travelers: typeof values.people === 'string' ? (values.people === '10+' ? 10 : parseInt(values.people) || 1) : values.people,
            interests: values.interests || [],
            budget: budgetMap[values.budget] || 5000,
          },
        }),
      });

      if (!generateRes.ok) {
        const errorData = await generateRes.json().catch(() => ({}));
        throw new Error(errorData.detail || '触发生成失败');
      }

      // 3. 等待生成完成
      const success = await waitForGeneration(newPlanId);

      if (success) {
        // 4. 获取生成的计划详情
        const detailRes = await authFetch(buildApiUrl(`/travel-plans/${newPlanId}`));
        if (detailRes.ok) {
          const planDetail = await detailRes.json();
          setGeneratedPlan(planDetail);
          message.success('旅行计划生成成功！');
        } else {
          message.warning('生成成功，但获取详情失败');
        }
      } else {
        message.error('生成超时或失败，请稍后重试');
      }
    } catch (error: any) {
      console.error('生成失败:', error);
      message.error(error.message || '生成旅行计划失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleSavePlan = () => {
    if (planId) {
      message.success('计划已保存到我的行程！');
      navigate('/itineraries');
    } else {
      message.warning('请先生成旅行计划');
    }
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

      {/* 生成进度 */}
      {loading && (
        <Card className="generation-progress-card">
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <LoadingOutlined style={{ fontSize: 32, marginBottom: 16 }} />
            <Progress percent={generationProgress} status="active" />
            <p style={{ marginTop: 8, color: '#666' }}>{generationStatus || '处理中...'}</p>
          </div>
        </Card>
      )}

      {generatedPlan && (
        <Card className="generated-plan-card" title={generatedPlan.title}>
          <div className="plan-summary">
            <Space size="large">
              <span><CalendarOutlined /> {generatedPlan.duration_days}天</span>
              <span><UserOutlined /> {generatedPlan.preferences?.travelers || 1}人</span>
              <span><EnvironmentOutlined /> {generatedPlan.destination}</span>
              <span>日期：{generatedPlan.start_date?.slice(0, 10)} 至 {generatedPlan.end_date?.slice(0, 10)}</span>
            </Space>
          </div>

          <Divider>行程安排</Divider>

          <Row gutter={16}>
            <Col span={10}>
              <div className="itinerary-details">
                {generatedPlan.generated_plans?.[0]?.daily_itineraries?.map((day: any, dayIndex: number) => (
                  <div key={dayIndex} className="day-section">
                    <h3>Day {day.day || dayIndex + 1}</h3>
                    {day.attractions?.map((attraction: any, idx: number) => (
                      <Card key={idx} className="activity-card">
                        <div className="activity-content">
                          <h4>{attraction.name}</h4>
                          {attraction.description && (
                            <p className="activity-description">{attraction.description}</p>
                          )}
                          {attraction.address && (
                            <p className="activity-location">{attraction.address}</p>
                          )}
                        </div>
                      </Card>
                    ))}
                  </div>
                ))}
                {(!generatedPlan.generated_plans || generatedPlan.generated_plans.length === 0) && (
                  <div style={{ textAlign: 'center', color: '#999', padding: '20px 0' }}>
                    暂无行程详情
                  </div>
                )}
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
              查看我的行程
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
};

export default PlanGeneratorPage;