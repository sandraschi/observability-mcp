import { PageHero } from "@/components/layout/PageHero";
import { Card, CardTitle } from "@/components/ui/card";

export function HelpPage() {
  return (
    <div className="space-y-6 max-w-3xl">
      <PageHero
        eyebrow="Guide"
        title="Help"
        lead="Observability-MCP is the control plane for the fleet PLG stack — not a second Grafana on port 3000."
      />
      <Card>
        <CardTitle>Quick start</CardTitle>
        <ol className="list-decimal list-inside text-sm text-muted-foreground mt-3 space-y-2">
          <li>Start unified monitoring (ports 12000–12006).</li>
          <li>
            Run this webapp:{" "}
            <code className="text-primary">web_sota/start.ps1</code>
          </li>
          <li>Open Charts to pick beginner-friendly Grafana dashboards.</li>
          <li>
            Use Tools page or IDE MCP on{" "}
            <code className="text-primary">http://127.0.0.1:12007/mcp</code>
          </li>
        </ol>
      </Card>
      <Card>
        <CardTitle>Ports</CardTitle>
        <ul className="text-xs font-mono mt-2 space-y-1 text-muted-foreground">
          <li>12000 Grafana · 12001 Prometheus · 12002 Loki</li>
          <li>12007 MCP HTTP · 12008 this UI · 12009 process /metrics</li>
        </ul>
      </Card>
      <Card>
        <CardTitle>Agentic workflow</CardTitle>
        <p className="text-sm text-muted-foreground mt-2">
          Tool{" "}
          <code className="text-primary">agentic_observability_workflow</code>{" "}
          runs stack check → error logs → MCP health. Set{" "}
          <code className="text-primary">OBSERVABILITY_SAMPLING_BASE_URL</code>{" "}
          for LLM-planned triage.
        </p>
      </Card>
    </div>
  );
}
