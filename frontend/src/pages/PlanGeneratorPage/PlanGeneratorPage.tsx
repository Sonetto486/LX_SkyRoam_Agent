import React, { useState, useMemo, useCallback } from 'react';
import { Card, Form, Input, Select, DatePicker, Button, Space, message, Divider, Row, Col } from 'antd';
import { CalendarOutlined, UserOutlined, EnvironmentOutlined, ClockCircleOutlined } from '@ant-design/icons';
import './PlanGeneratorPage.css';
import MapComponent from '../../components/MapComponent/MapComponent';

const { Option } = Select;
const { RangePicker } = DatePicker;

// ========== 辅助函数：归一化每日行程 ==========
// 将后端可能返回的不同结构统一转换成 { time, name, description, location, lat, lng } 数组
function normalizeDailyItinerary(day: any): any[] {
  // 1. 已经有 activities 字段
  if (day.activities && Array.isArray(day.activities)) {
    return day.activities.map((act: any) => ({
      time: act.time || act.start_time,
      name: act.name || act.title,
      description: act.description,
      location: act.location || act.address,
      lat: act.location_lat || act.lat,
      lng: act.location_lng || act.lng,
    }));
  }
  // 2. 模块化 LLM 生成的 schedule 结构
  if (day.schedule && Array.isArray(day.schedule)) {
    return day.schedule.map((item: any) => ({
      time: item.time || item.start_time,
      name: item.title || item.activity,
      description: item.description,
      location: item.location,
      lat: item.location_lat || item.lat,
      lng: item.location_lng || item.lng,
    }));
  }
  // 3. 纯 attractions 列表
  if (day.attractions && Array.isArray(day.attractions)) {
    return day.attractions.map((attr: any) => ({
      time: attr.suggested_time,
      name: attr.name,
      description: attr.description,
      location: attr.address,
      lat: attr.location_lat || attr.lat,
      lng: attr.location_lng || attr.lng,
    }));
  }
  return [];
}

// 从计划数据中提取目的地中心点
function extractCenter(plan: any): { lat: number; lng: number } {
  // 默认北京天安门
  const defaultCenter = { lat: 39.9042, lng: 116.4074 };
  if (!plan) return defaultCenter;

  // 优先从 selected_plan.destination_info 获取
  const destInfo = plan.selected_plan?.destination_info || plan.generated_plans?.[0]?.destination_info;
  if (destInfo && destInfo.latitude && destInfo.longitude) {
    return { lat: destInfo.latitude, lng: destInfo.longitude };
  }
  return defaultCenter;
}

// 从计划数据中提取标记点（支持按天过滤）
function extractMarkers(plan: any, viewMode: 'day' | 'full', currentDay: number): any[] {
  if (!plan) return [];

  const itineraries = plan.selected_plan?.daily_itineraries || plan.generated_plans?.[0]?.daily_itineraries;
  if (!itineraries || !Array.isArray(itineraries)) return [];

  const markers: any[] = [];

  for (const day of itineraries) {
    // 如果按天查看且不是当前天，跳过
    if (viewMode === 'day' && day.day !== currentDay) continue;

    const activities = normalizeDailyItinerary(day);
    for (const act of activities) {
      // 必须有坐标才生成标记点
      if (act.lat && act.lng) {
        markers.push({
          id: `${day.day}-${act.name}`,
          name: act.name,
          position: { lat: act.lat, lng: act.lng },
          address: act.location || '',
          day: day.day,
          time: act.time,
          isHovered: false,
        });
      }
    }
  }
  return markers;
}

