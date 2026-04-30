import React, { useState } from 'react';
import { Card, Form, Input, Select, DatePicker, Button, Space, message, Divider, Row, Col, Progress, Tag, Steps, Modal, Popconfirm } from 'antd';
import { CalendarOutlined, UserOutlined, EnvironmentOutlined, ClockCircleOutlined, SaveOutlined, LoadingOutlined, PlusOutlined, DeleteOutlined, CheckOutlined, ReloadOutlined, CloseOutlined, EditOutlined } from '@ant-design/icons';
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

// 出行方式选项
const TRAVEL_MODES = [
  { value: 'flight', label: '飞机', icon: '✈️' },
  { value: 'train', label: '火车', icon: '🚄' },
  { value: 'car', label: '自驾', icon: '🚗' },
  { value: 'bus', label: '大巴', icon: '🚌' },
  { value: 'self_drive', label: '自驾游', icon: '🚙' },
];

// 行程标签选项
const TRIP_TAGS = [
  '蜜月', '亲子', '自驾', '徒步', '摄影', '美食', '文化', '休闲', '冒险', '购物'
];

// 物品分类
const PACKING_CATEGORIES = [
  { value: '证件', label: '证件' },
  { value: '衣物', label: '衣物' },
  { value: '电子设备', label: '电子设备' },
  { value: '洗漱用品', label: '洗漱用品' },
  { value: '药品', label: '药品' },
  { value: '其他', label: '其他' },
];

interface Member {
  name: string;
  role: string;
}

interface PackingItem {
  name: string;
  category: string;
  checked: boolean;
}

