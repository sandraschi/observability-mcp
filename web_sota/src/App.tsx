import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { Dashboard } from "./pages/dashboard";
import { HealthMonitor } from "./pages/HealthMonitor";
import { LogExplorer } from "./pages/LogExplorer";
import { Alerts } from "./pages/Alerts";
import { Chat } from "./pages/chat";
import { Control } from "./pages/control";
import { Settings } from "./pages/settings";
import { Visualizer } from "./pages/visualizer";
import { GrafanaExplorer } from "./pages/GrafanaExplorer";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="health" element={<HealthMonitor />} />
          <Route path="logs" element={<LogExplorer />} />
          <Route path="alerts" element={<Alerts />} />
          <Route path="visualizer" element={<Visualizer />} />
          <Route path="grafana" element={<GrafanaExplorer />} />
          <Route path="control" element={<Control />} />
          <Route path="chat" element={<Chat />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
