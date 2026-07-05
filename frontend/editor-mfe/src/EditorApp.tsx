// Epic/Story Editor MFE — port 3003 (architecture.md section 8).
//
// Browse/edit epics+stories seeded via scripts/seed_epics_stories.py (epic/
// story *generation* is still deferred — see docs/deferred_scope.md), and
// export selected stories to GitHub (real: Milestones + Issues) or Jira
// (real UI, backend raises NotImplementedError — see
// agents/issue_tracker_export/adapter.py).

import { useCallback, useEffect, useState } from "react";

import { listEpics, type Epic, type ExportResult } from "./api/editorBffClient";
import { EpicList } from "./components/EpicList";
import { ExportPanel } from "./components/ExportPanel";

const PROJECT_ID = import.meta.env.VITE_DEFAULT_PROJECT_ID || "acme-2026";

export default function EditorApp() {
  const [epics, setEpics] = useState<Epic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEpicIds, setSelectedEpicIds] = useState<Set<string>>(new Set());
  const [selectedStoryIds, setSelectedStoryIds] = useState<Set<string>>(new Set());

  const loadEpics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listEpics(PROJECT_ID);
      setEpics(result.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadEpics();
  }, [loadEpics]);

  function toggleEpic(epicId: string) {
    setSelectedEpicIds((prev) => {
      const next = new Set(prev);
      if (next.has(epicId)) {
        next.delete(epicId);
      } else {
        next.add(epicId);
      }
      return next;
    });
  }

  function toggleStory(storyId: string) {
    setSelectedStoryIds((prev) => {
      const next = new Set(prev);
      if (next.has(storyId)) {
        next.delete(storyId);
      } else {
        next.add(storyId);
      }
      return next;
    });
  }

  function handleExported(result: ExportResult) {
    const exportedStoryIds = new Set(result.exported.map((item) => item.story_id));
    setSelectedStoryIds((prev) => {
      const next = new Set(prev);
      exportedStoryIds.forEach((id) => next.delete(id));
      return next;
    });
  }

  if (loading) {
    return <p>Loading epics…</p>;
  }

  if (error) {
    return <p role="alert">{error}</p>;
  }

  return (
    <div>
      <h2>Epic/Story Editor</h2>
      <EpicList
        epics={epics}
        selectedEpicIds={selectedEpicIds}
        selectedStoryIds={selectedStoryIds}
        onToggleEpic={toggleEpic}
        onToggleStory={toggleStory}
      />
      <ExportPanel
        selectedEpicIds={[...selectedEpicIds]}
        selectedStoryIds={[...selectedStoryIds]}
        onExported={handleExported}
      />
    </div>
  );
}
