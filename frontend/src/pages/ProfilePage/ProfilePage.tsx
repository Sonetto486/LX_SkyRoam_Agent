import React, { useState, useEffect } from 'react';
import { Card, Button, Space, Typography, Avatar, Row, Col, Tag, Statistic, Modal, Form, Input, message, Spin } from 'antd';
import { EditOutlined, EnvironmentOutlined, CalendarOutlined, StarOutlined } from '@ant-design/icons';
import './ProfilePage.css';
import { UserOutlined } from '@ant-design/icons';


import axios from 'axios';

const { Title, Paragraph } = Typography;

interface User {
  id: string;
  username: string;
  email: string;
  avatar: string;
  full_name?: string;
  bio: string;
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
  const [form] = Form.useForm();

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
      <Card className="map-card">
        <Title level={3}>我的足迹</Title>
        <div className="interactive-map">
          {/* 这里可以集成真实的地图组件 */}
          <div className="map-placeholder">
            <h3>互动地图</h3>
            <p>显示已收藏和已点亮的足迹点</p>
          </div>
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
