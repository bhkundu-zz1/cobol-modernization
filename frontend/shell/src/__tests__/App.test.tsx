import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("../remotes", () => ({
  UploadApp: () => <div>Upload remote content</div>,
  ReviewApp: () => <div>Review remote content</div>,
  EditorApp: () => {
    throw new Error("simulated Editor remote load failure");
  },
  AdminApp: () => <div>Admin remote content</div>,
}));

// Imported after the mock so App picks up the mocked remotes module.
const { default: App } = await import("../App");

describe("App (shell)", () => {
  it("renders the Upload remote by default", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText("Upload remote content")).toBeInTheDocument());
  });

  it("switches to the Review Queue remote on nav click", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "Review Queue" }));
    await waitFor(() => expect(screen.getByText("Review remote content")).toBeInTheDocument());
  });

  it("composes all four nav sections", () => {
    render(<App />);
    expect(screen.getByRole("button", { name: "Upload / Ingestion" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Review Queue" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Epic/Story Editor" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Admin / Observability" })).toBeInTheDocument();
  });

  it("isolates a failing remote's error boundary state to its own tab (regression: state must not leak to sibling tabs on switch)", async () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const user = userEvent.setup();
    render(<App />);

    // Visit the failing Editor tab first so its RemoteErrorBoundary catches
    // an error and sets hasError=true.
    await user.click(screen.getByRole("button", { name: "Epic/Story Editor" }));
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());

    // Switching to a sibling tab must render that remote's real content,
    // not the Editor boundary's stale "unavailable" fallback (this broke
    // once when the boundary wasn't remounted per tab via a `key` prop).
    await user.click(screen.getByRole("button", { name: "Upload / Ingestion" }));
    await waitFor(() => expect(screen.getByText("Upload remote content")).toBeInTheDocument());
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Review Queue" }));
    await waitFor(() => expect(screen.getByText("Review remote content")).toBeInTheDocument());
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();

    consoleErrorSpy.mockRestore();
  });
});
