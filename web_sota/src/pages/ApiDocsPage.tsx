import { PageHero } from "@/components/layout/PageHero";

export function ApiDocsPage() {
  return (
    <div className="space-y-4 h-[calc(100vh-8rem)] flex flex-col">
      <PageHero
        eyebrow="REST"
        title="API docs"
        lead="OpenAPI for /api helpers on :12007. MCP tools use POST /mcp (JSON-RPC), not these routes."
      />
      <iframe
        title="OpenAPI docs"
        src="/docs"
        className="flex-1 w-full rounded-lg border border-border bg-background min-h-[480px]"
      />
    </div>
  );
}
