import React, { useState, useRef, useEffect } from 'react';
import { FloatButton, Modal, Input, Button, List, Avatar, Spin, Space, Typography, message, Card, Select, DatePicker, TimePicker, Descriptions, Tag, Divider } from 'antd';
import { MessageOutlined, SendOutlined, RobotOutlined, UserOutlined, CalendarOutlined, EnvironmentOutlined, StarOutlined, ShopOutlined, HomeOutlined, FlagOutlined } from '@ant-design/icons';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';
import { authFetch } from '../../utils/auth';
import './AIAssistant.css';

const { TextArea } = Input;
const { Text } = Typography;

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  sources?: Array<{ title?: string; content?: string; score?: number }>;
  entities?: Array<{ type: string; name: string; icon: string }>;
}

// RAG API 端点
const RAG_API_URL = 'http://localhost:8000/api/rag';

// 实体类型配置
const ENTITY_CONFIG = {
  attraction: { label: '景点', icon: '🏛️', color: '#52c41a' },
  restaurant: { label: '餐馆', icon: '🍜', color: '#fa8c16' },
  hotel: { label: '酒店', icon: '🏨', color: '#1890ff' }
};

interface RecommendationItem {
  name: string;
  type: string;
  icon: string;
  summary: string;
}

const AIAssistant: React.FC = () => {
  const [visible, setVisible] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [plans, setPlans] = useState<any[]>([]);
  const [addModalVisible, setAddModalVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedEntity, setSelectedEntity] = useState<any | null>(null);
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [attractionDetail, setAttractionDetail] = useState<any | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<any>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (visible) {
      scrollToBottom();
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }
  }, [visible, messages]);

  useEffect(() => {
    const handleSetContext = (event: CustomEvent) => {
      const { context, openModal = true } = event.detail || {};
      if (context) {
        const initialMessages: Message[] = [
          {
            role: 'assistant',
            content: context,
            timestamp: Date.now()
          }
        ];
        setMessages(initialMessages);
        if (openModal) {
          setVisible(true);
        }
      }
    };

    window.addEventListener('ai-assistant:set-context', handleSetContext as EventListener);
    return () => {
      window.removeEventListener('ai-assistant:set-context', handleSetContext as EventListener);
    };
  }, []);

  const getLastAssistantIndex = (messagesList: Message[]): number => {
    for (let i = messagesList.length - 1; i >= 0; i--) {
      if (messagesList[i].role === 'assistant') {
        return i;
      }
    }
    return -1;
  };

  const normalizeSourceAsEntity = (source: any) => {
    let name = source?.title || source?.name || '';
    let type = source?.type || 'attraction';
    
    // 如果名称太短或明显不是实体名，尝试从内容中提取
    if (name.length <= 2 || ['哎呀', '哈哈', '对了', '嗯嗯'].includes(name)) {
      if (source?.content) {
        const contentExtract = source.content.match(/(?:推荐|去|在)([\u4e00-\u9fa5]{2,20}(?:烤鸭|小吃|炸酱面|卤煮|餐厅|饭馆|酒店|景点|公园))/);
        if (contentExtract) {
          name = contentExtract[1];
        }
      }
    }
    
    return {
      name: name || '推荐地点',
      type: type || inferEntityType(name),
      icon: source?.icon || getEntityIcon(type),
      content: source?.content || '',
      score: source?.score,
    };
  };

  const getEntityIcon = (type: string): string => {
    switch (type) {
      case 'restaurant': return '🍜';
      case 'hotel': return '🏨';
      default: return '🏛️';
    }
  };

  const inferEntityType = (text: string): string => {
    if (/(酒店|民宿|住宿|客栈)/.test(text)) return 'hotel';
    if (/(饭馆|餐馆|餐厅|小吃|烤鸭|火锅|海鲜|奶酪|小龙虾|夜宵|美食|吃|炒肝|豌豆黄|驴打滚|双皮奶|面|店)/.test(text)) {
      return 'restaurant';
    }
    if (/(景点|公园|寺|庙|故宫|长城|博物馆|胡同|广场|巷|山|湖|园)/.test(text)) return 'attraction';
    return 'attraction';
  };

  const extractRecommendationsFromContent = (content: string): RecommendationItem[] => {
    // 1. 先尝试用正则提取被标记的实体
    const markedEntities: RecommendationItem[] = [];
    
    // 提取景点标记
    const attractionRegex = /\[景点\](.*?)\[\/?景点\]/g;
    let match;
    while ((match = attractionRegex.exec(content)) !== null) {
      const name = match[1].trim();
      if (name && name.length > 1 && !markedEntities.some(e => e.name === name)) {
        markedEntities.push({
          name,
          type: 'attraction',
          icon: '🏛️',
          summary: `推荐景点：${name}`
        });
      }
    }
    
    // 提取餐馆标记
    const restaurantRegex = /\[餐馆\](.*?)\[\/?餐馆\]/g;
    while ((match = restaurantRegex.exec(content)) !== null) {
      const name = match[1].trim();
      if (name && name.length > 1 && !markedEntities.some(e => e.name === name)) {
        markedEntities.push({
          name,
          type: 'restaurant',
          icon: '🍜',
          summary: `推荐餐馆：${name}`
        });
      }
    }
    
    // 提取酒店标记
    const hotelRegex = /\[酒店\](.*?)\[\/?酒店\]/g;
    while ((match = hotelRegex.exec(content)) !== null) {
      const name = match[1].trim();
      if (name && name.length > 1 && !markedEntities.some(e => e.name === name)) {
        markedEntities.push({
          name,
          type: 'hotel',
          icon: '🏨',
          summary: `推荐酒店：${name}`
        });
      }
    }
    
    // 如果有标记实体，直接返回
    if (markedEntities.length > 0) {
      return markedEntities;
    }
    
    // 2. 如果没有标记，使用改进的自然语言提取
    const textRecs: RecommendationItem[] = [];
    const extractedNames = new Set<string>();
    
    // 已知的实体名称列表（优先匹配）
    const knownEntities = [
      '全聚德', '四季民福', '护国寺小吃', '方砖厂69号', '方砖厂',
      '胡大饭馆', '胡大', '门框胡同百年卤煮', '门框胡同',
      '故宫', '南锣鼓巷', '簋街', '天安门', '长城', '颐和园',
      '炸酱面', '烤鸭', '卤煮', '豆汁', '驴打滚', '豌豆黄',
      '河沿肉饼', '大董烤鸭', '便宜坊', '都一处', '姚记炒肝'
    ];
    
    // 先检查已知实体
    for (const name of knownEntities) {
      if (content.includes(name) && !extractedNames.has(name)) {
        extractedNames.add(name);
        
        let type = 'attraction';
        if (/(烤鸭|小吃|炸酱面|卤煮|火锅|餐厅|饭馆|饭店|美食|豆汁|驴打滚|豌豆黄|炒肝|肉饼)/.test(name)) {
          type = 'restaurant';
        } else if (/(酒店|民宿|住宿|客栈|旅馆)/.test(name)) {
          type = 'hotel';
        }
        
        textRecs.push({
          name,
          type,
          icon: getEntityIcon(type),
          summary: `推荐${ENTITY_CONFIG[type as keyof typeof ENTITY_CONFIG]?.label || '地点'}：${name}`
        });
      }
    }
    
    // 如果没有找到已知实体，尝试正则匹配
    if (textRecs.length === 0) {
      const patterns = [
        /\d+[\.、\s]+(?:必打卡|推荐|必去|一定要|安利|试试|尝尝|记得去|可以去|建议去)(?:的|是|当然)?\s*([\u4e00-\u9fa5a-zA-Z0-9·•\-]{2,20})/g,
        /(?:早餐|午餐|晚餐|夜宵)?(?:推荐|必去|一定要|安利|试试|尝尝|记得去|可以去)(?:的|是)?\s*([\u4e00-\u9fa5a-zA-Z0-9·•\-]{2,20})/g,
      ];
      
      for (const pattern of patterns) {
        let match;
        while ((match = pattern.exec(content)) !== null) {
          const name = match[1].trim();
          if (name && 
              name.length >= 2 && 
              !extractedNames.has(name) &&
              !['哎呀', '哈哈', '对了', '嗯嗯', '嘿嘿', '嘻嘻', '哦哦', '当然', '必打卡'].includes(name)) {
            
            extractedNames.add(name);
            const type = inferEntityType(name);
            
            textRecs.push({
              name,
              type,
              icon: getEntityIcon(type),
              summary: `推荐：${name}`
            });
          }
        }
      }
    }
    
    return textRecs.slice(0, 8);
  };

  // 在 AIAssistant 组件内部添加以下代码（放在其他函数附近，比如 extractRecommendationsFromContent 之后）

