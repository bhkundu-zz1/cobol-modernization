// Client for the Ingestion BFF (:8001). Base URL comes from the
// environment, never hardcoded, per this project's .env-everywhere rule.
const BASE_URL = import.meta.env.VITE_INGESTION_BFF_URL || "http://localhost:8001";

export interface UploadResponse {
  upload_batch_id: string;
  job_run_id: string;
}

export interface UploadedJob {
  filename: string;
  job_run_id: string;
}

export interface MultiFileUploadResponse {
  upload_batch_id: string;
  jobs: UploadedJob[];
}

export interface MainframeElement {
  element_id: string;
  element_type: string;
  version?: string | null;
}

export interface JobStatus {
  job_run_id: string;
  status: "running" | "completed" | "failed" | "killed";
  tasks: { agent_task_id: string; agent: string; status: string }[];
}

export interface FileToUpload {
  file: File;
  relativePath?: string;
}

// Uploads one or more files in a single batch — one pipeline job is
// triggered per file server-side (backend/ingestion_bff/app/routes/upload.py),
// so a folder selection with multiple COBOL programs gets a recommendation
// for every program, not just the first.
export async function uploadFiles(projectId: string, filesToUpload: FileToUpload[]): Promise<MultiFileUploadResponse> {
  const formData = new FormData();
  formData.append("project_id", projectId);
  for (const { file } of filesToUpload) {
    formData.append("files", file);
  }
  // relative_path is a label only (e.g. "payroll-project/PAYROLL01.CBL") —
  // browsers cannot expose a file's true absolute OS path for security
  // reasons, so this is the best "file location" reference available,
  // captured via the folder picker's webkitRelativePath. Sent as a
  // parallel list matched by upload order.
  if (filesToUpload.some((f) => f.relativePath)) {
    for (const { relativePath, file } of filesToUpload) {
      formData.append("relative_paths", relativePath ?? file.name);
    }
  }

  const response = await fetch(`${BASE_URL}/bff/uploads`, { method: "POST", body: formData });
  if (!response.ok) {
    throw new Error(`upload failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

export async function listMainframeElements(params: {
  projectId: string;
  tool: string;
  system: string;
  subsystem: string;
  elementType?: string;
}): Promise<{ elements: MainframeElement[] }> {
  const query = new URLSearchParams({
    project_id: params.projectId,
    tool: params.tool,
    system: params.system,
    subsystem: params.subsystem,
    element_type: params.elementType || "COBOL",
  });
  const response = await fetch(`${BASE_URL}/bff/mainframe-elements?${query.toString()}`);
  if (!response.ok) {
    throw new Error(`list elements failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

export async function pullMainframeElement(params: {
  projectId: string;
  tool: string;
  system: string;
  subsystem: string;
  elementType?: string;
  elementId: string;
}): Promise<UploadResponse> {
  const response = await fetch(`${BASE_URL}/bff/mainframe-pulls`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id: params.projectId,
      tool: params.tool,
      system: params.system,
      subsystem: params.subsystem,
      element_type: params.elementType || "COBOL",
      element_id: params.elementId,
    }),
  });
  if (!response.ok) {
    throw new Error(`mainframe pull failed: ${response.status} ${await response.text()}`);
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

export async function getJobStatus(projectId: string, jobRunId: string): Promise<JobStatus> {
  const response = await fetch(`${BASE_URL}/bff/jobs/${jobRunId}?project_id=${encodeURIComponent(projectId)}`);
  if (!response.ok) {
    throw new JobStatusError(response.status, `job status fetch failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}
