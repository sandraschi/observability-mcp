import { Layers } from "lucide-react";
import {
  Cpu,
  HardDrive,
  MemoryStick,
  Minus,
  Network,
  RefreshCw,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { callTool } from "../lib/mcp-client";
import { useAppStore } from "../lib/store";

interface Metrics {
  service_name: string;
  timestamp: string;
  cpu_percent: number;
  memory_mb: number;
  disk_usage_percent: number;
  network_io: {
    bytes_sent: number;
    bytes_recv: number;
    packets_sent: number;
    packets_recv: number;
  };
}

interface HistoryPoint {
  cpu_percent: number;
  memory_mb: number;
}

function Sparkline({ data, color }: { data: number[]; color: string }) {
  if (data.length < 2) return <div className="h-8 w-full" />;
  const max = Math.max(...data, 1);
  const w = 120;
  const h = 32;
  const pts = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * w;
      const y = h - (v / max) * h;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg width={w} height={h} className="overflow-visible">
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function Trend({
  history,
  field,
}: { history: HistoryPoint[]; field: keyof HistoryPoint }) {
  if (history.length < 3) return <Minus className="w-3 h-3 text-zinc-500" />;
  const recent = history.slice(-5).map((h) => h[field] as number);
  const avg =
    recent.slice(0, -1).reduce((a, b) => a + b, 0) / (recent.length - 1);
  const last = recent[recent.length - 1];
  if (last > avg * 1.05) return <TrendingUp className="w-3 h-3 text-red-400" />;
  if (last < avg * 0.95)
    return <TrendingDown className="w-3 h-3 text-emerald-400" />;
  return <Minus className="w-3 h-3 text-zinc-500" />;
}

function GaugeBar({
  value,
  max = 100,
  warn = 70,
  crit = 90,
}: { value: number; max?: number; warn?: number; crit?: number }) {
  const pct = Math.min((value / max) * 100, 100);
  const color =
    pct >= crit
      ? "bg-red-500"
      : pct >= warn
        ? "bg-amber-500"
        : "bg-emerald-500";
  return (
    <div className="h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-500 ${color}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export function Dashboard() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [trends, setTrends] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const { setStatus } = useAppStore();
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function fetchMetrics() {
    try {
      const result = (await callTool("collect_performance_metrics", {
        service_name: "system",
      })) as {
        metrics: Metrics;
        trends: Record<string, string>;
      };
      setMetrics(result.metrics);
      setTrends(result.trends ?? {});
      setHistory((h) => [
        ...h.slice(-29),
        {
          cpu_percent: result.metrics.cpu_percent,
          memory_mb: result.metrics.memory_mb,
        },
      ]);
      setLastUpdated(new Date());
      setStatus("connected");
      setError(null);
    } catch (e) {
      setError(String(e));
      setStatus("error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchMetrics();
    intervalRef.current = setInterval(fetchMetrics, 5000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const fmtMb = (mb: number) =>
    mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb.toFixed(0)} MB`;
  const fmtBytes = (b: number) =>
    b >= 1e9
      ? `${(b / 1e9).toFixed(1)} GB`
      : b >= 1e6
        ? `${(b / 1e6).toFixed(1)} MB`
        : `${(b / 1e3).toFixed(0)} KB`;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold font-mono text-zinc-100">
            System Metrics
          </h1>
          <p className="text-zinc-500 font-mono text-sm mt-1">
            {lastUpdated
              ? `updated ${lastUpdated.toLocaleTimeString()}`
              : "polling…"}
          </p>
        </div>
        <button
          onClick={fetchMetrics}
          className="flex items-center gap-2 px-3 py-1.5 rounded border border-zinc-700 text-zinc-400 hover:text-zinc-200 hover:border-zinc-600 text-xs font-mono transition-colors"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
          refresh
        </button>
      </div>

      {error && (
        <div className="border border-red-900 bg-red-950/30 rounded-lg p-4 font-mono text-sm text-red-400">
          {error}
        </div>
      )}

      <Link
        to="/grafana"
        className="flex items-center justify-between gap-4 rounded-xl border border-amber-500/25 bg-gradient-to-r from-amber-950/30 to-zinc-900/50 px-5 py-4 hover:border-amber-500/40 transition-colors group"
      >
        <div className="flex items-center gap-3">
          <Layers className="w-8 h-8 text-amber-500/90" />
          <div>
            <p className="font-medium text-zinc-100">Open Grafana dashboards</p>
            <p className="text-sm text-zinc-500">
              Categorized chart picker — no crayons required
            </p>
          </div>
        </div>
        <span className="text-sm text-amber-400 group-hover:text-amber-300 font-mono">
          Charts →
        </span>
      </Link>

      {/* KPI grid */}
      <div className="grid grid-cols-2 gap-4">
        {/* CPU */}
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-zinc-400">
              <Cpu className="w-4 h-4" />
              <span className="text-xs font-mono uppercase tracking-widest">
                CPU
              </span>
            </div>
            <Trend history={history} field="cpu_percent" />
          </div>
          <div className="flex items-end justify-between">
            <div className="text-4xl font-mono font-bold text-zinc-100">
              {loading ? "—" : `${metrics?.cpu_percent.toFixed(1)}%`}
            </div>
            <Sparkline
              data={history.map((h) => h.cpu_percent)}
              color="#f59e0b"
            />
          </div>
          <GaugeBar value={metrics?.cpu_percent ?? 0} warn={70} crit={90} />
          <div className="text-xs font-mono text-zinc-500">
            {trends.cpu_trend ? `trend: ${trends.cpu_trend}` : ""}
          </div>
        </div>

        {/* Memory */}
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-zinc-400">
              <MemoryStick className="w-4 h-4" />
              <span className="text-xs font-mono uppercase tracking-widest">
                Memory
              </span>
            </div>
            <Trend history={history} field="memory_mb" />
          </div>
          <div className="flex items-end justify-between">
            <div className="text-4xl font-mono font-bold text-zinc-100">
              {loading ? "—" : fmtMb(metrics?.memory_mb ?? 0)}
            </div>
            <Sparkline data={history.map((h) => h.memory_mb)} color="#3b82f6" />
          </div>
          <GaugeBar
            value={metrics?.memory_mb ?? 0}
            max={65536}
            warn={49152}
            crit={58982}
          />
          <div className="text-xs font-mono text-zinc-500">
            {trends.memory_trend ? `trend: ${trends.memory_trend}` : ""}
          </div>
        </div>

        {/* Disk */}
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-zinc-400">
              <HardDrive className="w-4 h-4" />
              <span className="text-xs font-mono uppercase tracking-widest">
                Disk
              </span>
            </div>
          </div>
          <div className="text-4xl font-mono font-bold text-zinc-100">
            {loading ? "—" : `${metrics?.disk_usage_percent.toFixed(1)}%`}
          </div>
          <GaugeBar
            value={metrics?.disk_usage_percent ?? 0}
            warn={75}
            crit={90}
          />
        </div>

        {/* Network */}
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-zinc-400">
              <Network className="w-4 h-4" />
              <span className="text-xs font-mono uppercase tracking-widest">
                Network
              </span>
            </div>
          </div>
          <div className="space-y-2 font-mono text-sm">
            <div className="flex justify-between text-zinc-300">
              <span className="text-zinc-500">↑ sent</span>
              <span>
                {loading ? "—" : fmtBytes(metrics?.network_io.bytes_sent ?? 0)}
              </span>
            </div>
            <div className="flex justify-between text-zinc-300">
              <span className="text-zinc-500">↓ recv</span>
              <span>
                {loading ? "—" : fmtBytes(metrics?.network_io.bytes_recv ?? 0)}
              </span>
            </div>
            <div className="flex justify-between text-zinc-400 text-xs pt-1 border-t border-zinc-800">
              <span className="text-zinc-600">pkts sent</span>
              <span>
                {loading
                  ? "—"
                  : (metrics?.network_io.packets_sent ?? 0).toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between text-zinc-400 text-xs">
              <span className="text-zinc-600">pkts recv</span>
              <span>
                {loading
                  ? "—"
                  : (metrics?.network_io.packets_recv ?? 0).toLocaleString()}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Prometheus hint */}
      <div className="border border-zinc-800 rounded-lg px-4 py-3 flex items-center gap-3 text-xs font-mono text-zinc-500">
        <span className="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" />
        Prometheus scrape endpoint active on{" "}
        <span className="text-amber-400">:12009</span> — unified Grafana on
        :12000
      </div>
    </div>
  );
}
