import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as editorBffClient from "../api/editorBffClient";
import { ExportPanel } from "../components/ExportPanel";

describe("ExportPanel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders nothing when no stories are selected", () => {
    const { container } = render(
      <ExportPanel selectedEpicIds={[]} selectedStoryIds={[]} onExported={vi.fn()} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("defaults to GitHub destination and shows the GitHub connect form", () => {
    render(<ExportPanel selectedEpicIds={["epic-1"]} selectedStoryIds={["story-1"]} onExported={vi.fn()} />);
    expect(screen.getByRole("radio", { name: "GitHub" })).toBeChecked();
    expect(screen.getByLabelText("Owner")).toBeInTheDocument();
  });

  it("switches to the Jira connect form when Jira is selected", async () => {
    const user = userEvent.setup();
    render(<ExportPanel selectedEpicIds={["epic-1"]} selectedStoryIds={["story-1"]} onExported={vi.fn()} />);
    await user.click(screen.getByRole("radio", { name: "Jira" }));
    expect(screen.getByLabelText("Project key")).toBeInTheDocument();
  });

  it("exports successfully and shows results", async () => {
    vi.spyOn(editorBffClient, "exportItems").mockResolvedValue({
      exported: [{ story_id: "story-1", external_issue_key: "acme/repo#42", external_issue_url: "https://github.com/acme/repo/issues/42" }],
      failed: [],
      epic_milestones: [{ epic_id: "epic-1", external_milestone_id: "3", external_milestone_url: "https://github.com/acme/repo/milestone/3" }],
    });
    const onExported = vi.fn();
    const user = userEvent.setup();

    render(<ExportPanel selectedEpicIds={["epic-1"]} selectedStoryIds={["story-1"]} onExported={onExported} />);
    await user.click(screen.getByRole("button", { name: /Export 1 item/ }));

    await waitFor(() => expect(onExported).toHaveBeenCalled());
    expect(screen.getByRole("link", { name: "acme/repo#42" })).toBeInTheDocument();
    expect(screen.getByText("1 milestone(s) created/reused.")).toBeInTheDocument();
  });

  it("surfaces the Jira NotImplementedError verbatim", async () => {
    vi.spyOn(editorBffClient, "exportItems").mockRejectedValue(
      new Error("export failed: 501 Jira export is not yet implemented")
    );
    const user = userEvent.setup();

    render(<ExportPanel selectedEpicIds={["epic-1"]} selectedStoryIds={["story-1"]} onExported={vi.fn()} />);
    await user.click(screen.getByRole("radio", { name: "Jira" }));
    await user.click(screen.getByRole("button", { name: /Export 1 item/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Jira export is not yet implemented");
  });
});
