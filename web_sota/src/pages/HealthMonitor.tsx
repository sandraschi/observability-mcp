import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  HeartPulse,
  Loader2,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import { callTool } from "../lib/mcp-client";

interface HealthResult {
  service_name: string;
  status: string;
  response_time_ms: number;
  timestamp: string;
  details?: { status_code?: number };
  error_message?: string;
}

interface CheckResult {
  health_check: HealthResult;
  historical_checks: number;
  recommendations: string[];
}

// Pre-seeded with common fleet MCP ports — user can add/remove
const FLEET_PRESETS = [
  { label: "observability-mcp", url: "http://127.0.0.1:12007/mcp" },
  { label: "advanced-memory", url: "http://127.0.0.1:10704/health" },
  { label: "docsops", url: "http://127.0.0.1:10794/health" },
  { label: "speechops", url: "http://127.0.0.1:10812/health" },
  { label: "worldlabs-mcp", url: "http://127.0.0.1:10865/health" },
  { label: "gitops", url: "http://127.0.0.1:10830/health" },
];

function StatusIcon({ status }: { status: string }) {
  if (status === "healthy")
    return <CheckCircle2 className="w-4 h-4 text-emerald-500" />;
  return <XCircle className="w-4 h-4 text-red-500" />;
}

function HealthCard({
  result,
  onClear,
}: {
  result: CheckResult;
  onClear: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const hc = result.health_check;
  const isHealthy = hc.status === "healthy";

  return (
    <div
      className={`border rounded-xl overflow-hidden transition-colors ${
        isHealthy
          ? "border-zinc-800 bg-zinc-900/50"
          : "border-red-900/60 bg-red-950/20"
      }`}
    >
      <div className="px-5 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <StatusIcon status={hc.status} />
          <div>
            <div className="font-mono text-sm text-zinc-100 truncate max-w-xs">
              {hc.service_name}
            </div>
            <div className="text-xs font-mono text-zinc-500 flex items-center gap-2 mt-0.5">
              <Clock className="w-3 h-3" />
              {hc.response_time_ms.toFixed(1)}ms
              {hc.details?.status_code && (
                <span className="text-zinc-600">
                  · HTTP {hc.details.status_code}
                </span>
              )}
              <span className="text-zinc-700">
                · {result.historical_checks} checks recorded
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setExpanded((e) => !e)}
            className="p-1 text-zinc-600 hover:text-zinc-400 transition-colors"
          >
            {expanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
          <button
            onClick={onClear}
            className="text-xs font-mono text-zinc-600 hover:text-zinc-400 px-2 py-1 transition-colors"
          >
            ×
          </button>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-zinc-800 px-5 py-4 space-y-3">
          {hc.error_message && (
            <div className="font-mono text-xs text-red-400 bg-red-950/30 rounded p-3">
              {hc.error_message}
            </div>
          )}
          {result.recommendations.length > 0 && (
            <div className="space-y-1">
              {result.recommendations.map((r, i) => (
                <div
                  key={i}
                  className="text-xs font-mono text-amber-400/80 flex gap-2"
                >
                  <span className="text-zinc-600">→</span> {r}
                </div>
              ))}
            </div>
          )}
          <div className="text-xs font-mono text-zinc-600">
            checked: {new Date(hc.timestamp).toLocaleTimeString()}
          </div>
        </div>
      )}
    </div>
  );
}

export function HealthMonitor() {
  const [url, setUrl] = useState("");
  const [timeout, setTimeout_] = useState(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<
    Array<{ id: number; data: CheckResult }>
  >([]);
  const [scanning, setScanning] = useState(false);

  async function check(targetUrl: string) {
    if (!targetUrl.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = (await callTool("monitor_server_health", {
        service_url: targetUrl.trim(),
        timeout_seconds: timeout,
      })) as CheckResult;
      setResults((r) => [{ id: Date.now(), data: result }, ...r]);
      setUrl("");
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function scanFleet() {
    setScanning(true);
    for (const preset of FLEET_PRESETS) {
      try {
        const result = (await callTool("monitor_server_health", {
          service_url: preset.url,
          timeout_seconds: 3,
        })) as CheckResult;
        setResults((r) => [
          { id: Date.now() + Math.random(), data: result },
          ...r,
        ]);
      } catch {
        /* individual failures collected in result */
      }
      await new Promise((res) => globalThis.setTimeout(res, 200));
    }
    setScanning(false);
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold font-mono text-zinc-100">
          Health Monitor
        </h1>
        <p className="text-zinc-500 font-mono text-sm mt-1">
          check any HTTP service endpoint
        </p>
      </div>

      {/* Input */}
      <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-5 space-y-4">
        <div className="flex gap-3">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && check(url)}
            placeholder="https://example.com/health"
            className="flex-1 bg-zinc-800/60 border border-zinc-700 rounded-lg px-4 py-2.5 text-sm font-mono text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-amber-500/50 transition-colors"
          />
          <input
            type="number"
            value={timeout}
            onChange={(e) => setTimeout_(Number(e.target.value))}
            min={1}
            max={30}
            className="w-20 bg-zinc-800/60 border border-zinc-700 rounded-lg px-3 py-2.5 text-sm font-mono text-zinc-100 focus:outline-none focus:border-amber-500/50 transition-colors text-center"
            title="Timeout (seconds)"
          />
          <button
            onClick={() => check(url)}
            disabled={loading || !url.trim()}
            className="px-5 py-2.5 bg-amber-500 hover:bg-amber-400 disabled:bg-zinc-700 disabled:text-zinc-500 text-zinc-900 font-mono text-sm font-semibold rounded-lg transition-colors flex items-center gap-2"
          >
            {loading && <Loader2 className="w-3 h-3 animate-spin" />}
            check
          </button>
        </div>

        {/* Fleet presets */}
        <div className="flex flex-wrap gap-2">
          {FLEET_PRESETS.map((p) => (
            <button
              key={p.label}
              onClick={() => setUrl(p.url)}
              className="px-2.5 py-1 text-xs font-mono rounded border border-zinc-700 text-zinc-500 hover:text-zinc-300 hover:border-zinc-600 transition-colors"
            >
              {p.label}
            </button>
          ))}
          <button
            onClick={scanFleet}
            disabled={scanning}
            className="px-2.5 py-1 text-xs font-mono rounded border border-amber-700/50 text-amber-600 hover:text-amber-400 hover:border-amber-500/50 transition-colors flex items-center gap-1 disabled:opacity-50"
          >
            {scanning && <Loader2 className="w-3 h-3 animate-spin" />}
            <HeartPulse className="w-3 h-3" />
            scan fleet
          </button>
        </div>
      </div>

      {error && (
        <div className="border border-red-900 bg-red-950/30 rounded-lg p-4 font-mono text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-mono uppercase tracking-widest text-zinc-500">
              Results ({results.length})
            </h2>
            <button
              onClick={() => setResults([])}
              className="text-xs font-mono text-zinc-600 hover:text-zinc-400 transition-colors"
            >
              clear all
            </button>
          </div>
          {results.map(({ id, data }) => (
            <HealthCard
              key={id}
              result={data}
              onClear={() => setResults((r) => r.filter((x) => x.id !== id))}
            />
          ))}
        </div>
      )}

      {results.length === 0 && !loading && (
        <div className="text-center py-16 text-zinc-700 font-mono text-sm">
          no results yet — enter a URL or scan fleet
        </div>
      )}
    </div>
  );
}
