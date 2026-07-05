import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as ingestionBffClient from "../api/ingestionBffClient";
import UploadApp from "../UploadApp";

describe("UploadApp", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders one JobProgress row per uploaded file", async () => {
    vi.spyOn(ingestionBffClient, "uploadFiles").mockResolvedValue({
      upload_batch_id: "batch-1",
      jobs: [
        { filename: "PAYROLL01.CBL", job_run_id: "jr-1" },
        { filename: "TIMESHEET.CBL", job_run_id: "jr-2" },
      ],
    });
    vi.spyOn(ingestionBffClient, "getJobStatus").mockResolvedValue({
      job_run_id: "jr-1",
      status: "running",
      tasks: [],
    });
    const user = userEvent.setup();

    render(<UploadApp />);

    const fileA = new File(["A"], "PAYROLL01.CBL", { type: "text/plain" });
    const fileB = new File(["B"], "TIMESHEET.CBL", { type: "text/plain" });
    await user.upload(screen.getByTestId("folder-input"), [fileA, fileB]);
    await user.click(screen.getByRole("button", { name: /Upload/ }));

    await waitFor(() => {
      expect(screen.getAllByText("PAYROLL01.CBL").length).toBeGreaterThan(0);
      expect(screen.getAllByText("TIMESHEET.CBL").length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Job/, { exact: false })).toHaveLength(2);
    });
  });
});