// 地理编码 - 通过后端 API 获取目的地坐标
const geocodeDestination = async (address: string): Promise<{ lat: number; lng: number; formattedAddress?: string } | null> => {
  if (!address) return null;

  try {
    const res = await fetch(buildApiUrl(`/map/geocode?address=${encodeURIComponent(address)}`));
    const data = await res.json();
    if (data.status === 'ok' && data.lng && data.lat) {
      return { 
        lng: data.lng, 
        lat: data.lat,
        formattedAddress: data.formatted_address || data.name || address
      };
    }
  } catch (e) {
    console.error('地理编码失败:', e);
  }
  return null;
};

// 批量地理编码 - 为实体列表添加坐标信息
const enrichEntitiesWithCoordinates = async (entities: Array<{ type: string; name: string; icon: string }>) => {
  if (!entities || entities.length === 0) return entities;
  
  const enrichedEntities = [];
  
  for (const entity of entities) {
    try {
      // 尝试获取坐标
      const coords = await geocodeDestination(entity.name);
      
      enrichedEntities.push({
        ...entity,
        coordinates: coords ? { lat: coords.lat, lng: coords.lng } : null,
        address: coords?.formattedAddress || entity.name,
        hasCoordinates: !!coords
      });
      
      // 添加小延迟避免请求过快
      await new Promise(resolve => setTimeout(resolve, 100));
      
    } catch (error) {
      console.error(`获取 ${entity.name} 坐标失败:`, error);
      enrichedEntities.push({
        ...entity,
        coordinates: null,
        address: entity.name,
        hasCoordinates: false
      });
    }
  }
  
  return enrichedEntities;
};

  const openEntityDetail = (entity: any) => {
    const normalized = normalizeSourceAsEntity(entity);
    setSelectedEntity(normalized);
    setDetailModalVisible(true);
    setDetailLoading(false);
    setAttractionDetail({
      name: normalized.name,
      description: normalized.content || `关于「${normalized.name}」的详细信息...`,
      address: entity?.address || normalized.content?.match(/地址[：:]([^\n]+)/)?.[1]?.trim() || '暂无地址信息',
      coordinates: entity?.coordinates || null,
      type: normalized.type,
      tags: typeof normalized.score === 'number' ? [`匹配度 ${Math.round(normalized.score * 100)}%`] : []
    });
  };

