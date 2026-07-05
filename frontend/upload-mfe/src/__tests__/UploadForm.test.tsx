import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as ingestionBffClient from "../api/ingestionBffClient";
import { UploadForm } from "../components/UploadForm";

describe("UploadForm", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows an error if submitted without a file", async () => {
    const user = userEvent.setup();
    render(<UploadForm projectId="acme-2026" onJobsStarted={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Upload" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("choose a file first");
  });

  it("uploads the selected file and calls onJobsStarted with its job", async () => {
    const uploadSpy = vi.spyOn(ingestionBffClient, "uploadFiles").mockResolvedValue({
      upload_batch_id: "batch-1",
      jobs: [{ filename: "PAYROLL01.CBL", job_run_id: "jr-1" }],
    });
    const onJobsStarted = vi.fn();
    const user = userEvent.setup();

    render(<UploadForm projectId="acme-2026" onJobsStarted={onJobsStarted} />);

    const file = new File(["IDENTIFICATION DIVISION."], "PAYROLL01.CBL", { type: "text/plain" });
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    await user.upload(input, file);
    await user.click(screen.getByRole("button", { name: "Upload" }));

    await waitFor(() =>
      expect(onJobsStarted).toHaveBeenCalledWith([{ filename: "PAYROLL01.CBL", job_run_id: "jr-1" }])
    );
    expect(uploadSpy).toHaveBeenCalledWith("acme-2026", [{ file, relativePath: undefined }]);
  });

  it("uploads every file selected via the folder picker and triggers a job for each", async () => {
    const uploadSpy = vi.spyOn(ingestionBffClient, "uploadFiles").mockResolvedValue({
      upload_batch_id: "batch-1",
      jobs: [
        { filename: "PAYROLL01.CBL", job_run_id: "jr-1" },
        { filename: "TIMESHEET.CBL", job_run_id: "jr-2" },
      ],
    });
    const onJobsStarted = vi.fn();
    const user = userEvent.setup();

    render(<UploadForm projectId="acme-2026" onJobsStarted={onJobsStarted} />);

    const fileA = new File(["A"], "PAYROLL01.CBL", { type: "text/plain" });
    Object.defineProperty(fileA, "webkitRelativePath", { value: "payroll-project/PAYROLL01.CBL" });
    const fileB = new File(["B"], "TIMESHEET.CBL", { type: "text/plain" });
    Object.defineProperty(fileB, "webkitRelativePath", { value: "payroll-project/TIMESHEET.CBL" });

    const input = screen.getByTestId("folder-input") as HTMLInputElement;
    await user.upload(input, [fileA, fileB]);

    expect(screen.getByText("payroll-project/PAYROLL01.CBL")).toBeInTheDocument();
    expect(screen.getByText("payroll-project/TIMESHEET.CBL")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upload 2 files" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Upload 2 files" }));

    await waitFor(() => expect(onJobsStarted).toHaveBeenCalledTimes(1));
    expect(uploadSpy).toHaveBeenCalledWith("acme-2026", [
      { file: fileA, relativePath: "payroll-project/PAYROLL01.CBL" },
      { file: fileB, relativePath: "payroll-project/TIMESHEET.CBL" },
    ]);
  });

  it("shows the error message if the upload fails", async () => {
    vi.spyOn(ingestionBffClient, "uploadFiles").mockRejectedValue(new Error("upload failed: 500 boom"));
    const user = userEvent.setup();

    render(<UploadForm projectId="acme-2026" onJobsStarted={vi.fn()} />);

    const file = new File(["x"], "BAD.CBL", { type: "text/plain" });
    await user.upload(screen.getByTestId("file-input"), file);
    await user.click(screen.getByRole("button", { name: "Upload" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("upload failed: 500 boom");
  });
});
