import React, { useState, useMemo, useEffect } from 'react';
import { Card, Button, Upload, Input, Typography, message, Tabs, Checkbox, Tag } from 'antd';
import { useNavigate } from 'react-router-dom';
import { UploadOutlined, LinkOutlined, HeartOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { authFetch } from '../../utils/auth';
import './SmartImportPage.css';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;
const { TabPane } = Tabs;

// ✅ 更新地点数据结构，增加亮点、经纬度、花费
interface ParsedLocation {
  id: number;
  name: string;
  type: string;
  address: string;
  day: string;
  excerpt: string;
  selected: boolean;
  image_url?: string;
  images?: string[];
  highlight?: string;      // 亮点/推荐理由
  lat?: number;            // 纬度
  lng?: number;            // 经度
  cost?: number;           // 预估人均花费（元）
}

// localStorage keys
const STORAGE_KEY_PLAN = 'smart_import_plan';
const STORAGE_KEY_CHECKED = 'smart_import_checked';

const SmartImportPage: React.FC = () => {
  const navigate = useNavigate();
  const [textInput, setTextInput] = useState('');
  const [linkInput, setLinkInput] = useState('');
  const [fileList, setFileList] = useState<any[]>([]);
  
  const [importLoading, setImportLoading] = useState(false);
  const [linkLoading, setLinkLoading] = useState(false);
  
  const [generatedPlan, setGeneratedPlan] = useState<any>(null);
  const [activeTab, setActiveTab] = useState('locations');
  const [checkedLocations, setCheckedLocations] = useState<{[id: number]: boolean}>({});

  // 从 localStorage 加载保存的数据
  useEffect(() => {
    try {
      const savedPlan = localStorage.getItem(STORAGE_KEY_PLAN);
      const savedChecked = localStorage.getItem(STORAGE_KEY_CHECKED);
      
      if (savedPlan) {
        const plan = JSON.parse(savedPlan);
        setGeneratedPlan(plan);
        if (plan.preferences?.parsed_locations) {
          const initialChecked: {[id: number]: boolean} = {};
          plan.preferences.parsed_locations.forEach((loc: ParsedLocation) => {
            initialChecked[loc.id] = loc.selected ?? true;
          });
          setCheckedLocations(initialChecked);
        }
        message.info('已恢复上次导入的数据');
      }
      
      if (savedChecked) {
        const checked = JSON.parse(savedChecked);
        setCheckedLocations(checked);
      }
    } catch (error) {
      console.error('恢复保存数据失败:', error);
      localStorage.removeItem(STORAGE_KEY_PLAN);
      localStorage.removeItem(STORAGE_KEY_CHECKED);
      message.warning('保存的数据已损坏，已自动清除');
    }
  }, []);

  useEffect(() => {
    if (generatedPlan) {
      try {
        localStorage.setItem(STORAGE_KEY_PLAN, JSON.stringify(generatedPlan));
      } catch (error) {
        console.error('保存数据失败:', error);
      }
    }
  }, [generatedPlan]);

  useEffect(() => {
    if (Object.keys(checkedLocations).length > 0) {
      try {
        localStorage.setItem(STORAGE_KEY_CHECKED, JSON.stringify(checkedLocations));
      } catch (error) {
        console.error('保存勾选状态失败:', error);
      }
    }
  }, [checkedLocations]);

  const clearSavedData = () => {
    localStorage.removeItem(STORAGE_KEY_PLAN);
    localStorage.removeItem(STORAGE_KEY_CHECKED);
    setGeneratedPlan(null);
    setCheckedLocations({});
    message.success('已清除所有保存的数据');
  };

  const parsedLocations: ParsedLocation[] = useMemo(() => {
    return generatedPlan?.preferences?.parsed_locations || [];
  }, [generatedPlan]);

  const totalLocations = parsedLocations.length;
  const uniqueDays = useMemo(() => new Set(parsedLocations.map(l => l.day)).size, [parsedLocations]);
  const selectedCount = Object.values(checkedLocations).filter(Boolean).length;
  const allChecked = totalLocations > 0 && selectedCount === totalLocations;

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => setTextInput(e.target.value);
  const handleLinkChange = (e: React.ChangeEvent<HTMLInputElement>) => setLinkInput(e.target.value);
  const handleFileChange = (info: any) => setFileList(info.fileList);

  const fetchImportData = async (payload: any, setLoading: (state: boolean) => void) => {
    setLoading(true);
    try {
      const response = await authFetch(`${process.env.REACT_APP_API_BASE_URL}/smart-import/import`, {
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

  const handleImageUpload = async () => {
    if (fileList.length === 0) {
      message.error('请先选择图片');
      return;
    }

    const file = fileList[0].originFileObj;
    if (!file) {
      message.error('无效的图片文件，请重新选择');
      return;
    }

    setImportLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await authFetch('/image-import/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || '图片解析失败');
      }

      const data = await response.json();

      if (data.success) {
        message.success('✅ 图片解析成功！');
        setGeneratedPlan(data.data);
        initializeCheckedLocations(data.data.preferences?.parsed_locations || []);
      } else {
        message.error(data.message || '图片解析失败，请重试');
      }
    } catch (error: any) {
      console.error('图片上传失败:', error);
      message.error(error.message || '图片上传失败，请检查后端服务');
    } finally {
      setImportLoading(false);
    }
  };

  const handleSubmit = () => {
    if (fileList.length > 0) {
      handleImageUpload();
      return;
    }

    if (!textInput && !linkInput) {
      message.error('请至少输入一种导入方式');
      return;
    }
    fetchImportData({ textInput, linkInput }, setImportLoading);
  };

  const initializeCheckedLocations = (locations: ParsedLocation[]) => {
    const initialChecked: {[id: number]: boolean} = {};
    locations.forEach(loc => {
      initialChecked[loc.id] = loc.selected ?? true; 
    });
    setCheckedLocations(initialChecked);
  };

  const handleLocationCheck = (id: number, checked: boolean) => {
    setCheckedLocations(prev => ({ ...prev, [id]: checked }));
  };

  const handleAllCheck = (checked: boolean) => {
    const newChecked: {[id: number]: boolean} = {};
    parsedLocations.forEach(loc => {
      newChecked[loc.id] = checked;
    });
    setCheckedLocations(newChecked);
  };

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

  const handleCreateNewItinerary = async () => {
    const finalSelectedLocations = getSelectedLocationObjects();
    console.log("勾选的地点列表：", finalSelectedLocations);
    if (finalSelectedLocations.length === 0) {
      message.warning('您必须至少选择一个地点才能生成行程');
      return;
    }
    
    const firstLocation = finalSelectedLocations[0];
    const destination = firstLocation.address || '未知目的地';
    const dayCount = uniqueDays;
    const title = `${destination} ${dayCount}天旅行计划`;
    
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
    console.log("发送给后端的行程数据：", planData);

    try {
      const response = await authFetch('/travel-plans/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(planData),
      });
      
      if (!response.ok) throw new Error('创建行程失败');
      const data = await response.json();
      
      message.success(`✅ 成功创建新行程！行程ID: ${data.id}`);
      
      localStorage.removeItem(STORAGE_KEY_PLAN);
      localStorage.removeItem(STORAGE_KEY_CHECKED);
      
      setTimeout(() => {
        window.location.href = `/itineraries/${data.id}`;
      }, 1500);
      
    } catch (error) {
      console.error('创建行程失败:', error);
      message.error('保存行程失败，请检查后端接口');
    }
  };

  // ✅ 更新后的地点卡片组件，展示亮点、花费、经纬度
  const LocationCard = ({ location }: { location: ParsedLocation }) => {
    const isChecked = checkedLocations[location.id] || false;
    const imageUrl = location.image_url 
      || `https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=${encodeURIComponent(`${location.name} 旅游景点`)}&image_size=square`;
    
    const typeColorMap: {[key: string]: string} = {
      '景点': 'blue', '餐饮': 'orange', '酒店': 'green', '交通': 'cyan'
    };
    
    return (
      <Card 
        hoverable 
        style={{ 
          border: isChecked ? '1px solid #1890ff' : '1px solid #e8e8e8', 
          borderRadius: 8, overflow: 'hidden', 
          opacity: isChecked ? 1 : 0.6,
          transition: 'all 0.3s'
        }}
        cover={<img src={imageUrl} alt={location.name} style={{ height: 160, objectFit: 'cover' }} />}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ flex: 1, paddingRight: 8 }}>
            <h4 style={{ margin: 0, color: '#262626', marginBottom: 8, fontSize: '16px' }}>
              {location.name}
            </h4>
            
            {/* 亮点标签 */}
            {location.highlight && (
              <Tag color="volcano" style={{ marginBottom: 8 }}>
                ✨ {location.highlight}
              </Tag>
            )}
            
            {/* 原文引用 */}
            <div style={{ background: '#f5f5f5', padding: '6px 8px', borderRadius: 4, marginBottom: 8 }}>
              <Text italic type="secondary" style={{ fontSize: 12 }}>
                “{location.excerpt}”
              </Text>
            </div>
            
            {/* 类型与地址 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <Tag color={typeColorMap[location.type] || 'default'}>{location.type}</Tag>
              <Text type="secondary" ellipsis style={{ fontSize: 12, maxWidth: '150px' }} title={location.address}>
                {location.address}
              </Text>
            </div>

            {/* 花费与经纬度 */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 4 }}>
              {location.cost != null && location.cost > 0 && (
                <Tag color="green">💰 人均 ¥{location.cost}</Tag>
              )}
              {location.lat != null && location.lng != null && (
                <Text type="secondary" style={{ fontSize: 11 }}>
                  📍 {location.lat.toFixed(4)}, {location.lng.toFixed(4)}
                </Text>
              )}
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
      <Card style={{ marginBottom: 24, borderRadius: 12 }}>
        <Title level={3} style={{ marginBottom: 8 }}>智能导入</Title>
        <Paragraph type="secondary" style={{ marginBottom: 24 }}>粘贴攻略/链接 → 自动提取地点 → 勾选确认 → 一键生成详细行程</Paragraph>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 24, marginBottom: 24 }}>
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
            <Upload
              multiple
              fileList={fileList}
              onChange={handleFileChange}
              maxCount={5}
              beforeUpload={() => false}
              customRequest={() => {}}
            >
              <Button icon={<UploadOutlined />}>选择图片</Button>
            </Upload>
            <Button
              type="primary"
              onClick={handleImageUpload}
              loading={importLoading}
              style={{ marginTop: 12, width: '100%' }}
              disabled={fileList.length === 0}
            >
              {importLoading ? '识别中...' : '📷 OCR识别图片'}
            </Button>
          </Card>
        </div>

        <div style={{ textAlign: 'center' }}>
          <Button type="primary" size="large" onClick={handleSubmit} loading={importLoading} style={{ width: 200 }}>
            {importLoading ? 'AI 深度解析中...' : '🚀 解析攻略内容'}
          </Button>
        </div>
      </Card>

      {generatedPlan && (
        <Card style={{ borderRadius: 12, position: 'relative' }}>
          <div style={{ marginBottom: 24 }}>
            <Title level={3} style={{ marginBottom: 8 }}>攻略解析结果</Title>
            <Paragraph type="secondary">AI 自动提取了以下地点，您可以取消勾选不需要的地点，随后生成正式行程。</Paragraph>
          </div>

          <Tabs activeKey={activeTab} onChange={setActiveTab} size="large">
            <TabPane tab={`📍 地点（${totalLocations}个）`} key="locations">
              <div style={{ display: 'flex', gap: 12, marginBottom: 20, background: '#fafafa', padding: 12, borderRadius: 8 }}>
                <Checkbox checked={allChecked} indeterminate={selectedCount > 0 && selectedCount < totalLocations} onChange={(e) => handleAllCheck(e.target.checked)}>
                  全选 ({selectedCount}/{totalLocations})
                </Checkbox>
                <div style={{ marginLeft: 'auto', display: 'flex', gap: 12 }}>
                  <Button icon={<DeleteOutlined />} onClick={clearSavedData} size="small" danger>清除结果</Button>
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