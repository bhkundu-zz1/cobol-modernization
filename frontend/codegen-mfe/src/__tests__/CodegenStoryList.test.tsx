import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CodegenStoryList } from "../components/CodegenStoryList";
import type { EligibleStorySummary } from "../api/codegenBffClient";

const BASE_STORY: EligibleStorySummary = {
  story: {
    _id: "story-a",
    title: "Extract PAYROLL01",
    description: "...",
    acceptance_criteria: [],
    source_program_ids: ["PAYROLL01"],
    code_generation_status: "not_generated",
    code_generation_target: null,
    generated_code_repo_path: null,
    generated_code_commit_sha: null,
    generated_code_commit_url: null,
    code_generation_error: null,
  },
  epic_title: "Payroll subsystem",
  recommended_targets: ["python_microservice"],
};

describe("CodegenStoryList", () => {
  it("shows an empty-state message when there are no eligible stories", () => {
    render(<CodegenStoryList items={[]} generatingStoryId={null} onGenerate={vi.fn()} />);
    expect(screen.getByText("No approved stories are available for code generation yet.")).toBeInTheDocument();
  });

  it("calls onGenerate with the story id when Generate is clicked", async () => {
    const onGenerate = vi.fn();
    const user = userEvent.setup();
    render(<CodegenStoryList items={[BASE_STORY]} generatingStoryId={null} onGenerate={onGenerate} />);

    await user.click(screen.getByRole("button", { name: "Generate" }));

    expect(onGenerate).toHaveBeenCalledWith("story-a");
  });

  it("disables every row's button while any row is generating", () => {
    render(<CodegenStoryList items={[BASE_STORY]} generatingStoryId="story-a" onGenerate={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Generating…" })).toBeDisabled();
  });

  it("shows a link to the commit when a story has completed generation", () => {
    const generated: EligibleStorySummary = {
      ...BASE_STORY,
      story: {
        ...BASE_STORY.story,
        code_generation_status: "generated",
        generated_code_repo_path: "story-a",
        generated_code_commit_sha: "abc123",
        generated_code_commit_url: "https://github.com/acme-org/generated-migrations/commit/abc123",
      },
    };
    render(<CodegenStoryList items={[generated]} generatingStoryId={null} onGenerate={vi.fn()} />);
    expect(screen.getByRole("link", { name: "view commit" })).toHaveAttribute(
      "href",
      "https://github.com/acme-org/generated-migrations/commit/abc123"
    );
  });

  it("shows the error message when a story's generation failed", () => {
    const failed: EligibleStorySummary = {
      ...BASE_STORY,
      story: {
        ...BASE_STORY.story,
        code_generation_status: "failed",
        code_generation_error: "program has no plain_english_summary",
      },
    };
    render(<CodegenStoryList items={[failed]} generatingStoryId={null} onGenerate={vi.fn()} />);
    expect(screen.getByRole("alert")).toHaveTextContent("program has no plain_english_summary");
  });
});