const PlanGeneratorPage: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [generatedPlan, setGeneratedPlan] = useState<any>(null);
  const [planId, setPlanId] = useState<number | null>(null);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationStatus, setGenerationStatus] = useState<string>('');
  const [currentStep, setCurrentStep] = useState(0);
  const [members, setMembers] = useState<Member[]>([]);
  const [packingList, setPackingList] = useState<PackingItem[]>([]);
  const [cities, setCities] = useState<string[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [showPreview, setShowPreview] = useState(false);
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
    const maxAttempts = 120;
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

      const progress = Math.min(90, 10 + (attempts / maxAttempts) * 80);
      setGenerationProgress(Math.round(progress));

      attempts++;
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    return false;
  };

  // 检查 Celery Worker 状态
  const checkCeleryWorker = async (): Promise<boolean> => {
    try {
      // 注意：/health/celery 在根路径下，不在 /api/v1 下
      const apiUrl = process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:8001/api/v1';
      const baseUrl = apiUrl.replace(/\/api\/v1\/?$/, '');
      const res = await fetch(`${baseUrl}/health/celery`);
      if (res.ok) {
        const data = await res.json();
        return data.status === 'healthy' && data.worker_count > 0;
      }
      return false;
    } catch (error) {
      console.error('检查 Celery Worker 状态失败:', error);
      return false;
    }
  };

  // 同步生成（不需要 Celery Worker）
  const generateSync = async (planId: number, preferences: any) => {
    setGenerationProgress(30);
    setGenerationStatus('正在生成方案（同步模式）...');

    try {
      const generateRes = await authFetch(buildApiUrl(`/travel-plans/${planId}/generate-sync`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preferences }),
      });

      if (!generateRes.ok) {
        const errorData = await generateRes.json().catch(() => ({}));
        throw new Error(errorData.detail || '同步生成失败');
      }

      setGenerationProgress(90);
      const result = await generateRes.json();

      // 检查返回的结果是否有效
      if (result.status !== 'completed') {
        throw new Error('生成未完成');
      }

      return result;
    } catch (error) {
      // 同步生成失败，确保删除计划
      console.error('同步生成失败，尝试删除计划:', planId);
      await authFetch(buildApiUrl(`/travel-plans/${planId}`), { method: 'DELETE' }).catch(console.error);
      throw error;
    }
  };

  // 异步生成（需要 Celery Worker）
  const generateAsync = async (planId: number, preferences: any) => {
    setGenerationProgress(30);
    setGenerationStatus('已提交生成任务，等待处理...');

    try {
      const generateRes = await authFetch(buildApiUrl(`/travel-plans/${planId}/generate`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preferences }),
      });

      if (!generateRes.ok) {
        const errorData = await generateRes.json().catch(() => ({}));
        throw new Error(errorData.detail || '触发生成失败');
      }

      // 等待生成完成
      const success = await waitForGeneration(planId);
      if (!success) {
        throw new Error('生成超时或失败');
      }

      // 获取生成结果
      const detailRes = await authFetch(buildApiUrl(`/travel-plans/${planId}`));
      if (!detailRes.ok) {
        throw new Error('获取生成结果失败');
      }

      return await detailRes.json();
    } catch (error) {
      // 异步生成失败，确保删除计划
      console.error('异步生成失败，尝试删除计划:', planId);
      await authFetch(buildApiUrl(`/travel-plans/${planId}`), { method: 'DELETE' }).catch(console.error);
      throw error;
    }
  };

  const handleGenerate = async () => {
    // 从表单获取所有值
    const values = form.getFieldsValue(true);

    console.log('表单值:', values);

    // 检查必填字段
    if (!values.dateRange || !values.dateRange?.[0] || !values.dateRange?.[1]) {
      message.error('请选择旅行日期');
      return;
    }
    if (!values.destination) {
      message.error('请输入目的地');
      return;
    }
    if (!values.people) {
      message.error('请选择出行人数');
      return;
    }
    if (!values.budget) {
      message.error('请选择预算范围');
      return;
    }

    // 检查 Celery Worker 状态
    const useSyncMode = !await checkCeleryWorker();
    if (useSyncMode) {
      message.info('Celery Worker 未运行，将使用同步模式生成（可能需要较长时间）');
    }

    setLoading(true);
    setGenerationProgress(0);
    setGenerationStatus('');
    setGeneratedPlan(null);
    setPlanId(null);
    setShowPreview(false);

    let newPlanId: number | null = null;

    try {
      const durationDays = values.dateRange[1].diff(values.dateRange[0], 'days') + 1;

      const createData = {
        title: values.title || `${values.destination} ${durationDays}天旅行计划`,
        description: values.description,
        departure: values.departure,
        destination: values.destination,
        start_date: values.dateRange[0].format('YYYY-MM-DD'),
        end_date: values.dateRange[1].format('YYYY-MM-DD'),
        duration_days: durationDays,
        budget: budgetMap[values.budget] || 5000,
        transportation: values.travel_mode,
        preferences: {
          travelers: typeof values.people === 'string' ? (values.people === '10+' ? 10 : parseInt(values.people) || 1) : values.people,
          interests: values.interests || [],
        },
        cities: cities.length > 0 ? cities : undefined,
        members: members.length > 0 ? members.map(m => ({ ...m, avatar: undefined })) : undefined,
        packing_list: packingList.length > 0 ? packingList : undefined,
        travel_mode: values.travel_mode,
        tags: selectedTags.length > 0 ? selectedTags : undefined,
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
      newPlanId = createdPlan.id;
      setPlanId(newPlanId);

      // 准备偏好设置
      const preferences = {
        travelers: typeof values.people === 'string' ? (values.people === '10+' ? 10 : parseInt(values.people) || 1) : values.people,
        interests: values.interests || [],
        budget: budgetMap[values.budget] || 5000,
      };

      // 根据模式选择生成方式
      let planDetail: any;
      if (useSyncMode) {
        // 同步模式
        planDetail = await generateSync(newPlanId!, preferences);
      } else {
        // 异步模式
        planDetail = await generateAsync(newPlanId!, preferences);
      }

      setGenerationProgress(95);

      // 检查 generated_plans 是否有效
      if (!planDetail.generated_plans || planDetail.generated_plans.length === 0) {
        console.log('generated_plans 为空或不存在');
        await authFetch(buildApiUrl(`/travel-plans/${newPlanId}`), { method: 'DELETE' });
        setPlanId(null);
        message.error('生成完成，但方案内容为空，请重试');
        return;
      }

      // 检查 daily_itineraries 是否存在
      const dailyItineraries = planDetail.generated_plans[0]?.daily_itineraries;
      if (!dailyItineraries || dailyItineraries.length === 0) {
        console.log('daily_itineraries 为空或不存在');
        await authFetch(buildApiUrl(`/travel-plans/${newPlanId}`), { method: 'DELETE' });
        setPlanId(null);
        message.error('生成完成，但行程详情为空，请重试');
        return;
      }

      console.log('=== 生成成功 ===');
      console.log('daily_itineraries:', dailyItineraries);

      setGenerationProgress(100);
      setGeneratedPlan(planDetail);
      setShowPreview(true);
      message.success('旅行计划生成成功！请预览并确认');

    } catch (error: any) {
      console.error('生成失败:', error);
      // 如果计划已创建但生成失败，删除它
      if (newPlanId) {
        await authFetch(buildApiUrl(`/travel-plans/${newPlanId}`), { method: 'DELETE' });
        setPlanId(null);
      }
      message.error(error.message || '生成旅行计划失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // 重新生成
  const handleRegenerate = async () => {
    if (!planId) {
      message.error('请先生成旅行计划');
      return;
    }

    setLoading(true);
    setGenerationProgress(0);
    setGenerationStatus('');
    setShowPreview(false);

    try {
      setGenerationProgress(10);
      setGenerationStatus('重新生成方案中...');

      const generateRes = await authFetch(buildApiUrl(`/travel-plans/${planId}/generate`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preferences: generatedPlan?.preferences || {},
        }),
      });

      if (!generateRes.ok) {
        const errorData = await generateRes.json().catch(() => ({}));
        throw new Error(errorData.detail || '触发生成失败');
      }

      const success = await waitForGeneration(planId);

      if (success) {
        const detailRes = await authFetch(buildApiUrl(`/travel-plans/${planId}`));
        if (detailRes.ok) {
          const planDetail = await detailRes.json();

          // 检查 generated_plans 是否有效
          if (!planDetail.generated_plans || planDetail.generated_plans.length === 0) {
            message.error('重新生成完成，但方案内容为空');
            setLoading(false);
            return;
          }

          // 检查 daily_itineraries 是否存在
          const dailyItineraries = planDetail.generated_plans[0]?.daily_itineraries;
          if (!dailyItineraries || dailyItineraries.length === 0) {
            message.error('重新生成完成，但行程详情为空');
            setLoading(false);
            return;
          }

          setGeneratedPlan(planDetail);
          setShowPreview(true);
          message.success('旅行计划重新生成成功！');
        } else {
          message.error('重新生成成功，但获取详情失败');
        }
      } else {
        message.error('重新生成超时或失败，请稍后重试');
      }
    } catch (error: any) {
      console.error('重新生成失败:', error);
      message.error(error.message || '重新生成失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // 接受并保存
  const handleAccept = async () => {
    if (!planId) {
      message.error('请先生成旅行计划');
      return;
    }

    try {
      // 确保计划状态为 completed
      const statusRes = await authFetch(buildApiUrl(`/travel-plans/${planId}/status`));
      if (statusRes.ok) {
        const statusData = await statusRes.json();
        if (statusData.status !== 'completed') {
          message.error('计划尚未生成完成，无法保存');
          return;
        }
      }

      message.success('计划已保存到我的行程！');
      navigate('/itineraries');
    } catch (error) {
      console.error('保存失败:', error);
      message.error('保存失败，请重试');
    }
  };

  // 放弃本次生成
  const handleDiscard = async () => {
    if (!planId) {
      setGeneratedPlan(null);
      setShowPreview(false);
      return;
    }

    try {
      // 删除生成的计划
      const res = await authFetch(buildApiUrl(`/travel-plans/${planId}`), {
        method: 'DELETE',
      });
      if (res.ok) {
        message.info('已放弃本次生成');
        setGeneratedPlan(null);
        setPlanId(null);
        setShowPreview(false);
      } else {
        const errorData = await res.json().catch(() => ({}));
        message.error(errorData.detail || '删除失败');
      }
    } catch (error) {
      console.error('删除失败:', error);
      message.error('删除失败，请重试');
    }
  };

  // 编辑行程
  const handleEdit = () => {
    if (!planId) {
      message.error('请先生成旅行计划');
      return;
    }
    navigate(`/itineraries/${planId}`);
  };

  const addMember = () => {
    setMembers([...members, { name: '', role: '成员' }]);
  };

  const removeMember = (index: number) => {
    setMembers(members.filter((_, i) => i !== index));
  };

  const updateMember = (index: number, field: string, value: string) => {
    const newMembers = [...members];
    newMembers[index] = { ...newMembers[index], [field]: value };
    setMembers(newMembers);
  };

  const addPackingItem = () => {
    setPackingList([...packingList, { name: '', category: '其他', checked: false }]);
  };

  const removePackingItem = (index: number) => {
    setPackingList(packingList.filter((_, i) => i !== index));
  };

  const updatePackingItem = (index: number, field: string, value: any) => {
    const newPackingList = [...packingList];
    newPackingList[index] = { ...newPackingList[index], [field]: value };
    setPackingList(newPackingList);
  };

  const addCity = (city: string) => {
    if (city && !cities.includes(city)) {
      setCities([...cities, city]);
    }
  };

  const removeCity = (city: string) => {
    setCities(cities.filter(c => c !== city));
  };

  const toggleTag = (tag: string) => {
    if (selectedTags.includes(tag)) {
      setSelectedTags(selectedTags.filter(t => t !== tag));
    } else {
      setSelectedTags([...selectedTags, tag]);
    }
  };

  // 格式化日期显示
  const formatDateDisplay = () => {
    const dateRange = form.getFieldValue('dateRange');
    if (dateRange && Array.isArray(dateRange) && dateRange.length >= 2) {
      try {
        const start = dateRange[0];
        const end = dateRange[1];
        if (start && end && typeof start.format === 'function' && typeof end.format === 'function') {
          return `${start.format('YYYY-MM-DD')} 至 ${end.format('YYYY-MM-DD')}`;
        }
      } catch (e) {
        console.error('日期格式化错误:', e);
      }
    }
    return '未设置';
  };

  // 格式化人数显示
  const formatPeopleDisplay = () => {
    const people = form.getFieldValue('people');
    if (people) {
      return people === '10+' ? '十人及以上' : `${people}人`;
    }
    return '未设置';
  };

  // 渲染行程预览内容
  const renderPlanPreview = () => {
    if (!generatedPlan) {
      return (
        <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
          <LoadingOutlined style={{ fontSize: 32, marginBottom: 16 }} />
          <p>加载中...</p>
        </div>
      );
    }

    // 检查 generated_plans 是否存在
    const plans = generatedPlan.generated_plans;

    // 获取每日行程数据
    let dailyItineraries = [];
    if (plans && Array.isArray(plans) && plans.length > 0) {
      dailyItineraries = plans[0]?.daily_itineraries || [];
    }

    return (
      <div className="plan-preview-content">
        <div className="plan-summary">
          <Space size="large">
            <span><CalendarOutlined /> {generatedPlan.duration_days || 0}天</span>
            <span><UserOutlined /> {generatedPlan.preferences?.travelers || 1}人</span>
            <span><EnvironmentOutlined /> {generatedPlan.destination || '未知'}</span>
            <span>日期：{generatedPlan.start_date?.slice(0, 10) || '未设置'} 至 {generatedPlan.end_date?.slice(0, 10) || '未设置'}</span>
          </Space>
        </div>

        <Divider>行程安排预览</Divider>

        <Row gutter={16}>
          <Col span={14}>
            <div className="itinerary-details" style={{ maxHeight: 400, overflowY: 'auto' }}>
              {dailyItineraries.length > 0 ? (
                dailyItineraries.map((day: any, dayIndex: number) => (
                  <div key={dayIndex} className="day-section">
                    <h3 style={{ color: '#1890ff', borderBottom: '2px solid #1890ff', paddingBottom: 8 }}>
                      Day {day.day || dayIndex + 1} - {day.date || `第${dayIndex + 1}天`}
                    </h3>
                    {day.attractions?.map((attraction: any, idx: number) => (
                      <Card key={idx} className="activity-card" size="small" style={{ marginBottom: 8 }}>
                        <div className="activity-content">
                          <h4 style={{ margin: 0, color: '#333' }}>{attraction.name}</h4>
                          {attraction.description && (
                            <p className="activity-description" style={{ margin: '8px 0', color: '#666' }}>
                              {attraction.description}
                            </p>
                          )}
                          {attraction.address && (
                            <p className="activity-location" style={{ margin: 0, color: '#52c41a', fontSize: 12 }}>
                              <EnvironmentOutlined /> {attraction.address}
                            </p>
                          )}
                        </div>
                      </Card>
                    ))}
                    {day.meals && (
                      <div style={{ marginTop: 8, padding: 8, background: '#f6ffed', borderRadius: 4 }}>
                        <strong>餐饮推荐：</strong>
                        {Object.entries(day.meals).map(([key, value]: [string, any]) => (
                          <Tag key={key} color="green">{key}: {value}</Tag>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div style={{ textAlign: 'center', color: '#999', padding: '40px 0' }}>
                  暂无行程详情，请稍后重试
                </div>
              )}
            </div>
          </Col>
          <Col span={10}>
            <div className="map-section" style={{ height: 400, border: '1px solid #e8e8e8', borderRadius: 8, overflow: 'hidden' }}>
              <MapComponent
                markers={[]}
                center={{ lat: 18.2528, lng: 109.5127 }} // 三亚坐标
                zoom={11}
              />
            </div>
          </Col>
        </Row>

        <Divider>操作选项</Divider>

        <div className="preview-actions" style={{ textAlign: 'center' }}>
          <Space size="large">
            <Button
              type="primary"
              icon={<CheckOutlined />}
              onClick={handleAccept}
              size="large"
            >
              接受并保存
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRegenerate}
              loading={loading}
              size="large"
            >
              重新生成
            </Button>
            <Button
              icon={<EditOutlined />}
              onClick={handleEdit}
              size="large"
            >
              编辑行程
            </Button>
            <Popconfirm
              title="确定要放弃本次生成吗？"
              description="放弃后生成的计划将被删除"
              onConfirm={handleDiscard}
              okText="确定放弃"
              cancelText="取消"
            >
              <Button
                danger
                icon={<CloseOutlined />}
                size="large"
              >
                放弃
              </Button>
            </Popconfirm>
          </Space>
        </div>
      </div>
    );
  };

  return (
    <div className="plan-generator-page">
      <div className="page-header">
        <h1>一键生成旅行计划</h1>
        <p>输入您的旅行需求，AI 将为您生成个性化的旅行计划</p>
      </div>

      <Steps
        current={currentStep}
        onChange={setCurrentStep}
        style={{ marginBottom: 24 }}
        items={[
          { title: '基本信息', description: '目的地、日期、人数' },
          { title: '行程设置', description: '途经城市、出行方式' },
          { title: '成员与物品', description: '成员管理、物品清单' },
          { title: '生成计划', description: 'AI 生成行程' },
        ]}
      />

      <Card className="generator-form-card">
        <Form form={form} layout="vertical">
          {/* Step 1: 基本信息 */}
          <div style={{ display: currentStep === 0 ? 'block' : 'none' }}>
            <Form.Item name="title" label="行程名称（可选）">
              <Input placeholder="给您的旅行起个名字吧" maxLength={50} />
            </Form.Item>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="departure" label="出发地（可选）">
                  <Input placeholder="例如：北京" prefix={<EnvironmentOutlined />} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="destination" label="目的地" rules={[{ required: true, message: '请输入目的地' }]}>
                  <Input placeholder="例如：三亚" prefix={<EnvironmentOutlined />} />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item name="dateRange" label="旅行日期" rules={[{ required: true, message: '请选择旅行日期' }]}>
              <RangePicker
                style={{ width: '100%' }}
                prefix={<CalendarOutlined />}
                disabledDate={(current) => current && current < dayjs().startOf('day')}
              />
            </Form.Item>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="people" label="出行人数" rules={[{ required: true, message: '请选择出行人数' }]}>
                  <Select placeholder="选择出行人数" style={{ width: '100%' }}>
                    {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(person => (
                      <Option key={person} value={person}>{person}人</Option>
                    ))}
                    <Option value="10+">十人及以上</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="budget" label="预算范围" rules={[{ required: true, message: '请选择预算范围' }]}>
                  <Select placeholder="选择预算范围" style={{ width: '100%' }}>
                    <Option value="low">经济型（&lt; 3000元/人）</Option>
                    <Option value="medium">舒适型（3000-8000元/人）</Option>
                    <Option value="high">豪华型（&gt; 8000元/人）</Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>

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

            <Form.Item name="description" label="行程描述（可选）">
              <Input.TextArea placeholder="描述您的旅行期望和特殊需求" rows={3} maxLength={500} showCount />
            </Form.Item>
          </div>

          {/* Step 2: 行程设置 */}
          <div style={{ display: currentStep === 1 ? 'block' : 'none' }}>
            <Form.Item label="途经城市">
              <div className="cities-input">
                <Select
                  placeholder="输入城市名称"
                  style={{ width: 200 }}
                  showSearch
                  onSelect={addCity}
                  filterOption={(input, option) =>
                    (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
                  }
                >
                  {['北京', '上海', '广州', '深圳', '杭州', '成都', '重庆', '西安', '南京', '苏州', '厦门', '青岛', '大连', '三亚', '丽江'].map(city => (
                    <Option key={city} value={city} label={city}>{city}</Option>
                  ))}
                </Select>
                <div className="cities-tags" style={{ marginTop: 8 }}>
                  {cities.map(city => (
                    <Tag key={city} closable onClose={() => removeCity(city)} style={{ marginBottom: 4 }}>
                      {city}
                    </Tag>
                  ))}
                </div>
              </div>
            </Form.Item>

            <Form.Item name="travel_mode" label="出行方式">
              <div className="travel-mode-selector">
                {TRAVEL_MODES.map(mode => (
                  <div
                    key={mode.value}
                    className={`mode-option ${form.getFieldValue('travel_mode') === mode.value ? 'selected' : ''}`}
                    onClick={() => form.setFieldsValue({ travel_mode: mode.value })}
                  >
                    <span className="mode-icon">{mode.icon}</span>
                    <span className="mode-label">{mode.label}</span>
                  </div>
                ))}
              </div>
            </Form.Item>

            <Form.Item label="行程标签">
              <div className="tags-selector">
                {TRIP_TAGS.map(tag => (
                  <Tag
                    key={tag}
                    color={selectedTags.includes(tag) ? 'blue' : 'default'}
                    style={{ cursor: 'pointer', marginBottom: 8 }}
                    onClick={() => toggleTag(tag)}
                  >
                    {tag}
                  </Tag>
                ))}
              </div>
            </Form.Item>
          </div>

          {/* Step 3: 成员与物品 */}
          <div style={{ display: currentStep === 2 ? 'block' : 'none' }}>
            <Card title="参与成员" size="small" style={{ marginBottom: 16 }}>
              <div className="members-section">
                {members.map((member, index) => (
                  <Row key={index} gutter={8} style={{ marginBottom: 8 }}>
                    <Col span={10}>
                      <Input
                        placeholder="姓名"
                        value={member.name}
                        onChange={(e) => updateMember(index, 'name', e.target.value)}
                      />
                    </Col>
                    <Col span={10}>
                      <Select
                        value={member.role}
                        onChange={(value) => updateMember(index, 'role', value)}
                        style={{ width: '100%' }}
                      >
                        <Option value="组织者">组织者</Option>
                        <Option value="成员">成员</Option>
                        <Option value="儿童">儿童</Option>
                        <Option value="老人">老人</Option>
                      </Select>
                    </Col>
                    <Col span={4}>
                      <Button danger icon={<DeleteOutlined />} onClick={() => removeMember(index)} />
                    </Col>
                  </Row>
                ))}
                <Button type="dashed" icon={<PlusOutlined />} onClick={addMember} block>
                  添加成员
                </Button>
              </div>
            </Card>

            <Card title="物品清单" size="small">
              <div className="packing-section">
                {packingList.map((item, index) => (
                  <Row key={index} gutter={8} style={{ marginBottom: 8 }}>
                    <Col span={12}>
                      <Input
                        placeholder="物品名称"
                        value={item.name}
                        onChange={(e) => updatePackingItem(index, 'name', e.target.value)}
                      />
                    </Col>
                    <Col span={8}>
                      <Select
                        value={item.category}
                        onChange={(value) => updatePackingItem(index, 'category', value)}
                        style={{ width: '100%' }}
                      >
                        {PACKING_CATEGORIES.map(cat => (
                          <Option key={cat.value} value={cat.value}>{cat.label}</Option>
                        ))}
                      </Select>
                    </Col>
                    <Col span={4}>
                      <Button danger icon={<DeleteOutlined />} onClick={() => removePackingItem(index)} />
                    </Col>
                  </Row>
                ))}
                <Button type="dashed" icon={<PlusOutlined />} onClick={addPackingItem} block>
                  添加物品
                </Button>
              </div>
            </Card>
          </div>

          {/* Step 4: 生成计划 */}
          <div style={{ display: currentStep === 3 ? 'block' : 'none' }}>
            <div className="generate-section">
              <div className="summary-card">
                <h3>行程概览</h3>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div><strong>目的地：</strong>{form.getFieldValue('destination') || '未设置'}</div>
                  <div><strong>出发地：</strong>{form.getFieldValue('departure') || '未设置'}</div>
                  <div><strong>日期：</strong>{formatDateDisplay()}</div>
                  <div><strong>人数：</strong>{formatPeopleDisplay()}</div>
                  <div><strong>出行方式：</strong>{TRAVEL_MODES.find(m => m.value === form.getFieldValue('travel_mode'))?.label || '未设置'}</div>
                  {cities.length > 0 && <div><strong>途经城市：</strong>{cities.join(' → ')}</div>}
                  <div><strong>参与成员：</strong>{members.length > 0 ? `${members.filter(m => m.name).length}人` : '未添加'}</div>
                  <div><strong>物品清单：</strong>{packingList.length > 0 ? `${packingList.filter(p => p.name).length}项` : '未添加'}</div>
                  {selectedTags.length > 0 && <div><strong>标签：</strong>{selectedTags.join('、')}</div>}
                </Space>
              </div>

              <Button
                type="primary"
                onClick={handleGenerate}
                block
                size="large"
                loading={loading}
                icon={<ClockCircleOutlined />}
                style={{ marginTop: 24 }}
              >
                生成旅行计划
              </Button>
            </div>
          </div>

          {/* 导航按钮 */}
          <div className="step-navigation" style={{ marginTop: 24, display: 'flex', justifyContent: 'space-between' }}>
            {currentStep > 0 && (
              <Button onClick={() => setCurrentStep(currentStep - 1)}>
                上一步
              </Button>
            )}
            {currentStep < 3 && (
              <Button type="primary" onClick={() => setCurrentStep(currentStep + 1)} style={{ marginLeft: 'auto' }}>
                下一步
              </Button>
            )}
          </div>
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

      {/* 预览弹窗 */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckOutlined style={{ color: '#52c41a' }} />
            <span>行程预览 - {generatedPlan?.title || '加载中...'}</span>
          </div>
        }
        open={showPreview && generatedPlan !== null}
        onCancel={() => {
          console.log('Modal onCancel called');
          setShowPreview(false);
        }}
        footer={null}
        width={1000}
        className="plan-preview-modal"
        destroyOnClose={false}
        maskClosable={false}
        centered
      >
        {generatedPlan ? renderPlanPreview() : (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <LoadingOutlined style={{ fontSize: 32 }} />
            <p style={{ marginTop: 16, color: '#666' }}>加载预览内容...</p>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default PlanGeneratorPage;
