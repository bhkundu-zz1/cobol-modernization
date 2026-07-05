import { useState } from "react";

import { Badge } from "@harness/design-system";

import { listEpicStories, type Epic, type Story } from "../api/editorBffClient";
import { StoryDetail } from "./StoryDetail";
import { StoryEditForm } from "./StoryEditForm";

const PROJECT_ID = import.meta.env.VITE_DEFAULT_PROJECT_ID || "acme-2026";

export interface EpicListProps {
  epics: Epic[];
  selectedEpicIds: Set<string>;
  selectedStoryIds: Set<string>;
  onToggleEpic: (epicId: string) => void;
  onToggleStory: (storyId: string) => void;
}

export function EpicList({
  epics,
  selectedEpicIds,
  selectedStoryIds,
  onToggleEpic,
  onToggleStory,
}: EpicListProps) {
  const [expandedEpicIds, setExpandedEpicIds] = useState<Set<string>>(new Set());
  const [storiesByEpicId, setStoriesByEpicId] = useState<Record<string, Story[]>>({});
  const [loadingEpicId, setLoadingEpicId] = useState<string | null>(null);
  const [expandedStoryId, setExpandedStoryId] = useState<string | null>(null);
  const [editingStoryId, setEditingStoryId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function toggleExpand(epicId: string) {
    const next = new Set(expandedEpicIds);
    if (next.has(epicId)) {
      next.delete(epicId);
      setExpandedEpicIds(next);
      return;
    }
    next.add(epicId);
    setExpandedEpicIds(next);

    if (!storiesByEpicId[epicId]) {
      setLoadingEpicId(epicId);
      setError(null);
      try {
        const result = await listEpicStories(PROJECT_ID, epicId);
        setStoriesByEpicId((prev) => ({ ...prev, [epicId]: result.items }));
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoadingEpicId(null);
      }
    }
  }

  function handleStorySaved(epicId: string, story: Story) {
    setStoriesByEpicId((prev) => ({
      ...prev,
      [epicId]: prev[epicId].map((s) => (s._id === story._id ? story : s)),
    }));
    setEditingStoryId(null);
  }

  if (epics.length === 0) {
    return <p>No epics yet — run scripts/seed_epics_stories.py or generate epics/stories.</p>;
  }

  return (
    <div>
      {error && <p role="alert">{error}</p>}
      {epics.map((epic) => (
        <div key={epic._id} style={{ border: "1px solid #e5e7eb", borderRadius: "0.375rem", marginBottom: "0.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.5rem" }}>
            <input
              type="checkbox"
              aria-label={`Select epic ${epic.title}`}
              checked={selectedEpicIds.has(epic._id)}
              onChange={() => onToggleEpic(epic._id)}
            />
            <button type="button" onClick={() => toggleExpand(epic._id)}>
              {expandedEpicIds.has(epic._id) ? "▾" : "▸"}
            </button>
            <strong>{epic.title}</strong>
            <span>{epic.description}</span>
            {epic.export_target && <Badge tone="success">exported to {epic.export_target}</Badge>}
          </div>

          {expandedEpicIds.has(epic._id) && (
            <div style={{ paddingLeft: "2rem" }}>
              {loadingEpicId === epic._id && <p>Loading stories…</p>}
              {(storiesByEpicId[epic._id] ?? []).map((story) => (
                <div key={story._id} style={{ borderTop: "1px solid #f3f4f6", padding: "0.5rem 0" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <input
                      type="checkbox"
                      aria-label={`Select story ${story.title}`}
                      checked={selectedStoryIds.has(story._id)}
                      onChange={() => onToggleStory(story._id)}
                    />
                    <button
                      type="button"
                      onClick={() => setExpandedStoryId(expandedStoryId === story._id ? null : story._id)}
                    >
                      {story.title}
                    </button>
                    <Badge tone={story.export_status === "exported" ? "success" : "neutral"}>
                      {story.export_status}
                    </Badge>
                    {story.edited_by_human && <Badge tone="warning">edited</Badge>}
                  </div>

                  {expandedStoryId === story._id &&
                    (editingStoryId === story._id ? (
                      <StoryEditForm
                        story={story}
                        onSaved={(saved) => handleStorySaved(epic._id, saved)}
                        onCancel={() => setEditingStoryId(null)}
                      />
                    ) : (
                      <StoryDetail story={story} onEdit={() => setEditingStoryId(story._id)} />
                    ))}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
