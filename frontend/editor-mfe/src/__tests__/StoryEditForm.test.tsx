import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as editorBffClient from "../api/editorBffClient";
import type { Story } from "../api/editorBffClient";
import { StoryEditForm } from "../components/StoryEditForm";

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

describe("StoryEditForm", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("pre-fills fields from the story", () => {
    render(<StoryEditForm story={BASE_STORY} onSaved={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByLabelText("Title")).toHaveValue(BASE_STORY.title);
    expect(screen.getByLabelText("Description")).toHaveValue(BASE_STORY.description);
    expect(screen.getByLabelText("Acceptance criterion 1")).toHaveValue("Handles overtime correctly");
  });

  it("calls updateStory and onSaved when Save is clicked", async () => {
    const updateStorySpy = vi
      .spyOn(editorBffClient, "updateStory")
      .mockResolvedValue({ story_id: "story-1", edited_by_human: true, edit_history_ref: ["e1"] });
    const onSaved = vi.fn();
    const user = userEvent.setup();

    render(<StoryEditForm story={BASE_STORY} onSaved={onSaved} onCancel={vi.fn()} />);
    await user.clear(screen.getByLabelText("Title"));
    await user.type(screen.getByLabelText("Title"), "Revised title");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    expect(updateStorySpy).toHaveBeenCalledWith(
      "story-1",
      expect.objectContaining({ title: "Revised title", edited_by: expect.any(String) })
    );
  });

  it("adds and removes acceptance criteria", async () => {
    const user = userEvent.setup();
    render(<StoryEditForm story={BASE_STORY} onSaved={vi.fn()} onCancel={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Add acceptance criterion" }));
    expect(screen.getByLabelText("Acceptance criterion 2")).toBeInTheDocument();

    await user.click(screen.getAllByRole("button", { name: "Remove" })[1]);
    expect(screen.queryByLabelText("Acceptance criterion 2")).not.toBeInTheDocument();
  });

  it("shows an error if updateStory fails", async () => {
    vi.spyOn(editorBffClient, "updateStory").mockRejectedValue(new Error("update story failed: 500"));
    const user = userEvent.setup();

    render(<StoryEditForm story={BASE_STORY} onSaved={vi.fn()} onCancel={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("update story failed: 500");
  });

  it("calls onCancel when Cancel is clicked", async () => {
    const onCancel = vi.fn();
    const user = userEvent.setup();
    render(<StoryEditForm story={BASE_STORY} onSaved={vi.fn()} onCancel={onCancel} />);
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalled();
  });
});
