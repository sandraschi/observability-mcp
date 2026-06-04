import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { Alerts } from "./pages/Alerts";
import { AppsPage } from "./pages/AppsPage";
import { ChatPage } from "./pages/ChatPage";
import { Control } from "./pages/control";
import { Dashboard } from "./pages/dashboard";
import { GrafanaDashboards } from "./pages/GrafanaDashboards";
import { GrafanaExplorer } from "./pages/GrafanaExplorer";
import { HealthMonitor } from "./pages/HealthMonitor";
import { ApiDocsPage } from "./pages/ApiDocsPage";
import { HelpPage } from "./pages/HelpPage";
import { LogExplorer } from "./pages/LogExplorer";
import { LogsPage } from "./pages/LogsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SkillsPage } from "./pages/SkillsPage";
import { ToolsPage } from "./pages/ToolsPage";
import { Visualizer } from "./pages/visualizer";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="health" element={<HealthMonitor />} />
          <Route path="loki" element={<LogExplorer />} />
          <Route path="logs" element={<LogsPage />} />
          <Route path="alerts" element={<Alerts />} />
          <Route path="visualizer" element={<Visualizer />} />
          <Route path="grafana" element={<GrafanaDashboards />} />
          <Route path="grafana/manage" element={<GrafanaExplorer />} />
          <Route path="control" element={<Control />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="tools" element={<ToolsPage />} />
          <Route path="skills" element={<SkillsPage />} />
          <Route path="apps" element={<AppsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="api" element={<ApiDocsPage />} />
          <Route path="help" element={<HelpPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
