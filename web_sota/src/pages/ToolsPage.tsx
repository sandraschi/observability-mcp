import { useEffect, useState } from "react";
import { apiGet } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { Card, CardTitle } from "@/components/ui/card";
import { useLogger } from "@/context/LoggerContext";

type ToolRow = { name: string; description: string };
type PromptRow = { name: string; description: string };

export function ToolsPage() {
  const { log } = useLogger();
  const [tools, setTools] = useState<ToolRow[]>([]);
  const [prompts, setPrompts] = useState<PromptRow[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const t = await apiGet<{ tools: ToolRow[] }>("/api/tools");
        setTools(t.tools ?? []);
        log("info", `Loaded ${t.tools?.length ?? 0} tools`);
      } catch (e) {
        log("error", String(e));
      }
    })();
    (async () => {
      try {
        const p = await apiGet<{ prompts: PromptRow[] }>("/api/prompts");
        setPrompts(p.prompts ?? []);
      } catch (e) {
        log("error", String(e));
      }
    })();
  }, [log]);

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="MCP surface"
        title="Tools & prompts"
        lead="Registered on the server at :12007. Call via IDE MCP client or JSON-RPC at /mcp."
      />
      <Card>
        <CardTitle>Tools ({tools.length})</CardTitle>
        <ul className="mt-4 space-y-3 max-h-[50vh] overflow-y-auto">
          {tools.map((t) => (
            <li key={t.name} className="border-b border-border/40 pb-2">
              <div className="font-mono text-sm text-primary">{t.name}</div>
              <div className="text-xs text-muted-foreground mt-1">
                {t.description || "—"}
              </div>
            </li>
          ))}
        </ul>
      </Card>
      <Card>
        <CardTitle>Prompts ({prompts.length})</CardTitle>
        <ul className="mt-4 space-y-2">
          {prompts.map((p) => (
            <li key={p.name}>
              <span className="font-mono text-sm text-primary">{p.name}</span>
              <span className="text-xs text-muted-foreground block">
                {p.description}
              </span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
