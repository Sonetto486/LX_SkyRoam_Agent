import React, { useState, useMemo, useEffect } from 'react';
import { Card, Button, Upload, Input, Typography, message, Tabs, Checkbox, Tag, Modal, DatePicker, Select, Radio } from 'antd';
import { useNavigate } from 'react-router-dom';
import { UploadOutlined, LinkOutlined, HeartOutlined, PlusOutlined, DeleteOutlined, SaveOutlined, StarOutlined } from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import { authFetch } from '../../utils/auth';
import './SmartImportPage.css';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;
const { TabPane } = Tabs;
const { RangePicker } = DatePicker;

// 类型颜色映射（全局常量）
const TYPE_COLOR_MAP: {[key: string]: string} = {
  '景点': 'blue', '餐饮': 'orange', '酒店': 'green', '交通': 'cyan'
};

interface TravelPlan {
  id: number;
  title: string;
  start_date: string;
  destination: string;
}

// ✅ 更新地点数据结构，增加亮点、经纬度、花费、格式化地址
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
  formatted_address?: string; // 格式化地址
  province?: string;       // 省份
  city?: string;           // 城市
  district?: string;       // 区县
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
  const [activeTab, setActiveTab] = useState('attractions'); // 默认显示景点标签页
  const [checkedLocations, setCheckedLocations] = useState<{[id: number]: boolean}>({});

  // 保存行程相关状态
  const [saveModalVisible, setSaveModalVisible] = useState(false);
  const [saveMode, setSaveMode] = useState<'new' | 'merge'>('new'); // 创建新行程或合并到已有行程
  const [planTitle, setPlanTitle] = useState('');
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs] | null>(null);
  const [existingPlans, setExistingPlans] = useState<TravelPlan[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<number | undefined>(undefined);
  const [saveLoading, setSaveLoading] = useState(false);
  const [loadingPlans, setLoadingPlans] = useState(false); // 加载已有行程的状态
  
  // 智能规划相关状态
  const [smartPlanModalVisible, setSmartPlanModalVisible] = useState(false);
  const [smartPlanDays, setSmartPlanDays] = useState(3);
  const [smartPlanLoading, setSmartPlanLoading] = useState(false);
  const [smartPlanResult, setSmartPlanResult] = useState<SmartPlanResult | null>(null);

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

  // 加载已有行程列表
  const loadExistingPlans = async () => {
    setLoadingPlans(true);
    try {
      const response = await authFetch('/travel-plans/');
      if (response.ok) {
        const data = await response.json();
        // 后端返回格式：{ plans: [...], total: ... }
        setExistingPlans(data.plans || []);
      }
    } catch (error) {
      console.error('加载已有行程失败:', error);
      message.warning('加载已有行程失败，请稍后重试');
    } finally {
      setLoadingPlans(false);
    }
  };

  // 打开保存模态框
  const handleOpenSaveModal = () => {
    const finalSelectedLocations = getSelectedLocationObjects();
    if (finalSelectedLocations.length === 0) {
      message.warning('您必须至少选择一个地点才能保存行程');
      return;
    }

    // 加载已有行程列表
    loadExistingPlans();

    // 生成默认标题
    const firstLocation = finalSelectedLocations[0];
    const destination = firstLocation.city || firstLocation.address || '未知目的地';
    const title = `${destination} ${uniqueDays}天旅行计划`;
    setPlanTitle(title);

    // 生成默认日期范围
    const startDate = dayjs();
    const endDate = dayjs().add(uniqueDays - 1, 'day');
    setDateRange([startDate, endDate]);

    setSaveModalVisible(true);
  };

  // 关闭保存模态框
  const handleCloseSaveModal = () => {
    setSaveModalVisible(false);
    setSaveMode('new');
    setPlanTitle('');
    setDateRange(null);
    setSelectedPlanId(undefined);
  };

  const parsedLocations: ParsedLocation[] = useMemo(() => {
    return generatedPlan?.preferences?.parsed_locations || [];
  }, [generatedPlan]);

  // 按类型分类的地点
  const filteredLocations = useMemo(() => {
    return {
      '景点': parsedLocations.filter(loc => loc.type === '景点'),
      '交通': parsedLocations.filter(loc => loc.type === '交通'),
      '酒店': parsedLocations.filter(loc => loc.type === '酒店'),
      '餐饮': parsedLocations.filter(loc => loc.type === '餐饮'),
    };
  }, [parsedLocations]);

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

  // 保存行程（创建新行程或合并到已有行程）
  const handleSaveItinerary = async () => {
    const finalSelectedLocations = getSelectedLocationObjects();
    if (finalSelectedLocations.length === 0) {
      message.warning('您必须至少选择一个地点才能保存行程');
      return;
    }

    if (!dateRange) {
      message.warning('请选择行程日期');
      return;
    }

    const [startDate, endDate] = dateRange;
    const dayCount = endDate.diff(startDate, 'day') + 1;
    const firstLocation = finalSelectedLocations[0];
    const destination = firstLocation.city || firstLocation.address || '未知目的地';

    setSaveLoading(true);

    try {
      if (saveMode === 'new') {
        // 创建新行程
        const planData = {
          title: planTitle || `${destination} ${dayCount}天旅行计划`,
          description: `智能导入的${destination}旅行计划，包含${finalSelectedLocations.length}个地点`,
          destination,
          departure: '',
          start_date: startDate.format('YYYY-MM-DD'),
          end_date: endDate.format('YYYY-MM-DD'),
          duration_days: dayCount,
          preferences: {
            parsed_locations: finalSelectedLocations,
          },
        };

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

        handleCloseSaveModal();

        setTimeout(() => {
          window.location.href = `/itineraries/${data.id}`;
        }, 1500);

      } else {
        // 合并到已有行程
        if (selectedPlanId === undefined) {
          message.warning('请选择要合并的行程');
          setSaveLoading(false);
          return;
        }

        // 获取已有行程的详情
        const existingResponse = await authFetch(`/travel-plans/${selectedPlanId}/`);
        if (!existingResponse.ok) throw new Error('获取已有行程失败');
        const existingPlan = await existingResponse.json();

        // 获取已有行程的地点和天数
        const existingLocations = existingPlan.preferences?.parsed_locations || [];
        
        // 计算已有行程的最大天数
        const existingDays = existingLocations.map((loc: any) => {
          const dayStr = String(loc.day);
          const match = dayStr.match(/\d+/);
          return match ? parseInt(match[0], 10) : 1;
        });
        const maxDay = existingDays.length > 0 ? Math.max(...existingDays) : 0;

        // 基于名称去重（更合理的去重方式）
        const existingNames = new Set(existingLocations.map((loc: any) => String(loc.name).trim()));
        
        // 处理新地点：设置正确的天数（放在最后一天），并去重
        const processedNewLocations = finalSelectedLocations
          .filter(loc => !existingNames.has(String(loc.name).trim()))
          .map((loc, index) => ({
            ...loc,
            // 将新地点放在最后一天，每个地点按顺序分配到后续天数
            day: `Day ${maxDay + Math.floor(index / 3) + 1}`,
          }));

        // 如果所有地点都已存在，仍然允许合并（可能用户想添加重复地点）
        if (processedNewLocations.length === 0) {
          message.info('所有选中的地点已存在于目标行程中');
        }

        console.log('合并信息:', {
          existingCount: existingLocations.length,
          selectedCount: finalSelectedLocations.length,
          newCount: processedNewLocations.length,
          maxDay,
        });

        // 更新行程：合并旧地点和新地点
        const updatedLocations = [...existingLocations, ...processedNewLocations];
        const updatedPlan = {
          ...existingPlan,
          preferences: {
            ...existingPlan.preferences,
            parsed_locations: updatedLocations,
          },
        };

        const response = await authFetch(`/travel-plans/${selectedPlanId}/`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updatedPlan),
        });

        if (!response.ok) throw new Error('合并行程失败');

        message.success(`✅ 成功合并 ${processedNewLocations.length} 个地点到行程`);

        localStorage.removeItem(STORAGE_KEY_PLAN);
        localStorage.removeItem(STORAGE_KEY_CHECKED);

        handleCloseSaveModal();

        setTimeout(() => {
          window.location.href = `/itineraries/${selectedPlanId}`;
        }, 1500);
      }
    } catch (error) {
      console.error('保存行程失败:', error);
      message.error('保存行程失败，请检查后端接口');
    } finally {
      setSaveLoading(false);
    }
  };

  // ✅ 更新后的地点卡片组件，展示亮点、花费、经纬度和详细地址
  const LocationCard = ({ location }: { location: ParsedLocation }) => {
    const isChecked = checkedLocations[location.id] || false;
    const imageUrl = location.image_url
      || `https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=${encodeURIComponent(`${location.name} 旅游景点`)}&image_size=square`;

    // 获取显示地址（优先使用格式化地址，其次使用原始地址）
    const displayAddress = location.formatted_address || location.address;
    
    // 获取省市区信息
    const regionInfo = [];
    if (location.province) regionInfo.push(location.province);
    if (location.city) regionInfo.push(location.city);
    if (location.district) regionInfo.push(location.district);
    const regionText = regionInfo.join(' > ');

    return (
      <Card
        hoverable
        className={`location-card ${isChecked ? 'location-card-checked' : ''}`}
        cover={<img src={imageUrl} alt={location.name} style={{ height: 160, objectFit: 'cover' }} />}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ flex: 1, paddingRight: 8 }}>
            <h4 className="location-name">
              {location.name}
            </h4>

            {/* 亮点标签 */}
            {location.highlight && (
              <Tag color="volcano" style={{ marginBottom: 8 }}>
                ✨ {location.highlight}
              </Tag>
            )}

            {/* 原文引用 */}
            <div className="location-excerpt">
              <Text italic type="secondary" style={{ fontSize: 12 }}>
                "{location.excerpt}"
              </Text>
            </div>

            {/* 类型标签 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, marginTop: 8 }}>
              <Tag color={TYPE_COLOR_MAP[location.type] || 'default'}>{location.type}</Tag>
            </div>

            {/* 省市区信息 */}
            {regionText && (
              <div style={{ marginBottom: 4 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  🏙️ {regionText}
                </Text>
              </div>
            )}

            {/* 详细地址 */}
            {displayAddress && (
              <div className="location-address">
                <Text type="secondary" ellipsis style={{ fontSize: 12 }} title={displayAddress}>
                  📮 {displayAddress}
                </Text>
              </div>
            )}

            {/* 花费与经纬度 */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
              {location.cost != null && location.cost > 0 && (
                <Tag color="green">💰 人均 ¥{location.cost}</Tag>
              )}
              {location.lat != null && location.lng != null && (
                <Tag color="purple" style={{ fontSize: 11 }}>
                  📍 {location.lat.toFixed(4)}, {location.lng.toFixed(4)}
                </Tag>
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
    <div className="smart-import-page">
      <Card className="import-card" style={{ marginBottom: 24 }}>
        <Title level={3} style={{ marginBottom: 8 }}>智能导入</Title>
        <Paragraph type="secondary" style={{ marginBottom: 24 }}>粘贴攻略/链接 → 自动提取地点 → 勾选确认 → 一键生成详细行程</Paragraph>

        <div className="import-methods">
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

        <div className="submit-section">
          <Button type="primary" size="large" onClick={handleSubmit} loading={importLoading} style={{ width: 200 }}>
            {importLoading ? 'AI 深度解析中...' : '🚀 解析攻略内容'}
          </Button>
        </div>
      </Card>

      {generatedPlan && (
        <Card className="import-card" style={{ position: 'relative' }}>
          <div style={{ marginBottom: 24 }}>
            <Title level={3} style={{ marginBottom: 8 }}>攻略解析结果</Title>
            <Paragraph type="secondary">AI 自动提取了以下地点，您可以取消勾选不需要的地点，随后生成正式行程。</Paragraph>
          </div>

          <Tabs activeKey={activeTab} onChange={setActiveTab} size="large">
            {/* 按类型分类的地点标签页 */}
            <TabPane tab={`🏛️ 景点（${filteredLocations.景点.length}个）`} key="attractions">
              <div className="toolbar-section">
                <Checkbox checked={allChecked} indeterminate={selectedCount > 0 && selectedCount < totalLocations} onChange={(e) => handleAllCheck(e.target.checked)}>
                  全选 ({selectedCount}/{totalLocations})
                </Checkbox>
                <div style={{ marginLeft: 'auto', display: 'flex', gap: 12 }}>
                  <Button icon={<DeleteOutlined />} onClick={clearSavedData} size="small" danger>清除结果</Button>
                  <Button icon={<HeartOutlined />} onClick={handleFavoriteLocations} size="small">收藏</Button>
                  <Button icon={<PlusOutlined />} size="small">加入清单</Button>
                  <Button icon={<StarOutlined />} onClick={handleSmartPlan} size="small" type="primary">智能规划</Button>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 20 }}>
                {filteredLocations.景点.length > 0 ? (
                  filteredLocations.景点.map((loc) => <LocationCard key={loc.id} location={loc} />)
                ) : (
                  <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: 40, color: 'var(--text-soft)' }}>暂无景点数据</div>
                )}
              </div>
            </TabPane>

            <TabPane tab={`🚗 交通（${filteredLocations.交通.length}个）`} key="transport">
              <div className="toolbar-section">
                <Checkbox checked={allChecked} indeterminate={selectedCount > 0 && selectedCount < totalLocations} onChange={(e) => handleAllCheck(e.target.checked)}>
                  全选 ({selectedCount}/{totalLocations})
                </Checkbox>
                <div style={{ marginLeft: 'auto', display: 'flex', gap: 12 }}>
                  <Button icon={<DeleteOutlined />} onClick={clearSavedData} size="small" danger>清除结果</Button>
                  <Button icon={<HeartOutlined />} onClick={handleFavoriteLocations} size="small">收藏</Button>
                  <Button icon={<PlusOutlined />} size="small">加入清单</Button>
                  <Button icon={<StarOutlined />} onClick={handleSmartPlan} size="small" type="primary">智能规划</Button>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 20 }}>
                {filteredLocations.交通.length > 0 ? (
                  filteredLocations.交通.map((loc) => <LocationCard key={loc.id} location={loc} />)
                ) : (
                  <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: 40, color: 'var(--text-soft)' }}>暂无交通数据</div>
                )}
              </div>
            </TabPane>

            <TabPane tab={`🏨 住宿（${filteredLocations.酒店.length}个）`} key="hotels">
              <div className="toolbar-section">
                <Checkbox checked={allChecked} indeterminate={selectedCount > 0 && selectedCount < totalLocations} onChange={(e) => handleAllCheck(e.target.checked)}>
                  全选 ({selectedCount}/{totalLocations})
                </Checkbox>
                <div style={{ marginLeft: 'auto', display: 'flex', gap: 12 }}>
                  <Button icon={<DeleteOutlined />} onClick={clearSavedData} size="small" danger>清除结果</Button>
                  <Button icon={<HeartOutlined />} onClick={handleFavoriteLocations} size="small">收藏</Button>
                  <Button icon={<PlusOutlined />} size="small">加入清单</Button>
                  <Button icon={<StarOutlined />} onClick={handleSmartPlan} size="small" type="primary">智能规划</Button>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 20 }}>
                {filteredLocations.酒店.length > 0 ? (
                  filteredLocations.酒店.map((loc) => <LocationCard key={loc.id} location={loc} />)
                ) : (
                  <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: 40, color: 'var(--text-soft)' }}>暂无住宿数据</div>
                )}
              </div>
            </TabPane>

            <TabPane tab={`🍽️ 美食（${filteredLocations.餐饮.length}个）`} key="food">
              <div className="toolbar-section">
                <Checkbox checked={allChecked} indeterminate={selectedCount > 0 && selectedCount < totalLocations} onChange={(e) => handleAllCheck(e.target.checked)}>
                  全选 ({selectedCount}/{totalLocations})
                </Checkbox>
                <div style={{ marginLeft: 'auto', display: 'flex', gap: 12 }}>
                  <Button icon={<DeleteOutlined />} onClick={clearSavedData} size="small" danger>清除结果</Button>
                  <Button icon={<HeartOutlined />} onClick={handleFavoriteLocations} size="small">收藏</Button>
                  <Button icon={<PlusOutlined />} size="small">加入清单</Button>
                  <Button icon={<StarOutlined />} onClick={handleSmartPlan} size="small" type="primary">智能规划</Button>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 20 }}>
                {filteredLocations.餐饮.length > 0 ? (
                  filteredLocations.餐饮.map((loc) => <LocationCard key={loc.id} location={loc} />)
                ) : (
                  <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: 40, color: 'var(--text-soft)' }}>暂无美食数据</div>
                )}
              </div>
            </TabPane>

            <TabPane tab={`📅 行程（${uniqueDays}天）`} key="itinerary">
              <div className="toolbar-section">
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
                      <Title level={4} className="day-title">{day}</Title>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 20 }}>
                        {locations.map((loc) => <LocationCard key={loc.id} location={loc} />)}
                      </div>
                    </div>
                  ));
                })()}
              </div>
            </TabPane>
          </Tabs>

          <div className="bottom-action-bar">
            <span className="selected-count">
              已选择 <strong>{selectedCount}</strong> 个地点
            </span>
            <Button type="primary" size="large" onClick={handleOpenSaveModal} icon={<SaveOutlined />} style={{ width: 180 }}>
              保存行程
            </Button>
          </div>
        </Card>
      )}

      {/* 保存行程模态框 */}
      <Modal
        title="保存行程"
        visible={saveModalVisible}
        onCancel={handleCloseSaveModal}
        footer={null}
        width={520}
      >
        <div style={{ padding: 8 }}>
          {/* 保存方式选择 */}
          <div style={{ marginBottom: 20 }}>
            <Text strong style={{ display: 'block', marginBottom: 8 }}>保存方式</Text>
            <Radio.Group
              value={saveMode}
              onChange={(e) => setSaveMode(e.target.value as 'new' | 'merge')}
              style={{ display: 'flex', gap: 24 }}
            >
              <Radio value="new">创建新行程</Radio>
              <Radio value="merge">合并到已有行程</Radio>
            </Radio.Group>
          </div>

          {/* 行程名称 */}
          <div style={{ marginBottom: 20 }}>
            <Text strong style={{ display: 'block', marginBottom: 8 }}>行程名称</Text>
            <Input
              value={planTitle}
              onChange={(e) => setPlanTitle(e.target.value)}
              placeholder="请输入行程名称"
              style={{ width: '100%' }}
            />
          </div>

          {/* 行程日期 */}
          <div style={{ marginBottom: 20 }}>
            <Text strong style={{ display: 'block', marginBottom: 8 }}>行程日期</Text>
            <RangePicker
              value={dateRange}
              onChange={(dates) => {
                if (dates && dates.length === 2) {
                  setDateRange([dates[0]!, dates[1]!]);
                }
              }}
              style={{ width: '100%' }}
              allowClear={false}
            />
          </div>

          {/* 选择已有行程（合并模式） */}
          {saveMode === 'merge' && (
            <div style={{ marginBottom: 20 }}>
              <Text strong style={{ display: 'block', marginBottom: 8 }}>选择目标行程</Text>
              <Select
                value={selectedPlanId}
                onChange={(value) => setSelectedPlanId(value as number)}
                placeholder={loadingPlans ? "加载中..." : existingPlans.length === 0 ? "暂无已有行程，请先创建新行程" : "请选择要合并的行程"}
                style={{ width: '100%' }}
                loading={loadingPlans}
                disabled={loadingPlans || existingPlans.length === 0}
                options={existingPlans.map(plan => ({
                  value: plan.id,
                  label: `${plan.title} (${plan.start_date})`,
                }))}
              />
              {existingPlans.length === 0 && !loadingPlans && (
                <Text type="secondary" style={{ fontSize: 12, marginTop: 4, display: 'block' }}>
                  您还没有创建过行程，请选择"创建新行程"
                </Text>
              )}
              {existingPlans.length > 0 && !selectedPlanId && !loadingPlans && (
                <Text type="warning" style={{ fontSize: 12, marginTop: 4, display: 'block', color: '#faad14' }}>
                  ⚠️ 请选择要合并的目标行程
                </Text>
              )}
            </div>
          )}

          {/* 操作按钮 */}
          <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
            <Button onClick={handleCloseSaveModal}>取消</Button>
            <Button
              type="primary"
              onClick={handleSaveItinerary}
              loading={saveLoading}
            >
              {saveLoading ? '保存中...' : '确认保存'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* 智能规划模态框 */}
      <Modal
        title="🔮 智能规划"
        visible={smartPlanModalVisible}
        onCancel={() => setSmartPlanModalVisible(false)}
        width={600}
        footer={null}
      >
        {!smartPlanResult ? (
          <div>
            <p style={{ marginBottom: 16 }}>选择天数后，系统将自动为您规划每日行程安排</p>
            
            <div style={{ marginBottom: 16 }}>
              <Text strong style={{ display: 'block', marginBottom: 8 }}>计划天数</Text>
              <Select
                value={smartPlanDays}
                onChange={(value) => setSmartPlanDays(value as number)}
                style={{ width: 200 }}
                options={[
                  { value: 1, label: '1天' },
                  { value: 2, label: '2天' },
                  { value: 3, label: '3天' },
                  { value: 4, label: '4天' },
                  { value: 5, label: '5天' },
                  { value: 6, label: '6天' },
                  { value: 7, label: '7天' },
                ]}
              />
            </div>

            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
              <Button onClick={() => setSmartPlanModalVisible(false)}>取消</Button>
              <Button
                type="primary"
                onClick={() => handleSmartPlanExecute()}
                loading={smartPlanLoading}
                disabled={selectedCount === 0}
              >
                {smartPlanLoading ? '规划中...' : '开始规划'}
              </Button>
            </div>
          </div>
        ) : (
          <div>
            {/* 住宿推荐 - 放在最前面 */}
            <div style={{ marginBottom: 20, padding: 16, background: '#e6f7ff', border: '1px solid #91d5ff', borderRadius: 8 }}>
              <Title level={4} style={{ marginBottom: 12 }}>
                🏨 住宿区域推荐
              </Title>
              {smartPlanResult.accommodation_recommendation ? (
                <>
                  <p style={{ marginBottom: 8 }}>
                    {smartPlanResult.accommodation_recommendation.message}
                  </p>
                  <p style={{ marginBottom: 8, fontSize: 14 }}>
                    <strong>推荐中心点坐标：</strong>{smartPlanResult.accommodation_recommendation.center_lat.toFixed(4)}, {smartPlanResult.accommodation_recommendation.center_lng.toFixed(4)}
                  </p>
                  <p style={{ marginBottom: 8, fontSize: 14 }}>
                    <strong>到各景点平均距离：</strong>{smartPlanResult.accommodation_recommendation.average_distance_km} km
                  </p>
                  {smartPlanResult.accommodation_recommendation.nearby_attractions && smartPlanResult.accommodation_recommendation.nearby_attractions.length > 0 && (
                    <div style={{ marginTop: 12 }}>
                      <Text strong>附近景点（距离由近及远）：</Text>
                      <ul style={{ marginTop: 8, paddingLeft: 20 }}>
                        {smartPlanResult.accommodation_recommendation.nearby_attractions.map((a, idx) => (
                          <li key={idx} style={{ fontSize: 13 }}>
                            {a.name}（{a.distance_km} km）
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              ) : (
                <p style={{ color: '#999' }}>暂无住宿推荐数据</p>
              )}
            </div>

            {/* 规划结果警告 */}
            {smartPlanResult.warnings.map((warning, idx) => (
              <Tag color="warning" key={idx} style={{ marginBottom: 8, display: 'block' }}>
                ⚠️ {warning}
              </Tag>
            ))}

            <div style={{ maxHeight: 500, overflowY: 'auto' }}>
              {smartPlanResult.daily_plans.map((dayPlan) => (
                <div key={dayPlan.day_number} style={{ marginBottom: 24 }}>
                  <Title level={4} style={{ marginBottom: 12 }}>
                    📅 Day {dayPlan.day_number} ({dayPlan.start_time} - {dayPlan.end_time})
                  </Title>
                  
                  {dayPlan.warnings.map((warning, idx) => (
                    <Text type="warning" key={idx} style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
                      ⚠️ {warning}
                    </Text>
                  ))}

                  <div style={{ borderLeft: '3px solid #1890ff', paddingLeft: 16 }}>
                    {dayPlan.items.map((item, idx) => {
                      if (item.type === 'transport') {
                        // 交通段展示
                        return (
                          <div key={idx} style={{ marginBottom: 8, padding: 8, background: '#f0f2f5', borderRadius: 8 }}>
                            <div>🚗 {item.from} → {item.to}</div>
                            <div style={{ fontSize: 12, color: '#666' }}>
                              出发 {item.departure_time} 到达 {item.arrival_time}
                            </div>
                            <div style={{ fontSize: 12, display: 'flex', gap: 12, marginTop: 4 }}>
                              <span>🚶 步行 {item.modes?.walking.duration_min}分钟</span>
                              <span>🚗 驾车 {item.modes?.driving.duration_min}分钟</span>
                              <span>🚌 公交 {item.modes?.transit.duration_min}分钟</span>
                            </div>
                          </div>
                        );
                      } else {
                        // 地点/餐饮/酒店展示
                        return (
                          <div key={idx} style={{ marginBottom: 12, padding: 12, background: '#f8f9fa', borderRadius: 8 }}>
                            <div>
                              <strong>{item.name}</strong>
                              <Tag color={TYPE_COLOR_MAP[item.type] || 'default'} style={{ marginLeft: 8 }}>
                                {item.type}{item.meal_type && ` (${item.meal_type})`}
                              </Tag>
                              <span style={{ marginLeft: 16, fontSize: 12 }}>
                                {item.arrival_time} - {item.departure_time}
                                {item.estimated_duration && ` (${item.estimated_duration}小时)`}
                              </span>
                            </div>
                            {item.address && <div style={{ fontSize: 12, marginTop: 4 }}>� {item.address}</div>}
                          </div>
                        );
                      }
                    })}
                  </div>
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 16 }}>
              <Button onClick={() => {
                setSmartPlanResult(null);
                setSmartPlanDays(3);
              }}>重新规划</Button>
              <Button onClick={() => setSmartPlanModalVisible(false)}>关闭</Button>
              <Button type="primary" onClick={() => handleSaveSmartPlan()}>保存规划</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );

  // 智能规划相关类型
  interface SmartPlanItem {
    type: string;           // "transport" | "景点" | "餐饮" | "酒店"
    name?: string;          // 地点名称（非交通段有）
    from?: string;          // 交通段的起点
    to?: string;            // 交通段的终点
    arrival_time?: string;
    departure_time?: string;
    modes?: {               // 交通段专用
      walking: { duration_min: number; distance_km: number };
      driving: { duration_min: number; distance_km: number };
      transit: { duration_min: number; distance_km: number };
    };
    // 地点专用字段
    id?: number;
    lat?: number;
    lng?: number;
    estimated_duration?: number;
    meal_type?: string;
    address?: string;
  }

  interface SmartPlanDay {
    day_number: number;
    start_time: string;
    end_time: string;
    items: SmartPlanItem[];    // 改为 items
    warnings: string[];
  }

  interface AccommodationAttraction {
    name: string;
    lat: number;
    lng: number;
    distance_km: number;
  }

  interface AccommodationRecommendation {
    center_lat: number;
    center_lng: number;
    average_distance_km: number;
    nearby_attractions: AccommodationAttraction[];
    message: string;
  }

  interface SmartPlanResult {
    success: boolean;
    daily_plans: SmartPlanDay[];
    warnings: string[];
    use_virtual_hotel: boolean;
    total_locations: number;
    days: number;
    accommodation_recommendation: AccommodationRecommendation;
  }

  // 智能规划处理函数
  function handleSmartPlan() {
    setSmartPlanResult(null);
    setSmartPlanModalVisible(true);
  }

  async function handleSmartPlanExecute() {
    if (selectedCount === 0) {
      message.warning('请先选择要规划的地点');
      return;
    }

    setSmartPlanLoading(true);

    try {
      const selectedLocations = parsedLocations.filter(loc => checkedLocations[loc.id]);
      
      const locations = selectedLocations.map(loc => ({
        id: loc.id,
        name: loc.name,
        lat: loc.lat || 0,
        lng: loc.lng || 0,
        type: loc.type,
        estimated_duration: loc.cost ? loc.cost / 100 : 1.0,
        address: loc.address || loc.formatted_address || ''
      }));

      const response = await authFetch('/smart-plan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          locations,
          days: smartPlanDays,
          return_to_hotel: true
        })
      });

      if (!response.ok) throw new Error('规划失败');
      
      const result = await response.json();
      setSmartPlanResult(result);
      
    } catch (error) {
      console.error('智能规划失败:', error);
      message.error('智能规划失败，请稍后重试');
    } finally {
      setSmartPlanLoading(false);
    }
  }

  // 保存智能规划结果
  async function handleSaveSmartPlan() {
    if (!smartPlanResult) {
      message.warning('没有可保存的规划结果');
      return;
    }

    // 将智能规划结果转换为保存格式（只保存非交通段）
    const allLocations: ParsedLocation[] = [];
    
    smartPlanResult.daily_plans.forEach((dayPlan) => {
      dayPlan.items.forEach((item) => {
        if (item.type !== 'transport') {
          allLocations.push({
            id: item.id || Math.random(),
            name: item.name || '',
            type: item.type,
            address: item.address || '',
            day: `Day ${dayPlan.day_number}`,
            excerpt: item.meal_type || '',
            selected: true,
            lat: item.lat,
            lng: item.lng,
            formatted_address: item.address,
          });
        }
      });
    });

    // 更新 generatedPlan 以便后续保存
    setGeneratedPlan({
      ...generatedPlan,
      preferences: {
        ...generatedPlan?.preferences,
        parsed_locations: allLocations,
      },
    });

    // 更新 checkedLocations
    const newCheckedLocations: {[id: number]: boolean} = {};
    allLocations.forEach(loc => {
      newCheckedLocations[loc.id] = true;
    });
    setCheckedLocations(newCheckedLocations);

    // 关闭智能规划模态框
    setSmartPlanModalVisible(false);
    setSmartPlanResult(null);

    // 显示保存成功提示，并自动打开保存模态框
    message.success('智能规划结果已准备好，可直接保存行程');
    handleOpenSaveModal();
  }
};

export default SmartImportPage;
