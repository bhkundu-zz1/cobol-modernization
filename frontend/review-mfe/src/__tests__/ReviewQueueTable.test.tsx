import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as reviewBffClient from "../api/reviewBffClient";
import type { ReviewItem } from "../api/reviewBffClient";
import { ReviewQueueTable } from "../components/ReviewQueueTable";

const ITEM: ReviewItem = {
  subject_id: "acme-2026:e9c24ee6-e7ce-40ed-956e-fe84a2db120e:cobol_program_structure",
  subject_filename: "PAYROLL01.CBL",
  subject_type: "cobol_program",
  recommendation: {
    _id: "rec-1",
    recommended_target: "python_microservice",
    rationale: "low complexity",
    risk_flags: ["unresolved external call"],
    alternative_considered: { target: "java_spring_boot", why_rejected: "n/a" },
  },
  confidence_score: 0.9,
  needs_human_review: false,
  job_run_status: "completed",
  human_review_status: "pending",
};

describe("ReviewQueueTable", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the empty message when there are no items", () => {
    render(<ReviewQueueTable items={[]} onDecisionRecorded={vi.fn()} />);
    expect(screen.getByText("No items in the review queue yet.")).toBeInTheDocument();
  });

  it("renders a row per item with program, target, and confidence", () => {
    render(<ReviewQueueTable items={[ITEM]} onDecisionRecorded={vi.fn()} />);
    expect(screen.getByText("PAYROLL01.CBL")).toBeInTheDocument();
    expect(screen.getByText("python_microservice")).toBeInTheDocument();
    expect(screen.getByText("0.90")).toBeInTheDocument();
    expect(screen.getByText("completed")).toBeInTheDocument();
  });

  it("falls back to the raw subject_id when no filename was denormalized (older documents)", () => {
    const itemWithoutFilename = { ...ITEM, subject_filename: null };
    render(<ReviewQueueTable items={[itemWithoutFilename]} onDecisionRecorded={vi.fn()} />);
    expect(screen.getByText(ITEM.subject_id)).toBeInTheDocument();
    expect(screen.queryByText("PAYROLL01.CBL")).not.toBeInTheDocument();
  });

  it("renders low-confidence items with a danger-tone badge", () => {
    const lowConfidenceItem = { ...ITEM, confidence_score: 0.3 };
    render(<ReviewQueueTable items={[lowConfidenceItem]} onDecisionRecorded={vi.fn()} />);
    const badge = screen.getByText("0.30");
    expect(badge.getAttribute("data-tone")).toBe("danger");
  });

  it("renders Approve/Reject controls for pending items", () => {
    render(<ReviewQueueTable items={[ITEM]} onDecisionRecorded={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reject" })).toBeInTheDocument();
  });

  it("expands a row to lazily fetch and show source + backlog detail", async () => {
    vi.spyOn(reviewBffClient, "getReviewItemSource").mockResolvedValue({
      filename: "PAYROLL01.CBL",
      source_text: "IDENTIFICATION DIVISION.",
      relative_path: "payroll-project/PAYROLL01.CBL",
      language: "cobol",
    });
    vi.spyOn(reviewBffClient, "getReviewItemBacklog").mockResolvedValue({ epic: null, story: null });
    const user = userEvent.setup();

    render(<ReviewQueueTable items={[ITEM]} onDecisionRecorded={vi.fn()} />);
    expect(screen.queryByText("IDENTIFICATION DIVISION.")).not.toBeInTheDocument();

    await user.click(screen.getByText("▸"));

    await waitFor(() => expect(screen.getByText("IDENTIFICATION DIVISION.")).toBeInTheDocument());
    expect(screen.getByText("payroll-project/PAYROLL01.CBL")).toBeInTheDocument();
  });

  it("collapses an expanded row when clicked again", async () => {
    vi.spyOn(reviewBffClient, "getReviewItemSource").mockResolvedValue({
      filename: "PAYROLL01.CBL",
      source_text: "IDENTIFICATION DIVISION.",
      relative_path: null,
      language: "cobol",
    });
    vi.spyOn(reviewBffClient, "getReviewItemBacklog").mockResolvedValue({ epic: null, story: null });
    const user = userEvent.setup();

    render(<ReviewQueueTable items={[ITEM]} onDecisionRecorded={vi.fn()} />);
    await user.click(screen.getByText("▸"));
    await waitFor(() => expect(screen.getByText("IDENTIFICATION DIVISION.")).toBeInTheDocument());

    await user.click(screen.getByText("▾"));
    expect(screen.queryByText("IDENTIFICATION DIVISION.")).not.toBeInTheDocument();
  });
});
