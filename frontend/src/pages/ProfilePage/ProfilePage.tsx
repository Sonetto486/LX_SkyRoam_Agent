import React, { useState } from 'react';
import { Card, Button, Space, Typography, Avatar, Row, Col, Tag, Statistic } from 'antd';
import { EditOutlined, EnvironmentOutlined, CalendarOutlined, StarOutlined } from '@ant-design/icons';
import './ProfilePage.css';

const { Title, Paragraph } = Typography;

interface User {
  id: string;
  username: string;
  email: string;
  avatar: string;
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
  const [user, setUser] = useState<User>({
    id: '1',
    username: '旅行者',
    email: 'traveler@example.com',
    avatar: 'https://picsum.photos/seed/user/200/200',
    bio: '热爱旅行，喜欢探索世界各地的文化和风景',
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

  return (
    <div className="profile-page">
      {/* 个人信息 */}
      <Card className="profile-card">
        <div className="profile-header">
          <Avatar size={128} src={user.avatar} />
          <div className="profile-info">
            <Space direction="vertical">
              <div>
                <Title level={2}>{user.username}</Title>
                <Button icon={<EditOutlined />}>编辑资料</Button>
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
    </div>
  );
};

export default ProfilePage;
