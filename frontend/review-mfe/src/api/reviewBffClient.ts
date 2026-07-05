const BASE_URL = import.meta.env.VITE_REVIEW_BFF_URL || "http://localhost:8002";

export interface ReviewItem {
  subject_id: string;
  subject_filename: string | null;
  subject_type: string;
  recommendation: {
    _id: string;
    recommended_target: string;
    rationale: string;
    risk_flags: string[];
    alternative_considered: { target: string; why_rejected: string };
    decision_factors?: Record<string, unknown>;
  };
  confidence_score: number;
  needs_human_review: boolean;
  job_run_status: string | null;
  human_review_status: string;
}

export interface ReviewItemSource {
  filename: string | null;
  source_text: string | null;
  relative_path: string | null;
  language: string | null;
}

export interface BacklogEpic {
  _id: string;
  title: string;
  description: string;
  confidence_score: number;
}

export interface BacklogStory {
  _id: string;
  epic_id: string;
  title: string;
  description: string;
  acceptance_criteria: string[];
  confidence_score: number;
}

export interface ReviewItemBacklog {
  epic: BacklogEpic | null;
  story: BacklogStory | null;
}

export interface ReviewItemsResponse {
  items: ReviewItem[];
  bookmark: string | null;
}

export async function listReviewItems(projectId: string, humanReviewStatus?: string): Promise<ReviewItemsResponse> {
  const params = new URLSearchParams({ project_id: projectId });
  if (humanReviewStatus) params.set("human_review_status", humanReviewStatus);

  const response = await fetch(`${BASE_URL}/bff/review-items?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`list review items failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

export async function recordDecision(
  projectId: string,
  recommendationId: string,
  decision: "approved" | "rejected",
  reviewedBy: string
): Promise<{ recommendation_id: string; human_review_status: string }> {
  const response = await fetch(
    `${BASE_URL}/bff/review-items/${recommendationId}/decision?project_id=${encodeURIComponent(projectId)}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, reviewed_by: reviewedBy }),
    }
  );
  if (!response.ok) {
    throw new Error(`record decision failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

// Deliberately not part of listReviewItems — fetched only when a reviewer
// expands a specific row (mirrors the Editor MFE's lazy-expand pattern for
// listEpicStories), since eagerly fetching full source text for every row
// would bloat the cached list payload for no benefit to unexpanded rows.
export async function getReviewItemSource(projectId: string, recommendationId: string): Promise<ReviewItemSource> {
  const response = await fetch(
    `${BASE_URL}/bff/review-items/${recommendationId}/source?project_id=${encodeURIComponent(projectId)}`
  );
  if (!response.ok) {
    throw new Error(`get source failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

export async function getReviewItemBacklog(projectId: string, recommendationId: string): Promise<ReviewItemBacklog> {
  const response = await fetch(
    `${BASE_URL}/bff/review-items/${recommendationId}/backlog?project_id=${encodeURIComponent(projectId)}`
  );
  if (!response.ok) {
    throw new Error(`get backlog failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

export async function triggerEpicStoryGeneration(projectId: string): Promise<{ job_run_id: string; status: string }> {
  const response = await fetch(`${BASE_URL}/bff/generate-epics-stories`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: projectId }),
  });
  if (!response.ok) {
    throw new Error(`generate epics/stories failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

export class JobStatusError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export interface EpicStoryJobStatus {
  job_run_id: string;
  status: "running" | "completed" | "failed" | "killed";
  tasks: { agent_task_id: string; agent: string; status: string }[];
}

export async function getEpicStoryJobStatus(projectId: string, jobRunId: string): Promise<EpicStoryJobStatus> {
  const response = await fetch(`${BASE_URL}/bff/jobs/${jobRunId}?project_id=${encodeURIComponent(projectId)}`);
  if (!response.ok) {
    throw new JobStatusError(response.status, `job status fetch failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}
