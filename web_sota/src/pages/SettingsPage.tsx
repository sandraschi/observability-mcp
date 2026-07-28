import { useEffect, useState } from "react";
import { apiGet } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { Card, CardTitle } from "@/components/ui/card";
import { useLogger } from "@/context/LoggerContext";

type Stats = {
  version?: string;
  tool_count?: number;
  grafana_url?: string;
  prometheus_url?: string;
  loki_url?: string;
  mcp_port?: number;
};

type LlmDiscover = {
  ollama_detected?: boolean;
  configured_sampling_url?: string | null;
  configured_model?: string;
  recommendation?: string | null;
};

export function SettingsPage() {
  const { log } = useLogger();
  const [stats, setStats] = useState<Stats | null>(null);
  const [llm, setLlm] = useState<LlmDiscover | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setStats(await apiGet<Stats>("/api/stats"));
      } catch (e) {
        log("error", String(e));
      }
    })();
    (async () => {
      try {
        setLlm(await apiGet<LlmDiscover>("/api/llm/discover"));
      } catch (e) {
        log("error", String(e));
      }
    })();
  }, [log]);

  return (
    <div className="space-y-6 max-w-2xl">
      <PageHero
        eyebrow="Configuration"
        title="Settings"
        lead="Unified PLG endpoints (12000–12002), MCP HTTP on 12007, and optional Ollama for chat and agentic sampling."
      />
      <Card>
        <CardTitle>Server</CardTitle>
        <p className="text-sm text-muted-foreground mt-2 font-mono">
          observability-mcp v{stats?.version ?? "…"} · {stats?.tool_count ?? 0}{" "}
          tools
        </p>
        <p className="text-xs text-muted-foreground mt-2">
          MCP HTTP port: {stats?.mcp_port ?? 12007}
        </p>
      </Card>
      <Card>
        <CardTitle>Unified monitoring (PLG)</CardTitle>
        <ul className="text-xs font-mono mt-2 space-y-1 text-muted-foreground">
          <li>Grafana: {stats?.grafana_url ?? "http://127.0.0.1:12000"}</li>
          <li>
            Prometheus: {stats?.prometheus_url ?? "http://127.0.0.1:12001"}
          </li>
          <li>Loki: {stats?.loki_url ?? "http://127.0.0.1:12002"}</li>
        </ul>
        <p className="text-xs text-muted-foreground mt-3">
          Start stack:{" "}
          <code className="text-primary">
            mcp-central-docs/monitoring/start-unified-monitoring.ps1
          </code>
        </p>
      </Card>
      <Card>
        <CardTitle>Local LLM</CardTitle>
        <p className="text-sm text-muted-foreground mt-2">
          {llm?.ollama_detected
            ? "Ollama detected on :11434"
            : "Ollama not detected"}
        </p>
        <p className="text-xs font-mono mt-2 break-all">
          {llm?.configured_sampling_url ||
            "OBSERVABILITY_SAMPLING_BASE_URL / LLM_BASE_URL not set"}
        </p>
        <p className="text-xs text-muted-foreground mt-2">
          Model: {llm?.configured_model ?? "llama3.2"}
        </p>
        {llm?.recommendation ? (
          <p className="text-xs text-primary mt-2">{llm.recommendation}</p>
        ) : null}
      </Card>
      <Card>
        <CardTitle>Process metrics</CardTitle>
        <p className="text-sm text-muted-foreground mt-2">
          This MCP exposes <code className="text-primary">/metrics</code> on{" "}
          <code className="text-primary">PROMETHEUS_PORT</code> (default 12009).
          That is not the Prometheus server on 12001.
        </p>
      </Card>
    </div>
  );
}
