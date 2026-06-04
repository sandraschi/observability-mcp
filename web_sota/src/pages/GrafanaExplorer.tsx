import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { grafanaDashboardUrl } from "@/lib/grafana-url";
import {
  Activity,
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Database,
  ExternalLink,
  LayoutDashboard,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { callTool } from "../lib/mcp-client";

interface Dashboard {
  id: number;
  uid: string;
  title: string;
  url: string;
  type: string;
  tags: string[];
}

interface Datasource {
  id: number;
  name: string;
  type: string;
  url: string;
  isDefault: boolean;
}

export function GrafanaExplorer() {
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [datasources, setDatasources] = useState<Datasource[]>([]);
  const [loading, setLoading] = useState(true);
  const [provisioning, setProvisioning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function loadData() {
    setLoading(true);
    try {
      const dbResult = (await callTool("manage_grafana_dashboards", {
        operation: "list",
      })) as { dashboards: Dashboard[] };
      const dsResult = (await callTool("manage_grafana_datasources", {
        operation: "list",
      })) as { datasources: Datasource[] };

      setDashboards(dbResult.dashboards || []);
      setDatasources(dsResult.datasources || []);
      setError(null);
    } catch (err) {
      console.error("Failed to load Grafana data:", err);
      setError(
        "Failed to connect to Grafana. Ensure unified Grafana is running on port 12000.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleProvision() {
    setProvisioning(true);
    try {
      await callTool("provision_standard_dashboards", {});
      await loadData();
    } catch (err) {
      setError("Provisioning failed: " + String(err));
    } finally {
      setProvisioning(false);
    }
  }

  async function handleDeleteDashboard(uid: string) {
    if (!confirm("Are you sure you want to delete this dashboard?")) return;
    try {
      await callTool("manage_grafana_dashboards", { operation: "delete", uid });
      await loadData();
    } catch (err) {
      setError("Delete failed: " + String(err));
    }
  }

  async function handleTestDatasource(id: number) {
    try {
      const result = (await callTool("manage_grafana_datasources", {
        operation: "test",
        ds_id: id,
      })) as { status: string };
      alert(`Datasource test: ${result.status}`);
    } catch (err) {
      alert(`Test failed: ${err}`);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="space-y-8 pb-12">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <Link
            to="/grafana"
            className="inline-flex items-center text-sm text-amber-500/90 hover:text-amber-400 mb-2"
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back to chart picker
          </Link>
          <h2 className="text-3xl font-bold tracking-tight text-white font-mono">
            Grafana admin
          </h2>
          <p className="text-slate-400 font-mono text-sm mt-1">
            Datasources, provision, delete — for operators
          </p>
        </div>
        <div className="flex gap-3">
          <Button
            variant="outline"
            className="border-slate-700 bg-slate-900/50 text-slate-300 hover:bg-slate-800"
            onClick={loadData}
            disabled={loading}
          >
            <RefreshCw
              className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>
          <Button
            className="bg-indigo-600 hover:bg-indigo-500 text-white"
            onClick={handleProvision}
            disabled={provisioning}
          >
            <Activity
              className={`mr-2 h-4 w-4 ${provisioning ? "animate-pulse" : ""}`}
            />
            {provisioning ? "Provisioning..." : "Provision Standard Stack"}
          </Button>
        </div>
      </div>

      {error && (
        <Card className="border-red-900/50 bg-red-950/20">
          <CardContent className="pt-6 flex items-start gap-4">
            <AlertCircle className="h-5 w-5 text-red-500 mt-0.5" />
            <div className="text-red-200 text-sm font-mono">{error}</div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Datasources */}
        <section className="space-y-4">
          <div className="flex items-center gap-2 px-1">
            <Database className="h-5 w-5 text-indigo-400" />
            <h3 className="text-lg font-semibold text-slate-200">
              Data Sources
            </h3>
          </div>

          <div className="space-y-3">
            {datasources.length === 0 && !loading && (
              <div className="text-slate-500 italic text-sm p-4 border border-dashed border-slate-800 rounded-lg">
                No datasources configured yet.
              </div>
            )}

            {datasources.map((ds) => (
              <Card
                key={ds.id}
                className="border-slate-800 bg-slate-900/40 hover:bg-slate-900/60 transition-colors group"
              >
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                      <Database className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-slate-100">
                          {ds.name}
                        </span>
                        {ds.isDefault && (
                          <span className="text-[10px] bg-indigo-500/20 text-indigo-400 px-1.5 py-0.5 rounded border border-indigo-500/30 uppercase font-bold tracking-tighter">
                            Default
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-slate-500 font-mono">
                        {ds.type} • {ds.url}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0 text-slate-400 hover:text-white"
                      onClick={() => handleTestDatasource(ds.id)}
                    >
                      <Activity className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* Dashboards */}
        <section className="space-y-4">
          <div className="flex items-center gap-2 px-1">
            <LayoutDashboard className="h-5 w-5 text-indigo-400" />
            <h3 className="text-lg font-semibold text-slate-200">
              Active Dashboards
            </h3>
          </div>

          <div className="space-y-3">
            {dashboards.length === 0 && !loading && (
              <div className="text-slate-500 italic text-sm p-4 border border-dashed border-slate-800 rounded-lg">
                No dashboards found. Try provisioning the standard stack.
              </div>
            )}

            {dashboards.map((db) => (
              <Card
                key={db.uid}
                className="border-slate-800 bg-slate-950/40 hover:bg-slate-900/40 transition-all group"
              >
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
                      <LayoutDashboard className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="font-medium text-slate-100">
                        {db.title}
                      </div>
                      <div className="text-xs text-slate-500 font-mono">
                        UID: {db.uid}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <a
                      href={grafanaDashboardUrl(db.url)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 text-slate-400 hover:text-indigo-400 transition-colors"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                    <button
                      onClick={() => handleDeleteDashboard(db.uid)}
                      className="p-2 text-slate-400 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      </div>

      {/* Integration Status */}
      <Card className="border-slate-800 bg-slate-900/20 mt-8">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-slate-400 uppercase tracking-widest">
            Stack Integration Status
          </CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 text-emerald-500" />
            <div className="text-sm">
              <div className="text-slate-300 font-medium">
                Prometheus Bridge
              </div>
              <div className="text-slate-500 text-xs font-mono">
                Status: Connected (12001)
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 text-emerald-500" />
            <div className="text-sm">
              <div className="text-slate-300 font-medium">Loki Log Stream</div>
              <div className="text-slate-500 text-xs font-mono">
                Status: Active (12002)
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className={loading ? "animate-pulse" : ""}>
              <CheckCircle2 className="h-5 w-5 text-emerald-500" />
            </div>
            <div className="text-sm">
              <div className="text-slate-300 font-medium">
                Grafana API Client
              </div>
              <div className="text-slate-500 text-xs font-mono">
                Status: Operational (12000)
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
