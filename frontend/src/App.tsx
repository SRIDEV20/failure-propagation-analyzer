import { Navigate, Route, Routes } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { DashboardProvider } from './context/DashboardContext';
import { AlertsPage } from './features/alerts/AlertsPage';
import { GraphPage } from './features/graph/GraphPage';
import { ImpactPage } from './features/impact/ImpactPage';
import { LogsPage } from './features/logs/LogsPage';
import { OverviewPage } from './features/overview/OverviewPage';

export default function App() {
  return (
    <DashboardProvider>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/graph" element={<GraphPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/impact" element={<ImpactPage />} />
          <Route path="/logs" element={<LogsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </DashboardProvider>
  );
}