const handleSend = async () => {
  if (!inputValue.trim() || loading) return;

  const userMessage: Message = {
    role: 'user',
    content: inputValue.trim(),
    timestamp: Date.now()
  };

  const newMessages = [...messages, userMessage];
  setMessages(newMessages);
  setInputValue('');
  setLoading(true);

  const assistantMessage: Message = {
    role: 'assistant',
    content: '',
    timestamp: Date.now() + 1
  };
  setMessages([...newMessages, assistantMessage]);

  try {
    const conversationHistory = messages.slice(-6).map(msg => ({
      role: msg.role,
      content: msg.content
    }));

    const response = await fetch(`${RAG_API_URL}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: userMessage.content,
        conversation_history: conversationHistory
      }),
    });
   
    if (!response.ok) {
      throw new Error(`请求失败 (${response.status})`);
    }

    const data = await response.json();

    // 【修改】不在回答后立即获取坐标，仅标记为待获取
    let entities = data.entities || [];
    if (entities.length > 0) {
      entities = entities.map((entity: any) => ({
        ...entity,
        coordinates: null,
        address: entity.name,
        hasCoordinates: false,
        coordinatesStatus: 'pending',
      }));
      console.log(`📋 发现 ${entities.length} 个实体，等待加入行程时获取坐标`);
    }

    setMessages(prev => {
      const updated = [...prev];
      const targetIndex = getLastAssistantIndex(updated);
      if (targetIndex !== -1) {
        updated[targetIndex] = {
          ...updated[targetIndex],
          content: data.answer || '无法获取回答',
          sources: data.sources || [],
            entities: entities,
        };
      }
      return updated;
    });

    if (data.sources && data.sources.length > 0) {
      message.info(`基于 ${data.sources.length} 条小红书攻略回答`, 2);
    }

  } catch (error: any) {
    console.error('AI对话失败:', error);
    message.error(error.message || 'AI对话失败，请稍后重试');
    
    setMessages(prev => {
      const updated = [...prev];
      const targetIndex = getLastAssistantIndex(updated);
      if (targetIndex !== -1) {
        updated[targetIndex] = {
          ...updated[targetIndex],
          content: `抱歉，遇到问题：${error.message || '未知错误'}`
        };
      }
      return updated;
    });
  } finally {
    setLoading(false);
  }
};

  const handleClear = () => {
    setMessages([]);
    message.success('对话已清空');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 渲染消息内容
  const renderMessageContent = (message: Message) => {
    const { content, entities } = message;
    const sources = message.sources || [];
    const textRecommendations = (!entities || entities.length === 0)
      ? extractRecommendationsFromContent(content)
      : [];

    return (
      <div className="ai-message-text">
        <div className="ai-message-content-text">{content}</div>

        {entities && entities.length > 0 && (
          <div className="ai-entities-section">
            <Divider className="ai-section-divider" />
            <Text type="secondary">📌 可加入行程：</Text>
            <div className="ai-entities-list">
              {entities.map((entity: any, idx: number) => {
                const config = ENTITY_CONFIG[entity.type as keyof typeof ENTITY_CONFIG];
                return (
                  <Card
                    key={idx}
                    size="small"
                    className="ai-entity-card"
                    style={{ borderLeft: `4px solid ${config?.color || '#6366f1'}` }}
                  >
                    <Space wrap>
                      <span className="ai-entity-icon">{entity.icon}</span>
                      <Text strong>{entity.name}</Text>
                      <Tag color={config?.color || 'default'}>{config?.label || entity.type}</Tag>
                      
                      <Button
                        type="link"
                        size="small"
                        icon={<CalendarOutlined />}
                        onClick={() => {
                          setSelectedEntity({
                            ...entity,
                            coordinates: entity.coordinates,
                            address: entity.address
                          });
                          setAddModalVisible(true);
                        }}
                      >
                        加入行程
                      </Button>
                      <Button
                        type="link"
                        size="small"
                        onClick={() => openEntityDetail({
                          ...entity,
                          coordinates: entity.coordinates,
                          address: entity.address
                        })}
                      >
                        查看详情
                      </Button>
                    </Space>
                  </Card>
                );
              })}
            </div>
          </div>
        )}

        {sources.length > 0 && (
          <div className="ai-sources-section">
            <Divider className="ai-section-divider" />
            <Text type="secondary">📚 参考来源：{sources.length} 条小红书攻略</Text>
            <div className="ai-sources-grid">
              {sources.map((source, idx: number) => {
                const score = typeof source.score === 'number' ? Math.round(source.score * 100) : null;
                return (
                  <Card
                    key={idx}
                    size="small"
                    className="ai-source-card"
                    title={source.title || '景点推荐'}
                    extra={score !== null ? <Tag color="blue">匹配度 {score}%</Tag> : null}
                  >
                    <div className="ai-source-snippet">{source.content || '暂无摘要'}</div>
                    <div className="ai-source-actions">
                      <Button size="small" onClick={() => openEntityDetail(source)}>
                        查看详情
                      </Button>
                      <Button
                        type="primary"
                        size="small"
                        icon={<CalendarOutlined />}
                        onClick={() => {
                          setSelectedEntity(normalizeSourceAsEntity(source));
                          setAddModalVisible(true);
                        }}
                      >
                        加入行程
                      </Button>
                    </div>
                  </Card>
                );
              })}
            </div>
          </div>
        )}

        {textRecommendations.length > 0 && (
          <div className="ai-text-rec-section">
            <Divider className="ai-section-divider" />
            <Text type="secondary">🧭 可加入行程的推荐：</Text>
            <div className="ai-text-rec-grid">
              {textRecommendations.map((rec: RecommendationItem, idx: number) => {
                const config = ENTITY_CONFIG[rec.type as keyof typeof ENTITY_CONFIG];
                return (
                  <Card key={idx} size="small" className="ai-text-rec-card">
                    <div className="ai-text-rec-top">
                      <Space align="start" size={10} wrap>
                        <span className="ai-text-rec-icon">{rec.icon}</span>
                        <div>
                          <div className="ai-text-rec-title">{rec.name}</div>
                          <Tag color={config?.color || 'default'}>{config?.label || rec.type}</Tag>
                        </div>
                      </Space>
                    </div>
                    <div className="ai-text-rec-summary">{rec.summary}</div>
                    <div className="ai-source-actions">
                      <Button size="small" onClick={() => openEntityDetail(rec)}>
                        查看详情
                      </Button>
                      <Button
                        type="primary"
                        size="small"
                        icon={<CalendarOutlined />}
                        onClick={() => {
                          setSelectedEntity(rec);
                          setAddModalVisible(true);
                        }}
                      >
                        加入行程
                      </Button>
                    </div>
                  </Card>
                );
              })}
            </div>
          </div>
        )}
      </div>
    );
  };

  // ... rest of the component (fetchPlans, handleAddToPlan, extractPlaceAndCity, etc.)
  // Keep all the existing functions exactly as they are
  
  const fetchPlans = async () => {
    try {
      const res = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLANS + '?limit=100'));
      if (!res.ok) throw new Error('获取行程失败');
      const data = await res.json();
      const list = Array.isArray(data) ? data : data.plans || [];
      setPlans(list);
    } catch (err: any) {
      console.warn('加载行程失败', err);
      setPlans([]);
    }
  };

  useEffect(() => {
    if (addModalVisible) {
      (async () => {
        await fetchPlans();

        const lastUserMsg = messages.slice().reverse().find(m => m.role === 'user');
        const contextTexts = [selectedEntity?.name, selectedEntity?.content, lastUserMsg?.content].filter(Boolean).join('\n');
        const { placeName, city } = extractPlaceAndCity(contextTexts || selectedEntity?.name || '');

        if (city) {
          const matched = (plans || []).filter(p => {
            const dest = (p.destination || '').toString();
            const cities = Array.isArray(p.cities) ? p.cities : (typeof p.cities === 'string' && p.cities ? [p.cities] : []);
            return dest === city || cities.includes(city);
          });
          if (matched.length > 0) {
            setSelectedPlanId(matched[0].id);
          }
        }

        if (!selectedEntity && placeName) {
          setSelectedEntity({ name: placeName, type: inferEntityType(placeName) });
        }
      })();
    }
  }, [addModalVisible]);

  const handleAddToPlan = async () => {
    if (!selectedEntity) return;
    setAdding(true);
    try {
      const lastUserMsg = messages.slice().reverse().find(m => m.role === 'user');
      const contextTexts = [selectedEntity?.name, selectedEntity?.content, lastUserMsg?.content].filter(Boolean).join('\n');
      const { placeName, city } = extractPlaceAndCity(contextTexts || selectedEntity?.name || '');

      let targetPlanId = selectedPlanId;
      if (!targetPlanId && city) {
        const matched = (plans || []).filter(p => {
          const dest = (p.destination || '').toString();
          const cities = Array.isArray(p.cities) ? p.cities : (typeof p.cities === 'string' && p.cities ? [p.cities] : []);
          return dest === city || cities.includes(city);
        });
        if (matched.length > 0) {
          targetPlanId = matched[0].id;
        }
      }

      if (!targetPlanId) {
        const today = new Date();
        const y = today.getFullYear();
        const m = String(today.getMonth() + 1).padStart(2, '0');
        const d = String(today.getDate()).padStart(2, '0');
        const startDate = `${y}-${m}-${d}`;

        const createData: any = {
          title: city ? `${city} 行程` : (selectedEntity.name || '新建行程'),
          destination: city || (selectedEntity.name || '未知目的地'),
          start_date: startDate,
          end_date: startDate,
          duration_days: 1,
        };

        const createRes = await authFetch(buildApiUrl('/travel-plans/'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(createData),
        });
        if (!createRes.ok) {
          const err = await createRes.json().catch(() => ({}));
          throw new Error(err.detail || '创建新行程失败');
        }
        const newPlan = await createRes.json();
        targetPlanId = newPlan.id;
      }

      // 【修改】优先使用实体已有的坐标
      let coords = selectedEntity.coordinates || null;
      let address = selectedEntity.address || undefined;
      
      // 如果没有坐标，尝试通过后端搜索获取
      if (!coords) {
        try {
          const keyword = placeName || selectedEntity.name;
          const searchBody = { keyword, city: city || undefined, category: selectedEntity?.type || undefined, page_size: 5 };
          const searchRes = await authFetch(buildApiUrl('/locations/search'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(searchBody),
          });
          if (searchRes.ok) {
            const searchData = await searchRes.json();
            const first = (searchData.results || [])[0];
            if (first && first.location) {
              coords = { lat: first.location.lat, lng: first.location.lng };
              address = first.address || first.name;
            }
          }
        } catch (err) {
          console.warn('地点搜索失败', err);
        }
        
        // 如果搜索也失败，最后尝试直接地理编码
        if (!coords) {
          try {
            const geoResult = await geocodeDestination(placeName || selectedEntity.name);
            if (geoResult) {
              coords = { lat: geoResult.lat, lng: geoResult.lng };
              address = geoResult.formattedAddress || address;
            }
          } catch (err) {
            console.warn('地理编码也失败', err);
          }
        }
      }

      let startTime = null;
      if (selectedDate) {
        startTime = selectedTime ? `${selectedDate}T${selectedTime}` : `${selectedDate}T09:00:00`;
      }

      const payload: any = {
        title: placeName || selectedEntity.name,
        description: `来自AI推荐：${selectedEntity.name}${address ? `\n地址：${address}` : ''}`,
        item_type: ['restaurant', 'hotel', 'attraction'].includes(selectedEntity.type)
          ? selectedEntity.type
          : 'attraction',
      };
      if (startTime) payload.start_time = startTime;
      if (coords) {
        payload.coordinates = coords;
      }
      if (address) payload.address = address;

      const res = await authFetch(buildApiUrl(`/travel-plans/${targetPlanId}/items`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        throw new Error(`添加失败 (${res.status})`);
      }
      message.success(`「${payload.title}」${coords ? '（已定位）' : ''}已加入行程`);

      window.dispatchEvent(new CustomEvent('ai-assistant:plan-updated', {
        detail: { planId: targetPlanId, timestamp: Date.now() }
      }));

      setAddModalVisible(false);
      setSelectedEntity(null);
      setSelectedPlanId(null);
      setSelectedDate(null);
      setSelectedTime(null);
    } catch (err: any) {
      console.error('加入行程失败', err);
      message.error(err.message || '加入行程失败');
    } finally {
      setAdding(false);
    }
  };

  const extractPlaceAndCity = (text: string) => {
    if (!text) return { placeName: '', city: '' };
    const firstLine = text.split(/\n+/)[0].trim();
    let placeName = firstLine.split(/[，。！？,;；\.]/)[0].trim();

    let city = '';
    const cityRegex = /在([\u4e00-\u9fa5\w\s]{2,8}?市)|去([\u4e00-\u9fa5\w\s]{2,8}?市)|([\u4e00-\u9fa5]{2,8}?市)|([\u4e00-\u9fa5]{2,8}?省)|香港|澳门|台北|台中|台南/;
    const m = text.match(cityRegex);
    if (m) {
      city = (m[1] || m[2] || m[3] || m[4] || m[0] || '').replace(/^在|去/, '').trim();
      city = city.replace(/[市省]$/, '');
    } else {
      const parenMatch = text.match(/(.+)（([\u4e00-\u9fa5]{2,8})）/);
      if (parenMatch) {
        placeName = parenMatch[1].trim();
        city = parenMatch[2].trim();
      } else {
        const dotMatch = firstLine.match(/^([\u4e00-\u9fa5]{2,10})[·.-]/);
        if (dotMatch) {
          city = dotMatch[1];
        }
      }
    }

    return { placeName, city };
  };

  return (
    <>
      <FloatButton
        icon={<MessageOutlined />}
        type="primary"
        style={{ right: 24, bottom: 24, width: 56, height: 56 }}
        onClick={() => setVisible(true)}
      />

      <Modal
        title={
          <Space>
            <RobotOutlined style={{ color: '#6366f1' }} />
            <span>AI 助手（RAG 智能问答）</span>
          </Space>
        }
        open={visible}
        onCancel={() => setVisible(false)}
        footer={null}
        width={900}
        className="ai-assistant-modal"
        styles={{ body: { padding: 0, height: '650px', display: 'flex', flexDirection: 'column' } }}
      >
        <div className="ai-assistant-container">
          <div className="ai-assistant-messages">
            {messages.length === 0 ? (
              <div className="ai-assistant-empty">
                <RobotOutlined style={{ fontSize: 48, color: '#d9d9d9', marginBottom: 16 }} />
                <Text type="secondary">我是您的AI旅行助手，基于小红书攻略为您提供智能问答~</Text>
                <div className="ai-empty-hint">
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    您可以问我：北京有什么好吃的？三亚值得去吗？推荐几个景点...
                  </Text>
                </div>
              </div>
            ) : (
              <List
                dataSource={messages}
                renderItem={(item: Message) => (
                  <List.Item
                    style={{
                      border: 'none',
                      padding: '12px 16px',
                      justifyContent: item.role === 'user' ? 'flex-end' : 'flex-start',
                    }}
                  >
                    <div className={`ai-message ${item.role === 'user' ? 'ai-message-user' : 'ai-message-assistant'}`}>
                      <Space align="start" size={12}>
                        {item.role === 'assistant' && (
                          <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#6366f1', flexShrink: 0 }} />
                        )}
                        <div className="ai-message-content">
                          {renderMessageContent(item)}
                        </div>
                        {item.role === 'user' && (
                          <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#10b981', flexShrink: 0 }} />
                        )}
                      </Space>
                    </div>
                  </List.Item>
                )}
              />
            )}
            {loading && (
              <div className="ai-loading-row">
                <Space>
                  <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#6366f1' }} />
                  <Spin size="small" />
                  <Text type="secondary">正在检索小红书攻略...</Text>
                </Space>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="ai-assistant-input">
            <Space.Compact style={{ width: '100%' }}>
              <TextArea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="输入您的问题...（Shift+Enter换行，Enter发送）"
                autoSize={{ minRows: 1, maxRows: 4 }}
                disabled={loading}
                style={{ resize: 'none' }}
              />
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleSend}
                loading={loading}
                disabled={!inputValue.trim()}
                style={{ height: 'auto' }}
              >
                发送
              </Button>
            </Space.Compact>
            {messages.length > 0 && (
              <Button type="text" size="small" onClick={handleClear} style={{ marginTop: 8, padding: 0 }}>
                清空对话
              </Button>
            )}
          </div>
        </div>
      </Modal>

      {/* 加入行程模态框 */}
      <Modal
        title="加入已有行程"
        open={addModalVisible}
        onCancel={() => setAddModalVisible(false)}
        onOk={handleAddToPlan}
        okText={adding ? '添加中...' : '确认添加'}
        cancelText="取消"
        width={450}
        okButtonProps={{ disabled: adding }}
      >
        <div className="ai-modal-field">
          <Text strong>选择目标行程</Text>
          <Select
            className="ai-modal-select"
            placeholder="请选择行程"
            value={selectedPlanId ?? undefined}
            onChange={(v: number | null) => setSelectedPlanId(v)}
            options={(() => {
              const lastUserMsg = messages.slice().reverse().find(m => m.role === 'user');
              const contextTexts = [selectedEntity?.name, selectedEntity?.content, lastUserMsg?.content].filter(Boolean).join('\n');
              const city = extractPlaceAndCity(contextTexts || selectedEntity?.name || '').city;
              let opts: any[] = [];
              const pool = plans || [];
              if (city) {
                const matched = pool.filter(p => {
                  const dest = (p.destination || '').toString();
                  const cities = Array.isArray(p.cities) ? p.cities : (typeof p.cities === 'string' && p.cities ? [p.cities] : []);
                  return dest === city || cities.includes(city);
                });
                opts = matched.map(p => ({ label: p.title || `行程 ${p.id}`, value: p.id }));
              } else {
                opts = pool.map(p => ({ label: p.title || `行程 ${p.id}`, value: p.id }));
              }
              opts.push({ label: '创建新行程', value: null });
              return opts;
            })()}
          />
        </div>
        <div className="ai-modal-field">
          <Text strong>选择具体时间（可选）</Text>
          <div className="ai-modal-time-row">
              <DatePicker 
                className="ai-modal-date" 
                placeholder="选择日期" 
                onChange={(_, d) => setSelectedDate(typeof d === 'string' ? d : null)} 
              />
              <TimePicker 
                className="ai-modal-time" 
                placeholder="选择时间" 
                format="HH:mm" 
                onChange={(_, t) => setSelectedTime(typeof t === 'string' ? t : null)} 
              />
          </div>
        </div>
        <div>
          <Text strong>要添加的内容</Text>
          <div className="ai-modal-content-preview">
            {selectedEntity?.name || '未选择'}
            <Tag style={{ marginLeft: 8 }} color={selectedEntity?.type === 'restaurant' ? '#fa8c16' : '#52c41a'}>
              {selectedEntity?.type === 'restaurant' ? '餐馆' : selectedEntity?.type === 'hotel' ? '酒店' : '景点'}
            </Tag>
          </div>
        </div>
      </Modal>

      {/* 详情模态框 */}
      <Modal
        title={<Space><EnvironmentOutlined style={{ color: '#6366f1' }} /><span>详情</span></Space>}
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>关闭</Button>,
          <Button key="add" type="primary" icon={<CalendarOutlined />} onClick={() => {
            setDetailModalVisible(false);
            if (selectedEntity) setAddModalVisible(true);
          }}>加入行程</Button>
        ]}
        width={500}
      >
        {detailLoading ? <div className="ai-detail-loading"><Spin /></div> : attractionDetail && (
          <Descriptions column={1} bordered size="small" className="ai-attraction-detail">
            <Descriptions.Item label="名称">{attractionDetail.name}</Descriptions.Item>
            <Descriptions.Item label="类型">
              <Tag color={attractionDetail.type === 'restaurant' ? '#fa8c16' : '#52c41a'}>
                {attractionDetail.type === 'restaurant' ? '餐馆' : '景点'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="地址">
              {attractionDetail.address || '暂无地址信息'}
            </Descriptions.Item>
            {attractionDetail.coordinates && (
              <Descriptions.Item label="坐标">
                {Number(attractionDetail.coordinates.lat).toFixed(6)}, {Number(attractionDetail.coordinates.lng).toFixed(6)}
                <Tag color="green" style={{ marginLeft: 8 }}>已定位</Tag>
              </Descriptions.Item>
            )}
            <Descriptions.Item label="简介">{attractionDetail.description}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </>
  );
};

export default AIAssistant;