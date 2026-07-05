import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as ingestionBffClient from "../api/ingestionBffClient";
import { MainframeConnectForm } from "../components/MainframeConnectForm";

describe("MainframeConnectForm", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("defaults to the mock tool and lists elements on browse", async () => {
    vi.spyOn(ingestionBffClient, "listMainframeElements").mockResolvedValue({
      elements: [{ element_id: "PAYROLL01", element_type: "COBOL", version: "12" }],
    });
    const user = userEvent.setup();

    render(<MainframeConnectForm projectId="acme-2026" onJobStarted={vi.fn()} />);

    expect(screen.getByRole("combobox")).toHaveValue("mock");
    await user.click(screen.getByRole("button", { name: "List elements" }));

    expect(await screen.findByText(/PAYROLL01/)).toBeInTheDocument();
  });

  it("pulls the selected element and calls onJobStarted", async () => {
    vi.spyOn(ingestionBffClient, "listMainframeElements").mockResolvedValue({
      elements: [{ element_id: "PAYROLL01", element_type: "COBOL", version: "12" }],
    });
    vi.spyOn(ingestionBffClient, "pullMainframeElement").mockResolvedValue({
      upload_batch_id: "batch-2",
      job_run_id: "jr-2",
    });
    const onJobStarted = vi.fn();
    const user = userEvent.setup();

    render(<MainframeConnectForm projectId="acme-2026" onJobStarted={onJobStarted} />);

    await user.click(screen.getByRole("button", { name: "List elements" }));
    await screen.findByText(/PAYROLL01/);
    await user.click(screen.getByRole("radio"));
    await user.click(screen.getByRole("button", { name: "Pull selected" }));

    await waitFor(() => expect(onJobStarted).toHaveBeenCalledWith("jr-2"));
  });

  it("selecting a real (non-mock) tool and pulling surfaces the not-implemented error cleanly", async () => {
    vi.spyOn(ingestionBffClient, "listMainframeElements").mockResolvedValue({
      elements: [{ element_id: "PAYROLL01", element_type: "COBOL" }],
    });
    vi.spyOn(ingestionBffClient, "pullMainframeElement").mockRejectedValue(
      new Error(
        "mainframe pull failed: 501 Endevor connector wire protocol not yet implemented (selecting a real, non-mock tool before its wire protocol is implemented)"
      )
    );
    const onJobStarted = vi.fn();
    const user = userEvent.setup();

    render(<MainframeConnectForm projectId="acme-2026" onJobStarted={onJobStarted} />);

    await user.selectOptions(screen.getByRole("combobox"), "endevor");
    await user.click(screen.getByRole("button", { name: "List elements" }));
    await screen.findByText(/PAYROLL01/);
    await user.click(screen.getByRole("radio"));
    await user.click(screen.getByRole("button", { name: "Pull selected" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("not yet implemented");
    expect(onJobStarted).not.toHaveBeenCalled();
  });

  it("requires an element to be selected before pulling", async () => {
    const user = userEvent.setup();
    render(<MainframeConnectForm projectId="acme-2026" onJobStarted={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Pull selected" })).toBeDisabled();
  });
});
