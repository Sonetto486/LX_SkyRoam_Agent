import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import 'antd/dist/reset.css';
import './pages/common.css';
import './App.css';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';

import Layout from './components/Layout/Layout';
import RouterApp from './app/router/RouterApp';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';

// 开发环境下导入升级通知测试和重置工具
if (process.env.NODE_ENV === 'development') {
  import('./utils/upgradeNoticeReset');
  import('./utils/testUpgradeNotice');
}

// 内部组件：使用主题配置 Ant Design
const AppContent: React.FC = () => {
  const { isDark } = useTheme();
  dayjs.locale('zh-cn');
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          // Notion 设计系统主题色
          colorPrimary: '#5645d4',
          colorInfo: '#0075de',
          colorSuccess: '#1aae39',
          colorWarning: '#dd5b00',
          colorError: '#e03131',
          borderRadius: 8,
          fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif',
        },
        algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
      }}
    >
      <Router>
        <div className="App">
          <Layout>
            <RouterApp />
          </Layout>
        </div>
      </Router>
    </ConfigProvider>
  );
};

const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
};

export default App;
