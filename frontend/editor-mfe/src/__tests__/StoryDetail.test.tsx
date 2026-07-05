import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Story } from "../api/editorBffClient";
import { StoryDetail } from "../components/StoryDetail";

const BASE_STORY: Story = {
  _id: "story-1",
  epic_id: "epic-1",
  title: "Extract gross-pay calc",
  description: "Move gross-pay computation into a Python microservice.",
  acceptance_criteria: ["Handles overtime correctly"],
  source_program_ids: ["PAYROLL01:2000-CALC-GROSS"],
  generated_by_agent: "epic-story-writer@v1",
  edited_by_human: false,
  edit_history_ref: [],
  export_status: "not_exported",
  export_target: null,
  external_issue_key: null,
  external_issue_url: null,
};

describe("StoryDetail", () => {
  it("renders description, acceptance criteria, and traceability", () => {
    render(<StoryDetail story={BASE_STORY} onEdit={vi.fn()} />);
    expect(screen.getByText(BASE_STORY.description)).toBeInTheDocument();
    expect(screen.getByText("Handles overtime correctly")).toBeInTheDocument();
    expect(screen.getByText("PAYROLL01:2000-CALC-GROSS")).toBeInTheDocument();
  });

  it("does not show an export link when not exported", () => {
    render(<StoryDetail story={BASE_STORY} onEdit={vi.fn()} />);
    expect(screen.queryByText(/View on/)).not.toBeInTheDocument();
  });

  it("shows a View on GitHub link once exported", () => {
    const exported: Story = {
      ...BASE_STORY,
      export_status: "exported",
      export_target: "github",
      external_issue_key: "acme/repo#42",
      external_issue_url: "https://github.com/acme/repo/issues/42",
    };
    render(<StoryDetail story={exported} onEdit={vi.fn()} />);
    const link = screen.getByRole("link", { name: /View on GitHub/ });
    expect(link).toHaveAttribute("href", "https://github.com/acme/repo/issues/42");
  });

  it("calls onEdit when Edit is clicked", async () => {
    const onEdit = vi.fn();
    const user = userEvent.setup();
    render(<StoryDetail story={BASE_STORY} onEdit={onEdit} />);
    await user.click(screen.getByRole("button", { name: "Edit" }));
    expect(onEdit).toHaveBeenCalled();
  });
});
