import { useEffect, useState } from "react";
import { apiGet } from "@/api/client";
import { Card, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/layout/PageHero";
import { useLogger } from "@/context/LoggerContext";

type SkillMeta = { name: string; uri: string };

export function SkillsPage() {
  const { log } = useLogger();
  const [skills, setSkills] = useState<SkillMeta[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [markdown, setMarkdown] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const r = await apiGet<{ skills: SkillMeta[] }>("/api/skills");
        setSkills(r.skills ?? []);
      } catch (e) {
        log("error", String(e));
      }
    })();
  }, [log]);

  useEffect(() => {
    if (!selected) return;
    (async () => {
      try {
        const r = await apiGet<{ markdown: string }>(`/api/skills/${selected}`);
        setMarkdown(r.markdown ?? "");
      } catch (e) {
        log("error", String(e));
      }
    })();
  }, [log, selected]);

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="skill://"
        title="Skills"
        lead="Bundled expert instructions for agents. Served via SkillsDirectoryProvider on the MCP server."
      />
      <div className="flex flex-wrap gap-2">
        {skills.map((s) => (
          <button
            key={s.name}
            type="button"
            onClick={() => setSelected(s.name)}
            className={`px-3 py-1 rounded-md text-xs font-mono border ${
              selected === s.name ? "border-primary text-primary bg-primary/10" : "border-border text-muted-foreground"
            }`}
          >
            {s.name}
          </button>
        ))}
      </div>
      <Card>
        <CardTitle>{selected ?? "Select a skill"}</CardTitle>
        <pre className="mt-4 text-xs whitespace-pre-wrap font-mono text-muted-foreground max-h-[55vh] overflow-y-auto">
          {markdown || "Pick observability-expert to view SKILL.md"}
        </pre>
      </Card>
    </div>
  );
}
