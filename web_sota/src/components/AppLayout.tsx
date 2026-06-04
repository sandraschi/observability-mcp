import { useState } from "react";
import {
  Activity,
  Bell,
  BookOpen,
  FileCode,
  HeartPulse,
  HelpCircle,
  Layers,
  LayoutDashboard,
  LayoutGrid,
  Menu,
  MessageSquare,
  ScrollText,
  Search,
  Settings,
  Sliders,
  Terminal,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { ConnectionBootstrap } from "@/components/ConnectionBootstrap";
import { LoggerPanel } from "@/components/layout/LoggerPanel";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/lib/store";

const nav = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/grafana", label: "Charts", icon: Layers },
  { to: "/health", label: "Health", icon: HeartPulse },
  { to: "/loki", label: "Loki", icon: Search },
  { to: "/tools", label: "Tools", icon: Terminal },
  { to: "/api", label: "API docs", icon: FileCode },
  { to: "/chat", label: "Chat", icon: MessageSquare },
  { to: "/logs", label: "Logs", icon: ScrollText },
  { to: "/skills", label: "Skills", icon: BookOpen },
  { to: "/apps", label: "Fleet apps", icon: LayoutGrid },
  { to: "/alerts", label: "Alerts", icon: Bell },
  { to: "/visualizer", label: "Visualizer", icon: Activity },
  { to: "/control", label: "Control", icon: Sliders },
  { to: "/settings", label: "Settings", icon: Settings },
  { to: "/help", label: "Help", icon: HelpCircle },
] as const;

export function AppLayout() {
  const [open, setOpen] = useState(true);
  const [mobile, setMobile] = useState(false);
  const loc = useLocation();
  const { status } = useAppStore();

  return (
    <div className="min-h-screen flex text-foreground">
      <ConnectionBootstrap />
      <aside
        className={cn(
          "hidden md:flex flex-col border-r border-border bg-card/40 backdrop-blur-xl h-screen sticky top-0 z-30 transition-all duration-300",
          open ? "w-64" : "w-[4.5rem]",
        )}
      >
        <div className="h-14 flex items-center gap-2 px-4 border-b border-border/60">
          <div className="w-8 h-8 rounded bg-primary/20 border border-primary/40 flex items-center justify-center shrink-0">
            <span className="text-primary text-xs font-mono font-bold">OB</span>
          </div>
          {open && (
            <div>
              <div className="font-bold leading-tight font-mono text-sm">observability-mcp</div>
              <div className="text-[10px] text-muted-foreground">v0.3.0b1 · :12008</div>
            </div>
          )}
        </div>
        <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors font-mono",
                  isActive ? "bg-secondary text-secondary-foreground" : "hover:bg-muted/50",
                  !open && "justify-center px-2",
                )
              }
              title={!open ? label : undefined}
            >
              <Icon className="h-5 w-5 shrink-0" />
              {open && label}
            </NavLink>
          ))}
        </nav>
        <div className="px-3 py-3 border-t border-border/60 text-xs font-mono flex items-center gap-2">
          {status === "connected" ? (
            <Wifi className="h-3 w-3 text-primary shrink-0" />
          ) : (
            <WifiOff className="h-3 w-3 text-red-400 shrink-0" />
          )}
          {open && (
            <span className={status === "connected" ? "text-primary" : "text-muted-foreground"}>
              {status === "connected" ? ":12007 ok" : status === "connecting" ? "connecting…" : "offline"}
            </span>
          )}
        </div>
        <div className="p-2 border-t border-border/60">
          <Button variant="ghost" className="w-full" size="sm" onClick={() => setOpen(!open)}>
            {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </Button>
        </div>
      </aside>

      <div className="md:hidden fixed top-0 left-0 right-0 z-50 h-12 border-b border-border bg-background/90 backdrop-blur flex items-center px-3 gap-2">
        <Button variant="ghost" size="icon" onClick={() => setMobile(!mobile)}>
          <Menu className="h-5 w-5" />
        </Button>
        <span className="font-semibold text-sm font-mono">observability-mcp</span>
      </div>
      {mobile && (
        <div className="md:hidden fixed inset-0 z-40 bg-background/95 pt-14 px-3 pb-6 overflow-y-auto">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setMobile(false)}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-3 text-sm mb-1 font-mono",
                loc.pathname === to ? "bg-secondary" : "hover:bg-muted/50",
              )}
            >
              <Icon className="h-5 w-5" />
              {label}
            </NavLink>
          ))}
        </div>
      )}

      <div className="flex-1 flex flex-col min-w-0 min-h-screen pt-12 md:pt-0 pb-24 md:pb-28">
        <header className="hidden md:flex h-14 items-center border-b border-border/60 px-6 bg-background/40 backdrop-blur-sm sticky top-0 z-20">
          <div className="text-sm text-muted-foreground font-mono">
            MCP <code className="text-primary">/mcp</code> · API <code className="text-primary">/api</code> · PLG{" "}
            <code className="text-primary">12000–12002</code>
          </div>
        </header>
        <main className="flex-1 p-4 md:p-6 max-w-6xl w-full mx-auto">
          <Outlet />
        </main>
      </div>

      <LoggerPanel />
    </div>
  );
}
