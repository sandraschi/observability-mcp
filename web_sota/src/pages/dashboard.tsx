import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity, BarChart3, ListTree, Cpu, Clock } from "lucide-react";

export function Dashboard() {
    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold tracking-tight text-white">Observability Dashboard</h2>
                    <p className="text-slate-400">System telemetry and telemetry trace overview</p>
                </div>
            </div>

            {/* KPI Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card className="border-slate-800 bg-slate-950/50">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-slate-200">
                            Total Traces
                        </CardTitle>
                        <ListTree className="h-4 w-4 text-emerald-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-white">1,204</div>
                        <p className="text-xs text-slate-400">
                            Last 60 minutes
                        </p>
                    </CardContent>
                </Card>

                <Card className="border-slate-800 bg-slate-950/50">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-slate-200">
                            Error Rate
                        </CardTitle>
                        <Activity className="h-4 w-4 text-red-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-white">0.05%</div>
                        <p className="text-xs text-slate-400">
                            Nominal thresholds
                        </p>
                    </CardContent>
                </Card>

                <Card className="border-slate-800 bg-slate-950/50">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-slate-200">
                            FastMCP Bridge
                        </CardTitle>
                        <Clock className="h-4 w-4 text-blue-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-white">10825</div>
                        <p className="text-xs text-slate-400">
                            Latency: 2ms
                        </p>
                    </CardContent>
                </Card>

                <Card className="border-slate-800 bg-slate-950/50">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-slate-200">
                            Collector Load
                        </CardTitle>
                        <Cpu className="h-4 w-4 text-orange-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-white">3.1%</div>
                        <p className="text-xs text-slate-400">
                            Aggregator efficiency
                        </p>
                    </CardContent>
                </Card>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
                <Card className="col-span-4 border-slate-800 bg-slate-950/50">
                    <CardHeader>
                        <CardTitle className="text-white">Live Telemetry Stream</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="h-[200px] font-mono text-xs p-4 overflow-y-auto border border-slate-800 rounded-md bg-slate-900/50 text-slate-400 space-y-1">
                            <p className="text-blue-400">[info] Trace ID: 882f-22a1 span started</p>
                            <p>[debug] FastMCP request: tool_call/usage_ops</p>
                            <p>[trace] span 882f-22a1 completed in 45ms</p>
                            <p className="text-emerald-400">[success] Aggregated metrics exported to Jaeger</p>
                            <div className="animate-pulse inline-block h-2 w-1 bg-slate-500 ml-1" />
                        </div>
                    </CardContent>
                </Card>
                <Card className="col-span-3 border-slate-800 bg-slate-950/50">
                    <CardHeader>
                        <CardTitle className="text-white">Analysis Health</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            <div className="flex items-center">
                                <BarChart3 className="h-4 w-4 text-slate-400 mr-2" />
                                <div className="ml-2 space-y-1">
                                    <p className="text-sm font-medium leading-none text-white">Sampling Rate</p>
                                    <p className="text-xs text-slate-400">100% of all spans</p>
                                </div>
                            </div>
                            <div className="flex items-center">
                                <Activity className="h-4 w-4 text-slate-600 mr-2" />
                                <div className="ml-2 space-y-1">
                                    <p className="text-sm font-medium leading-none text-white text-opacity-50">Local Pipeline</p>
                                    <p className="text-xs text-slate-500">FastAPI bridge healthy</p>
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
