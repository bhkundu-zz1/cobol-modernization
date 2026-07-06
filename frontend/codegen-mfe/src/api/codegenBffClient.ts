const BASE_URL = import.meta.env.VITE_CODEGEN_BFF_URL || "http://localhost:8008";

export type CodeGenTarget = "python" | "java_spring_boot";

export interface EligibleStory {
  _id: string;
  title: string;
  description: string;
  acceptance_criteria: string[];
  source_program_ids: string[];
  code_generation_status: "not_generated" | "generating" | "generated" | "failed";
  code_generation_target: CodeGenTarget | null;
  generated_code_repo_path: string | null;
  generated_code_commit_sha: string | null;
  generated_code_commit_url: string | null;
  code_generation_error: string | null;
}

export interface EligibleStorySummary {
  story: EligibleStory;
  epic_title: string | null;
  recommended_targets: string[];
}

export interface EligibleStoriesResponse {
  items: EligibleStorySummary[];
}

export async function listEligibleStories(projectId: string): Promise<EligibleStoriesResponse> {
  const response = await fetch(`${BASE_URL}/bff/codegen/eligible-stories?project_id=${encodeURIComponent(projectId)}`);
  if (!response.ok) {
    throw new Error(`list eligible stories failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

export async function triggerCodeGeneration(
  projectId: string,
  storyId: string,
  targetLanguage: CodeGenTarget
): Promise<{ job_run_id: string; status: string }> {
  const response = await fetch(`${BASE_URL}/bff/codegen/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: projectId, story_id: storyId, target_language: targetLanguage }),
  });
  if (!response.ok) {
    throw new Error(`generate code failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

export class CodegenJobStatusError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export interface CodegenJobStatus {
  job_run_id: string;
  status: "running" | "completed" | "failed" | "killed";
  tasks: { agent_task_id: string; agent: string; status: string }[];
}

export async function getCodegenJobStatus(projectId: string, jobRunId: string): Promise<CodegenJobStatus> {
  const response = await fetch(`${BASE_URL}/bff/codegen/jobs/${jobRunId}?project_id=${encodeURIComponent(projectId)}`);
  if (!response.ok) {
    throw new CodegenJobStatusError(
      response.status,
      `codegen job status fetch failed: ${response.status} ${await response.text()}`
    );
  }
  return response.json();
}
