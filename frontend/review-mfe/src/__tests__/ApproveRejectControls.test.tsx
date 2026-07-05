import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as reviewBffClient from "../api/reviewBffClient";
import { ApproveRejectControls } from "../components/ApproveRejectControls";

describe("ApproveRejectControls", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows Approve/Reject buttons when status is pending", () => {
    render(<ApproveRejectControls recommendationId="rec-1" currentStatus="pending" onDecisionRecorded={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reject" })).toBeInTheDocument();
  });

  it("shows the status text (no buttons) once already decided", () => {
    render(<ApproveRejectControls recommendationId="rec-1" currentStatus="approved" onDecisionRecorded={vi.fn()} />);
    expect(screen.getByText("approved")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
  });

  it("calls recordDecision and onDecisionRecorded when Approve is clicked", async () => {
    const recordDecisionSpy = vi
      .spyOn(reviewBffClient, "recordDecision")
      .mockResolvedValue({ recommendation_id: "rec-1", human_review_status: "approved" });
    const onDecisionRecorded = vi.fn();
    const user = userEvent.setup();

    render(<ApproveRejectControls recommendationId="rec-1" currentStatus="pending" onDecisionRecorded={onDecisionRecorded} />);
    await user.click(screen.getByRole("button", { name: "Approve" }));

    await waitFor(() => expect(onDecisionRecorded).toHaveBeenCalledWith("approved"));
    expect(recordDecisionSpy).toHaveBeenCalledWith(expect.any(String), "rec-1", "approved", expect.any(String));
  });

  it("shows an error if recordDecision fails", async () => {
    vi.spyOn(reviewBffClient, "recordDecision").mockRejectedValue(new Error("record decision failed: 500"));
    const user = userEvent.setup();

    render(<ApproveRejectControls recommendationId="rec-1" currentStatus="pending" onDecisionRecorded={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Reject" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("record decision failed: 500");
  });
});
