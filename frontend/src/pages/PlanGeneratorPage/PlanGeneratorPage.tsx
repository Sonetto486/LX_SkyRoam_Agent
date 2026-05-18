import React, { useState, useEffect, useCallback } from 'react';
import { Card, Form, Input, Select, DatePicker, Button, Space, message, Divider, Row, Col, Progress, Steps, Modal, Popconfirm, Alert, Spin, AutoComplete } from 'antd';
import { CalendarOutlined, UserOutlined, EnvironmentOutlined, ClockCircleOutlined, CheckOutlined, CloseOutlined, EditOutlined, StopOutlined, LoadingOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import './PlanGeneratorPage.css';
import MapComponent from '../../components/MapComponent/MapComponent';
import AttractionImageCarousel from '../../components/AttractionImageCarousel/AttractionImageCarousel';
import { buildApiUrl } from '../../config/api';
import { authFetch } from '../../utils/auth';

const { Option } = Select;
const { RangePicker } = DatePicker;

// 城市输入提示组件
interface CityInputProps {
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
}

const CityInput: React.FC<CityInputProps> = ({ value, onChange, placeholder }) => {
  const [options, setOptions] = useState<{ value: string; label: string }[]>([]);
  const [searching, setSearching] = useState(false);

  const fetchCityTips = useCallback(async (keyword: string) => {
    if (!keyword || keyword.length < 1) {
      setOptions([]);
      return;
    }

    setSearching(true);
    try {
      // 调用后端 API，后端会使用正确的 Web 服务 API Key
      const res = await fetch(buildApiUrl(`/map/tips?q=${encodeURIComponent(keyword)}&city_only=true`));
      const data = await res.json();
      if (data.options && Array.isArray(data.options)) {
        const cityOptions = data.options
          .filter((tip: any) => tip.value) // 过滤掉空值
          .map((tip: any) => ({
            value: tip.value,
            label: tip.label || tip.value,
          }));
        // 去重
        const uniqueOptions = cityOptions.filter(
          (opt: any, index: number, self: any) => self.findIndex((o: any) => o.value === opt.value) === index
        );
        setOptions(uniqueOptions.slice(0, 10));
      }
    } catch (e) {
      console.error('获取城市提示失败:', e);
    }
    setSearching(false);
  }, []);

  const handleSearch = (searchValue: string) => {
    fetchCityTips(searchValue);
  };

  const handleSelect = (selectedValue: string) => {
    onChange?.(selectedValue);
    setOptions([]);
  };

  return (
    <AutoComplete
      value={value}
      onChange={onChange}
      options={options}
      onSearch={handleSearch}
      onSelect={handleSelect}
      placeholder={placeholder}
      suffixIcon={searching ? <LoadingOutlined /> : <EnvironmentOutlined />}
      allowClear
      filterOption={false}
    />
  );
};

const PlanGeneratorPage: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedPlan, setGeneratedPlan] = useState<any>(null);
  const [planId, setPlanId] = useState<number | null>(null);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationStatus, setGenerationStatus] = useState<string>('');
  const [currentStep, setCurrentStep] = useState(0);
  const [showPreview, setShowPreview] = useState(false);
  const [showGeneratingModal, setShowGeneratingModal] = useState(false);
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const [celeryTaskId, setCeleryTaskId] = useState<string | null>(null);
  const [mapCenter, setMapCenter] = useState<{ lat: number; lng: number }>({ lat: 39.9042, lng: 116.4074 }); // 默认北京
  const [previewActiveDay, setPreviewActiveDay] = useState(0); // 预览时选中的天数
  const [viewMode, setViewMode] = useState<'full' | 'day'>('full'); // 'full' 表示全程，'day' 表示单天
  const navigate = useNavigate();

  // 切换天数时更新地图中心点（仅在单天模式下）
  useEffect(() => {
    if (showPreview && generatedPlan && viewMode === 'day') {
      const markers = getPlanMarkers();
      if (markers.length > 0) {
        setMapCenter(markers[0].position);
      }
    }
    // 全程模式不设置中心点，让 MapComponent 自己通过 setFitView 调整视野
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [previewActiveDay, viewMode, showPreview]);

  // 地理编码 - 通过后端 API 获取目的地坐标
  const geocodeDestination = async (destination: string): Promise<{ lat: number; lng: number } | null> => {
    if (!destination) return null;

    try {
      // 使用后端地理编码 API
      const res = await fetch(buildApiUrl(`/map/geocode?address=${encodeURIComponent(destination)}`));
      const data = await res.json();
      if (data.status === 'ok' && data.lng && data.lat) {
        return { lng: data.lng, lat: data.lat };
      }
    } catch (e) {
      console.error('地理编码失败:', e);
    }
    return null;
  };

  const pollGenerationStatus = async (id: number) => {
    try {
      const res = await authFetch(buildApiUrl(`/travel-plans/${id}/status`));
      if (!res.ok) throw new Error('获取状态失败');
      return await res.json();
    } catch (error) {
      console.error('轮询状态失败:', error);
      return null;
    }
  };

  const waitForGeneration = async (id: number): Promise<boolean> => {
    // 增加到 600 次尝试（10 分钟），因为 LLM 生成可能需要较长时间
    const maxAttempts = 600;
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

      if (status.status === 'failed') return false;

      setGenerationProgress(Math.min(90, 10 + (attempts / maxAttempts) * 80));
      attempts++;
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    const finalStatus = await pollGenerationStatus(id);
    return finalStatus?.status === 'completed';
  };

  const checkCeleryWorker = async (): Promise<boolean> => {
    try {
      const apiUrl = process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
      const baseUrl = apiUrl.replace(/\/api\/v1\/?$/, '');
      const res = await fetch(`${baseUrl}/health/celery`);
      if (res.ok) {
        const data = await res.json();
        return data.status === 'healthy' && data.worker_count > 0;
      }
      return false;
    } catch {
      return false;
    }
  };

  const generateSync = async (planId: number, preferences: any, mustVisitAttractions: string[] = []) => {
    setGenerationProgress(30);
    setGenerationStatus('正在生成方案（同步模式）...');

    const generateRes = await authFetch(buildApiUrl(`/travel-plans/${planId}/generate-sync`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ preferences, must_visit_attractions: mustVisitAttractions }),
    });

    if (!generateRes.ok) {
      const errorData = await generateRes.json().catch(() => ({}));
      throw new Error(errorData.detail || '同步生成失败');
    }

    setGenerationProgress(90);
    const result = await generateRes.json();
    if (result.status !== 'completed') throw new Error('生成未完成');
    return result;
  };

  const generateAsync = async (planId: number, preferences: any, mustVisitAttractions: string[] = []) => {
    setGenerationProgress(30);
    setGenerationStatus('已提交生成任务，等待处理...');

    const generateRes = await authFetch(buildApiUrl(`/travel-plans/${planId}/generate`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ preferences, must_visit_attractions: mustVisitAttractions }),
    });

    if (!generateRes.ok) {
      const errorData = await generateRes.json().catch(() => ({}));
      throw new Error(errorData.detail || '触发生成失败');
    }

    const generateData = await generateRes.json();
    if (generateData.task_id) setCeleryTaskId(generateData.task_id);

    const success = await waitForGeneration(planId);
    if (!success) throw new Error('生成超时或失败');

    const detailRes = await authFetch(buildApiUrl(`/travel-plans/${planId}`));
    if (!detailRes.ok) throw new Error('获取生成结果失败');
    return await detailRes.json();
  };

  const handleGenerate = async () => {
    if (isGenerating) {
      message.warning('正在生成中，请稍候...');
      return;
    }

    const values = form.getFieldsValue(true);

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

    const useSyncMode = !await checkCeleryWorker();
    if (useSyncMode) {
      message.info('Celery Worker 未运行，将使用同步模式生成（可能需要较长时间）');
    }

    setIsGenerating(true);
    setLoading(true);
    setGenerationProgress(0);
    setGenerationStatus('准备生成...');
    setGeneratedPlan(null);
    setPlanId(null);
    setCeleryTaskId(null);
    setShowPreview(false);
    setShowGeneratingModal(true);

    const controller = new AbortController();
    setAbortController(controller);

    let newPlanId: number | null = null;

    try {
      const durationDays = values.dateRange[1].diff(values.dateRange[0], 'days') + 1;

      // 解析必去景点（支持逗号、顿号、换行分隔）
      const mustVisitAttractions = values.must_visit_attractions
        ? values.must_visit_attractions
            .split(/[，,、\n]+/)
            .map((s: string) => s.trim())
            .filter(Boolean)
        : [];

      const createData = {
        title: values.title || `${values.destination} ${durationDays}天旅行计划`,
        destination: values.destination,
        start_date: values.dateRange[0].format('YYYY-MM-DD'),
        end_date: values.dateRange[1].format('YYYY-MM-DD'),
        duration_days: durationDays,
        preferences: {
          travelers: typeof values.people === 'string' ? (values.people === '10+' ? 10 : parseInt(values.people) || 1) : values.people,
          interests: values.interests || [],
        },
        must_visit_attractions: mustVisitAttractions,
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

      const preferences = {
        travelers: typeof values.people === 'string' ? (values.people === '10+' ? 10 : parseInt(values.people) || 1) : values.people,
        interests: values.interests || [],
      };

      const planDetail = useSyncMode
        ? await generateSync(newPlanId!, preferences, mustVisitAttractions)
        : await generateAsync(newPlanId!, preferences, mustVisitAttractions);

      if (controller.signal.aborted) throw new Error('生成已中止');

      setGenerationProgress(95);

      if (!planDetail.generated_plans || planDetail.generated_plans.length === 0) {
        await authFetch(buildApiUrl(`/travel-plans/${newPlanId}`), { method: 'DELETE' });
        setPlanId(null);
        message.error('生成完成，但方案内容为空，请重试');
        return;
      }

      setGenerationProgress(100);
      setGenerationStatus('生成完成！');
      setPreviewActiveDay(0); // 重置为第 1 天
      setGeneratedPlan(planDetail);
      setCeleryTaskId(null);
      setShowGeneratingModal(false);
      setShowPreview(true);

      // 获取目的地坐标并更新地图中心
      const destination = planDetail.destination || values.destination;
      if (destination) {
        const coords = await geocodeDestination(destination);
        if (coords) {
          setMapCenter(coords);
        }
      }

      message.success('旅行计划生成成功！请预览并确认');

    } catch (error: any) {
      if (error.message === '生成已中止' || error.name === 'AbortError') {
        message.info('已中止生成');
        return;
      }

      console.error('生成失败:', error);
      if (newPlanId) {
        await authFetch(buildApiUrl(`/travel-plans/${newPlanId}`), { method: 'DELETE' });
        setPlanId(null);
      }
      message.error(error.message || '生成旅行计划失败，请重试');
      setShowGeneratingModal(false);
    } finally {
      setLoading(false);
      setIsGenerating(false);
      setAbortController(null);
    }
  };

  const handleAbortGeneration = async () => {
    if (abortController) abortController.abort();

    const currentTaskId = celeryTaskId;
    if (currentTaskId) {
      setCeleryTaskId(null);
      try {
        const cancelController = new AbortController();
        const timeoutId = setTimeout(() => cancelController.abort(), 3000);
        await fetch(buildApiUrl(`/travel-plans/tasks/cancel/${currentTaskId}`), {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
          signal: cancelController.signal,
        });
        clearTimeout(timeoutId);
      } catch {}
    }

    setIsGenerating(false);
    setLoading(false);
    setShowGeneratingModal(false);
    setGenerationProgress(0);
    setGenerationStatus('');
    setAbortController(null);

    const currentPlanId = planId;
    if (currentPlanId) {
      setPlanId(null);
      setGeneratedPlan(null);
      try {
        await fetch(buildApiUrl(`/travel-plans/${currentPlanId}`), {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        });
        message.info('已中止生成，无效计划已删除');
      } catch {
        message.info('已中止生成');
      }
    } else {
      message.info('已中止生成');
    }
  };

  const handleAccept = async () => {
    if (!planId) {
      message.error('请先生成旅行计划');
      return;
    }
    message.success('计划已保存到我的行程！');
    navigate('/itineraries');
  };

  const handleDiscard = async () => {
    if (!planId) {
      setGeneratedPlan(null);
      setShowPreview(false);
      return;
    }

    try {
      await authFetch(buildApiUrl(`/travel-plans/${planId}`), { method: 'DELETE' });
      message.info('已放弃本次生成');
      setGeneratedPlan(null);
      setPlanId(null);
      setShowPreview(false);
    } catch {
      message.error('删除失败，请重试');
    }
  };

  const handleEdit = () => {
    if (!planId) {
      message.error('请先生成旅行计划');
      return;
    }
    navigate(`/itineraries/${planId}`);
  };

  const formatDateDisplay = () => {
    const dateRange = form.getFieldValue('dateRange');
    if (dateRange?.length >= 2) {
      try {
        return `${dateRange[0].format('YYYY-MM-DD')} 至 ${dateRange[1].format('YYYY-MM-DD')}`;
      } catch {}
    }
    return '未设置';
  };

  const formatPeopleDisplay = () => {
    const people = form.getFieldValue('people');
    return people ? (people === '10+' ? '十人及以上' : `${people}人`) : '未设置';
  };

  // 从生成方案中提取地图标记数据（根据 viewMode 决定显示哪些天的景点）
  const getPlanMarkers = () => {
    if (!generatedPlan) return [];

    const plans = generatedPlan.generated_plans;
    const dailyItineraries = plans?.[0]?.daily_itineraries || [];

    const markers: any[] = [];

    // 根据 viewMode 决定显示哪些天的景点
    const daysToShow = viewMode === 'full'
      ? dailyItineraries
      : [dailyItineraries[previewActiveDay]].filter(Boolean);

    // 诊断日志：打印后端返回的完整数据结构
    console.log('=== 地图标签诊断日志 ===');
    console.log('当前viewMode:', viewMode);
    console.log('dailyItineraries数量:', dailyItineraries.length);
    
    daysToShow.forEach((dayData: any, arrayIndex: number) => {
      const dayIndex = viewMode === 'full' ? arrayIndex : previewActiveDay;
      if (!dayData) return;

      console.log(`Day ${dayIndex + 1}:`, {
        date: dayData.date,
        attractionsCount: dayData.attractions?.length || 0,
        attractions: dayData.attractions?.map((a: any) => ({
          name: a.name,
          category: a.category,
          type: a.type,
          hasImages: !!(a.image_url || a.photos),
          coordinates: a.coordinates || { lat: a.latitude, lng: a.longitude }
        })) || []
      });

      // 添加当天景点
      if (dayData.attractions) {
        dayData.attractions.forEach((attraction: any, index: number) => {
          // 检查是否有坐标数据（支持多种格式）
          let position = null;

          // 格式1: coordinates 对象
          if (attraction.coordinates && attraction.coordinates.lat && attraction.coordinates.lng) {
            position = { lat: attraction.coordinates.lat, lng: attraction.coordinates.lng };
          }
          // 格式2: latitude/longitude 字段
          else if (attraction.latitude && attraction.longitude) {
            position = { lat: attraction.latitude, lng: attraction.longitude };
          }

          if (position) {
            const markerData = {
              id: `${dayIndex}-${attraction.name}`,
              name: attraction.name,
              position: position,
              address: attraction.address || '',
              day: dayIndex + 1,
              date: dayData.date,
              // 景点指标数据
              score: attraction.rating || attraction.score,
              type: attraction.category || attraction.type,
              price: attraction.price,
              // 是否为当前选中天数（全程模式下全部高亮，单天模式下只有当天高亮）
              isActive: viewMode === 'full' ? true : dayIndex === previewActiveDay,
            };
            
            // 诊断：检查是否有名称不匹配的问题
            if (attraction.category && attraction.category !== attraction.name) {
              console.warn(`⚠️ 潜在的景点名称问题:`, {
                name: attraction.name,
                category: attraction.category,
                markerWillShow: attraction.name
              });
            }
            
            markers.push(markerData);
          }
        });
      }
    });

    console.log('最终 markers 数据:', {
      数量: markers.length,
      景点列表: markers.map(m => ({
        name: m.name,
        day: m.day,
        type: m.type,
        position: m.position
      }))
    });
    console.log('=== 诊断完成 ===');
    
    return markers;
  };

  const renderPlanPreview = () => {
    if (!generatedPlan) {
      return (
        <div className="plan-preview-loading">
          <LoadingOutlined style={{ fontSize: 32, marginBottom: 16 }} />
          <p>加载中...</p>
        </div>
      );
    }

    const plans = generatedPlan.generated_plans;
    const dailyItineraries = plans?.[0]?.daily_itineraries || [];

    // 诊断：对比左侧列表和地图标记的景点名称
    const leftListAttractions = dailyItineraries.flatMap((day: any) =>
      (day.attractions || []).map((a: any) => a.name)
    );
    const mapMarkerAttractions = getPlanMarkers().map(m => m.name);
    
    const mismatchedAttractions = leftListAttractions.filter(
      (name: string) => !mapMarkerAttractions.includes(name)
    );
    
    if (mismatchedAttractions.length > 0) {
      console.warn('⚠️ 景点名称不匹配警告:', {
        message: '以下景点出现在左侧列表但不在地图上',
        mismatched: mismatchedAttractions,
        suggestion: '这可能表示景点缺少坐标数据或名称不一致'
      });
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
                    <h3 className="day-section-title">
                      Day {day.day || dayIndex + 1} - {day.date || `第${dayIndex + 1}天`}
                    </h3>
                    {day.attractions?.map((attraction: any, idx: number) => {
                      const images = attraction.photos || (attraction.image_url ? [attraction.image_url] : []);

                      return (
                        <Card key={idx} className="activity-card" size="small" style={{ marginBottom: 8 }}>
                          <div className="activity-content">
                            <h4 className="activity-title">{attraction.name}</h4>

                            {/* 图片轮播组件 */}
                            {images.length > 0 && (
                              <AttractionImageCarousel
                                images={images}
                                attractionName={attraction.name}
                                maxImagesToShow={2}
                              />
                            )}
                            
                            {/* 简要信息（始终显示） */}
                            {attraction.description && <p className="activity-description">{attraction.description}</p>}
                            {attraction.address && <p className="activity-location"><EnvironmentOutlined /> {attraction.address}</p>}

                            {/* 评分（直接显示） */}
                            {attraction.rating && (
                              <p className="detail-item" style={{ marginTop: 8 }}><span className="detail-label">评分：</span> ⭐ {attraction.rating}</p>
                            )}
                          </div>
                        </Card>
                      );
                    })}
                  </div>
                ))
              ) : (
                <div className="no-itinerary">暂无行程详情</div>
              )}
            </div>
          </Col>
          <Col span={10}>
            {/* 天数选择 */}
            <div style={{ marginBottom: 8 }}>
              <Space>
                {/* 全程按钮 */}
                <Button
                  type={viewMode === 'full' ? 'primary' : 'default'}
                  size="small"
                  onClick={() => setViewMode('full')}
                  style={{ fontWeight: viewMode === 'full' ? 'bold' : 'normal' }}
                >
                  全程
                </Button>
                {/* 各天按钮 */}
                {dailyItineraries.map((day: any, index: number) => (
                  <Button
                    key={index}
                    type={viewMode === 'day' && previewActiveDay === index ? 'primary' : 'default'}
                    size="small"
                    onClick={() => {
                      setViewMode('day');
                      setPreviewActiveDay(index);
                    }}
                  >
                    Day {day.day || index + 1}
                  </Button>
                ))}
              </Space>
            </div>
            {/* 地图 */}
            <div className="map-section" style={{ height: 360 }}>
              <MapComponent
                key={`map-${planId}-${viewMode}-${previewActiveDay}`}
                markers={getPlanMarkers()}
                center={mapCenter}
                zoom={11}
                viewMode={viewMode}
                currentDay={viewMode === 'day' ? previewActiveDay + 1 : undefined}
              />
            </div>
          </Col>
        </Row>

        <Divider>操作选项</Divider>

        <div className="preview-actions">
          <Space size="large">
            <Button type="primary" icon={<CheckOutlined />} onClick={handleAccept} size="large">接受并保存</Button>
            <Button icon={<EditOutlined />} onClick={handleEdit} size="large">编辑行程</Button>
            <Popconfirm title="确定要放弃本次生成吗？" onConfirm={handleDiscard} okText="确定放弃" cancelText="取消">
              <Button danger icon={<CloseOutlined />} size="large">放弃</Button>
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

            <Form.Item name="destination" label="目的地" rules={[{ required: true, message: '请输入目的地' }]}>
              <CityInput placeholder="输入城市名称" />
            </Form.Item>

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
            </Row>

            <Form.Item name="interests" label="兴趣偏好（可选）">
              <Select mode="multiple" placeholder="选择您的兴趣偏好" style={{ width: '100%' }}>
                <Option value="sightseeing">观光游览</Option>
                <Option value="food">美食探索</Option>
                <Option value="shopping">购物</Option>
                <Option value="culture">文化体验</Option>
                <Option value="adventure">冒险活动</Option>
                <Option value="relaxation">休闲度假</Option>
              </Select>
            </Form.Item>

            <Form.Item
              name="must_visit_attractions"
              label="必去景点（可选）"
              tooltip="输入您一定要去的景点，多个景点用逗号分隔"
            >
              <Input.TextArea placeholder="例如：故宫、长城、天坛" rows={2} maxLength={200} showCount />
            </Form.Item>
          </div>

          {/* Step 2: 生成计划 */}
          <div style={{ display: currentStep === 1 ? 'block' : 'none' }}>
            <div className="generate-section">
              <div className="summary-card">
                <h3>行程概览</h3>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div><strong>目的地：</strong>{form.getFieldValue('destination') || '未设置'}</div>
                  <div><strong>日期：</strong>{formatDateDisplay()}</div>
                  <div><strong>人数：</strong>{formatPeopleDisplay()}</div>
                </Space>
              </div>

              <Button
                type="primary"
                onClick={handleGenerate}
                block
                size="large"
                loading={loading}
                disabled={isGenerating}
                icon={<ClockCircleOutlined />}
                style={{ marginTop: 24 }}
              >
                {isGenerating ? '生成中...' : '生成旅行计划'}
              </Button>

              {isGenerating && (
                <Alert
                  message="正在生成旅行计划"
                  description="请耐心等待，生成过程中请勿关闭页面。"
                  type="info"
                  showIcon
                  style={{ marginTop: 16 }}
                />
              )}
            </div>
          </div>

          {/* 导航按钮 */}
          <div style={{ marginTop: 24, display: 'flex', justifyContent: 'space-between' }}>
            {currentStep > 0 && (
              <Button onClick={() => setCurrentStep(currentStep - 1)}>上一步</Button>
            )}
            {currentStep < 1 && (
              <Button type="primary" onClick={() => setCurrentStep(currentStep + 1)} style={{ marginLeft: 'auto' }}>
                下一步
              </Button>
            )}
          </div>
        </Form>
      </Card>

      {/* 生成中的模态框 */}
      <Modal
        title={<div className="modal-title-loading"><LoadingOutlined className="loading-icon" /><span>正在生成旅行计划...</span></div>}
        open={showGeneratingModal}
        onCancel={handleAbortGeneration}
        footer={
          <div className="modal-footer-center">
            <Popconfirm title="确定要中止生成吗？" onConfirm={handleAbortGeneration} okText="确定中止" cancelText="取消">
              <Button danger icon={<StopOutlined />} size="large">中止生成</Button>
            </Popconfirm>
          </div>
        }
        width={500}
        centered
        maskClosable={false}
        closable={false}
      >
        <div className="generating-modal-content">
          <Spin size="large" style={{ marginBottom: 24 }} />
          <Progress percent={Math.round(generationProgress)} status="active" strokeColor={{ '0%': '#108ee9', '100%': '#87d068' }} />
          <p className="generation-status">{generationStatus || '处理中...'}</p>
          <p className="generation-hint">预计需要 1 分钟，请耐心等待</p>
        </div>
      </Modal>

      {/* 预览弹窗 */}
      <Modal
        title={<div className="modal-title-success"><CheckOutlined className="success-icon" /><span>行程预览 - {generatedPlan?.title || '加载中...'}</span></div>}
        open={showPreview && generatedPlan !== null}
        onCancel={() => {
          setShowPreview(false);
          setPreviewActiveDay(0);
        }}
        footer={null}
        width={1000}
        className="plan-preview-modal"
        maskClosable={false}
        centered
      >
        {renderPlanPreview()}
      </Modal>
    </div>
  );
};

export default PlanGeneratorPage;
