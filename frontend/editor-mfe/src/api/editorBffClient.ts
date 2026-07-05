const BASE_URL = import.meta.env.VITE_EDITOR_ADMIN_BFF_URL || "http://localhost:8003";

export interface Epic {
  _id: string;
  title: string;
  description: string;
  export_target: "github" | "jira" | null;
  external_milestone_id: string | null;
  external_milestone_url: string | null;
}

export interface Story {
  _id: string;
  epic_id: string;
  title: string;
  description: string;
  acceptance_criteria: string[];
  source_program_ids: string[];
  generated_by_agent: string;
  edited_by_human: boolean;
  edit_history_ref: string[];
  export_status: "not_exported" | "exported";
  export_target: "github" | "jira" | null;
  external_issue_key: string | null;
  external_issue_url: string | null;
}

export interface EpicsResponse {
  items: Epic[];
  bookmark: string | null;
}

export interface StoriesResponse {
  items: Story[];
  bookmark: string | null;
}

export interface StoryPatchResult {
  story_id: string;
  edited_by_human: boolean;
  edit_history_ref: string[];
}

export interface ExportedStoryResult {
  story_id: string;
  external_issue_key: string;
  external_issue_url: string;
}

export interface FailedStoryResult {
  story_id: string;
  reason: string;
}

export interface ExportedMilestoneResult {
  epic_id: string;
  external_milestone_id: string;
  external_milestone_url: string;
}

export interface ExportResult {
  exported: ExportedStoryResult[];
  failed: FailedStoryResult[];
  epic_milestones: ExportedMilestoneResult[];
}

export async function listEpics(projectId: string): Promise<EpicsResponse> {
  const response = await fetch(`${BASE_URL}/bff/epics?${new URLSearchParams({ project_id: projectId })}`);
  if (!response.ok) {
    throw new Error(`list epics failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

export async function listEpicStories(projectId: string, epicId: string): Promise<StoriesResponse> {
  const response = await fetch(
    `${BASE_URL}/bff/epics/${epicId}/stories?${new URLSearchParams({ project_id: projectId })}`
  );
  if (!response.ok) {
    throw new Error(`list epic stories failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

export async function updateStory(
  storyId: string,
  patch: { title?: string; description?: string; acceptance_criteria?: string[]; edited_by: string }
): Promise<StoryPatchResult> {
  const response = await fetch(`${BASE_URL}/bff/stories/${storyId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!response.ok) {
    throw new Error(`update story failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

export async function exportItems(request: {
  project_id: string;
  tool: "github" | "jira";
  connection_config: Record<string, string>;
  epic_ids: string[];
  story_ids: string[];
}): Promise<ExportResult> {
  const response = await fetch(`${BASE_URL}/bff/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    // Jira raises a clean 501 "not yet implemented" error from the backend
    // (agents/issue_tracker_export/adapter.py) — surfaced verbatim, the same
    // failure path MainframeConnectForm already proves out for real
    // (non-mock) mainframe tools.
    throw new Error(`export failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}
