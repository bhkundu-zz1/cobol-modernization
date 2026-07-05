import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as reviewBffClient from "../api/reviewBffClient";
import ReviewApp from "../ReviewApp";

describe("ReviewApp", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(reviewBffClient, "listReviewItems").mockResolvedValue({ items: [], bookmark: null });
  });

  it("shows a loading state then the review queue heading", async () => {
    render(<ReviewApp />);
    expect(screen.getByText("Loading review queue…")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Review Queue")).toBeInTheDocument());
  });

  it("shows an error if the initial load fails", async () => {
    vi.spyOn(reviewBffClient, "listReviewItems").mockRejectedValue(new Error("list review items failed: 500"));
    render(<ReviewApp />);
    expect(await screen.findByRole("alert")).toHaveTextContent("list review items failed: 500");
  });

  it("triggers epic/story generation and polls until completed", async () => {
    vi.spyOn(reviewBffClient, "triggerEpicStoryGeneration").mockResolvedValue({
      job_run_id: "jr-epic-1",
      status: "running",
    });
    vi.spyOn(reviewBffClient, "getEpicStoryJobStatus")
      .mockResolvedValueOnce({ job_run_id: "jr-epic-1", status: "running", tasks: [] })
      .mockResolvedValueOnce({ job_run_id: "jr-epic-1", status: "completed", tasks: [] });
    const user = userEvent.setup();

    render(<ReviewApp />);
    await waitFor(() => expect(screen.getByText("Review Queue")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "Generate Epics & Stories" }));

    await waitFor(() => expect(screen.getByText("jr-epic-1")).toBeInTheDocument(), { timeout: 3000 });
    await waitFor(() => expect(screen.getByText("completed")).toBeInTheDocument(), { timeout: 3000 });
  });

  it("surfaces an error if triggering generation fails", async () => {
    vi.spyOn(reviewBffClient, "triggerEpicStoryGeneration").mockRejectedValue(
      new Error("generate epics/stories failed: 500")
    );
    const user = userEvent.setup();

    render(<ReviewApp />);
    await waitFor(() => expect(screen.getByText("Review Queue")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Generate Epics & Stories" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("generate epics/stories failed: 500");
  });
});
