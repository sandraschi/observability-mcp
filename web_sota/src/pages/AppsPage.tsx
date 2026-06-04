import { APPS_CATALOG } from "@/common/apps-catalog";
import { Card, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/layout/PageHero";

export function AppsPage() {
  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Fleet"
        title="Related apps"
        lead="Jump to other MCP web dashboards on the LAN. Update ports in apps-catalog.ts when your fleet changes."
      />
      <div className="grid gap-4 sm:grid-cols-2">
        {APPS_CATALOG.map((app) => {
          const Icon = app.icon;
          return (
            <Card key={app.id} className="hover:border-primary/40 transition-colors">
              <a href={app.url} target="_blank" rel="noreferrer" className="block p-1">
                <div className="flex items-start gap-3">
                  <Icon className="h-8 w-8 text-primary shrink-0" />
                  <div>
                    <CardTitle>{app.label}</CardTitle>
                    <p className="text-xs text-muted-foreground mt-1">{app.description}</p>
                    <p className="text-[10px] font-mono text-primary mt-2">
                      :{app.port} · {app.url}
                    </p>
                  </div>
                </div>
              </a>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