const PlanGeneratorPage: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [generatedPlan, setGeneratedPlan] = useState<any>(null);
  const [currentDay, setCurrentDay] = useState<number>(1);
  const [viewMode, setViewMode] = useState<'day' | 'full'>('day');

  // 预算映射：字符串 -> 数字（单位：元/人）
  const mapBudget = (budgetStr: string): number => {
    switch (budgetStr) {
      case 'low': return 2000;
      case 'medium': return 5000;
      case 'high': return 10000;
      default: return 5000;
    }
  };

  const handleGenerate = async (values: any) => {
    setLoading(true);
    try {
      const budgetNum = mapBudget(values.budget);

      // 1. 创建旅行计划
      const planResponse = await fetch('/api/v1/travel-plans/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify({
          title: `${values.destination} ${values.days}天旅行计划`,
          destination: values.destination,
          start_date: values.dateRange[0].format('YYYY-MM-DDTHH:mm:ss'),
          end_date: values.dateRange[1].format('YYYY-MM-DDTHH:mm:ss'),
          duration_days: values.days,
          transportation: '自驾',
          budget: budgetNum,
          preferences: {
            interests: values.interests || [],
            people_count: values.people
          }
        })
      });

      if (!planResponse.ok) {
        const errData = await planResponse.json();
        console.error('创建计划失败:', errData);
        throw new Error('创建旅行计划失败');
      }

      const planData = await planResponse.json();
      const planId = planData.id;

      // 2. 生成方案
      const generateResponse = await fetch(`/api/v1/travel-plans/${planId}/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify({
          preferences: {
            budget: budgetNum,
            interests: values.interests || [],
            people_count: values.people
          }
        })
      });

      if (!generateResponse.ok) {
        throw new Error('生成旅行方案失败');
      }

      const generateData = await generateResponse.json();
      const taskId = generateData.task_id;

      // 3. 轮询任务状态
      const pollTask = async () => {
        const statusResponse = await fetch(`/api/v1/travel-plans/tasks/status/${taskId}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
          }
        });

        if (statusResponse.ok) {
          const statusData = await statusResponse.json();
          if (statusData.status === 'success') {
            // 获取生成的计划详情
            const planDetailResponse = await fetch(`/api/v1/travel-plans/${planId}`, {
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
              }
            });

            if (planDetailResponse.ok) {
              const planDetail = await planDetailResponse.json();
              setGeneratedPlan({
                id: planId,
                title: `${values.destination} ${values.days}天旅行计划`,
                destination: values.destination,
                days: values.days,
                people: values.people,
                budget: values.budget,
                startDate: values.dateRange[0].format('YYYY-MM-DD'),
                endDate: values.dateRange[1].format('YYYY-MM-DD'),
                generated_plans: planDetail.generated_plans || [],
                selected_plan: planDetail.selected_plan
              });
              message.success('旅行计划生成成功！');
            }
            return true;
          } else if (statusData.status === 'failed') {
            throw new Error('生成失败');
          }
        }
        return false;
      };

      // 轮询最多 5 分钟（300次 * 1秒）
      for (let i = 0; i < 300; i++) {
        if (await pollTask()) break;
        await new Promise(resolve => setTimeout(resolve, 1000));
      }

    } catch (error) {
      message.error('生成旅行计划失败，请重试');
      console.error('Generate error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSavePlan = () => {
    message.success('计划保存成功！');
  };

  // 使用 useMemo 根据 generatedPlan 和 viewMode/currentDay 动态计算标记点和中心点
  const markers = useMemo(() => extractMarkers(generatedPlan, viewMode, currentDay), [generatedPlan, viewMode, currentDay]);
  const center = useMemo(() => extractCenter(generatedPlan), [generatedPlan]);

  // 为了让 MapComponent 正确重建（避免与 AMap 的 DOM 冲突），保留 key 但使用更有意义的值
  const mapKey = `${generatedPlan?.id}-${viewMode}-${currentDay}-${markers.length}`;

  // 行程数据归一化后用于渲染（与地图标记使用同一份归一化数据，保证一致性）
  const getNormalizedItineraries = useCallback(() => {
    if (!generatedPlan) return [];
    const itineraries = generatedPlan.selected_plan?.daily_itineraries ||
      generatedPlan.generated_plans?.[0]?.daily_itineraries;
    if (!itineraries || !Array.isArray(itineraries)) return [];
    // 为每一天附加归一化后的 activities 字段
    return itineraries.map((day: any) => ({
      ...day,
      normalizedActivities: normalizeDailyItinerary(day)
    }));
  }, [generatedPlan]);

  return (
    <div className="plan-generator-page">
      <div className="page-header">
        <h1>一键生成旅行计划</h1>
        <p>输入您的旅行需求，AI 将为您生成个性化的旅行计划</p>
      </div>

      <Card className="generator-form-card">
        <Form form={form} layout="vertical" onFinish={handleGenerate}>
          <Form.Item name="destination" label="目的地" rules={[{ required: true, message: '请输入目的地' }]}>
            <Input placeholder="例如：北京、上海、三亚" prefix={<EnvironmentOutlined />} />
          </Form.Item>

          <Form.Item name="dateRange" label="旅行日期" rules={[{ required: true, message: '请选择旅行日期' }]}>
            <RangePicker style={{ width: '100%' }} prefix={<CalendarOutlined />} />
          </Form.Item>

          <Form.Item name="days" label="旅行天数" rules={[{ required: true, message: '请选择旅行天数' }]}>
            <Select placeholder="选择旅行天数" style={{ width: '100%' }}>
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(day => (
                <Option key={day} value={day}>{day}天</Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="people" label="出行人数" rules={[{ required: true, message: '请选择出行人数' }]}>
            <Select placeholder="选择出行人数" style={{ width: '100%' }} prefix={<UserOutlined />}>
              {[1, 2, 3, 4, 5, 6, 7, 8].map(person => (
                <Option key={person} value={person}>{person}人</Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="budget" label="预算范围" rules={[{ required: true, message: '请选择预算范围' }]}>
            <Select placeholder="选择预算范围" style={{ width: '100%' }}>
              <Option value="low">经济型（&lt; 3000元/人）</Option>
              <Option value="medium">舒适型（3000-8000元/人）</Option>
              <Option value="high">豪华型（&gt; 8000元/人）</Option>
            </Select>
          </Form.Item>

          <Form.Item name="interests" label="兴趣偏好">
            <Select mode="multiple" placeholder="选择您的兴趣偏好" style={{ width: '100%' }}>
              <Option value="sightseeing">观光游览</Option>
              <Option value="food">美食探索</Option>
              <Option value="shopping">购物</Option>
              <Option value="culture">文化体验</Option>
              <Option value="adventure">冒险活动</Option>
              <Option value="relaxation">休闲度假</Option>
            </Select>
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" block size="large" loading={loading} icon={<ClockCircleOutlined />}>
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

          <Divider>行程安排与地图</Divider>

          <Row gutter={16}>
            <Col span={8}>
              <div className="itinerary-section">
                <div className="view-mode-controls">
                  <Space>
                    <Button type={viewMode === 'day' ? 'primary' : 'default'} size="small" onClick={() => setViewMode('day')}>按天查看</Button>
                    <Button type={viewMode === 'full' ? 'primary' : 'default'} size="small" onClick={() => setViewMode('full')}>全程查看</Button>
                  </Space>
                </div>

                {viewMode === 'day' && (
                  <div className="day-selector">
                    <Space>
                      {Array.from({ length: generatedPlan.days }, (_, i) => i + 1).map(day => (
                        <Button key={day} type={currentDay === day ? 'primary' : 'default'} size="small" onClick={() => setCurrentDay(day)}>
                          Day {day}
                        </Button>
                      ))}
                    </Space>
                  </div>
                )}

                {(() => {
                  const normalizedItineraries = getNormalizedItineraries();
                  if (normalizedItineraries.length === 0) return null;
                  return (
                    <div className="itinerary-list">
                      {(viewMode === 'day'
                        ? normalizedItineraries.filter((day: any) => day.day === currentDay)
                        : normalizedItineraries
                      ).map((day: any) => (
                        <div key={day.day} className="day-itinerary">
                          <h4>第{day.day}天 - {day.date}</h4>
                          <div className="activities-list">
                            {day.normalizedActivities.map((activity: any, idx: number) => (
                              <div key={idx} className="activity-item">
                                {activity.time && <div className="activity-time">{activity.time}</div>}
                                <div className="activity-content">
                                  <h5>{activity.name}</h5>
                                  {activity.description && <p>{activity.description}</p>}
                                  {activity.location && <small>{activity.location}</small>}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </div>
            </Col>

            <Col span={16}>
              <div className="map-section">
                <MapComponent
                  key={mapKey}
                  markers={markers}
                  center={center}
                  zoom={12}
                  viewMode={viewMode}
                  currentDay={currentDay}
                />
              </div>
            </Col>
          </Row>
        </Card>
      )}
    </div>
  );
};

export default PlanGeneratorPage;