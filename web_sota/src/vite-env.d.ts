/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_BACKEND_PORT?: string;
  readonly VITE_GRAFANA_URL?: string;
  readonly VITE_LOKI_URL?: string;
  readonly VITE_PROMETHEUS_SERVER_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
