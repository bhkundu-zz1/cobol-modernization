import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RemoteErrorBoundary } from "../RemoteErrorBoundary";

function ThrowingComponent(): React.ReactElement {
  throw new Error("simulated remote load failure");
}

function WorkingComponent() {
  return <p>Sibling content still rendering</p>;
}

describe("RemoteErrorBoundary", () => {
  it("renders children normally when there is no error", () => {
    render(
      <RemoteErrorBoundary remoteName="Upload/Ingestion">
        <WorkingComponent />
      </RemoteErrorBoundary>
    );
    expect(screen.getByText("Sibling content still rendering")).toBeInTheDocument();
  });

  it("renders a fallback for the failing remote without throwing to the caller", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <RemoteErrorBoundary remoteName="Epic/Story Editor">
        <ThrowingComponent />
      </RemoteErrorBoundary>
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Epic/Story Editor");
    expect(screen.getByRole("alert")).toHaveTextContent("temporarily unavailable");

    consoleErrorSpy.mockRestore();
  });

  it("isolates failure: a second, independent boundary around a working remote is unaffected", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <div>
        <RemoteErrorBoundary remoteName="Epic/Story Editor">
          <ThrowingComponent />
        </RemoteErrorBoundary>
        <RemoteErrorBoundary remoteName="Review Queue">
          <WorkingComponent />
        </RemoteErrorBoundary>
      </div>
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Epic/Story Editor");
    expect(screen.getByText("Sibling content still rendering")).toBeInTheDocument();

    consoleErrorSpy.mockRestore();
  });
});
