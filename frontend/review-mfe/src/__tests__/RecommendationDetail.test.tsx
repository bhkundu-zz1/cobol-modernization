import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ReviewItem, ReviewItemBacklog, ReviewItemSource } from "../api/reviewBffClient";
import { RecommendationDetail } from "../components/RecommendationDetail";

const ITEM: ReviewItem = {
  subject_id: "acme-2026:sf-1:cobol_program_structure",
  subject_filename: "PAYROLL01.CBL",
  subject_type: "cobol_program",
  recommendation: {
    _id: "rec-1",
    recommended_target: "python_microservice",
    rationale: "low complexity, no heavy state",
    risk_flags: ["unresolved external CALL to SUBRTN99"],
    alternative_considered: { target: "java_spring_boot", why_rejected: "no JVM investment justifying overhead" },
    decision_factors: { complexity: "low" },
  },
  confidence_score: 0.9,
  needs_human_review: false,
  job_run_status: "completed",
  human_review_status: "pending",
};

const SOURCE_WITH_TEXT: ReviewItemSource = {
  filename: "PAYROLL01.CBL",
  source_text: "IDENTIFICATION DIVISION.\nPROGRAM-ID. PAYROLL01.",
  relative_path: "payroll-project/PAYROLL01.CBL",
  language: "cobol",
};

const SOURCE_WITHOUT_TEXT: ReviewItemSource = {
  filename: null,
  source_text: null,
  relative_path: null,
  language: null,
};

const BACKLOG_WITH_STORY: ReviewItemBacklog = {
  epic: { _id: "epic-1", title: "Payroll subsystem", description: "Groups payroll processing.", confidence_score: 0.85 },
  story: {
    _id: "story-1",
    epic_id: "epic-1",
    title: "Extract PAYROLL01 gross-pay calc",
    description: "...",
    acceptance_criteria: ["References paragraph 1000-MAIN"],
    confidence_score: 0.8,
  },
};

const BACKLOG_EMPTY: ReviewItemBacklog = { epic: null, story: null };

describe("RecommendationDetail", () => {
  it("shows a loading state", () => {
    render(<RecommendationDetail item={ITEM} source={null} backlog={null} loading={true} error={null} />);
    expect(screen.getByText("Loading detail…")).toBeInTheDocument();
  });

  it("shows an error state", () => {
    render(<RecommendationDetail item={ITEM} source={null} backlog={null} loading={false} error="boom" />);
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
  });

  it("renders real COBOL source and its relative path label", () => {
    render(
      <RecommendationDetail item={ITEM} source={SOURCE_WITH_TEXT} backlog={BACKLOG_EMPTY} loading={false} error={null} />
    );
    expect(screen.getByText(/IDENTIFICATION DIVISION/)).toBeInTheDocument();
    expect(screen.getByText("payroll-project/PAYROLL01.CBL")).toBeInTheDocument();
  });

  it("shows a not-available message when source_text is null", () => {
    render(
      <RecommendationDetail
        item={ITEM}
        source={SOURCE_WITHOUT_TEXT}
        backlog={BACKLOG_EMPTY}
        loading={false}
        error={null}
      />
    );
    expect(screen.getByText(/Source not available for this upload/)).toBeInTheDocument();
  });

  it("renders recommendation rationale, alternative, and risk flags", () => {
    render(
      <RecommendationDetail item={ITEM} source={SOURCE_WITH_TEXT} backlog={BACKLOG_EMPTY} loading={false} error={null} />
    );
    expect(screen.getByText(ITEM.recommendation.rationale)).toBeInTheDocument();
    expect(screen.getByText(/java_spring_boot/)).toBeInTheDocument();
    expect(screen.getByText("unresolved external CALL to SUBRTN99")).toBeInTheDocument();
  });

  it("shows a not-yet-grouped placeholder when no epic/story exists", () => {
    render(
      <RecommendationDetail item={ITEM} source={SOURCE_WITH_TEXT} backlog={BACKLOG_EMPTY} loading={false} error={null} />
    );
    expect(screen.getByText(/Not yet grouped into an epic/)).toBeInTheDocument();
  });

  it("renders the generated epic/story with confidence badges when present", () => {
    render(
      <RecommendationDetail
        item={ITEM}
        source={SOURCE_WITH_TEXT}
        backlog={BACKLOG_WITH_STORY}
        loading={false}
        error={null}
      />
    );
    expect(screen.getByText("Payroll subsystem")).toBeInTheDocument();
    expect(screen.getByText("Extract PAYROLL01 gross-pay calc")).toBeInTheDocument();
    expect(screen.getByText("References paragraph 1000-MAIN")).toBeInTheDocument();
    expect(screen.getByText("0.85")).toBeInTheDocument();
    expect(screen.getByText("0.80")).toBeInTheDocument();
  });
});
