import { useMemo, useState } from "react";
import { GroupSidebar } from "@/components/groups/GroupSidebar";
import { BookUploadZone } from "@/components/books/BookUploadZone";
import { BookGrid } from "@/components/books/BookGrid";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { useGroups } from "@/api/groups";
import {
  BookOpen,
  Brain,
  Cloud,
  Code,
  Cpu,
  Database,
  Globe,
  Layers,
  Lock,
  Network,
  Rocket,
  Server,
  Settings,
  Shield,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

const ICON_KEYWORDS: [string[], LucideIcon][] = [
  [["ai", "ml", "machine learning", "deep learning", "neural", "llm", "agentic"], Brain],
  [["cloud", "aws", "azure", "gcp"], Cloud],
  [["security", "cyber"], Shield],
  [["privacy", "gdpr", "compliance"], Lock],
  [["data", "database", "sql", "postgres", "analytics"], Database],
  [["architecture", "system design", "design"], Layers],
  [["devops", "infrastructure", "docker", "kubernetes"], Server],
  [["network", "mesh", "distributed"], Network],
  [["api", "backend", "frontend", "web"], Globe],
  [["python", "java", "code", "programming", "software"], Code],
  [["spark", "hadoop", "big data", "streaming"], Cpu],
  [["startup", "product", "agile"], Rocket],
  [["automation", "config", "ops"], Settings],
  [["generative", "gpt", "prompt"], Sparkles],
];

function getGroupIcon(name: string): LucideIcon {
  const lower = name.toLowerCase();
  for (const [keywords, icon] of ICON_KEYWORDS) {
    if (keywords.some((kw) => lower.includes(kw))) return icon;
  }
  return BookOpen;
}

export function LibraryPage() {
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);
  const groups = useGroups();

  const selectedGroupName = useMemo(() => {
    if (!selectedGroupId || !groups.data) return null;
    return groups.data.find((g) => g.id === selectedGroupId)?.name ?? null;
  }, [selectedGroupId, groups.data]);

  return (
    <div className="flex h-screen bg-background text-foreground">
      <GroupSidebar
        selectedGroupId={selectedGroupId}
        onSelectGroup={setSelectedGroupId}
      />

      {selectedGroupId ? (
        <main className="flex-1 overflow-y-auto p-6">
          <div className="mx-auto flex max-w-5xl flex-col gap-6">
            <BookUploadZone groupId={selectedGroupId} />
            <BookGrid groupId={selectedGroupId} />
          </div>
        </main>
      ) : (
        <main className="flex-1 overflow-y-auto p-6">
          <div className="mx-auto max-w-5xl">
            <h1 className="mb-6 text-2xl font-bold">Library</h1>
            {groups.data && groups.data.length > 0 ? (
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
                {groups.data.map((group) => {
                  const Icon = getGroupIcon(group.name);
                  return (
                    <button
                      key={group.id}
                      onClick={() => setSelectedGroupId(group.id)}
                      className="flex flex-col items-center gap-3 rounded-xl border bg-card p-6 text-card-foreground shadow-sm transition-all hover:border-primary hover:shadow-md"
                    >
                      <div className="flex size-14 items-center justify-center rounded-full bg-muted">
                        <Icon className="size-7 text-muted-foreground" />
                      </div>
                      <span className="text-center text-sm font-medium">
                        {group.name}
                      </span>
                    </button>
                  );
                })}
              </div>
            ) : (
              <p className="text-center text-muted-foreground">
                No groups yet. Create one from the sidebar.
              </p>
            )}
          </div>
        </main>
      )}

      {selectedGroupId && selectedGroupName ? (
        <ChatPanel
          scope="group"
          scopeLabel={selectedGroupName}
          groupId={selectedGroupId}
        />
      ) : (
        <ChatPanel scope="library" scopeLabel="All Books" />
      )}
    </div>
  );
}
