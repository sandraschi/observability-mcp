import { useEffect, useRef, useState } from "react";
import { apiGet } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/layout/PageHero";
import { useLogger } from "@/context/LoggerContext";

const OLLAMA = "http://localhost:11434";

type Msg = { role: "user" | "assistant"; content: string };

async function ollamaChat(model: string, messages: Msg[]): Promise<string> {
  const r = await fetch(`${OLLAMA}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model,
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
      stream: false,
    }),
  });
  if (!r.ok) throw new Error(`Ollama HTTP ${r.status}`);
  const data = (await r.json()) as { message?: { content?: string } };
  return data.message?.content ?? "(empty)";
}

export function ChatPage() {
  const { log } = useLogger();
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "assistant",
      content:
        "I help with Grafana, Loki, and Prometheus triage. Ask about dashboards, log queries, or stack health.",
    },
  ]);
  const [input, setInput] = useState("");
  const [model, setModel] = useState("llama3.2");
  const [ollamaUp, setOllamaUp] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    (async () => {
      try {
        const d = await apiGet<{ ollama_detected?: boolean; configured_model?: string }>("/api/llm/discover");
        setOllamaUp(Boolean(d.ollama_detected));
        if (d.configured_model) setModel(d.configured_model);
      } catch (e) {
        log("error", String(e));
      }
    })();
  }, [log]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    if (!input.trim() || loading) return;
    const user: Msg = { role: "user", content: input.trim() };
    const next = [...messages, user];
    setMessages(next);
    setInput("");
    setLoading(true);
    log("info", `chat: ${user.content.slice(0, 80)}`);
    try {
      const reply = await ollamaChat(model, next);
      setMessages((m) => [...m, { role: "assistant", content: reply }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", content: String(e) }]);
      log("error", String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4 flex flex-col h-[calc(100vh-8rem)]">
      <PageHero
        eyebrow="Local LLM"
        title="Chat"
        lead="Ollama on :11434 for zero-cost ops questions. For MCP actions, use Tools or an IDE client on :12007."
      />
      <div className="flex flex-wrap gap-2 items-center text-xs">
        {ollamaUp === null ? (
          <span className="text-muted-foreground">Detecting Ollama…</span>
        ) : ollamaUp ? (
          <span className="text-primary">Ollama on :11434</span>
        ) : (
          <span className="text-red-400">Ollama not detected</span>
        )}
        <input
          className="bg-muted border border-border rounded px-2 py-1 text-xs font-mono"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          aria-label="Ollama model"
        />
      </div>
      <Card className="flex-1 flex flex-col min-h-0">
        <CardTitle>Messages</CardTitle>
        <div className="flex-1 overflow-y-auto mt-3 space-y-3 text-sm">
          {messages.map((m, i) => (
            <div
              key={`${i}-${m.role}`}
              className={m.role === "user" ? "text-foreground" : "text-muted-foreground"}
            >
              <span className="text-xs uppercase text-primary mr-2">{m.role}</span>
              {m.content}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
        <div className="flex gap-2 mt-3">
          <input
            className="flex-1 bg-muted border border-border rounded-md px-3 py-2 text-sm"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            placeholder="Ask about Loki labels, Grafana boards, alerts…"
          />
          <Button type="button" onClick={send} disabled={loading}>
            {loading ? "…" : "Send"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
