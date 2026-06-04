import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  DASHBOARD_CATEGORIES,
  type DashboardCategoryId,
  getCategory,
} from "@/data/dashboard-catalog";
import {
  type EnrichedDashboard,
  type GrafanaSearchHit,
  enrichDashboards,
  groupByCategory,
} from "@/lib/dashboard-matcher";
import { grafanaDashboardUrl } from "@/lib/grafana-url";
import { callTool } from "@/lib/mcp-client";
import {
  BarChart3,
  BookOpen,
  ExternalLink,
  HelpCircle,
  Layers,
  RefreshCw,
  Search,
  Sparkles,
  Wrench,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

function DashboardCard({
  item,
  missing,
}: { item: EnrichedDashboard; missing: boolean }) {
  const { hit, preset } = item;
  const title = preset?.displayTitle ?? hit.title;
  const tagline = preset?.tagline ?? "Live dashboard from your Grafana server";
  const emoji = preset?.emoji ?? "📊";
  const href = grafanaDashboardUrl(hit.url);
  const difficulty = preset?.difficulty ?? "intermediate";

  return (
    <Card
      className={`group relative overflow-hidden border-zinc-800/80 bg-gradient-to-br from-zinc-900/90 to-zinc-950/90 transition-all hover:border-amber-500/30 hover:shadow-lg hover:shadow-amber-950/20 ${
        missing ? "opacity-75 border-dashed" : ""
      }`}
    >
      <div className="absolute inset-0 bg-gradient-to-r from-amber-500/5 via-transparent to-violet-500/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
      <CardHeader className="pb-2 relative">
        <div className="flex items-start justify-between gap-3">
          <div className="flex gap-3 min-w-0">
            <span className="text-3xl leading-none select-none" aria-hidden>
              {emoji}
            </span>
            <div className="min-w-0">
              <CardTitle className="text-lg text-zinc-100 truncate">
                {title}
              </CardTitle>
              <CardDescription className="text-zinc-400 mt-1 line-clamp-2">
                {tagline}
              </CardDescription>
            </div>
          </div>
          <Badge
            variant="outline"
            className={
              difficulty === "beginner"
                ? "border-emerald-500/40 text-emerald-400 shrink-0"
                : "border-amber-500/40 text-amber-400 shrink-0"
            }
          >
            {difficulty === "beginner" ? "Easy" : "Nerdy"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 relative">
        {preset && (
          <>
            <div>
              <p className="text-[10px] uppercase tracking-widest text-zinc-500 mb-1.5">
                Good for
              </p>
              <ul className="flex flex-wrap gap-1.5">
                {preset.goodFor.map((g) => (
                  <li
                    key={g}
                    className="text-xs px-2 py-0.5 rounded-full bg-zinc-800/80 text-zinc-300 border border-zinc-700/50"
                  >
                    {g}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-widest text-zinc-500 mb-1.5">
                You&apos;ll see
              </p>
              <p className="text-sm text-zinc-400 leading-relaxed">
                {preset.youWillSee.join(" · ")}
              </p>
            </div>
          </>
        )}
        <div className="flex items-center justify-between gap-2 pt-1">
          <span className="text-[10px] font-mono text-zinc-600 truncate">
            uid: {hit.uid}
          </span>
          {missing ? (
            <span className="text-xs text-amber-500/90">
              Not in Grafana yet
            </span>
          ) : (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm font-medium text-amber-400 hover:text-amber-300 transition-colors"
            >
              Open charts
              <ExternalLink className="w-4 h-4" />
            </a>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function CategorySection({
  categoryId,
  items,
}: {
  categoryId: DashboardCategoryId;
  items: EnrichedDashboard[];
}) {
  const cat = getCategory(categoryId);
  if (items.length === 0) return null;

  return (
    <section className="space-y-4">
      <div className="flex items-end gap-3 border-b border-zinc-800/80 pb-3">
        <span className="text-2xl" aria-hidden>
          {cat.emoji}
        </span>
        <div>
          <h3 className="text-xl font-semibold text-zinc-100">{cat.title}</h3>
          <p className="text-sm text-zinc-500">{cat.subtitle}</p>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {items.map((item) => (
          <DashboardCard
            key={item.hit.uid + item.hit.title}
            item={item}
            missing={item.hit.id === -1}
          />
        ))}
      </div>
    </section>
  );
}

export function GrafanaDashboards() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [enriched, setEnriched] = useState<EnrichedDashboard[]>([]);

  async function load() {
    setLoading(true);
    try {
      const result = (await callTool("manage_grafana_dashboards", {
        operation: "list",
      })) as {
        dashboards: GrafanaSearchHit[];
      };
      setEnriched(enrichDashboards(result.dashboards ?? []));
      setError(null);
    } catch (e) {
      setError(
        "Could not reach Grafana. Start unified monitoring (port 12000) and copy .env.unified-monitoring.example to .env.",
      );
      setEnriched(enrichDashboards([]));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return enriched;
    return enriched.filter((item) => {
      const t = (item.preset?.displayTitle ?? item.hit.title).toLowerCase();
      const tags = (item.hit.tags ?? []).join(" ").toLowerCase();
      return (
        t.includes(q) ||
        tags.includes(q) ||
        item.hit.uid.toLowerCase().includes(q)
      );
    });
  }, [enriched, query]);

  const grouped = useMemo(() => groupByCategory(filtered), [filtered]);

  const categoryOrder = DASHBOARD_CATEGORIES.map((c) => c.id).filter((id) => {
    const items = grouped.get(id);
    return items && items.length > 0;
  });

  return (
    <div className="space-y-10 pb-16 -mx-2 max-w-[1400px]">
      {/* Hero */}
      <header className="relative rounded-2xl border border-zinc-800 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-amber-950/40 via-zinc-950 to-violet-950/30" />
        <div className="absolute inset-0 opacity-30 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-amber-500/20 via-transparent to-transparent" />
        <div className="relative px-8 py-10 md:py-12 space-y-6">
          <div className="flex flex-wrap items-center gap-2">
            <Badge className="bg-amber-500/20 text-amber-300 border-amber-500/30 hover:bg-amber-500/20">
              Not a crayon brand
            </Badge>
            <Badge variant="outline" className="border-zinc-600 text-zinc-400">
              Grafana @ 12000
            </Badge>
          </div>
          <div className="max-w-2xl space-y-3">
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-white">
              Charts & dashboards
            </h1>
            <p className="text-zinc-400 text-base leading-relaxed">
              Grafana is where the pretty graphs live. Pick a category below,
              open a board in a new tab, and ignore the jargon until you care.
              Green means happy; red means go make coffee then check logs.
            </p>
          </div>
          <div className="flex flex-wrap gap-3 text-sm text-zinc-500">
            <span className="inline-flex items-center gap-1.5">
              <BookOpen className="w-4 h-4 text-amber-500/80" />
              Beginner boards marked{" "}
              <strong className="text-emerald-500/90 font-normal">Easy</strong>
            </span>
            <span className="inline-flex items-center gap-1.5">
              <BarChart3 className="w-4 h-4 text-amber-500/80" />
              Opens real Grafana — no copy-paste URLs
            </span>
          </div>
        </div>
      </header>

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-4 sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
          <input
            type="search"
            placeholder="Search dashboards (plex, cameras, tailscale…)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-zinc-900/80 border border-zinc-700 text-zinc-100 placeholder:text-zinc-600 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/40 focus:border-amber-500/50"
          />
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            className="border-zinc-700 bg-zinc-900/50 text-zinc-300"
            onClick={load}
            disabled={loading}
          >
            <RefreshCw
              className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`}
            />
            Refresh list
          </Button>
          <Button
            asChild
            variant="outline"
            className="border-zinc-700 text-zinc-400"
          >
            <Link to="/grafana/manage">
              <Wrench className="w-4 h-4 mr-2" />
              Admin
            </Link>
          </Button>
          <a
            href={grafanaDashboardUrl("/dashboards")}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center rounded-md text-sm font-medium h-10 px-4 bg-amber-600 hover:bg-amber-500 text-zinc-950"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            All in Grafana
          </a>
        </div>
      </div>

      {error && (
        <Card className="border-red-900/50 bg-red-950/20">
          <CardContent className="pt-6 flex gap-3 text-sm text-red-200">
            <HelpCircle className="w-5 h-5 shrink-0 text-red-400" />
            <div>
              <p>{error}</p>
              <p className="mt-2 text-red-300/80">
                Presets below still show what to open once Grafana is up. Admin
                → Provision can install starter boards.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick start strip */}
      <Card className="border-amber-500/20 bg-amber-950/10">
        <CardContent className="py-5 flex flex-col md:flex-row md:items-center gap-4 md:gap-8">
          <div className="flex items-center gap-3 text-amber-200/90">
            <Layers className="w-8 h-8 text-amber-500" />
            <div>
              <p className="font-medium text-zinc-100">New here?</p>
              <p className="text-sm text-zinc-400">
                Start with Fleet overview, then open the MCP you care about.
              </p>
            </div>
          </div>
          <a
            href={grafanaDashboardUrl("/d/unified-monitoring-overview")}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center rounded-lg px-5 py-2.5 bg-amber-500/90 text-zinc-950 font-medium text-sm hover:bg-amber-400 transition-colors shrink-0"
          >
            Open fleet overview
            <ExternalLink className="w-4 h-4 ml-2" />
          </a>
        </CardContent>
      </Card>

      {loading && enriched.length === 0 ? (
        <div className="text-center py-20 text-zinc-500 font-mono text-sm">
          Loading dashboards from Grafana…
        </div>
      ) : categoryOrder.length === 0 ? (
        <Card className="border-dashed border-zinc-700">
          <CardContent className="py-12 text-center text-zinc-500">
            No dashboards match your search.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-12">
          {categoryOrder.map((id) => (
            <CategorySection
              key={id}
              categoryId={id}
              items={grouped.get(id)!}
            />
          ))}
        </div>
      )}

      <footer className="text-center text-xs text-zinc-600 font-mono pt-4">
        Tip: bookmark this page in observability-mcp — Grafana itself stays at{" "}
        <a
          href={grafanaDashboardUrl("/")}
          className="text-amber-600/80 hover:text-amber-500"
          target="_blank"
          rel="noreferrer"
        >
          :12000
        </a>
      </footer>
    </div>
  );
}
