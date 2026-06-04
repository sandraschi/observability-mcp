/**
 * Curated fleet dashboard catalog — plain-language labels for Grafana beginners.
 * Matched against live dashboards by uid, title, and tags.
 */

export type DashboardCategoryId =
  | "start-here"
  | "mcp-fleet"
  | "media-home"
  | "docs-tools"
  | "network-vpn"
  | "uncategorized";

export interface DashboardCategory {
  id: DashboardCategoryId;
  title: string;
  subtitle: string;
  emoji: string;
  sort: number;
}

export interface DashboardPreset {
  /** Exact Grafana dashboard uid when known */
  uid?: string;
  /** Match if title contains any of these (case-insensitive) */
  titleIncludes?: string[];
  /** Match if any tag matches */
  tagAny?: string[];
  displayTitle: string;
  tagline: string;
  emoji: string;
  category: DashboardCategoryId;
  difficulty: "beginner" | "intermediate";
  goodFor: string[];
  youWillSee: string[];
  sort: number;
}

export const DASHBOARD_CATEGORIES: DashboardCategory[] = [
  {
    id: "start-here",
    title: "Start here",
    subtitle: "One screen to see if the whole monitoring stack is alive",
    emoji: "🧭",
    sort: 0,
  },
  {
    id: "mcp-fleet",
    title: "MCP servers",
    subtitle: "Each repo that exposes tools — health, metrics, and logs",
    emoji: "🤖",
    sort: 1,
  },
  {
    id: "media-home",
    title: "Media & home",
    subtitle: "Libraries, streaming, cameras, and IoT around the house",
    emoji: "🏠",
    sort: 2,
  },
  {
    id: "docs-tools",
    title: "Docs & dev tools",
    subtitle: "Central docs, RAG, and MCP Studio",
    emoji: "📚",
    sort: 3,
  },
  {
    id: "network-vpn",
    title: "Network & VPN",
    subtitle: "Tailscale and mesh connectivity (legacy boards)",
    emoji: "🛡️",
    sort: 4,
  },
  {
    id: "uncategorized",
    title: "Everything else",
    subtitle: "Dashboards Grafana knows about but we have not filed yet",
    emoji: "📦",
    sort: 99,
  },
];

export const DASHBOARD_PRESETS: DashboardPreset[] = [
  {
    uid: "unified-monitoring-overview",
    displayTitle: "Fleet overview",
    tagline: "Are my MCP services up? Any errors in the last hour?",
    emoji: "🌐",
    category: "start-here",
    difficulty: "beginner",
    goodFor: ["First visit", "Morning check-in", "After restarting Docker"],
    youWillSee: [
      "Green/red service status",
      "Recent errors from all apps",
      "High-level traffic",
    ],
    sort: 0,
  },
  {
    uid: "devices-mcp-fleet",
    titleIncludes: ["devices-mcp"],
    tagAny: ["devices-mcp"],
    displayTitle: "Devices MCP",
    tagline: "Cameras, Ring, Home Assistant, and the IoT dashboard backend",
    emoji: "📹",
    category: "mcp-fleet",
    difficulty: "beginner",
    goodFor: [
      "Home security",
      "Camera offline debugging",
      "Ring scrape health",
    ],
    youWillSee: [
      "HTTP health probes",
      "Ring metrics",
      "Host and container logs",
    ],
    sort: 10,
  },
  {
    uid: "plex-mcp-fleet",
    titleIncludes: ["plex-mcp"],
    tagAny: ["plex-mcp"],
    displayTitle: "Plex MCP",
    tagline: "Is Plex MCP reachable and logging cleanly?",
    emoji: "🎬",
    category: "media-home",
    difficulty: "beginner",
    goodFor: ["Streaming issues", "MCP tool errors on Plex"],
    youWillSee: ["/health checks", "Probe latency", "Log streams"],
    sort: 20,
  },
  {
    uid: "calibre-mcp-fleet",
    titleIncludes: ["calibre-mcp"],
    tagAny: ["calibre-mcp"],
    displayTitle: "Calibre MCP",
    tagline: "E-book library MCP and Calibre Plus sidecar",
    emoji: "📖",
    category: "media-home",
    difficulty: "beginner",
    goodFor: ["Library sync", "Calibre Plus container health"],
    youWillSee: [
      "Prometheus scrape status",
      "Blackbox health",
      "Calibre Plus logs",
    ],
    sort: 21,
  },
  {
    uid: "mcd-rag-fleet",
    titleIncludes: ["mcd", "rag", "fleet probes"],
    tagAny: ["mcp-central-docs", "rag"],
    displayTitle: "Docs MCP & RAG",
    tagline: "Central documentation server and semantic index health",
    emoji: "🧠",
    category: "docs-tools",
    difficulty: "intermediate",
    goodFor: ["RAG index size", "docs-mcp availability"],
    youWillSee: ["Index metrics", "API status probes", "docs-mcp logs"],
    sort: 30,
  },
  {
    titleIncludes: ["mcp studio"],
    tagAny: ["mcp-studio"],
    displayTitle: "MCP Studio",
    tagline: "Studio process health and API activity",
    emoji: "🎛️",
    category: "docs-tools",
    difficulty: "intermediate",
    goodFor: ["Studio crashes", "Connection counts"],
    youWillSee: ["Status panels", "Memory and request rates"],
    sort: 31,
  },
  {
    titleIncludes: ["tailscale"],
    tagAny: ["tailscale"],
    displayTitle: "Tailscale boards",
    tagline: "VPN mesh, devices, and MCP server overview",
    emoji: "🔗",
    category: "network-vpn",
    difficulty: "intermediate",
    goodFor: ["VPN troubleshooting", "Device activity"],
    youWillSee: ["Device status", "Traffic", "Log panels"],
    sort: 40,
  },
];

export function getCategory(id: DashboardCategoryId): DashboardCategory {
  return (
    DASHBOARD_CATEGORIES.find((c) => c.id === id) ??
    DASHBOARD_CATEGORIES[DASHBOARD_CATEGORIES.length - 1]
  );
}
