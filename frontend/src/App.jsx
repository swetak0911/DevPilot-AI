import React from 'react';
import { BrowserRouter, Routes, Route, Outlet, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/common/Navbar';
import Sidebar from './components/common/Sidebar';

import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import RepositoryExplorerPage from './pages/RepositoryExplorerPage';
import TaskCreationPage from './pages/TaskCreationPage';
import AgentWorkspacePage from './pages/AgentWorkspacePage';
import CodeReviewPage from './pages/CodeReviewPage';
import DevOpsPage from './pages/DevOpsPage';
import DeploymentRiskPage from './pages/DeploymentRiskPage';
import MonitoringPage from './pages/MonitoringPage';
import SettingsPage from './pages/SettingsPage';

function AppLayout() {
  return (
    <div className="min-h-screen bg-surface-950 flex flex-col text-slate-100">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 overflow-x-hidden min-h-[calc(100vh-4rem)]">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* App Dashboard & Engineering Workspaces */}
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/repositories" element={<RepositoryExplorerPage />} />
            <Route path="/tasks/new" element={<TaskCreationPage />} />
            <Route path="/workspace" element={<AgentWorkspacePage />} />
            <Route path="/agent" element={<Navigate to="/workspace" replace />} />
            <Route path="/review" element={<CodeReviewPage />} />
            <Route path="/devops" element={<DevOpsPage />} />
            <Route path="/risk" element={<DeploymentRiskPage />} />
            <Route path="/monitoring" element={<MonitoringPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
