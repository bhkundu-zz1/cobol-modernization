import { useEffect, useState } from "react";

import { getJobStatus, JobStatusError, type JobStatus } from "../api/ingestionBffClient";

export interface JobProgressProps {
  projectId: string;
  jobRunId: string;
  pollIntervalMs?: number;
}

// POST /bff/uploads returns 202 + job_run_id before the Celery worker has
// necessarily picked up the task — the job_run document itself is only
// created lazily by the first task's checkpoint write (orchestrator/
// checkpoint.py). A poll landing in that window gets a real 404, not a
// broken job — confirmed live: the same job_run_id 404s once then 200s on
// the very next poll a couple seconds later. Retry through a bounded
// number of "not found yet" responses instead of treating the first 404 as
// fatal; only report an error if it's still missing after that.
const MAX_NOT_FOUND_RETRIES = 5;

export function JobProgress({ projectId, jobRunId, pollIntervalMs = 2000 }: JobProgressProps) {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    let notFoundCount = 0;

    async function poll() {
      try {
        const result = await getJobStatus(projectId, jobRunId);
        if (cancelled) return;
        setStatus(result);
        if (result.status === "running") {
          timer = setTimeout(poll, pollIntervalMs);
        }
      } catch (err) {
        if (cancelled) return;
        if (err instanceof JobStatusError && err.status === 404 && notFoundCount < MAX_NOT_FOUND_RETRIES) {
          notFoundCount += 1;
          timer = setTimeout(poll, pollIntervalMs);
          return;
        }
        setError(err instanceof Error ? err.message : String(err));
      }
    }

    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [projectId, jobRunId, pollIntervalMs]);

  if (error) {
    return <p role="alert">{error}</p>;
  }

  if (!status) {
    return <p>Checking job status…</p>;
  }

  return (
    <div>
      <p>
        Job <code>{status.job_run_id}</code>: <strong>{status.status}</strong>
      </p>
      <ul>
        {status.tasks.map((task) => (
          <li key={task.agent_task_id}>
            {task.agent}: {task.status}
          </li>
        ))}
      </ul>
    </div>
  );
}
