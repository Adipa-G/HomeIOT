import { Routes, Route } from 'react-router';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AppLayout } from './layouts/AppLayout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import DevicesPage from './pages/DevicesPage';
import DeviceDetailPage from './pages/DeviceDetailPage';
import ModulesPage from './pages/ModulesPage';
import ModuleCreatePage from './pages/ModuleCreatePage';
import ModuleDetailPage from './pages/ModuleDetailPage';
import ModuleResultsPage from './pages/ModuleResultsPage';
import ModuleStatusesPage from './pages/ModuleStatusesPage';
import OtaPlatformsPage from './pages/OtaPlatformsPage';
import OtaReleasesPage from './pages/OtaReleasesPage';
import OtaDetailPage from './pages/OtaDetailPage';
import UsersPage from './pages/UsersPage';
import DevCommandsPage from './pages/DevCommandsPage';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/devices" element={<DevicesPage />} />
          <Route path="/devices/:deviceId" element={<DeviceDetailPage />} />
          <Route path="/modules" element={<ModulesPage />} />
          <Route path="/modules/new" element={<ModuleCreatePage />} />
          <Route path="/modules/results" element={<ModuleResultsPage />} />
          <Route path="/modules/statuses" element={<ModuleStatusesPage />} />
          <Route path="/modules/:moduleId" element={<ModuleDetailPage />} />
          <Route path="/ota" element={<OtaPlatformsPage />} />
          <Route path="/ota/:platform" element={<OtaReleasesPage />} />
          <Route path="/ota/:platform/:version" element={<OtaDetailPage />} />
          <Route path="/users" element={<UsersPage />} />
          <Route path="/dev-commands" element={<DevCommandsPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
