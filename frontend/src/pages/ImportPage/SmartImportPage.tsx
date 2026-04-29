import React, { useState, useMemo } from 'react';
import { Card, Button, Upload, Input, Typography, message, Tabs, Checkbox, Tag } from 'antd';
import { UploadOutlined, LinkOutlined, HeartOutlined, PlusOutlined } from '@ant-design/icons';
import { authFetch } from '../../utils/auth';
import './SmartImportPage.css';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;
const { TabPane } = Tabs;

// 定义后端返回的地点数据结构
interface ParsedLocation {
  id: number;
  name: string;
  type: string;
  address: string;
  day: string;
  excerpt: string;
  selected: boolean;
  image_url?: string; // 地点图片URL
  images?: string[]; // 地点图片URL列表
}

const SmartImportPage: React.FC = () => {
  const [textInput, setTextInput] = useState('');
  const [linkInput, setLinkInput] = useState('');
  const [fileList, setFileList] = useState<any[]>([]);
  
  // 加载状态
  const [importLoading, setImportLoading] = useState(false);
  const [linkLoading, setLinkLoading] = useState(false);
  
  // 数据存储
  const [generatedPlan, setGeneratedPlan] = useState<any>(null);
  const [activeTab, setActiveTab] = useState('locations');
  // 使用地点 ID 作为 key，管理勾选状态
  const [checkedLocations, setCheckedLocations] = useState<{[id: number]: boolean}>({});

  // 提取原始地点列表方便后续计算
  const parsedLocations: ParsedLocation[] = useMemo(() => {
    return generatedPlan?.preferences?.parsed_locations || [];
  }, [generatedPlan]);

  // 动态计算总数和天数
  const totalLocations = parsedLocations.length;
  const uniqueDays = useMemo(() => new Set(parsedLocations.map(l => l.day)).size, [parsedLocations]);
  const selectedCount = Object.values(checkedLocations).filter(Boolean).length;
  const allChecked = totalLocations > 0 && selectedCount === totalLocations;

  // 输入事件
  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => setTextInput(e.target.value);
  const handleLinkChange = (e: React.ChangeEvent<HTMLInputElement>) => setLinkInput(e.target.value);
  const handleFileChange = (info: any) => setFileList(info.fileList);

  // 统一的请求逻辑封装
  const fetchImportData = async (payload: any, setLoading: (state: boolean) => void) => {
    setLoading(true);
    try {
      const response = await authFetch('http://localhost:8000/api/v1/smart-import/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error('请求失败');
      const data = await response.json();
      
      if (data.success) {
        message.success('✅ 解析并生成行程成功！');
        setGeneratedPlan(data.data);
        initializeCheckedLocations(data.data.preferences?.parsed_locations || []);
      } else {
        message.error(data.message || '解析失败，请重试');
      }
    } catch (error) {
      message.error('网络错误或服务端异常');
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleXiaohongshuLink = () => {
    if (!linkInput || !linkInput.includes('xiaohongshu.com')) {
      message.error('请输入有效的小红书链接');
      return;
    }
    fetchImportData({ linkInput }, setLinkLoading);
  };

  const handleSubmit = () => {
    if (!textInput && !linkInput && fileList.length === 0) {
      message.error('请至少输入一种导入方式');
      return;
    }
    fetchImportData({ textInput, linkInput, fileList }, setImportLoading);
  };

  // 初始化勾选状态 (默认全部按照后端的 selected 状态)
  const initializeCheckedLocations = (locations: ParsedLocation[]) => {
    const initialChecked: {[id: number]: boolean} = {};
    locations.forEach(loc => {
      initialChecked[loc.id] = loc.selected ?? true; 
    });
    setCheckedLocations(initialChecked);
  };

  // 处理单个地点的勾选
  const handleLocationCheck = (id: number, checked: boolean) => {
    setCheckedLocations(prev => ({ ...prev, [id]: checked }));
  };

  // 全选/取消全选
  const handleAllCheck = (checked: boolean) => {
    const newChecked: {[id: number]: boolean} = {};
    parsedLocations.forEach(loc => {
      newChecked[loc.id] = checked;
    });
    setCheckedLocations(newChecked);
  };

  // 获取当前所有选中的完整地点对象
  const getSelectedLocationObjects = () => {
    return parsedLocations.filter(loc => checkedLocations[loc.id]);
  };

  const handleFavoriteLocations = () => {
    const selected = getSelectedLocationObjects();
    if (selected.length > 0) {
      message.success(`已收藏 ${selected.length} 个地点`);
    } else {
      message.warning('请先选择地点');
    }
  };

  // 最终创建行程的提交操作
  const handleCreateNewItinerary = async () => {
    const finalSelectedLocations = getSelectedLocationObjects();
    if (finalSelectedLocations.length === 0) {
      message.warning('您必须至少选择一个地点才能生成行程');
      return;
    }
    
    // 获取目的地信息（从第一个地点提取）
    const firstLocation = finalSelectedLocations[0];
    const destination = firstLocation.address || '未知目的地';
    
    // 生成行程标题
    const dayCount = uniqueDays;
    const title = `${destination} ${dayCount}天旅行计划`;
    
    // 构建请求数据
    const planData = {
      title,
      description: `智能导入的${destination}旅行计划，包含${finalSelectedLocations.length}个地点`,
      destination,
      departure: '',
      start_date: new Date().toISOString().split('T')[0],
      end_date: new Date(Date.now() + dayCount * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      duration_days: dayCount,
      preferences: {
        parsed_locations: finalSelectedLocations,
      },
    };
    
    try {
      const response = await authFetch('http://localhost:8000/api/v1/travel-plans/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(planData),
      });
      
      if (!response.ok) throw new Error('创建行程失败');
      const data = await response.json();
      
      message.success(`✅ 成功创建新行程！行程ID: ${data.id}`);
      
      // 跳转到行程详情页或我的行程列表
      setTimeout(() => {
        window.location.href = `/plans/${data.id}`;
      }, 1500);
      
    } catch (error) {
      message.error('创建行程失败，请重试');
      console.error('Error creating itinerary:', error);
    }
  };

  // 渲染单个地点卡片
  const LocationCard = ({ location }: { location: ParsedLocation }) => {
    const isChecked = checkedLocations[location.id] || false;
    // 优先使用后端提供的图片，否则使用默认的生成图片
    const imageUrl = location.image_url || `https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=${encodeURIComponent(`${location.name} 旅游景点`)}&image_size=square`;
    
    const typeColorMap: {[key: string]: string} = {
      '景点': 'blue', '餐饮': 'orange', '酒店': 'green', '交通': 'cyan'
    };
    
    return (
      <Card 
        hoverable 
        style={{ 
          border: isChecked ? '1px solid #1890ff' : '1px solid #e8e8e8', 
          borderRadius: 8, overflow: 'hidden', 
          opacity: isChecked ? 1 : 0.6, // 未选中时稍微变淡
          transition: 'all 0.3s'
        }}
        cover={<img src={imageUrl} alt={location.name} style={{ height: 160, objectFit: 'cover' }} />}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ flex: 1, paddingRight: 8 }}>
            <h4 style={{ margin: 0, color: '#262626', marginBottom: 8, fontSize: '16px' }}>{location.name}</h4>
            
            {/* 突出展示原文引用 */}
            <div style={{ background: '#f5f5f5', padding: '6px 8px', borderRadius: 4, marginBottom: 8 }}>
              <Text italic type="secondary" style={{ fontSize: 12 }}>
                “{location.excerpt}”
              </Text>
            </div>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Tag color={typeColorMap[location.type] || 'default'}>{location.type}</Tag>
              <Text type="secondary" ellipsis style={{ fontSize: 12, maxWidth: '150px' }} title={location.address}>
                {location.address}
              </Text>
            </div>
          </div>
          <Checkbox 
            checked={isChecked} 
            onChange={(e) => handleLocationCheck(location.id, e.target.checked)}
            style={{ transform: 'scale(1.2)', marginTop: 4 }}
          />
        </div>
      </Card>
    );
  };

  return (
    <div className="smart-import-page" style={{ minHeight: '100vh', background: '#f0f2f5', padding: '24px', paddingBottom: '100px' }}>
      {/* 1. 导入操作区 */}
      <Card style={{ marginBottom: 24, borderRadius: 12 }}>
        <Title level={3} style={{ marginBottom: 8 }}>智能导入</Title>
        <Paragraph type="secondary" style={{ marginBottom: 24 }}>粘贴攻略/链接 → 自动提取地点 → 勾选确认 → 一键生成详细行程</Paragraph>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 24, marginBottom: 24 }}>
          {/* 输入框省略，与原版保持一致... */}
          <Card title="文本输入" size="small" type="inner">
            <TextArea placeholder="粘贴旅行计划文本或描述" value={textInput} onChange={handleTextChange} rows={4} />
          </Card>
          <Card title="小红书链接" size="small" type="inner">
            <div style={{ display: 'flex', gap: '8px' }}>
              <Input placeholder="输入小红书分享链接" prefix={<LinkOutlined />} value={linkInput} onChange={handleLinkChange} />
              <Button type="default" onClick={handleXiaohongshuLink} loading={linkLoading}>提取</Button>
            </div>
          </Card>
          <Card title="截图上传" size="small" type="inner">
            <Upload multiple fileList={fileList} onChange={handleFileChange} maxCount={5}>
              <Button icon={<UploadOutlined />}>选择图片</Button>
            </Upload>
          </Card>
        </div>

        <div style={{ textAlign: 'center' }}>
          <Button type="primary" size="large" onClick={handleSubmit} loading={importLoading} style={{ width: 200 }}>
            {importLoading ? 'AI 深度解析中...' : '🚀 解析攻略内容'}
          </Button>
        </div>
      </Card>

      {/* 2. 解析结果与确认区 */}
      {generatedPlan && (
        <Card style={{ borderRadius: 12, position: 'relative' }}>
          <div style={{ marginBottom: 24 }}>
            <Title level={3} style={{ marginBottom: 8 }}>攻略解析结果</Title>
            <Paragraph type="secondary">AI 自动提取了以下地点，您可以取消勾选不需要的地点，随后生成正式行程。</Paragraph>
          </div>

          <Tabs activeKey={activeTab} onChange={setActiveTab} size="large">
            {/* Tab 1: 地点平铺视图 */}
            <TabPane tab={`📍 地点（${totalLocations}个）`} key="locations">
              {/* 批量操作 */}
              <div style={{ display: 'flex', gap: 12, marginBottom: 20, background: '#fafafa', padding: 12, borderRadius: 8 }}>
                <Checkbox checked={allChecked} indeterminate={selectedCount > 0 && selectedCount < totalLocations} onChange={(e) => handleAllCheck(e.target.checked)}>
                  全选 ({selectedCount}/{totalLocations})
                </Checkbox>
                <div style={{ marginLeft: 'auto', display: 'flex', gap: 12 }}>
                  <Button icon={<HeartOutlined />} onClick={handleFavoriteLocations} size="small">收藏</Button>
                  <Button icon={<PlusOutlined />} size="small">加入清单</Button>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 20 }}>
                {parsedLocations.length > 0 ? (
                  parsedLocations.map((loc) => <LocationCard key={loc.id} location={loc} />)
                ) : (
                  <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: 40, color: '#999' }}>暂无地点数据</div>
                )}
              </div>
            </TabPane>
            
            {/* Tab 2: 按天分组视图 */}
            <TabPane tab={`📅 行程（${uniqueDays}天）`} key="itinerary">
              <div style={{ display: 'flex', gap: 12, marginBottom: 20, background: '#fafafa', padding: 12, borderRadius: 8 }}>
                 <Checkbox checked={allChecked} indeterminate={selectedCount > 0 && selectedCount < totalLocations} onChange={(e) => handleAllCheck(e.target.checked)}>
                  全选 ({selectedCount}/{totalLocations})
                </Checkbox>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
                {(() => {
                  const locationsByDay: {[day: string]: ParsedLocation[]} = {};
                  parsedLocations.forEach((loc) => {
                    if (!locationsByDay[loc.day]) locationsByDay[loc.day] = [];
                    locationsByDay[loc.day].push(loc);
                  });
                  
                  return Object.entries(locationsByDay).map(([day, locations]) => (
                    <div key={day}>
                      <Title level={4} style={{ borderBottom: '2px solid #1890ff', display: 'inline-block', paddingBottom: 4, marginBottom: 16 }}>{day}</Title>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 20 }}>
                        {locations.map((loc) => <LocationCard key={loc.id} location={loc} />)}
                      </div>
                    </div>
                  ));
                })()}
              </div>
            </TabPane>
          </Tabs>

          {/* 3. 底部悬浮操作栏 (Sticky Bar) */}
          <div style={{
            position: 'fixed', bottom: 0, left: 0, right: 0, 
            background: '#fff', padding: '16px 40px',
            boxShadow: '0 -4px 12px rgba(0,0,0,0.05)',
            display: 'flex', justifyContent: 'flex-end', alignItems: 'center',
            zIndex: 100
          }}>
            <span style={{ marginRight: 24, fontSize: 16 }}>
              已选择 <strong style={{ color: '#1890ff', fontSize: 20 }}>{selectedCount}</strong> 个地点
            </span>
            <Button type="primary" size="large" onClick={handleCreateNewItinerary} style={{ width: 180 }}>
              创建为新行程
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
};

export default SmartImportPage;