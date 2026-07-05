import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as ingestionBffClient from "../api/ingestionBffClient";
import { JobProgress } from "../components/JobProgress";

describe("JobProgress", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows the job status and task list once loaded", async () => {
    vi.spyOn(ingestionBffClient, "getJobStatus").mockResolvedValue({
      job_run_id: "jr-1",
      status: "completed",
      tasks: [
        { agent_task_id: "t1", agent: "ingestion_chunking", status: "completed" },
        { agent_task_id: "t2", agent: "cobol_structural", status: "completed" },
      ],
    });

    render(<JobProgress projectId="acme-2026" jobRunId="jr-1" />);

    await waitFor(() => expect(screen.getByText("jr-1")).toBeInTheDocument());
    expect(screen.getAllByText("completed", { exact: false }).length).toBeGreaterThan(0);
    expect(screen.getByText(/ingestion_chunking/)).toBeInTheDocument();
  });

  it("shows an error if the status fetch fails", async () => {
    vi.spyOn(ingestionBffClient, "getJobStatus").mockRejectedValue(new Error("job status fetch failed: 404"));

    render(<JobProgress projectId="acme-2026" jobRunId="jr-missing" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("job status fetch failed: 404");
  });

  it("polls again while status is running", async () => {
    const getJobStatusSpy = vi
      .spyOn(ingestionBffClient, "getJobStatus")
      .mockResolvedValueOnce({ job_run_id: "jr-1", status: "running", tasks: [] })
      .mockResolvedValueOnce({ job_run_id: "jr-1", status: "completed", tasks: [] });

    render(<JobProgress projectId="acme-2026" jobRunId="jr-1" pollIntervalMs={10} />);

    await waitFor(() => expect(getJobStatusSpy).toHaveBeenCalledTimes(2), { timeout: 1000 });
  });

  it("retries through a transient 404 (job_run not yet checkpointed) instead of failing immediately", async () => {
    const getJobStatusSpy = vi
      .spyOn(ingestionBffClient, "getJobStatus")
      .mockRejectedValueOnce(new ingestionBffClient.JobStatusError(404, "job status fetch failed: 404"))
      .mockResolvedValueOnce({ job_run_id: "jr-1", status: "completed", tasks: [] });

    render(<JobProgress projectId="acme-2026" jobRunId="jr-1" pollIntervalMs={10} />);

    await waitFor(() => expect(screen.getByText("jr-1")).toBeInTheDocument(), { timeout: 1000 });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(getJobStatusSpy).toHaveBeenCalledTimes(2);
  });

  it("gives up and shows an error after repeated 404s", async () => {
    vi.spyOn(ingestionBffClient, "getJobStatus").mockRejectedValue(
      new ingestionBffClient.JobStatusError(404, "job status fetch failed: 404 job_run not found")
    );

    render(<JobProgress projectId="acme-2026" jobRunId="jr-gone" pollIntervalMs={5} />);

    expect(await screen.findByRole("alert", undefined, { timeout: 2000 })).toHaveTextContent("job_run not found");
  });
});
