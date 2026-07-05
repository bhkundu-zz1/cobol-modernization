import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as editorBffClient from "../api/editorBffClient";
import type { Epic, Story } from "../api/editorBffClient";
import { EpicList } from "../components/EpicList";

const EPIC: Epic = {
  _id: "epic-1",
  title: "Extract payroll gross-pay calculation",
  description: "Migrate gross-pay off the mainframe.",
  export_target: null,
  external_milestone_id: null,
  external_milestone_url: null,
};

const STORY: Story = {
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

function renderList(overrides: Partial<React.ComponentProps<typeof EpicList>> = {}) {
  return render(
    <EpicList
      epics={[EPIC]}
      selectedEpicIds={new Set()}
      selectedStoryIds={new Set()}
      onToggleEpic={vi.fn()}
      onToggleStory={vi.fn()}
      {...overrides}
    />
  );
}

describe("EpicList", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a placeholder message when there are no epics", () => {
    render(
      <EpicList epics={[]} selectedEpicIds={new Set()} selectedStoryIds={new Set()} onToggleEpic={vi.fn()} onToggleStory={vi.fn()} />
    );
    expect(screen.getByText(/No epics yet/)).toBeInTheDocument();
  });

  it("lists epic titles collapsed by default", () => {
    renderList();
    expect(screen.getByText(EPIC.title)).toBeInTheDocument();
    expect(screen.queryByText(STORY.title)).not.toBeInTheDocument();
  });

  it("loads and shows stories when an epic is expanded", async () => {
    vi.spyOn(editorBffClient, "listEpicStories").mockResolvedValue({ items: [STORY], bookmark: null });
    const user = userEvent.setup();
    renderList();

    await user.click(screen.getByText("▸"));

    await waitFor(() => expect(screen.getByText(STORY.title)).toBeInTheDocument());
  });

  it("calls onToggleEpic when the epic checkbox is clicked", async () => {
    const onToggleEpic = vi.fn();
    const user = userEvent.setup();
    renderList({ onToggleEpic });

    await user.click(screen.getByLabelText(`Select epic ${EPIC.title}`));
    expect(onToggleEpic).toHaveBeenCalledWith("epic-1");
  });

  it("expands story detail and switches to edit mode", async () => {
    vi.spyOn(editorBffClient, "listEpicStories").mockResolvedValue({ items: [STORY], bookmark: null });
    const user = userEvent.setup();
    renderList();

    await user.click(screen.getByText("▸"));
    await waitFor(() => screen.getByText(STORY.title));
    await user.click(screen.getByRole("button", { name: STORY.title }));

    expect(await screen.findByText(STORY.description)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.getByLabelText("Title")).toBeInTheDocument();
  });
});
