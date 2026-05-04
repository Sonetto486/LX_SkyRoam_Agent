import React from 'react';
import { Routes, Route } from 'react-router-dom';
import RequireAdmin from '../../components/Auth/RequireAdmin';
import MainLayout from '../../components/Layout/MainLayout';
import DiscoverPage from '../../pages/DiscoverPage/DiscoverPage';
import TopicDetailPage from '../../pages/TopicDetailPage/TopicDetailPage';
import TopicsPage from '../../pages/TopicsPage/TopicsPage';
import PublicPlansPage from '../../pages/PublicPlansPage/PublicPlansPage';
import PlanDetailPage from '../../pages/PlanDetailPage/PlanDetailPage';
import ItineraryListPage from '../../pages/ItineraryPage/ItineraryListPage';
import ItineraryWorkspace from '../../pages/ItineraryPage/ItineraryWorkspace';
import SmartImportPage from '../../pages/ImportPage/SmartImportPage';
import PlanGeneratorPage from '../../pages/PlanGeneratorPage/PlanGeneratorPage';
import ProfilePage from '../../pages/ProfilePage/ProfilePage';
import LoginPage from '../../pages/LoginPage/LoginPage';
import RegisterPage from '../../pages/RegisterPage/RegisterPage';
import UsersAdminPage from '../../pages/Admin/UsersAdminPage';
import HistoryAdminPage from '../../pages/Admin/HistoryAdminPage';
import AttractionDetailsAdminPage from '../../pages/Admin/AttractionDetailsAdminPage';
import UpgradeControlPage from '../../pages/Admin/UpgradeControlPage/UpgradeControlPage';

const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* 认证路由 */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      
      {/* 主布局路由 */}
      <Route element={<MainLayout />}>
        {/* 发现灵感模块 */}
        <Route path="/discover" element={<DiscoverPage />} />
        <Route path="/topics" element={<TopicsPage />} />
        <Route path="/topics/:id" element={<TopicDetailPage />} />
        <Route path="/public-plans" element={<PublicPlansPage />} />
        <Route path="/plans/:id" element={<PlanDetailPage />} />
        
        {/* 我的行程管理模块 */}
        <Route path="/itineraries" element={<ItineraryListPage />} />
        <Route path="/itineraries/:id" element={<ItineraryWorkspace />} />
        
        {/* 智能导入模块 */}
        <Route path="/import" element={<SmartImportPage />} />
        
        {/* 一键生成模块 */}
        <Route path="/generate" element={<PlanGeneratorPage />} />
        
        {/* 个人中心模块 */}
        <Route path="/profile" element={<ProfilePage />} />
        
        {/* 管理员模块 */}
        <Route path="/admin/users" element={<RequireAdmin><UsersAdminPage /></RequireAdmin>} />
        <Route path="/admin/history" element={<RequireAdmin><HistoryAdminPage /></RequireAdmin>} />
        <Route path="/admin/attraction-details" element={<RequireAdmin><AttractionDetailsAdminPage /></RequireAdmin>} />
        <Route path="/admin/upgrade-control" element={<RequireAdmin><UpgradeControlPage /></RequireAdmin>} />
        
        {/* 默认路由 */}
        <Route path="/" element={<DiscoverPage />} />
      </Route>
    </Routes>
  );
};

export default AppRoutes;
