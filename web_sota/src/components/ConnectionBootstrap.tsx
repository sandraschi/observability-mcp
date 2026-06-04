import { useEffect } from "react";
import { apiGet } from "@/api/client";
import { useLogger } from "@/context/LoggerContext";
import { useAppStore } from "@/lib/store";

export function ConnectionBootstrap() {
  const { setStatus, setError } = useAppStore();
  const { log } = useLogger();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setStatus("connecting");
      try {
        await apiGet<{ status: string }>("/api/health");
        if (!cancelled) {
          setStatus("connected");
          setError(null);
          log("info", "Backend :12007 healthy");
        }
      } catch (e) {
        if (!cancelled) {
          setStatus("error");
          setError(String(e));
          log("error", `Backend offline: ${e}`);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [log, setError, setStatus]);

  return null;
}
