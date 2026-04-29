import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout, Tabs, Card, Button, Space, Badge, Tooltip, Empty, Spin } from 'antd';
import { 
  EditOutlined, 
  SyncOutlined, 
  CarOutlined, 
  SaveOutlined, 
  ExportOutlined,
  PlusOutlined,
  EnvironmentOutlined
} from '@ant-design/icons';
import MapComponent from '../../components/MapComponent/MapComponent';
import './ItineraryWorkspace.css';

const { Content, Sider } = Layout;

interface Itinerary {
  id: string;
  title: string;
  days: Day[];
  destination: string;
  startDate: string;
  endDate: string;
  weather: Weather[];
}

interface Day {
  id: number;
  date: string;
  activities: Activity[];
}

interface Activity {
  id: number;
  name: string;
  location: string;
  address: string;
  coordinates: { lat: number; lng: number };
  startTime: string;
  endTime: string;
  description: string;
  images: string[];
}

interface Weather {
  date: string;
  temperature: string;
  condition: string;
  icon: string;
}

const ItineraryWorkspace: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeDay, setActiveDay] = useState(0);
  const [hoveredActivity, setHoveredActivity] = useState<number | null>(null);

  // 模拟数据加载
  useEffect(() => {
    const fetchItinerary = async () => {
      setLoading(true);
      // 模拟 API 调用
      setTimeout(() => {
        setItinerary({
          id: id || '1',
          title: '东京5日游',
          destination: '东京, 日本',
          startDate: '2026-05-01',
          endDate: '2026-05-05',
          weather: [
            { date: '2026-05-01', temperature: '18°C', condition: '晴', icon: '☀️' },
            { date: '2026-05-02', temperature: '20°C', condition: '多云', icon: '☁️' },
            { date: '2026-05-03', temperature: '19°C', condition: '小雨', icon: '🌧️' },
            { date: '2026-05-04', temperature: '21°C', condition: '晴', icon: '☀️' },
            { date: '2026-05-05', temperature: '22°C', condition: '晴', icon: '☀️' }
          ],
          days: [
            {
              id: 1,
              date: '2026-05-01',
              activities: [
                {
                  id: 1,
                  name: '浅草寺',
                  location: '浅草, 东京',
                  address: '日本东京都台东区浅草2-3-1',
                  coordinates: { lat: 35.714722, lng: 139.796667 },
                  startTime: '09:00',
                  endTime: '11:00',
                  description: '东京最古老的寺庙，以雷门和仲见世商店街闻名',
                  images: ['https://picsum.photos/seed/asakusa/800/600']
                },
                {
                  id: 2,
                  name: '东京晴空塔',
                  location: '墨田区, 东京',
                  address: '日本东京都墨田区押上1-1-2',
                  coordinates: { lat: 35.710063, lng: 139.810700 },
                  startTime: '11:30',
                  endTime: '14:00',
                  description: '东京的地标建筑，高634米，是世界第二高的建筑',
                  images: ['https://picsum.photos/seed/skytree/800/600']
                },
                {
                  id: 3,
                  name: '银座',
                  location: '银座, 东京',
                  address: '日本东京都中央区银座',
                  coordinates: { lat: 35.671247, lng: 139.766922 },
                  startTime: '15:00',
                  endTime: '18:00',
                  description: '东京最繁华的商业区，有许多高端商店和餐厅',
                  images: ['https://picsum.photos/seed/ginza/800/600']
                }
              ]
            },
            {
              id: 2,
              date: '2026-05-02',
              activities: [
                {
                  id: 4,
                  name: '明治神宫',
                  location: '涩谷区, 东京',
                  address: '日本东京都涩谷区代代木神园町1-1',
                  coordinates: { lat: 35.676206, lng: 139.699684 },
                  startTime: '09:00',
                  endTime: '11:30',
                  description: '位于市中心的大型神道教神社，环境宁静',
                  images: ['https://picsum.photos/seed/meiji/800/600']
                },
                {
                  id: 5,
                  name: '涩谷十字路口',
                  location: '涩谷, 东京',
                  address: '日本东京都涩谷区涩谷',
                  coordinates: { lat: 35.659462, lng: 139.700574 },
                  startTime: '12:00',
                  endTime: '14:00',
                  description: '世界上最繁忙的十字路口之一',
                  images: ['https://picsum.photos/seed/shibuya/800/600']
                },
                {
                  id: 6,
                  name: '新宿御苑',
                  location: '新宿区, 东京',
                  address: '日本东京都新宿区新宿御苑1-1',
                  coordinates: { lat: 35.685278, lng: 139.710000 },
                  startTime: '14:30',
                  endTime: '17:00',
                  description: '融合了日式、英式和法式风格的庭园',
                  images: ['https://picsum.photos/seed/ ShinjukuGyoen/800/600']
                }
              ]
            }
          ]
        });
        setLoading(false);
      }, 1000);
    };

    fetchItinerary();
  }, [id]);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!itinerary) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
        <Empty description="行程不存在" />
      </div>
    );
  }

  // 准备地图标记数据
  const mapMarkers = itinerary.days.flatMap(day => 
    day.activities.map(activity => ({
      id: activity.id,
      name: activity.name,
      position: activity.coordinates,
      address: activity.address,
      isHovered: hoveredActivity === activity.id
    }))
  );

  return (
    <Layout style={{ minHeight: 'calc(100vh - 112px)', background: '#fff', borderRadius: 8, overflow: 'hidden' }}>
      {/* 左半屏：信息流面板 */}
      <Sider width={480} style={{ background: '#fff', borderRight: '1px solid #f0f0f0' }}>
        {/* 顶部看板 */}
        <div className="workspace-header">
          <div className="itinerary-info">
            <h1 className="itinerary-title">{itinerary.title}</h1>
            <div className="itinerary-meta">
              <span>{itinerary.destination}</span>
              <span>{itinerary.startDate} - {itinerary.endDate}</span>
              <span>{itinerary.days.length}天</span>
            </div>
          </div>
          
          {/* 天气信息 */}
          <div className="weather-info">
            <h3>天气概览</h3>
            <div className="weather-cards">
              {itinerary.weather.map((day, index) => (
                <div key={index} className="weather-card">
                  <div className="weather-date">{day.date.split('-').slice(1).join('/')}</div>
                  <div className="weather-icon">{day.icon}</div>
                  <div className="weather-temp">{day.temperature}</div>
                  <div className="weather-condition">{day.condition}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
        
        {/* 天数标签页 */}
        <Tabs 
          activeKey={activeDay.toString()}
          onChange={(key) => setActiveDay(parseInt(key))}
          style={{ borderBottom: '1px solid #f0f0f0' }}
        >
          {itinerary.days.map((day, index) => (
            <Tabs.TabPane 
              key={index} 
              tab={
                <Space>
                  <span>Day {index + 1}</span>
                  <span style={{ fontSize: '12px', color: '#999' }}>
                    {day.date.split('-').slice(1).join('/')}
                  </span>
                </Space>
              }
            >
              {/* 活动列表 */}
              <div className="activities-list">
                {day.activities.map((activity) => (
                  <Card 
                    key={activity.id}
                    className={`activity-card ${hoveredActivity === activity.id ? 'hovered' : ''}`}
                    onMouseEnter={() => setHoveredActivity(activity.id)}
                    onMouseLeave={() => setHoveredActivity(null)}
                    actions={[
                      <Button 
                        key="edit" 
                        icon={<EditOutlined />} 
                        size="small"
                      >
                        编辑
                      </Button>,
                      <Button 
                        key="remove" 
                        danger 
                        size="small"
                      >
                        移除
                      </Button>
                    ]}
                  >
                    <div className="activity-time">
                      <span>{activity.startTime}</span>
                      <span>→</span>
                      <span>{activity.endTime}</span>
                    </div>
                    <h3 className="activity-name">{activity.name}</h3>
                    <div className="activity-location">{activity.location}</div>
                    <div className="activity-description">{activity.description}</div>
                    {activity.images.length > 0 && (
                      <div className="activity-images">
                        <img 
                          src={activity.images[0]} 
                          alt={activity.name} 
                          className="activity-image"
                        />
                      </div>
                    )}
                  </Card>
                ))}
                
                {/* 添加活动按钮 */}
                <Button 
                  type="dashed" 
                  block 
                  icon={<PlusOutlined />}
                  className="add-activity-btn"
                >
                  添加活动
                </Button>
              </div>
            </Tabs.TabPane>
          ))}
        </Tabs>
      </Sider>
      
      {/* 右半屏：地图模式 */}
      <Content style={{ position: 'relative' }}>
        {/* 地图组件 */}
        <MapComponent 
          markers={mapMarkers}
          center={itinerary.days[0].activities[0].coordinates}
          zoom={12}
        />
        
        {/* 地图控制按钮 */}
        <div className="map-controls">
          <Tooltip title="路线编辑">
            <Button 
              icon={<EditOutlined />} 
              className="map-control-btn"
              style={{ background: '#fff', boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)' }}
            />
          </Tooltip>
          <Tooltip title="一键优化">
            <Button 
              icon={<SyncOutlined />} 
              className="map-control-btn"
              style={{ background: '#fff', boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)' }}
            />
          </Tooltip>
          <Tooltip title="显示交通工具">
            <Button 
              icon={<CarOutlined />} 
              className="map-control-btn"
              style={{ background: '#fff', boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)' }}
            />
          </Tooltip>
          <Tooltip title="保存行程">
            <Button 
              icon={<SaveOutlined />} 
              className="map-control-btn"
              style={{ background: '#1890ff', color: '#fff', boxShadow: '0 2px 8px rgba(24, 144, 255, 0.3)' }}
            />
          </Tooltip>
          <Tooltip title="分享行程">
            <Button 
              icon={<ExportOutlined />} 
              className="map-control-btn"
              style={{ background: '#52c41a', color: '#fff', boxShadow: '0 2px 8px rgba(82, 196, 26, 0.3)' }}
            />
          </Tooltip>
        </div>
      </Content>
    </Layout>
  );
};

export default ItineraryWorkspace;
