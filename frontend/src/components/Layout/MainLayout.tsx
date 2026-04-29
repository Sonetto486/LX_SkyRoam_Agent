import React, { useState } from 'react';
import { Layout, Menu, Button, Dropdown, Space } from 'antd';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { 
  HomeOutlined, 
  CalendarOutlined, 
  UserOutlined, 
  SettingOutlined, 
  PlusOutlined, 
  LogoutOutlined,
  ImportOutlined,
  FileTextOutlined
} from '@ant-design/icons';
// 临时注释掉 AuthContext 导入，实际项目中需要创建该文件
// import { useAuth } from '../../context/AuthContext';
import './MainLayout.css';

const { Sider, Content } = Layout;
const { SubMenu } = Menu;

const MainLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  // 临时模拟 logout，实际项目中需要使用 useAuth
  const logout = () => {
    console.log('Logout');
    navigate('/login');
  };
  const [collapsed, setCollapsed] = useState(false);
  const isAdmin = false; // 模拟管理员权限

  // 获取当前路由对应的菜单项
  const getSelectedKey = () => {
    const path = location.pathname;
    if (path.startsWith('/discover')) return '1';
    if (path.startsWith('/itineraries')) return '2';
    if (path.startsWith('/import')) return '5';
    if (path.startsWith('/generate')) return '6';
    if (path.startsWith('/profile')) return '3';
    if (path.startsWith('/admin')) return '4';
    return '1';
  };

  // 创建行程的下拉菜单
  const createMenu = {
    items: [
      {
        key: '1',
        label: '手动创建',
        onClick: () => navigate('/itineraries/new')
      },
      {
        key: '2',
        label: (
          <Space>
            <ImportOutlined />
            智能导入
          </Space>
        ),
        onClick: () => navigate('/import')
      }
    ]
  };



  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 左侧边栏 */}
      <Sider 
        collapsible 
        collapsed={collapsed} 
        onCollapse={setCollapsed}
        style={{ 
          backgroundColor: '#0f172a',
          boxShadow: '2px 0 8px rgba(0, 0, 0, 0.15)'
        }}
      >
        {/* 品牌 Logo */}
        <div className="logo" style={{ padding: '24px', textAlign: 'center' }}>
          <div style={{ 
            width: collapsed ? 48 : 120, 
            height: 48, 
            borderRadius: '50%', 
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            margin: '0 auto',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 12px rgba(102, 126, 234, 0.4)'
          }}>
            <img 
              src="/images/logo.png" 
              alt="Logo" 
              style={{ 
                width: collapsed ? 24 : 32, 
                height: collapsed ? 24 : 32 
              }} 
            />
          </div>
          {!collapsed && (
            <div style={{ 
              marginTop: 16, 
              color: '#fff', 
              fontSize: 16, 
              fontWeight: 600 
            }}>
              洛曦 云旅Agent
            </div>
          )}
        </div>
        
        {/* 核心操作区 */}
        <div style={{ padding: '0 16px 16px' }}>
          <Dropdown menu={createMenu} placement="bottomRight">
            <Button 
              type="primary" 
              danger 
              ghost
              block
              icon={<PlusOutlined />}
              style={{ 
                background: 'linear-gradient(135deg, #f56565 0%, #e53e3e 100%)',
                border: 'none',
                color: '#fff',
                fontWeight: 600,
                padding: '12px 16px'
              }}
            >
              {!collapsed && '创建行程'}
            </Button>
          </Dropdown>
        </div>
        
        {/* 导航菜单栏 */}
        <Menu 
          theme="dark" 
          mode="inline" 
          selectedKeys={[getSelectedKey()]} 
          style={{ 
            backgroundColor: '#0f172a',
            borderRight: 'none'
          }}
        >
          <Menu.Item key="1" icon={<HomeOutlined />} onClick={() => navigate('/discover')}>
            发现
          </Menu.Item>
          <Menu.Item key="2" icon={<CalendarOutlined />} onClick={() => navigate('/itineraries')}>
            我的行程
          </Menu.Item>
          <Menu.Item key="5" icon={<ImportOutlined />} onClick={() => navigate('/import')}>
            智能导入
          </Menu.Item>
          <Menu.Item key="6" icon={<FileTextOutlined />} onClick={() => navigate('/generate')}>
            一键生成
          </Menu.Item>
          <Menu.Item key="3" icon={<UserOutlined />} onClick={() => navigate('/profile')}>
            个人中心
          </Menu.Item>
          {isAdmin && (
            <SubMenu key="4" icon={<SettingOutlined />} title="管理后台">
              <Menu.Item key="4-1" onClick={() => navigate('/admin/users')}>
                用户管理
              </Menu.Item>
              <Menu.Item key="4-2" onClick={() => navigate('/admin/history')}>
                历史管理
              </Menu.Item>
              <Menu.Item key="4-3" onClick={() => navigate('/admin/attraction-details')}>
                景点详情管理
              </Menu.Item>
              <Menu.Item key="4-4" onClick={() => navigate('/admin/upgrade-control')}>
                升级控制
              </Menu.Item>
            </SubMenu>
          )}
        </Menu>
      </Sider>
      
      <Layout className="site-layout">
        {/* 主内容区 */}
        <Content style={{ 
          margin: '24px',
          padding: '24px',
          minHeight: 280,
          background: '#f0f2f5',
          borderRadius: 8,
          overflow: 'auto'
        }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};



export default MainLayout;
