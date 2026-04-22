import React, { useState, useEffect, useRef } from 'react';
import { Card, Button, Space, Typography, Avatar, Row, Col, Tag, Statistic, Modal, Form, Input, message, Spin, Drawer, Descriptions, Image, Carousel } from 'antd';
import { EditOutlined, EnvironmentOutlined, CalendarOutlined, StarOutlined, UserOutlined } from '@ant-design/icons';
import AMapLoader from '@amap/amap-jsapi-loader';
import './ProfilePage.css';

import axios from 'axios';

const { Title, Paragraph } = Typography;

interface User {
  id: string;
  username: string;
  email: string;
  avatar: string;
  full_name?: string;
  bio: string;
  favorite_locations?: number[];
  highlighted_locations?: number[];
  travelStats: {
    trips: number;
    destinations: number;
    days: number;
    favorites: number;
  };
  collections: {
    id: number;
    name: string;
    image: string;
    description: string;
  }[];
  journals: {
    id: number;
    title: string;
    date: string;
    content: string;
    image: string;
  }[];
}

const ProfilePage: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isEditModalVisible, setIsEditModalVisible] = useState<boolean>(false);
  const [selectedLocation, setSelectedLocation] = useState<any>(null); // 保存当前选中的地图点信息
  const [form] = Form.useForm();
  const mapContainerRef = useRef<HTMLDivElement>(null);

  // 获取用户数据
  const fetchUserProfile = async () => {
    try {
      setLoading(true);
      // 使用我们在 auth 工具中统一定义的 token key 获取 token
      const token = localStorage.getItem('auth_token');
      const baseURL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8001/api/v1';

      // 调用获取当前用户信息接口
      const response = await axios.get(`${baseURL}/users/me`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });

      const userData = response.data;
      
      // 合并后端返回的真实用户数据与暂时的Mock展示数据
      setUser({
        id: userData.id.toString(),
        username: userData.username,
        email: userData.email,
        full_name: userData.full_name || '',
        avatar: userData.avatar || 'https://picsum.photos/seed/user/200/200',
        bio: userData.photo_mood || userData.preferences || '热爱旅行，喜欢探索世界各地的文化和风景',
        favorite_locations: userData.favorite_locations || [],
        highlighted_locations: userData.highlighted_locations || [],
        // 以下统计数据和列表目前保持Mock，实际应根据后端关联查询返回（如行程、收藏记录）
        travelStats: {
          trips: 12,
          destinations: 28,
          days: 67,
          favorites: 45
        },
        collections: [
          {
            id: 1,
            name: '日本樱花季',
            image: 'https://picsum.photos/seed/japan1/400/300',
            description: '2026年3月东京、京都樱花之旅'
          },
          {
            id: 2,
            name: '欧洲文化之旅',
            image: 'https://picsum.photos/seed/europe/400/300',
            description: '2026年6月巴黎、罗马、巴塞罗那'
          }
        ],
        journals: [
          {
            id: 1,
            title: '东京之行',
            date: '2026-03-15',
            content: '今天参观了浅草寺和东京晴空塔，天气非常好，拍了很多照片。',
            image: 'https://picsum.photos/seed/tokyo/400/300'
          },
          {
            id: 2,
            title: '巴黎印象',
            date: '2026-06-10',
            content: '埃菲尔铁塔的夜景真的很美，卢浮宫的艺术珍品令人震撼。',
            image: 'https://picsum.photos/seed/paris/400/300'
          }
        ]
      });
    } catch (error) {
      console.error('Failed to fetch user profile', error);
      message.error('获取个人信息失败，请确保已登录');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUserProfile();
  }, []);

  // 高德地图初始化与标记点渲染
  useEffect(() => {
    if (!user) return;
    
    // 合并地点 ids
    const allIds = [
      ...(user.favorite_locations || []),
      ...(user.highlighted_locations || []),
    ];
    if (allIds.length === 0) return;

    let mapInstance: any = null;

    const fetchLocationsAndInitMap = async () => {
      try {
        const baseURL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8001/api/v1';
        const idsStr = Array.from(new Set(allIds)).join(',');
        
        // 调用我们刚刚写的批量获取地点经纬度接口
        const res = await axios.get(`${baseURL}/locations/batch`, {
          params: { ids: idsStr }
        });
        const locations = res.data;
        
        // 打印批量获取到的所有地点信息，方便确认后端是否成功返回了图片等扩展字段
        console.log('🌍 [Map Data Loaded] 获取到的所有地点信息:', locations);

        // 设置高德地图安全密钥（由于Typescript中window对象默认没有这个属性，需要通过类型断言绕过或声明）
        (window as any)._AMapSecurityConfig = {
          securityJsCode: '054290bb89b647cc29159cafc2fd0333',
        };

        // 加载高德地图
        const AMap = await AMapLoader.load({
           // 在此处填写你申请的高德 Web JS API Key
           key: '3c860a8217597619941f033146dde8ec',  // <-- 用户需要替换的地方
           version: '2.0',
           plugins: ['AMap.Marker', 'AMap.MarkerCluster'],
        });

        if (mapContainerRef.current) {
          mapInstance = new AMap.Map(mapContainerRef.current, {
            zoom: 4,
            center: [104.06, 30.67], // 中国中心参考坐标
          });

          // 创建一个共享的信息窗体 InfoWindow
          const infoWindow = new AMap.InfoWindow({
            offset: new AMap.Pixel(0, -15),
          });

          // 提取供聚合组件使用的坐标数据
          const points = locations
            .filter((loc: any) => loc.latitude && loc.longitude)
            .map((loc: any) => ({
              lnglat: [loc.longitude, loc.latitude],
              extData: loc
            }));

          // 定义渲染悬浮卡片的公用方法
          const showInfoWindow = (dataItems: any[], position: any) => {
            let infoHtml = `<div style="width: 240px; max-height: 400px; overflow-y: auto; padding: 4px; font-family: sans-serif;">`;
            
            dataItems.forEach((item: any, index: number) => {
               const loc = item.extData;
               let imageUrl = '';
               try {
                 let images = [];
                 if (Array.isArray(loc.media_images)) {
                   images = loc.media_images;
                 } else if (typeof loc.media_images === 'string' && loc.media_images) {
                   images = JSON.parse(loc.media_images);
                 }
                 if (images.length > 0) {
                   imageUrl = images[0].url || images[0];
                 }
               } catch (err) {}

               infoHtml += `
                 <div style="border-bottom: ${index < dataItems.length - 1 ? '1px dashed #ccc' : 'none'}; padding-bottom: 12px; margin-bottom: 12px;">
                   <h4 style="margin: 0 0 8px 0; font-size: 16px; color: #333;">${loc.location_name || loc.name}</h4>
                   ${imageUrl 
                     ? `<img src="${imageUrl}" style="width: 100%; height: 140px; object-fit: cover; border-radius: 4px; margin-bottom: 8px;" />` 
                     : `<div style="width: 100%; height: 140px; background: #f5f5f5; border-radius: 4px; margin-bottom: 8px; display: flex; align-items: center; justify-content: center; color: #999; font-size: 12px;">暂无图片</div>`
                   }
                   <div style="font-size: 12px; color: #666; max-height: 60px; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;">
                       ${loc.description || '暂无详细介绍'}
                   </div>
                 </div>
               `;
            });
            infoHtml += `</div>`;

            infoWindow.setContent(infoHtml);
            infoWindow.open(mapInstance, position);
          };

          // 实例化高德点聚合组件 MarkerCluster
          const cluster = new AMap.MarkerCluster(mapInstance, points, {
            gridSize: 60,
            maxZoom: 17, // 最大聚合放大级别
            renderClusterMarker: (context: any) => {
               // 【针对多个点聚合的样式】
               const count = context.count;
               const hasHigh = context.clusterData.some((d: any) => user.highlighted_locations?.includes(d.extData.id));
               const hasFav = context.clusterData.some((d: any) => user.favorite_locations?.includes(d.extData.id));
               const markerColor = hasHigh ? '#FF4D4F' : (hasFav ? '#FFD700' : '#40a9ff');

               const div = document.createElement('div');
               div.style.backgroundColor = markerColor;
               div.style.width = '30px';
               div.style.height = '30px';
               div.style.borderRadius = '50%';
               div.style.border = '2px solid white';
               div.style.boxShadow = '0 2px 4px rgba(0,0,0,0.3)';
               div.style.display = 'flex';
               div.style.alignItems = 'center';
               div.style.justifyContent = 'center';
               div.style.color = 'white';
               div.style.fontSize = '14px';
               div.style.fontWeight = 'bold';
               div.innerHTML = count;
               
               context.marker.setContent(div);
               context.marker.setOffset(new AMap.Pixel(-15, -15));

               // 直接绑定事件到生成的 Marker 实例上
               context.marker.on('mouseover', () => {
                 showInfoWindow(context.clusterData, context.marker.getPosition());
               });

               context.marker.on('click', () => {
                 // 点击放大地图
                 if (mapInstance.getZoom() < 17) {
                   mapInstance.zoomIn();
                   mapInstance.setCenter(context.marker.getPosition());
                 }
               });
            },
            renderMarker: (context: any) => {
               // 【针对散开后单个标记点的样式】
               const loc = context.data[0].extData;
               const isFav = user.favorite_locations?.includes(loc.id);
               const isHigh = user.highlighted_locations?.includes(loc.id);
               const markerColor = isHigh ? '#FF4D4F' : (isFav ? '#FFD700' : '#40a9ff');

               const div = document.createElement('div');
               div.style.backgroundColor = markerColor;
               div.style.width = '16px';
               div.style.height = '16px';
               div.style.borderRadius = '50%';
               div.style.border = '2px solid white';
               div.style.boxShadow = '0 2px 4px rgba(0,0,0,0.3)';

               context.marker.setContent(div);
               context.marker.setOffset(new AMap.Pixel(-8, -8));

               // 针对落单的情况，绑定 hover 事件
               context.marker.on('mouseover', () => {
                 showInfoWindow(context.data, context.marker.getPosition());
               });
            }
          });
          
          if (locations.length > 0) {
            mapInstance.setFitView();
          }
        }

      } catch (error) {
        console.error('Map loading or data fetching failed:', error);
      }
    };

    fetchLocationsAndInitMap();

    return () => {
      if (mapInstance) {
        mapInstance.destroy();
      }
    };
  }, [user]);

  const handleEditClick = () => {
    if (user) {
      form.setFieldsValue({
        full_name: user.full_name,
        email: user.email,
        photo_mood: user.bio, // 填充已有的个性签名 (photo_mood)
      });
      setIsEditModalVisible(true);
    }
  };

  const handleEditCancel = () => {
    setIsEditModalVisible(false);
  };

  const handleEditSubmit = async () => {
    try {
      const values = await form.validateFields();
      const token = localStorage.getItem('auth_token');
      const baseURL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8001/api/v1';

      // 调用更新用户信息接口
      await axios.patch(`${baseURL}/users/me`, values, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      message.success('个人资料更新成功');
      setIsEditModalVisible(false);
      // 重新获取最新数据
      fetchUserProfile();
    } catch (error: any) {
      console.error('Failed to update profile', error);
      if (error.response?.data?.detail) {
         message.error(error.response.data.detail);
      } else {
         message.error('更新失败');
      }
    }
  };

  if (loading || !user) {
    return <div className="loading-container"><Spin size="large" /></div>;
  }

  return (
    <div className="profile-page">
      {/* 个人信息 */}
      <Card className="profile-card">
        <div className="profile-header">
          <Avatar size={128} src={user.avatar} />
          <div className="profile-info">
            <Space direction="vertical">
              <div>
                <Title level={2}>{user.full_name || user.username}</Title>
                <Button icon={<EditOutlined />} onClick={handleEditClick}>
                  编辑资料
                </Button>
              </div>
              <Paragraph>{user.bio}</Paragraph>
              <div className="profile-email">{user.email}</div>
            </Space>
          </div>
        </div>
      </Card>

      {/* 旅行统计 */}
      <Card className="stats-card">
        <Title level={3}>旅行统计</Title>
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={6}>
            <Statistic 
              title="旅行次数" 
              value={user.travelStats.trips} 
              prefix={<CalendarOutlined />} 
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic 
              title="目的地" 
              value={user.travelStats.destinations} 
              prefix={<EnvironmentOutlined />} 
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic 
              title="旅行天数" 
              value={user.travelStats.days} 
              prefix={<CalendarOutlined />} 
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic 
              title="收藏地点" 
              value={user.travelStats.favorites} 
              prefix={<StarOutlined />} 
            />
          </Col>
        </Row>
      </Card>

      {/* 互动地图 */}
      <Card className="map-card" bodyStyle={{ padding: 0, overflow: 'hidden' }}>
        <Title level={3} style={{ padding: '24px 24px 0 24px', margin: 0 }}>我的足迹</Title>
        <div className="interactive-map">
          {(!user?.favorite_locations?.length && !user?.highlighted_locations?.length) ? (
             <div className="map-placeholder">
               <h3>互动地图</h3>
               <p>你还没有收藏或点亮的足迹点，快去发现世界吧！</p>
             </div>
          ) : (
             <div 
                ref={mapContainerRef} 
                className="amap-container"
             ></div>
          )}
        </div>
      </Card>

      {/* 收藏与记录 */}
      <Row gutter={[24, 24]}>
        {/* 收藏的行程 */}
        <Col xs={24} lg={12}>
          <Card title="收藏的行程" className="collection-card">
            {user.collections.map((collection) => (
              <Card key={collection.id} className="collection-item">
                <div className="collection-image">
                  <img src={collection.image} alt={collection.name} />
                </div>
                <div className="collection-content">
                  <Title level={4}>{collection.name}</Title>
                  <Paragraph>{collection.description}</Paragraph>
                </div>
              </Card>
            ))}
          </Card>
        </Col>

        {/* 旅行记录 */}
        <Col xs={24} lg={12}>
          <Card title="旅行记录" className="journal-card">
            {user.journals.map((journal) => (
              <Card key={journal.id} className="journal-item">
                <div className="journal-image">
                  <img src={journal.image} alt={journal.title} />
                </div>
                <div className="journal-content">
                  <div className="journal-header">
                    <Title level={4}>{journal.title}</Title>
                    <Tag>{journal.date}</Tag>
                  </div>
                  <Paragraph>{journal.content}</Paragraph>
                </div>
              </Card>
            ))}
          </Card>
        </Col>
      </Row>

      {/* 编辑资料弹窗 */}
      <Modal
        title="编辑个人资料"
        open={isEditModalVisible}
        onOk={handleEditSubmit}
        onCancel={handleEditCancel}
        okText="保存"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            name="full_name"
            label="昵称/姓名"
            rules={[
              { required: false, message: '请输入你的昵称/姓名' },
              { max: 50, message: '长度不能超过50个字符' }
            ]}
          >
            <Input placeholder="输入你想展示的昵称" />
          </Form.Item>

          <Form.Item
            name="email"
            label="电子邮箱"
            rules={[
              { required: false, message: '请输入邮箱' },
              { type: 'email', message: '邮箱格式不正确' }
            ]}
          >
            <Input placeholder="输入新的电子邮箱" />
          </Form.Item>
          <Form.Item
            name="photo_mood"
            label="照片心情 / 个人简介"
            rules={[
              { required: false }
            ]}
          >
            <Input.TextArea rows={3} placeholder="写点什么介绍一下自己" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ProfilePage;
