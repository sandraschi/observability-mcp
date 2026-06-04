import {
  AlertCircle,
  AlertTriangle,
  Bell,
  Info,
  Loader2,
  Send,
  Zap,
} from "lucide-react";
import { useState } from "react";
import { callTool } from "../lib/mcp-client";

interface AlertConfig {
  metric_name: string;
  threshold: number;
  operator: string;
  severity: string;
  enabled: boolean;
}

const DEFAULT_ALERTS: AlertConfig[] = [
  {
    metric_name: "cpu_percent",
    threshold: 90.0,
    operator: "gt",
    severity: "warning",
    enabled: true,
  },
  {
    metric_name: "memory_mb",
    threshold: 1000.0,
    operator: "gt",
    severity: "error",
    enabled: true,
  },
  {
    metric_name: "error_rate",
    threshold: 0.05,
    operator: "gt",
    severity: "error",
    enabled: true,
  },
];

const SEVERITY_STYLES: Record<string, string> = {
  info: "text-blue-400 border-blue-900/40 bg-blue-950/20",
  warning: "text-amber-400 border-amber-900/40 bg-amber-950/20",
  error: "text-red-400 border-red-900/40 bg-red-950/20",
  critical: "text-rose-400 border-rose-900/40 bg-rose-950/20",
};

function SeverityIcon({ severity }: { severity: string }) {
  if (severity === "info") return <Info className="w-4 h-4" />;
  if (severity === "warning") return <AlertTriangle className="w-4 h-4" />;
  if (severity === "critical") return <Zap className="w-4 h-4" />;
  return <AlertCircle className="w-4 h-4" />;
}

export function Alerts() {
  const [logMsg, setLogMsg] = useState("");
  const [logLevel, setLogLevel] = useState("info");
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState<string | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);

  async function sendLog() {
    if (!logMsg.trim()) return;
    setSending(true);
    setSendResult(null);
    setSendError(null);
    try {
      const result = (await callTool("send_logs_to_loki", {
        log_message: logMsg.trim(),
        level: logLevel,
        labels: { source: "webapp" },
      })) as { status: string; timestamp: string; loki_endpoint: string };
      setSendResult(
        `sent at ${new Date(result.timestamp).toLocaleTimeString()} → ${result.loki_endpoint}`,
      );
      setLogMsg("");
    } catch (e) {
      setSendError(String(e));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold font-mono text-zinc-100">Alerts</h1>
        <p className="text-zinc-500 font-mono text-sm mt-1">
          configured thresholds &amp; manual log injection
        </p>
      </div>

      {/* Active alert configs */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4 text-zinc-500" />
          <h2 className="text-xs font-mono uppercase tracking-widest text-zinc-500">
            Active Alert Configs
          </h2>
        </div>
        <p className="text-xs font-mono text-zinc-600">
          Loaded at server startup. Edit thresholds in server.py →{" "}
          <span className="text-zinc-400">default_alerts</span> and restart.
        </p>

        <div className="space-y-3">
          {DEFAULT_ALERTS.map((alert, i) => (
            <div
              key={i}
              className={`border rounded-xl px-5 py-4 flex items-center justify-between ${SEVERITY_STYLES[alert.severity] ?? SEVERITY_STYLES.info}`}
            >
              <div className="flex items-center gap-3">
                <SeverityIcon severity={alert.severity} />
                <div>
                  <div className="font-mono text-sm font-semibold">
                    {alert.metric_name}
                  </div>
                  <div className="font-mono text-xs mt-0.5 opacity-70">
                    {alert.operator === "gt"
                      ? ">"
                      : alert.operator === "lt"
                        ? "<"
                        : alert.operator}{" "}
                    {alert.threshold.toLocaleString()}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono opacity-70 uppercase">
                  {alert.severity}
                </span>
                <div
                  className={`w-2 h-2 rounded-full ${alert.enabled ? "bg-current" : "bg-zinc-700"}`}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-zinc-800" />

      {/* Manual log injection */}
      <div className="space-y-4">
        <h2 className="text-xs font-mono uppercase tracking-widest text-zinc-500">
          Manual Log Injection
        </h2>
        <p className="text-xs font-mono text-zinc-600">
          Send a log entry directly to Loki — useful for annotating deployments
          or incidents.
        </p>

        <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-5 space-y-4">
          <div className="flex gap-2">
            {(["debug", "info", "warning", "error", "critical"] as const).map(
              (lvl) => (
                <button
                  key={lvl}
                  onClick={() => setLogLevel(lvl)}
                  className={`px-2.5 py-1 text-xs font-mono rounded transition-colors ${
                    logLevel === lvl
                      ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                      : "text-zinc-600 border border-zinc-700 hover:text-zinc-400"
                  }`}
                >
                  {lvl}
                </button>
              ),
            )}
          </div>

          <div className="flex gap-3">
            <input
              type="text"
              value={logMsg}
              onChange={(e) => setLogMsg(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendLog()}
              placeholder="Deployment complete: observability-mcp v0.1.1"
              className="flex-1 bg-zinc-800/60 border border-zinc-700 rounded-lg px-4 py-2.5 text-sm font-mono text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-amber-500/50 transition-colors"
            />
            <button
              onClick={sendLog}
              disabled={sending || !logMsg.trim()}
              className="px-5 py-2.5 bg-amber-500 hover:bg-amber-400 disabled:bg-zinc-700 disabled:text-zinc-500 text-zinc-900 font-mono text-sm font-semibold rounded-lg transition-colors flex items-center gap-2"
            >
              {sending ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <Send className="w-3 h-3" />
              )}
              send
            </button>
          </div>

          {sendResult && (
            <div className="font-mono text-xs text-emerald-400 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 flex-shrink-0" />
              {sendResult}
            </div>
          )}
          {sendError && (
            <div className="font-mono text-xs text-red-400 bg-red-950/30 rounded p-3">
              {sendError}
            </div>
          )}
        </div>
      </div>

      {/* Loki info */}
      <div className="border border-zinc-800 rounded-lg px-4 py-3 text-xs font-mono text-zinc-600 space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-zinc-700">Loki endpoint:</span>
          <span className="text-zinc-400">
            {import.meta.env.VITE_LOKI_URL ?? "http://127.0.0.1:12002"}
          </span>
        </div>
        <div className="text-zinc-700">
          Set <span className="text-zinc-500">LOKI_URL</span> env var on the
          backend to point to your Loki instance. Use the Log Explorer page to
          query collected logs.
        </div>
      </div>
    </div>
  );
}
