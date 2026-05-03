import React, { useState, useEffect, useRef } from 'react';
import { 
  Card, 
  Button, 
  Input, 
  AutoComplete,
  DatePicker, 
  Select, 
  Form, 
  Row, 
  Col, 
  Typography, 
  Space,
  Steps,
  Alert,
  Spin,
  Progress,
  InputNumber,
  Empty,
  Tooltip,
  Tag,
  Tabs,
  Grid,
  Timeline
} from 'antd';
import type { AutoCompleteProps } from 'antd';
import { 
  SearchOutlined, 
  GlobalOutlined, 
  CheckCircleOutlined,
  LoadingOutlined,
  UserOutlined,
  HeartOutlined,
  EnvironmentOutlined,
  StarFilled,
  LinkOutlined,
  ClockCircleOutlined,
  PictureOutlined
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import dayjs from 'dayjs';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';
import { authFetch } from '../../utils/auth';
import { createDebouncedFetcher } from '../../utils/searchUtils';
import { TRANSPORTATION_OPTIONS, AGE_GROUP_OPTIONS, FOOD_PREFERENCES_OPTIONS, DIETARY_RESTRICTIONS_OPTIONS, PREFERENCES_OPTIONS } from '../../constants/travel';


const { Title, Paragraph, Text } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

interface TravelRequest {
  departure?: string;  // 出发地（可选）
  destination: string;
  dateRange: [dayjs.Dayjs, dayjs.Dayjs];
  budget: number;
  preferences: string[];
  requirements: string;
  transportation?: string;  // 出行方式（可选）
  travelers: number;  // 出行人数
  foodPreferences: string[];  // 口味偏好
  dietaryRestrictions: string[];  // 忌口/饮食限制
  ageGroups: string[];  // 年龄组成
}

const TravelPlanPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [generationStatus, setGenerationStatus] = useState<string>('idle');
  const [progress, setProgress] = useState(0);
  const [autoSubmitting, setAutoSubmitting] = useState(false);
  const hasAutoSubmitted = useRef(false);
  const pollTimerRef = useRef<any>(null);
  const currentPlanIdRef = useRef<number | null>(null);
  const isMountedRef = useRef(true);
  // 新增：预览数据
  const [previewData, setPreviewData] = useState<any | null>(null);
  const [depOptions, setDepOptions] = useState<AutoCompleteProps['options']>([]);
  const [destOptions, setDestOptions] = useState<AutoCompleteProps['options']>([]);
  const placeCacheRef = useRef<Map<string, { value: string; label: React.ReactNode }[]>>(new Map());
  const [tipsEnabled, setTipsEnabled] = useState<boolean>(true);

  // 预览渲染工具函数（在组件内，便于使用）
  const getTitle = (item: any, fallback: string = '未命名') => (
    item?.title || item?.name || item?.note_title || item?.poiName || item?.restaurant_name || fallback
  );

  const getDesc = (item: any) => (
    item?.desc || item?.description || item?.note_desc || item?.summary || item?.address || ''
  );

  const getImage = (item: any) => {
    const pickUrl = (u: any) => {
      if (!u) return undefined;
      const s = String(u).trim().replace(/[`"]/g, '');
      return s.split(/\s+/)[0];
    };
    const candidates: (string | undefined)[] = [];

    // 小红书优先使用 img_urls
    if (Array.isArray(item?.img_urls) && item.img_urls.length) {
      candidates.push(pickUrl(item.img_urls[0]));
    }

    // 常见图片字段
    candidates.push(
      pickUrl(item?.cover_url),
      pickUrl(item?.image_url),
      pickUrl(item?.thumbnail)
    );

    // images 可能是字符串或对象
    if (Array.isArray(item?.images) && item.images.length) {
      const img0 = item.images[0];
      candidates.push(pickUrl(typeof img0 === 'string' ? img0 : img0?.url));
    }

    // photos 可能是字符串或对象（如高德返回 { url }）
    if (Array.isArray(item?.photos) && item.photos.length) {
      const p0 = item.photos[0];
      candidates.push(pickUrl(typeof p0 === 'string' ? p0 : p0?.url));
    }

    return candidates.find((u) => typeof u === 'string' && u.length > 0);
  };

  const normalizePreview = (pv: any) => {
    if (!pv || typeof pv !== 'object') return pv;
    const sections = pv.sections || {
      weather: pv.weather,
      hotels: pv.hotels,
      attractions: pv.attractions,
      restaurants: pv.restaurants,
      flights: pv.flights,
      xiaohongshu_notes: pv.xiaohongshu_notes,
    };
    return { sections };
  };

  const lastPreviewHashRef = useRef<string | null>(null);
  const lastProgressRef = useRef<number>(0);

  const setPreviewDataIfChanged = (pv: any) => {
    const normalized = normalizePreview(pv);
    const hash = (() => {
      try { return JSON.stringify(normalized); } catch { return String(normalized); }
    })();
    if (lastPreviewHashRef.current === hash) return;
    lastPreviewHashRef.current = hash;
    setPreviewData(normalized);
  };

  const setProgressIfChanged = (p: number) => {
    if (p === lastProgressRef.current) return;
    lastProgressRef.current = p;
    setProgress(p);
  };

  const safeImgSrc = (url?: string) => {
    if (!url) return undefined;
    try {
      const u = new URL(url);
      const host = (u.hostname || '').toLowerCase();
      if (host.endsWith('.xhscdn.com') || host.endsWith('.xiaohongshu.com') || host === 'img.xiaohongshu.com') {
        return buildApiUrl(`/proxy/image?url=${encodeURIComponent(url)}`);
      }
      return url;
    } catch {
      return url;
    }
  };

  const getPrice = (item: any) => {
    const p = item?.price || item?.price_total || item?.min_price || item?.avg_price || item?.price_per_night;
    return typeof p === 'number' ? `¥${p}` : typeof p === 'string' ? p : undefined;
  };

  const getLikes = (item: any) => {
    const v = item?.likes || item?.like_count || item?.liked_count;
    return typeof v === 'number' ? v : undefined;
  };

  const hasPriceValue = (value?: string) => {
    if (typeof value !== 'string') return false;
    return value.trim().length > 0 && value !== '价格未知';
  };

  const getWeatherCardStyle = (day: any) => {
    const text = `${day?.dayweather || ''}${day?.nightweather || ''}`;
    const lower = text.toLowerCase();
    if (/雪|snow/.test(lower)) {
      return {
        background: 'linear-gradient(135deg, #83a4d4 0%, #b6fbff 100%)',
        color: '#0d1b2a',
      };
    }
    if (/雨|storm|雷/.test(lower)) {
      return {
        background: 'linear-gradient(135deg, #314755 0%, #26a0da 100%)',
        color: '#f0f8ff',
      };
    }
    if (/阴|云|cloud/.test(lower)) {
      return {
        background: 'linear-gradient(135deg, #bdc3c7 0%, #2c3e50 100%)',
        color: '#f4f8fb',
      };
    }
    if (/晴|sun/.test(lower)) {
      return {
        background: 'linear-gradient(135deg, #f6d365 0%, #fda085 100%)',
        color: '#4a1b00',
      };
    }
    return {
      background: 'linear-gradient(135deg, #a1c4fd 0%, #c2e9fb 100%)',
      color: '#0f172a',
    };
  };

  const previewScrollPosRef = useRef<Record<string, number>>({});

  const PreviewGrid: React.FC<{ data: any[]; renderCard: (item: any, idx: number) => React.ReactNode; emptyText: string; scrollKey: string }> = ({ data, renderCard, emptyText, scrollKey }) => {
    const [visible, setVisible] = useState<number>(12);
    const containerRef = useRef<HTMLDivElement | null>(null);
    const onScroll = (e: React.UIEvent<HTMLDivElement>) => {
      const el = e.currentTarget;
      if (el.scrollTop + el.clientHeight >= el.scrollHeight - 40) {
        setVisible((v) => Math.min(v + 12, data.length));
      }
      previewScrollPosRef.current[scrollKey] = el.scrollTop;
    };
    useEffect(() => {
      const pos = previewScrollPosRef.current[scrollKey] || 0;
      if (containerRef.current) {
        containerRef.current.scrollTop = pos;
      }
    }, [data, scrollKey]);
    if (!Array.isArray(data) || data.length === 0) {
      return <Empty description={emptyText} />;
    }
    const slice = data.slice(0, visible);
    return (
      <div ref={containerRef} style={{ maxHeight: 420, overflowY: 'auto', paddingRight: 8 }} onScroll={onScroll}>
        <Row gutter={[16, 16]}>
          {slice.map((item, idx) => (
            <Col xs={24} sm={12} md={8} lg={6} key={idx}>
              {renderCard(item, idx)}
            </Col>
          ))}
        </Row>
      </div>
    );
  };

  const renderPreviewGrid = (
    data: any[],
    renderCard: (item: any, idx: number) => React.ReactNode,
    emptyText: string,
    scrollKey: string
  ) => {
    return <PreviewGrid data={data} renderCard={renderCard} emptyText={emptyText} scrollKey={scrollKey} />;
  };

  const fetchPlaces = async (q: string, signal?: AbortSignal) => {
    const url = buildApiUrl(`${API_ENDPOINTS.MAP_INPUT_TIPS}?q=${encodeURIComponent(q)}&datatype=all&citylimit=false`);
    const res = await fetch(url, { signal, headers: { Accept: 'application/json' } });
    if (!res.ok) return [] as { value: string; label: React.ReactNode }[];
    const data = await res.json();
    const options = Array.isArray(data?.options) ? data.options : [];
    return options.map((item: any, idx: number) => {
      const main = item?.value || '';
      const sub = item?.district || '';
      return {
        value: item?.value || main,
        key: `${item?.value || ''}-${item?.adcode || ''}-${item?.location || ''}-${idx}`,
        label: (
          <Space direction="vertical" size={0} style={{ lineHeight: 1.2 }}>
            <span style={{ fontWeight: 500 }}>{main}</span>
            {sub && <Text type="secondary" style={{ fontSize: 12 }}>{sub}</Text>}
          </Space>
        ),
      };
    });
  };

  const depFetcher = createDebouncedFetcher(fetchPlaces, setDepOptions, placeCacheRef.current, 300);
  const handleSearchDeparture = (v: string) => depFetcher('dep', v);

  const destFetcher = createDebouncedFetcher(fetchPlaces, setDestOptions, placeCacheRef.current, 300);
  const handleSearchDestination = (v: string) => destFetcher('dest', v);

  // 接收来自首页的表单数据并自动提交
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(buildApiUrl(API_ENDPOINTS.MAP_HEALTH));
        const data = await res.json();
        setTipsEnabled(Boolean(data?.input_tips_enabled));
      } catch {
        setTipsEnabled(true);
      }
    })();
    return () => {
      isMountedRef.current = false;
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    const formData = location.state?.formData;
    if (formData && !hasAutoSubmitted.current) {
      console.log('接收到首页表单数据，自动提交:', formData);
      
      // 处理日期数据：将字符串转换为dayjs对象
      const processedData = { ...formData };
      if (formData.dateRange && Array.isArray(formData.dateRange) && formData.dateRange.length === 2) {
        processedData.dateRange = [
          dayjs(formData.dateRange[0]),
          dayjs(formData.dateRange[1])
        ];
      }
      
      // 预填表单
      form.setFieldsValue(processedData);
      
      // 标记已自动提交，防止重复提交
      hasAutoSubmitted.current = true;
      setAutoSubmitting(true);
      
      setTimeout(() => {
        form.submit();
      }, 100); // 稍微延迟确保表单已渲染
    }
  }, [location.state, form]);

  const steps = [
    {
      title: '填写需求',
      description: '输入您的旅行需求',
      icon: <GlobalOutlined />
    },
    {
      title: 'AI分析',
      description: '智能分析您的需求',
      icon: <LoadingOutlined />
    },
    {
      title: '生成方案',
      description: '为您生成旅行方案',
      icon: <SearchOutlined />
    },
    {
      title: '完成',
      description: '方案生成完成',
      icon: <CheckCircleOutlined />
    }
  ];

  const [previewActiveKey, setPreviewActiveKey] = useState<string>('weather');

  const handleSubmit = async (values: TravelRequest) => {
    setLoading(true);
    setAutoSubmitting(false); // 重置自动提交状态
    setCurrentStep(1);
    
    try {
      // 创建旅行计划
      const specialRequirements = typeof values.requirements === 'string'
        ? values.requirements.trim()
        : '';

      const payload: Record<string, any> = {
        title: (values.departure ? `${values.departure} → ` : '') + `${values.destination} 旅行计划`,
        departure: values.departure || null,
        destination: values.destination,
        start_date: values.dateRange[0].format('YYYY-MM-DD HH:mm:ss'),
        end_date: values.dateRange[1].format('YYYY-MM-DD HH:mm:ss'),
        duration_days: values.dateRange[1].diff(values.dateRange[0], 'day') + 1,
        budget: values.budget,
        transportation: values.transportation,
        preferences: { 
          interests: values.preferences,
          travelers: values.travelers,
          foodPreferences: values.foodPreferences,
          dietaryRestrictions: values.dietaryRestrictions,
          ageGroups: values.ageGroups
        }
      };

      if (specialRequirements) {
        payload.requirements = { special_requirements: specialRequirements };
      }

      const response = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLANS), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error('创建计划失败');
      }

      const plan = await response.json();
      console.log('创建计划响应:', plan);
      
      if (!plan || !plan.id) {
        throw new Error('创建计划响应格式错误');
      }
      
      
      
      // 开始生成方案
      await generatePlans(plan.id, values);
      
    } catch (error) {
      console.error('提交失败:', error);
      setCurrentStep(0);
    } finally {
      setLoading(false);
    }
  };

  const generatePlans = async (planId: number, preferences: TravelRequest) => {
    console.log('开始生成方案:', { planId, preferences });
    setCurrentStep(2);
    setGenerationStatus('generating');
    setPreviewData(null); // 重置预览
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    currentPlanIdRef.current = planId;
    
    try {
      // 处理特殊要求：如果是字符串，转换为字典格式
      const specialRequirements = typeof preferences.requirements === 'string'
        ? preferences.requirements.trim()
        : '';
      
      const requirementsPayload = specialRequirements
        ? { special_requirements: specialRequirements }
        : (typeof preferences.requirements === 'object' && preferences.requirements !== null
          ? preferences.requirements
          : undefined);

      // 启动方案生成
      const response = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_GENERATE(planId)), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preferences: {
            budget_priority: preferences.budget < 3000 ? 'low' : 'medium',
            activity_preference: preferences.preferences || ['culture'],
            travelers: preferences.travelers,
            foodPreferences: preferences.foodPreferences,
            dietaryRestrictions: preferences.dietaryRestrictions,
            ageGroups: preferences.ageGroups
          },
          requirements: requirementsPayload,
          num_plans: 3
        }),
      });

      if (!response.ok) {
        throw new Error('启动方案生成失败');
      }

      // 通过SSE流式订阅状态
      try {
        const res = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_STATUS_STREAM(planId)));
        if (!res.ok || !res.body) {
          await pollGenerationStatus(planId);
          return;
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let finished = false;
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split('\n\n');
          buffer = parts.pop() || '';
          for (const part of parts) {
            const line = part.split('\n').find((l) => l.startsWith('data: '));
            if (!line) continue;
            const jsonStr = line.slice(6);
            try {
              const evt = JSON.parse(jsonStr);
              if (typeof evt.progress === 'number') setProgressIfChanged(evt.progress);
              if (evt.preview) setPreviewDataIfChanged(evt.preview);
              if (evt.status === 'completed') {
                setCurrentStep(3);
                setGenerationStatus('completed');
                setProgress(100);
                setPreviewData(null);
                lastPreviewHashRef.current = null;
                setTimeout(() => navigate(`/plan/${planId}`), 2000);
                finished = true;
                return;
              } else if (evt.status === 'failed') {
                setGenerationStatus('failed');
                finished = true;
                return;
              } else if (evt.status === 'timeout') {
                setGenerationStatus('timeout');
                finished = true;
                return;
              }
            } catch {}
          }
        }
        if (!finished && generationStatus === 'generating') {
          await pollGenerationStatus(planId);
        }
      } catch {
        await pollGenerationStatus(planId);
      }
      
    } catch (error) {
      console.error('生成方案失败:', error);
      setGenerationStatus('failed');
    }
  };

  const pollGenerationStatus = async (planId: number) => {
    let pollCount = 0;
    const maxPolls = 150; // 最大轮询次数：150次 * 6秒 = 15分钟
    pollTimerRef.current = setInterval(async () => {
      if (currentPlanIdRef.current !== planId) {
        if (pollTimerRef.current) {
          clearInterval(pollTimerRef.current);
          pollTimerRef.current = null;
        }
        return;
      }
      try {
        pollCount++;
        console.log(`轮询状态 ${pollCount}/${maxPolls}: 计划 ${planId}`);
        
        const response = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_STATUS(planId)));
        const status = await response.json();
        
        // 如果处于生成中，尝试读取预览
        if (status.status === 'generating') {
        const preview = Array.isArray(status.generated_plans)
          ? status.generated_plans.find((p: any) => p?.is_preview && p?.preview_type === 'raw_data_preview')
          : null;
        if (isMountedRef.current) {
          if (preview) {
            setPreviewDataIfChanged(preview);
          }
        }
        }
        
        // 动态更新进度，基于轮询次数
        const newProgress = Math.min(10 + (pollCount * 0.6), 90);
        if (isMountedRef.current) setProgress(newProgress);
        
        console.log(`状态: ${status.status}, 进度: ${newProgress}%`);
        
        if (status.status === 'completed') {
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
          }
          if (isMountedRef.current) {
            setCurrentStep(3);
            setGenerationStatus('completed');
            setProgress(100);
            setPreviewData(null);
          }
          console.log('方案生成完成！');
          
          // 跳转到方案详情页
          setTimeout(() => {
            navigate(`/plan/${planId}`);
          }, 2000);
        } else if (status.status === 'failed') {
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
          }
          if (isMountedRef.current) setGenerationStatus('failed');
          console.log('方案生成失败');
        } else if (pollCount >= maxPolls) {
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
          }
          if (isMountedRef.current) setGenerationStatus('timeout');
          console.log('轮询超时，已达到最大次数');
        }
      } catch (error) {
        console.error('轮询状态失败:', error);
      }
    }, 6000);
  };

  const getStatusAlert = () => {
    switch (generationStatus) {
      case 'generating':
        return (
          <Alert
            message="正在生成您的专属旅行方案"
            description="AI正在为您分析目的地信息，收集航班、酒店、景点等数据，请稍候..."
            type="info"
            showIcon
            style={{ marginBottom: 24 }}
          />
        );
      case 'completed':
        return (
          <Alert
            message="方案生成完成！"
            description="您的专属旅行方案已生成，即将跳转到详情页面..."
            type="success"
            showIcon
            style={{ marginBottom: 24 }}
          />
        );
      case 'failed':
        return (
          <Alert
            message="方案生成失败"
            description="很抱歉，方案生成过程中出现了问题，请重试。"
            type="error"
            showIcon
            style={{ marginBottom: 24 }}
          />
        );
      case 'timeout':
        return (
          <Alert
            message="生成时间较长"
            description="方案生成时间较长，您可以稍后查看历史记录页面，或重新生成。"
            type="warning"
            showIcon
            style={{ marginBottom: 24 }}
            action={
              <Button 
                size="small" 
                onClick={() => navigate('/history')}
              >
                查看历史记录
              </Button>
            }
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="travel-plan-page" style={{ maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: '40px' }}>
        <Title level={2}>创建您的专属旅行计划</Title>
        <Paragraph style={{ fontSize: '16px', color: '#666' }}>
          请填写您的旅行需求，AI将为您生成个性化的旅行方案
        </Paragraph>
      </div>

      {/* 步骤指示器 */}
      <Card style={{ marginBottom: '24px' }}>
        <Steps current={currentStep} items={steps} />
      </Card>

      {/* 状态提示 */}
      {getStatusAlert()}
      
      {/* 自动提交提示 */}
      {autoSubmitting && (
        <Card style={{ marginBottom: '24px' }}>
          <Alert
            message="正在自动处理您的旅行需求"
            description="检测到您从首页跳转，正在自动提交表单..."
            type="info"
            showIcon
          />
        </Card>
      )}

      {/* 进度条 */}
      {generationStatus === 'generating' && (
        <Card style={{ marginBottom: '24px' }}>
          <div style={{ textAlign: 'center' }}>
            <Progress 
              percent={progress} 
              status="active"
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
              format={(p) => (
                <span style={{ color: '#fff' }}>{(p ?? 0).toFixed(2)}%</span>
              )}
            />
            <Text type="secondary" style={{ marginTop: '8px', display: 'block' }}>
              正在收集数据并生成方案...
            </Text>
          </div>
        </Card>
      )}

      {/* 预览数据展示 */}
      {generationStatus === 'generating' && previewData && (
        <Card 
          title={
            <Space align="center">
              <PictureOutlined />
              <span>{previewData.title || '实时数据预览'}</span>
            </Space>
          }
          style={{ marginBottom: '24px' }}
          bodyStyle={{ padding: isMobile ? '12px' : '24px' }}
        >
          <Tabs
            activeKey={previewActiveKey}
            onChange={(k) => setPreviewActiveKey(String(k))}
            tabPosition={isMobile ? 'top' : 'left'}
            items={[
              {
                key: 'weather',
                label: '天气',
                children: (
                  (() => {
                    const weatherRaw = previewData.sections?.weather;
                    const isArray = Array.isArray(weatherRaw);
                    const weatherObj = isArray ? { location: '', forecast: weatherRaw, recommendations: [] } : weatherRaw;
                    const location = weatherObj?.location;
                    const forecast = Array.isArray(weatherObj?.forecast) ? weatherObj?.forecast : (isArray ? weatherRaw : []);
                    const recommendations = Array.isArray(weatherObj?.recommendations) ? weatherObj?.recommendations : [];
                    const emojiFor = (w?: string) => {
                      const s = (w || '').toLowerCase();
                      if (!s) return '🌤️';
                      if (s.includes('晴')) return '☀️';
                      if (s.includes('云')) return '☁️';
                      if (s.includes('雨')) return '🌧️';
                      if (s.includes('雪')) return '❄️';
                      if (s.includes('雷')) return '⛈️';
                      if (s.includes('阴')) return '☁️';
                      return '🌤️';
                    };
                    return Array.isArray(forecast) && forecast.length ? (
                      <div>
                        {location && (
                          <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
                            目的地：{location}
                          </Text>
                        )}
                        <div style={{ display: 'flex', gap: 12, overflowX: 'auto', paddingBottom: 8 }}>
                          {forecast.map((d: any, idx: number) => {
                            const cardStyle = getWeatherCardStyle(d);
                            return (
                              <div
                                key={idx}
                                style={{
                                  minWidth: isMobile ? 220 : 240,
                                  padding: '16px',
                                  borderRadius: 16,
                                  ...cardStyle,
                                }}
                              >
                                <Text strong style={{ fontSize: 16, color: cardStyle.color || '#fff' }}>
                                  {d?.date || ''}（周{d?.week || ''}）
                                </Text>
                                <div style={{ marginTop: 12, display: 'flex', justifyContent: 'space-between' }}>
                                  <div>
                                  <div>{emojiFor(d?.dayweather)} 日间 {d?.dayweather}</div>
                                  <div>{emojiFor(d?.nightweather)} 夜间 {d?.nightweather}</div>
                                </div>
                                <div style={{ textAlign: 'right' }}>
                                  {d?.daytemp && <div>⬆ {d.daytemp}℃</div>}
                                  {d?.nighttemp && <div>⬇ {d.nighttemp}℃</div>}
                                </div>
                              </div>
                              {(d?.daywind || d?.nightwind) && (
                                <div style={{ marginTop: 8, fontSize: 12 }}>
                                  风向 {d?.daywind || d?.nightwind} / 风力 {d?.daypower || d?.nightpower}
                                </div>
                              )}
                              </div>
                            );
                          })}
                        </div>
                        {recommendations.length ? (
                          <Alert
                            type="info"
                            showIcon
                            message="出行建议"
                            description={recommendations.join('、')}
                            style={{ marginTop: 16 }}
                          />
                        ) : null}
                      </div>
                    ) : <Empty description="暂无天气数据" />;
                  })()
                ),
              },
              
              {
                key: 'hotels',
                label: '酒店',
                children: (
                  renderPreviewGrid(
                    previewData.sections?.hotels || [],
                    (h: any) => {
                      const cover = getImage(h);
                      return (
                        <Card
                          hoverable
                          style={{ borderRadius: 16 }}
                          cover={
                            cover ? (
                              <img src={safeImgSrc(cover)} alt={getTitle(h)} height={160} style={{ objectFit: 'cover', width: '100%' }} loading="lazy" />
                            ) : undefined
                          }
                        >
                          <Space direction="vertical" size={8} style={{ width: '100%' }}>
                            <div style={{ fontWeight: 600 }}>{getTitle(h, '酒店')}</div>
                            <Space size={8} wrap>
                              {h?.rating && <Tag color="gold">评分 {h.rating}</Tag>}
                              {getPrice(h) && <Tag color="orange">{getPrice(h)}</Tag>}
                              {h?.distance && <Tag color="blue">距景点 {h.distance}m</Tag>}
                            </Space>
                            {getDesc(h) && <div style={{ color: '#666' }}>{getDesc(h)}</div>}
                          </Space>
                        </Card>
                      );
                    },
                    "暂无酒店数据",
                    "hotels"
                  )
                ),
              },
              {
                key: 'attractions',
                label: '景点',
                children: (
                  renderPreviewGrid(
                    previewData.sections?.attractions || [],
                    (a: any) => {
                      const cover = getImage(a);
                      const title = getTitle(a, '景点');
                      const desc = getDesc(a);
                      return (
                        <Card
                          hoverable
                          style={{ borderRadius: 16, height: '100%' }}
                          cover={
                            cover ? (
                              <div style={{ position: 'relative', height: 160, overflow: 'hidden' }}>
                                <img src={safeImgSrc(cover)} alt={title} height={160} style={{ objectFit: 'cover', width: '100%' }} loading="lazy" />
                                {a?.rating && (
                                  <Tag color="gold" style={{ position: 'absolute', top: 8, right: 8 }}>
                                    <StarFilled /> {a.rating}
                                  </Tag>
                                )}
                              </div>
                            ) : undefined
                          }
                        >
                          <Space direction="vertical" size={8}>
                            <div style={{ fontWeight: 600 }}>{title}</div>
                            <Space wrap size={6}>
                              {a?.category && <Tag>{a.category}</Tag>}
                              {a?.business_area && <Tag color="green">{a.business_area}</Tag>}
                              {a?.distance && <Tag color="blue">距 {a.distance}m</Tag>}
                              {hasPriceValue(a?.price_range) && <Tag color="orange">{a.price_range}</Tag>}
                            </Space>
                            {a?.address && <Text type="secondary">{a.address}</Text>}
                            {desc && <div style={{ color: '#666' }}>{desc}</div>}
                          </Space>
                        </Card>
                      );
                    },
                    "暂无景点数据",
                    "attractions"
                  )
                ),
              },
              {
                key: 'restaurants',
                label: '餐厅',
                children: (
                  renderPreviewGrid(
                    previewData.sections?.restaurants || [],
                    (r: any) => {
                      const cover = getImage(r);
                      const title = getTitle(r, '餐厅');
                      const desc = getDesc(r);
                      const price = typeof r.price === 'number'
                        ? `约 ¥${r.price}`
                        : (hasPriceValue(r?.price_range) ? r.price_range : getPrice(r));
                      return (
                        <Card
                          hoverable
                          style={{ borderRadius: 16, height: '100%' }}
                          cover={
                            cover ? (
                              <div style={{ position: 'relative', height: 160, overflow: 'hidden' }}>
                                <img src={safeImgSrc(cover)} alt={title} height={160} style={{ objectFit: 'cover', width: '100%' }} loading="lazy" />
                                {r?.rating && (
                                  <Tag color="gold" style={{ position: 'absolute', top: 8, right: 8 }}>
                                    <StarFilled /> {r.rating}
                                  </Tag>
                                )}
                              </div>
                            ) : undefined
                          }
                        >
                          <Space direction="vertical" size={8}>
                            <div style={{ fontWeight: 600 }}>{title}</div>
                            <Space wrap size={6}>
                              {price && <Tag color="orange">{price}</Tag>}
                              {r?.opening_hours && (
                                <Tag icon={<ClockCircleOutlined />} color="green">
                                  {r.opening_hours}
                                </Tag>
                              )}
                              {r?.business_area && <Tag color="green">{r.business_area}</Tag>}
                            </Space>
                            {r?.address && <Text type="secondary">{r.address}</Text>}
                            {Array.isArray(r?.specialties) && r.specialties.length > 0 && (
                              <Space wrap size={4}>
                                {r.specialties.slice(0, 5).map((s: any, idx: number) => (
                                  <Tag key={idx} color="geekblue">
                                    {typeof s === 'string' ? s : (s?.name || s?.dish_name || '特色菜')}
                                  </Tag>
                                ))}
                              </Space>
                            )}
                            {desc && <div style={{ color: '#666' }}>{desc}</div>}
                          </Space>
                        </Card>
                      );
                    },
                    "暂无餐厅数据",
                    "restaurants"
                  )
                ),
              },
              {
                key: 'flights',
                label: '航班',
                children: (
                  (() => {
                    const flights = previewData.sections?.flights || [];
                    if (!Array.isArray(flights) || flights.length === 0) {
                      return <Empty description="暂无航班数据" />;
                    }
                    const onScroll = (e: React.UIEvent<HTMLDivElement>) => {
                      previewScrollPosRef.current["flights"] = e.currentTarget.scrollTop;
                    };
                    const flightsPos = previewScrollPosRef.current["flights"] || 0;
                    return (
                      <div style={{ maxHeight: 420, overflowY: 'auto', paddingRight: 8 }} onScroll={onScroll} ref={(el) => { if (el) el.scrollTop = flightsPos; }}>
                        <Timeline mode={isMobile ? 'left' : 'alternate'}>
                          {flights.map((f: any, idx: number) => (
                            <Timeline.Item key={idx} color="blue">
                              <Card hoverable style={{ borderRadius: 16 }}>
                                <Space direction="vertical" size={6} style={{ width: '100%' }}>
                                  <Space wrap size={8}>
                                    <div style={{ fontWeight: 600 }}>{getTitle(f, '航班')}</div>
                                    {f?.airline && <Tag color="blue">{f.airline}</Tag>}
                                    {f?.flight_no && <Tag>{f.flight_no}</Tag>}
                                    {getPrice(f) && <Tag color="orange">{getPrice(f)}</Tag>}
                                  </Space>
                                  <Space wrap size={12}>
                                    {f?.departure_time && <Tag color="green">出发 {f.departure_time}</Tag>}
                                    {f?.arrival_time && <Tag color="green">到达 {f.arrival_time}</Tag>}
                                  </Space>
                                  {getDesc(f) && <div style={{ color: '#666' }}>{getDesc(f)}</div>}
                                </Space>
                              </Card>
                            </Timeline.Item>
                          ))}
                        </Timeline>
                      </div>
                    );
                  })()
                ),
              },
              {
                key: 'xhs',
                label: '小红书',
                children: (
                  renderPreviewGrid(
                    previewData.sections?.xiaohongshu_notes || [],
                    (item: any) => {
                      const cover = getImage(item);
                      const title = getTitle(item);
                      const desc = getDesc(item);
                      const likes = getLikes(item);
                      const tags = Array.isArray(item?.tag_list) ? item.tag_list.slice(0, 5) : [];
                      const location = item?.location;
                      return (
                        <Card
                          hoverable
                          style={{ borderRadius: 16, height: '100%' }}
                          cover={
                            cover ? (
                              <div style={{ position: 'relative', height: 160, overflow: 'hidden' }}>
                                <img src={safeImgSrc(cover)} alt={title} height={160} style={{ objectFit: 'cover', width: '100%' }} loading="lazy" />
                                {typeof likes === 'number' && (
                                  <Tag color="magenta" style={{ position: 'absolute', top: 8, right: 8 }}>
                                    <HeartOutlined /> {likes}
                                  </Tag>
                                )}
                              </div>
                            ) : undefined
                          }
                        >
                          <Space direction="vertical" size={8} style={{ width: '100%' }}>
                            <Tooltip title={title}>
                              <div
                                style={{
                                  fontWeight: 600,
                                  lineHeight: 1.4,
                                  display: '-webkit-box',
                                  WebkitLineClamp: 2,
                                  WebkitBoxOrient: 'vertical',
                                  overflow: 'hidden',
                                }}
                              >
                                {title}
                              </div>
                            </Tooltip>
                            {tags.length > 0 && (
                              <Space wrap size={4}>
                                {tags.map((t: string) => (
                                  <Tag key={t} color="geekblue">
                                    {t}
                                  </Tag>
                                ))}
                              </Space>
                            )}
                            {location && (
                              <Tag icon={<EnvironmentOutlined />} color="green">
                                {location}
                              </Tag>
                            )}
                            {desc && (
                              <div
                                style={{
                                  color: '#666',
                                  display: '-webkit-box',
                                  WebkitLineClamp: 3,
                                  WebkitBoxOrient: 'vertical',
                                  overflow: 'hidden',
                                }}
                              >
                                {desc}
                              </div>
                            )}
                            {item?.url && (
                              <Button size="small" type="link" href={item.url} target="_blank" icon={<LinkOutlined />}>
                                查看原文
                              </Button>
                            )}
                          </Space>
                        </Card>
                      );
                    },
                    "暂无小红书数据",
                    "xhs"
                  )
                ),
              },
            ]}
          />
        </Card>
      )}

      {/* 表单 */}
      {currentStep === 0 && (
        <Card 
          title={
            <Space>
              <GlobalOutlined />
              旅行需求
            </Space>
          }
          style={{ 
            borderRadius: '12px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
          }}
        >
          <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmit}
            size="large"
            initialValues={{
              travelers: 2,
              foodPreferences: [],
              dietaryRestrictions: [],
              ageGroups: []
            }}
          >
            <Row gutter={[24, 16]}>
              <Col xs={24} sm={12}>
                <Form.Item
                  name="departure"
                  label="出发地"
                >
                  {tipsEnabled ? (
                    <AutoComplete
                      options={depOptions}
                      onSearch={handleSearchDeparture}
                      onSelect={(val) => form.setFieldsValue({ departure: val })}
                      onChange={(val) => form.setFieldsValue({ departure: val })}
                      filterOption={false}
                      style={{ width: '100%' }}
                    >
                      <Input placeholder="请输入出发地" prefix={<GlobalOutlined />} />
                    </AutoComplete>
                  ) : (
                    <Input
                      placeholder="请输入出发地"
                      prefix={<GlobalOutlined />}
                      value={form.getFieldValue('departure')}
                      onChange={(e) => form.setFieldsValue({ departure: e.target.value })}
                    />
                  )}
                </Form.Item>
              </Col>
              
              <Col xs={24} sm={12}>
                <Form.Item
                  name="destination"
                  label="目的地"
                  rules={[
                    { required: true, message: '请输入目的地' },
                    {
                      validator: (_, value) => {
                        if (typeof value === 'string' && value.trim().length > 0) return Promise.resolve();
                        return Promise.reject(new Error('请输入目的地'));
                      }
                    }
                  ]}
                >
                  {tipsEnabled ? (
                    <AutoComplete
                      options={destOptions}
                      onSearch={handleSearchDestination}
                      onSelect={(val) => form.setFieldsValue({ destination: val })}
                      onChange={(val) => form.setFieldsValue({ destination: val })}
                      filterOption={false}
                      style={{ width: '100%' }}
                    >
                      <Input placeholder="请输入目的地" prefix={<GlobalOutlined />} />
                    </AutoComplete>
                  ) : (
                    <Input
                      placeholder="请输入目的地"
                      prefix={<GlobalOutlined />}
                      value={form.getFieldValue('destination')}
                      onChange={(e) => form.setFieldsValue({ destination: e.target.value })}
                    />
                  )}
                </Form.Item>
              </Col>
            </Row>
            
            <Row gutter={[24, 16]}>
              <Col xs={24} sm={12} style={{ minWidth: 0 }}>
                <Form.Item
                  name="dateRange"
                  label="出行时间"
                  rules={[
                    { required: true, message: '请选择出行时间' },
                    {
                      validator: (_, value) => {
                        if (!value || value.length !== 2) return Promise.resolve();
                        const days = value[1].diff(value[0], 'day') + 1;
                        if (days > 10) {
                          return Promise.reject(new Error('单次旅行时间不能超过 10 天'));
                        }
                        return Promise.resolve();
                      },
                    },
                  ]}
                >
                  <RangePicker 
                    className="mobile-vertical-range"
                    popupClassName="mobile-vertical-range-dropdown"
                    style={{ width: '100%', minWidth: 0 }}
                    placeholder={["出发日期", "返回日期"]}
                  />
                </Form.Item>
              </Col>
              
              <Col xs={24} sm={12}>
                <Form.Item
                  name="travelers"
                  label="出行人数"
                  rules={[{ required: true, message: '请选择出行人数' }]}
                >
                  <InputNumber
                    min={1}
                    max={200}
                    style={{ width: '100%' }}
                    placeholder="请输入出行人数"
                    prefix={<UserOutlined />}
                    addonAfter="人"
                  />
                </Form.Item>
              </Col>
            </Row>
            
            <Row gutter={[24, 16]}>
              <Col xs={24} sm={12}>
                <Form.Item
                  name="budget"
                  label={
                    <span>
                      总预算范围
                      <Tooltip title="这是整个行程的总预算，系统会自动分配：30-35%用于航班和酒店，65-70%用于每日餐饮、景点和交通">
                        <span style={{ marginLeft: 4, color: '#1890ff', cursor: 'help' }}>ℹ️</span>
                      </Tooltip>
                    </span>
                  }
                  rules={[{ required: true, message: '请选择预算范围' }]}
                >
                  <Select placeholder="选择总预算范围">
                    <Option value={200}>200元以下</Option>
                    <Option value={500}>500元以下</Option>
                    <Option value={1000}>1000元以下</Option>
                    <Option value={3000}>1000-3000元</Option>
                    <Option value={5000}>3000-5000元</Option>
                    <Option value={10000}>5000-10000元</Option>
                    <Option value={20000}>10000元以上</Option>
                    <Option value={30000}>20000-30000元</Option>
                    <Option value={50000}>50000元以上</Option>
                  </Select>
                </Form.Item>
              </Col>
              
              <Col xs={24} sm={12}>
                <Form.Item
                  name="transportation"
                  label="出行方式"
                >
                  <Select placeholder="请选择出行方式（可选）" allowClear options={TRANSPORTATION_OPTIONS} />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={[24, 16]}>
              <Col xs={24} sm={12}>
                <Form.Item name="preferences" label="旅行偏好">
                  <Select 
                    mode="multiple" 
                    placeholder="选择您的旅行偏好"
                    allowClear
                    options={PREFERENCES_OPTIONS}
                  />
                </Form.Item>
              </Col>

              <Col xs={24} sm={12}>
                <Form.Item name="ageGroups" label="年龄组成">
                  <Select 
                    mode="multiple" 
                    placeholder="选择出行人员年龄组成"
                    allowClear
                    options={AGE_GROUP_OPTIONS}
                  />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={[24, 16]}>
              <Col xs={24} sm={12}>
                <Form.Item name="foodPreferences" label="口味偏好">
                  <Select 
                    mode="multiple" 
                    placeholder="选择您的口味偏好"
                    allowClear
                    options={FOOD_PREFERENCES_OPTIONS}
                  />
                </Form.Item>
              </Col>

              <Col xs={24} sm={12}>
                <Form.Item name="dietaryRestrictions" label="忌口/饮食限制">
                  <Select 
                    mode="multiple" 
                    placeholder="选择忌口或饮食限制"
                    allowClear
                    options={DIETARY_RESTRICTIONS_OPTIONS}
                  />
                </Form.Item>
              </Col>
            </Row>
            
            <Form.Item name="requirements" label="特殊要求">
              <Input.TextArea 
                placeholder="请输入特殊要求（如：带老人、带小孩、无障碍设施、特殊饮食需求等）"
                rows={3}
              />
            </Form.Item>
            
            <Form.Item>
              <Button 
                type="primary" 
                htmlType="submit" 
                loading={loading}
                icon={<SearchOutlined />}
                size="large"
                style={{ 
                  width: '100%',
                  height: '48px',
                  borderRadius: '8px'
                }}
              >
                {loading ? '正在创建计划...' : '开始生成方案'}
              </Button>
            </Form.Item>
          </Form>
        </Card>
      )}

      {/* 生成中状态 */}
      {currentStep > 0 && currentStep < 3 && (
        <Card style={{ textAlign: 'center', padding: '40px' }}>
          <Spin size="large" />
          <div style={{ marginTop: '16px' }}>
            <Title level={4}>
              {currentStep === 1 && '正在分析您的需求...'}
              {currentStep === 2 && '正在生成旅行方案...'}
            </Title>
            <Paragraph>
              {currentStep === 1 && 'AI正在理解您的旅行偏好和需求'}
              {currentStep === 2 && '正在收集航班、酒店、景点等信息，为您生成最佳方案'}
            </Paragraph>
          </div>
        </Card>
      )}

      {/* 完成状态 */}
      {currentStep === 3 && (
        <Card style={{ textAlign: 'center', padding: '40px' }}>
          <CheckCircleOutlined style={{ fontSize: '64px', color: '#52c41a', marginBottom: '16px' }} />
          <Title level={3} style={{ color: '#52c41a' }}>
            方案生成完成！
          </Title>
          <Paragraph>
            您的专属旅行方案已生成，即将跳转到详情页面查看完整方案。
          </Paragraph>
        </Card>
      )}
    </div>
  );
};

export default TravelPlanPage;
