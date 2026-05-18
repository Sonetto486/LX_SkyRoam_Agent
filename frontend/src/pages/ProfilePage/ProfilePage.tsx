import React, { useState, useEffect, useRef } from 'react';
import { Card, Button, Space, Typography, Avatar, Row, Col, Tag, Statistic, Modal, Form, Input, message, Spin } from 'antd';
import { EditOutlined, EnvironmentOutlined, CalendarOutlined, StarOutlined } from '@ant-design/icons';
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
  collections: { id: number; name: string; image: string; description: string }[];
  journals: { id: number; title: string; date: string; content: string; image: string }[];
}

const ProfilePage: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [mapLoading, setMapLoading] = useState<boolean>(true);
  const [travelStats, setTravelStats] = useState({ trips: 0, destinations: 0, days: 0, favorites: 0 });
  const [isEditModalVisible, setIsEditModalVisible] = useState<boolean>(false);
  const [form] = Form.useForm();
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);

  const calculatePlanDays = (plan: any) => {
    if (typeof plan?.duration_days === 'number') return plan.duration_days;
    if (plan?.start_date && plan?.end_date) {
      const start = new Date(plan.start_date);
      const end = new Date(plan.end_date);
      if (!Number.isNaN(start.getTime()) && !Number.isNaN(end.getTime())) {
        const diff = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
        return diff >= 0 ? diff + 1 : 0;
      }
    }
    return 0;
  };

  const formatDate = (value?: string) => {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toISOString().slice(0, 10);
  };

  const resolveImage = (images: any, fallbackSeed: string) => {
    if (Array.isArray(images) && images.length > 0) {
      const first = images[0];
      if (typeof first === 'string') return first;
      if (first?.url) return first.url;
    }
    return `https://picsum.photos/seed/${fallbackSeed}/400/300`;
  };

  const buildCollections = (plans: any[]) =>
    plans.map((plan: any) => ({
      id: plan.id,
      name: plan.title || plan.destination || '未命名行程',
      image: resolveImage(plan?.images, `plan-${plan.id}`),
      description: plan.description || plan.destination || '暂无简介'
    }));

  const buildJournalsFromItems = (items: any[], fallbackPrefix: string) =>
    items.map((item: any, index: number) => ({
      id: item.id || index + 1,
      title: item.title || item.location || '行程记录',
      date: formatDate(item.start_time) || formatDate(item.created_at) || '',
      content: item.description || item.item_type || '暂无内容',
      image: resolveImage(item.images, `${fallbackPrefix}-${item.id || index}`)
    }));

  const fetchTravelPlansData = async (token: string | null) => {
    const baseURL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1';
    const response = await axios.get(`${baseURL}/travel-plans`, {
      params: { skip: 0, limit: 1000 },
      headers: { Authorization: `Bearer ${token}` }
    });
    const plans = response.data?.plans || [];
    const totalTrips = typeof response.data?.total === 'number' ? response.data.total : plans.length;
    return { plans, totalTrips };
  };

  const fetchUserProfile = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('auth_token');
      const baseURL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1';
      const response = await axios.get(`${baseURL}/users/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const userData = response.data;
      const favoriteCount = Array.isArray(userData.favorite_locations) ? userData.favorite_locations.length : 0;
      const { plans, totalTrips } = await fetchTravelPlansData(token);

      const destinationSet = new Set<string>();
      let totalDays = 0;
      plans.forEach((plan: any) => {
        const dest = plan?.destination;
        if (Array.isArray(dest)) dest.forEach((d: any) => d && destinationSet.add(String(d)));
        else if (dest) destinationSet.add(String(dest));
        totalDays += calculatePlanDays(plan);
      });

      setTravelStats({ trips: totalTrips, destinations: destinationSet.size, days: totalDays, favorites: favoriteCount });

      const collections = buildCollections(plans);
      const plansForItems = plans.slice(0, 3);
      const itemResults = await Promise.allSettled(
        plansForItems.map((plan: any) =>
          axios.get(`${baseURL}/travel-plans/${plan.id}/items`, { headers: { Authorization: `Bearer ${token}` } })
        )
      );

      const journalItems: any[] = [];
      itemResults.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          journalItems.push(...(Array.isArray(result.value.data) ? result.value.data : []));
        } else {
          const fb = plansForItems[index];
          if (fb) journalItems.push({ id: fb.id, title: fb.title || fb.destination || '行程记录', start_time: fb.start_date, description: fb.description, images: [] });
        }
      });

      const journals = buildJournalsFromItems(journalItems.slice(0, 6), 'journal');

      setUser({
        id: userData.id.toString(), username: userData.username, email: userData.email,
        full_name: userData.full_name || '', avatar: userData.avatar || 'https://picsum.photos/seed/user/200/200',
        bio: userData.photo_mood || userData.preferences || '热爱旅行，喜欢探索世界各地的文化和风景',
        favorite_locations: userData.favorite_locations || [], highlighted_locations: userData.highlighted_locations || [],
        collections, journals
      });
    } catch (error) {
      console.error('Failed to fetch user profile', error);
      message.error('获取个人信息失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUserProfile(); }, []);

  // 地图初始化
  useEffect(() => {
    if (!user) return;
    const allIds = [...(user.favorite_locations || []), ...(user.highlighted_locations || [])];
    const uniqueIds = Array.from(new Set(allIds));

    const initMap = async () => {
      try {
        setMapLoading(true);
        const baseURL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1';
        (window as any)._AMapSecurityConfig = { securityJsCode: '054290bb89b647cc29159cafc2fd0333' };
        const AMap = await AMapLoader.load({ key: '3c860a8217597619941f033146dde8ec', version: '2.0', plugins: [] });
        if (!mapContainerRef.current) return;

        const map = new AMap.Map(mapContainerRef.current, {
          zoom: 5, center: [104.06, 30.67], viewMode: '2D', lang: 'zh_cn',
          mapStyle: 'amap://styles/light', features: ['bg', 'road', 'building', 'point'], showBuildingBlock: true,
        });
        mapInstanceRef.current = map;
        if (uniqueIds.length === 0) { setMapLoading(false); return; }

        const res = await axios.get(`${baseURL}/locations/batch`, { params: { ids: uniqueIds.join(',') } });
        const locations = res.data;
        const infoWindow = new AMap.InfoWindow({ offset: new AMap.Pixel(0, -35), closeWhenClickMap: true });

        locations.forEach((loc: any) => {
          if (!loc.latitude || !loc.longitude) return;
          const isFav = user.favorite_locations?.includes(loc.id);
          const isHigh = user.highlighted_locations?.includes(loc.id);
          let markerColor = '#40a9ff';
          if (isHigh) markerColor = '#FF4D4F';
          else if (isFav) markerColor = '#FFD700';

          const markerContent = document.createElement('div');
          markerContent.innerHTML = `<div style="position:relative;width:28px;height:28px;"><div style="position:absolute;top:2px;left:2px;width:24px;height:24px;background:${markerColor};border-radius:50%;border:3px solid white;box-shadow:0 3px 8px rgba(0,0,0,0.3);transition:transform 0.2s;"></div><div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);width:0;height:0;border-left:6px solid transparent;border-right:6px solid transparent;border-top:8px solid ${markerColor};"></div></div>`;

          const marker = new AMap.Marker({
            position: [loc.longitude, loc.latitude], content: markerContent,
            offset: new AMap.Pixel(-14, -28), title: loc.location_name || loc.name,
            zIndex: isHigh ? 200 : isFav ? 150 : 100,
          });

          marker.on('mouseover', () => {
            let imageUrl = '';
            if (Array.isArray(loc.media_images) && loc.media_images.length > 0) imageUrl = loc.media_images[0].url || loc.media_images[0];
            const infoContent = `<div style="width:280px;font-family:sans-serif;overflow:hidden;border-radius:8px;">${imageUrl ? `<div style="position:relative;height:160px;overflow:hidden;"><img src="${imageUrl}" style="width:100%;height:100%;object-fit:cover;" onerror="this.parentElement.style.display='none'"/><div style="position:absolute;bottom:0;left:0;right:0;background:linear-gradient(transparent,rgba(0,0,0,0.6));padding:30px 12px 8px;"><h4 style="margin:0;font-size:18px;color:#fff;">${loc.location_name || loc.name}</h4></div></div>` : `<div style="padding:12px 12px 0;"><h4 style="margin:0 0 4px;font-size:17px;">${loc.location_name || loc.name}</h4></div>`}<div style="padding:10px 12px;"><p style="margin:8px 0;font-size:13px;color:#555;line-height:1.6;">${loc.description || '暂无详细介绍'}</p>${loc.address ? `<div style="display:flex;align-items:center;margin-top:8px;padding-top:8px;border-top:1px solid #f0f0f0;"><span>📍</span><span style="font-size:12px;color:#999;margin-left:4px;">${loc.address}</span></div>` : ''}</div></div>`;
            infoWindow.setContent(infoContent);
            infoWindow.open(map, marker.getPosition());
            const dot = markerContent.querySelector('div > div:first-child') as HTMLElement;
            if (dot) dot.style.transform = 'scale(1.3)';
          });

          marker.on('mouseout', () => {
            const dot = markerContent.querySelector('div > div:first-child') as HTMLElement;
            if (dot) dot.style.transform = 'scale(1)';
          });

          marker.on('click', () => map.setZoomAndCenter(14, [loc.longitude, loc.latitude]));
          map.add(marker);
        });

        if (locations.length > 0) {
          const positions = locations.filter((l: any) => l.latitude && l.longitude).map((l: any) => [l.longitude, l.latitude]);
          if (positions.length > 0) map.setFitView(positions, false, [80, 80, 80, 80]);
        }
        setMapLoading(false);
      } catch (error) {
        console.error('Map failed:', error);
        setMapLoading(false);
      }
    };

    initMap();
    return () => { if (mapInstanceRef.current) { mapInstanceRef.current.destroy(); mapInstanceRef.current = null; } };
  }, [user]);

  const handleEditClick = () => {
    if (user) { form.setFieldsValue({ full_name: user.full_name, email: user.email, photo_mood: user.bio }); setIsEditModalVisible(true); }
  };

  const handleEditSubmit = async () => {
    try {
      const values = await form.validateFields();
      const token = localStorage.getItem('auth_token');
      const baseURL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1';
      await axios.patch(`${baseURL}/users/me`, values, { headers: { Authorization: `Bearer ${token}` } });
      message.success('更新成功');
      setIsEditModalVisible(false);
      fetchUserProfile();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '更新失败');
    }
  };

  if (loading || !user) {
    return <div style={{ width: '100%', height: 'calc(100vh - 64px)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Spin size="large" /></div>;
  }

  return (
    <div className="profile-page">
      <div className="profile-top-section">
        <Card className="profile-card">
          <div className="profile-header">
            <Avatar size={80} src={user.avatar} />
            <div className="profile-info">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                <Title level={4} style={{ margin: 0 }}>{user.full_name || user.username}</Title>
                <Button type="text" size="small" icon={<EditOutlined />} onClick={handleEditClick} />
              </div>
              <Paragraph ellipsis={{ rows: 2 }} style={{ margin: '4px 0', color: '#666', fontSize: 13 }}>{user.bio}</Paragraph>
              <div style={{ fontSize: 12, color: '#999' }}>{user.email}</div>
            </div>
          </div>
        </Card>
        <Card className="stats-card">
          <div className="stats-row">
            <div className="stat-item"><Statistic title="旅行次数" value={travelStats.trips} prefix={<CalendarOutlined style={{ color: '#1890ff' }} />} /></div>
            <div className="stat-item"><Statistic title="目的地" value={travelStats.destinations} prefix={<EnvironmentOutlined style={{ color: '#52c41a' }} />} /></div>
            <div className="stat-item"><Statistic title="旅行天数" value={travelStats.days} prefix={<CalendarOutlined style={{ color: '#faad14' }} />} /></div>
            <div className="stat-item"><Statistic title="收藏地点" value={travelStats.favorites} prefix={<StarOutlined style={{ color: '#ff4d4f' }} />} /></div>
          </div>
        </Card>
      </div>

      <div className="map-section">
        <Card className="map-card">
          <div className="map-card-header">
            <Title level={5} style={{ margin: 0 }}>🗺️ 我的足迹</Title>
            <div className="map-legend">
              <span><span className="legend-dot" style={{ background: '#FF4D4F' }}></span>高亮</span>
              <span><span className="legend-dot" style={{ background: '#FFD700' }}></span>收藏</span>
              <span><span className="legend-dot" style={{ background: '#40a9ff' }}></span>普通</span>
            </div>
          </div>
          <div className="map-container-wrapper">
            <div ref={mapContainerRef} />
            {mapLoading && <div className="loading-overlay"><Spin size="large" /></div>}
          </div>
        </Card>
      </div>

      <div className="bottom-section">
        <Card title="📦 收藏的行程">
          {user.collections.length > 0 ? user.collections.map(c => (
            <Card key={c.id} className="inner-card" size="small">
              <div className="card-item-content">
                <div className="card-item-image"><img src={c.image} alt={c.name} onError={e => { (e.target as HTMLImageElement).src = 'https://picsum.photos/seed/fallback/400/300'; }} /></div>
                <div className="card-item-info"><h5>{c.name}</h5><Paragraph ellipsis={{ rows: 2 }}>{c.description}</Paragraph></div>
              </div>
            </Card>
          )) : <div className="empty-state"><EnvironmentOutlined /><p>暂无收藏</p></div>}
        </Card>
        <Card title="📝 旅行记录">
          {user.journals.length > 0 ? user.journals.map(j => (
            <Card key={j.id} className="inner-card" size="small">
              <div className="card-item-content">
                <div className="card-item-image"><img src={j.image} alt={j.title} onError={e => { (e.target as HTMLImageElement).src = 'https://picsum.photos/seed/fallback/400/300'; }} /></div>
                <div className="card-item-info">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}><h5>{j.title}</h5>{j.date && <Tag color="blue" style={{ fontSize: 10 }}>{j.date}</Tag>}</div>
                  <Paragraph ellipsis={{ rows: 2 }}>{j.content}</Paragraph>
                </div>
              </div>
            </Card>
          )) : <div className="empty-state"><CalendarOutlined /><p>暂无记录</p></div>}
        </Card>
      </div>

      <Modal title="编辑个人资料" open={isEditModalVisible} onOk={handleEditSubmit} onCancel={() => setIsEditModalVisible(false)} okText="保存" cancelText="取消" destroyOnHidden>
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item name="full_name" label="昵称" rules={[{ max: 50 }]}><Input placeholder="输入昵称" /></Form.Item>
          <Form.Item name="email" label="邮箱" rules={[{ type: 'email' }]}><Input placeholder="输入邮箱" /></Form.Item>
          <Form.Item name="photo_mood" label="简介"><Input.TextArea rows={3} placeholder="介绍一下自己" /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ProfilePage;