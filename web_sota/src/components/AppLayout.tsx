import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard, HeartPulse, ScrollText, Bell, Wifi, WifiOff, Loader2,
  MessageSquare, Sliders, Settings as SettingsIcon, Activity, Layers
} from "lucide-react";
import { useAppStore } from "../lib/store";

const NAV = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/health", icon: HeartPulse, label: "Health Monitor" },
  { to: "/logs", icon: ScrollText, label: "Log Explorer" },
  { to: "/grafana", icon: Layers, label: "Grafana" },
  { to: "/alerts", icon: Bell, label: "Alerts" },
  { to: "/visualizer", icon: Activity, label: "Visualizer" },
  { to: "/control", icon: Sliders, label: "Control" },
  { to: "/chat", icon: MessageSquare, label: "AI Chat" },
  { to: "/settings", icon: SettingsIcon, label: "Settings" },
];

export function AppLayout() {
  const { status } = useAppStore();

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100 font-sans overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 border-r border-zinc-800 flex flex-col bg-zinc-950/80 backdrop-blur-md">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded bg-amber-500/20 border border-amber-500/40 flex items-center justify-center">
              <span className="text-amber-400 text-xs font-mono font-bold">OB</span>
            </div>
            <div>
              <div className="text-sm font-semibold text-zinc-100 font-mono">observability</div>
              <div className="text-[10px] text-zinc-500 font-mono">mcp v0.1.0</div>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                  isActive
                    ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60"
                }`
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span className="font-mono">{label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Connection indicator */}
        <div className="px-4 py-4 border-t border-zinc-800">
          <div className="flex items-center gap-2 text-xs font-mono">
            {status === "connecting" && <Loader2 className="w-3 h-3 animate-spin text-zinc-500" />}
            {status === "connected" && <Wifi className="w-3 h-3 text-emerald-500" />}
            {status === "error" && <WifiOff className="w-3 h-3 text-red-500" />}
            <span className={
              status === "connected" ? "text-emerald-500" :
              status === "error" ? "text-red-500" : "text-zinc-500"
            }>
              {status === "connecting" ? "connecting…" : status === "connected" ? ":10902 ok" : "backend offline"}
            </span>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-8 max-w-6xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
