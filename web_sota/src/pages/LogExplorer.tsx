import { useState } from "react";
import { callTool } from "../lib/mcp-client";
import { Search, AlertTriangle, TrendingUp, Loader2, ChevronDown, ChevronUp } from "lucide-react";

interface LogEntry { stream: Record<string, string>; values: [string, string][]; }
interface QueryResult { query: string; results: { data?: { result?: LogEntry[] } }; analysis: Record<string, unknown>; }
interface PatternResult { query: string; time_window: string; patterns: { common_patterns: Array<{ pattern: string; occurrences: number }> }; anomalies: Array<{ type: string; severity: string; description: string }>; trends: { trend: string; description: string }; recommendations: string[]; }

const TIME_WINDOWS = ["1h", "6h", "12h", "24h", "7d"];

export function LogExplorer() {
  const [query, setQuery] = useState('{service="observability-mcp"}');
  const [limit, setLimit] = useState(50);
  const [timeWindow, setTimeWindow] = useState("1h");
  const [mode, setMode] = useState<"query" | "patterns">("query");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [patternResult, setPatternResult] = useState<PatternResult | null>(null);
  const [expandedStreams, setExpandedStreams] = useState<Set<number>>(new Set());

  async function runQuery() {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      if (mode === "query") {
        const result = await callTool("query_loki_logs", { query: query.trim(), limit }) as QueryResult;
        setQueryResult(result);
        setPatternResult(null);
      } else {
        const result = await callTool("analyze_log_patterns", { query: query.trim(), time_window: timeWindow, min_occurrences: 2 }) as PatternResult;
        setPatternResult(result);
        setQueryResult(null);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  const entries: LogEntry[] = queryResult?.results?.data?.result ?? [];
  const totalEntries = entries.reduce((n, e) => n + e.values.length, 0);

  const toggleStream = (i: number) => setExpandedStreams((s) => {
    const n = new Set(s);
    n.has(i) ? n.delete(i) : n.add(i);
    return n;
  });

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold font-mono text-zinc-100">Log Explorer</h1>
        <p className="text-zinc-500 font-mono text-sm mt-1">LogQL queries via Loki</p>
      </div>

      {/* Controls */}
      <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-5 space-y-4">
        {/* Mode toggle */}
        <div className="flex gap-2">
          {(["query", "patterns"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-3 py-1.5 text-xs font-mono rounded transition-colors ${
                mode === m
                  ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                  : "text-zinc-500 border border-zinc-700 hover:text-zinc-300"
              }`}
            >
              {m}
            </button>
          ))}
        </div>

        {/* Query input */}
        <div className="flex gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runQuery()}
            placeholder='{job="my-service"} |= "ERROR"'
            className="flex-1 bg-zinc-800/60 border border-zinc-700 rounded-lg px-4 py-2.5 text-sm font-mono text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-amber-500/50 transition-colors"
          />
          {mode === "query" ? (
            <input
              type="number"
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              min={1} max={1000}
              className="w-20 bg-zinc-800/60 border border-zinc-700 rounded-lg px-3 py-2.5 text-sm font-mono text-zinc-100 focus:outline-none focus:border-amber-500/50 transition-colors text-center"
              title="Limit"
            />
          ) : (
            <div className="flex gap-1">
              {TIME_WINDOWS.map((tw) => (
                <button
                  key={tw}
                  onClick={() => setTimeWindow(tw)}
                  className={`px-2.5 py-1.5 text-xs font-mono rounded transition-colors ${
                    timeWindow === tw
                      ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                      : "text-zinc-500 border border-zinc-700 hover:text-zinc-300"
                  }`}
                >
                  {tw}
                </button>
              ))}
            </div>
          )}
          <button
            onClick={runQuery}
            disabled={loading}
            className="px-5 py-2.5 bg-amber-500 hover:bg-amber-400 disabled:bg-zinc-700 disabled:text-zinc-500 text-zinc-900 font-mono text-sm font-semibold rounded-lg transition-colors flex items-center gap-2"
          >
            {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Search className="w-3 h-3" />}
            run
          </button>
        </div>

        {/* Example queries */}
        <div className="flex flex-wrap gap-2 text-xs font-mono">
          <span className="text-zinc-600">examples:</span>
          {[
            '{service="observability-mcp"}',
            '{service="observability-mcp"} |= "error"',
            '{level="error"}',
          ].map((q) => (
            <button key={q} onClick={() => setQuery(q)} className="text-zinc-500 hover:text-amber-400 transition-colors">
              {q}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="border border-red-900 bg-red-950/30 rounded-lg p-4 font-mono text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Query results */}
      {queryResult && !loading && (
        <div className="space-y-4">
          <div className="text-xs font-mono text-zinc-500 flex items-center gap-4">
            <span>{totalEntries} log entries</span>
            <span className="text-zinc-700">·</span>
            <span>{entries.length} streams</span>
            {queryResult.analysis && typeof queryResult.analysis === "object" && (queryResult.analysis as Record<string, unknown>).total_entries !== undefined && (
              <>
                <span className="text-zinc-700">·</span>
                <span>{String((queryResult.analysis as Record<string, unknown>).unique_services ?? 0)} services</span>
              </>
            )}
          </div>

          {entries.length === 0 && (
            <div className="text-center py-12 text-zinc-700 font-mono text-sm border border-zinc-800 rounded-xl">
              no results — Loki may not be running or no logs match the query
            </div>
          )}

          {entries.map((entry, i) => (
            <div key={i} className="border border-zinc-800 rounded-xl overflow-hidden">
              <button
                className="w-full px-5 py-3 flex items-center justify-between hover:bg-zinc-800/30 transition-colors"
                onClick={() => toggleStream(i)}
              >
                <div className="flex gap-3 text-xs font-mono text-left flex-wrap">
                  {Object.entries(entry.stream).map(([k, v]) => (
                    <span key={k}>
                      <span className="text-zinc-600">{k}=</span>
                      <span className="text-amber-400">"{v}"</span>
                    </span>
                  ))}
                </div>
                <div className="flex items-center gap-2 text-xs font-mono text-zinc-600 flex-shrink-0 ml-4">
                  {entry.values.length} entries
                  {expandedStreams.has(i) ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </div>
              </button>
              {expandedStreams.has(i) && (
                <div className="border-t border-zinc-800 bg-zinc-950/50 divide-y divide-zinc-900 max-h-80 overflow-y-auto">
                  {entry.values.map(([ts, msg], j) => {
                    const t = new Date(Number(ts) / 1_000_000);
                    const isError = /error|exception|fail/i.test(msg);
                    return (
                      <div key={j} className="px-5 py-2 flex gap-4 text-xs font-mono hover:bg-zinc-900/40">
                        <span className="text-zinc-700 flex-shrink-0 w-24">
                          {t.toLocaleTimeString()}
                        </span>
                        <span className={isError ? "text-red-400" : "text-zinc-400"}>{msg}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Pattern results */}
      {patternResult && !loading && (
        <div className="space-y-6">
          <div className="text-xs font-mono text-zinc-500">
            window: {patternResult.time_window} · {patternResult.patterns.common_patterns.length} patterns
          </div>

          {/* Anomalies */}
          {patternResult.anomalies.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-mono uppercase tracking-widest text-red-500">Anomalies</h3>
              {patternResult.anomalies.map((a, i) => (
                <div key={i} className="border border-red-900/40 bg-red-950/20 rounded-lg px-4 py-3 flex items-start gap-3">
                  <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="text-sm font-mono text-red-300">{a.description}</div>
                    <div className="text-xs font-mono text-zinc-500 mt-1">{a.type} · {a.severity}</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Trend */}
          <div className="border border-zinc-800 bg-zinc-900/50 rounded-lg px-4 py-3 flex items-center gap-3">
            <TrendingUp className="w-4 h-4 text-zinc-500" />
            <div className="text-sm font-mono text-zinc-400">
              {patternResult.trends.description}
              <span className={`ml-2 text-xs ${patternResult.trends.trend === "increasing" ? "text-amber-400" : "text-zinc-600"}`}>
                [{patternResult.trends.trend}]
              </span>
            </div>
          </div>

          {/* Patterns table */}
          {patternResult.patterns.common_patterns.length > 0 ? (
            <div className="border border-zinc-800 rounded-xl overflow-hidden">
              <div className="px-5 py-3 border-b border-zinc-800 flex justify-between text-xs font-mono text-zinc-600 uppercase tracking-widest">
                <span>Pattern</span><span>Occurrences</span>
              </div>
              {patternResult.patterns.common_patterns.map((p, i) => (
                <div key={i} className="px-5 py-2.5 flex justify-between items-center hover:bg-zinc-900/40 border-b border-zinc-900 last:border-0">
                  <span className="font-mono text-sm text-zinc-300 truncate max-w-md">{p.pattern}</span>
                  <span className="font-mono text-sm text-amber-400 flex-shrink-0">{p.occurrences}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-zinc-700 font-mono text-sm border border-zinc-800 rounded-xl">
              no patterns found matching threshold
            </div>
          )}

          {/* Recommendations */}
          {patternResult.recommendations.length > 0 && (
            <div className="space-y-1">
              {patternResult.recommendations.map((r, i) => (
                <div key={i} className="text-xs font-mono text-amber-400/70 flex gap-2">
                  <span className="text-zinc-600">→</span>{r}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
