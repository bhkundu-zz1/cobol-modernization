import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as codegenBffClient from "../api/codegenBffClient";
import CodegenApp from "../CodegenApp";

const ELIGIBLE_STORY = {
  story: {
    _id: "story-a",
    title: "Extract PAYROLL01",
    description: "...",
    acceptance_criteria: ["References paragraph 1000-MAIN"],
    source_program_ids: ["PAYROLL01"],
    code_generation_status: "not_generated" as const,
    code_generation_target: null,
    generated_code_repo_path: null,
    generated_code_commit_sha: null,
    generated_code_commit_url: null,
    code_generation_error: null,
  },
  epic_title: "Payroll subsystem",
  recommended_targets: ["python_microservice"],
};

describe("CodegenApp", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(codegenBffClient, "listEligibleStories").mockResolvedValue({ items: [] });
  });

  it("shows a loading state then the Code Generation heading", async () => {
    render(<CodegenApp />);
    expect(screen.getByText("Loading approved stories…")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Code Generation")).toBeInTheDocument());
  });

  it("shows an error if the initial load fails", async () => {
    vi.spyOn(codegenBffClient, "listEligibleStories").mockRejectedValue(
      new Error("list eligible stories failed: 500")
    );
    render(<CodegenApp />);
    expect(await screen.findByRole("alert")).toHaveTextContent("list eligible stories failed: 500");
  });

  it("lists eligible stories and shows the approved-only description", async () => {
    vi.spyOn(codegenBffClient, "listEligibleStories").mockResolvedValue({ items: [ELIGIBLE_STORY] });
    render(<CodegenApp />);

    await waitFor(() => expect(screen.getByText("Extract PAYROLL01")).toBeInTheDocument());
    expect(screen.getByText("Approved stories only.")).toBeInTheDocument();
    expect(screen.getByText("Payroll subsystem")).toBeInTheDocument();
  });

  it("triggers code generation with the selected language and polls until completed", async () => {
    vi.spyOn(codegenBffClient, "listEligibleStories").mockResolvedValue({ items: [ELIGIBLE_STORY] });
    const triggerSpy = vi
      .spyOn(codegenBffClient, "triggerCodeGeneration")
      .mockResolvedValue({ job_run_id: "jr-codegen-1", status: "running" });
    vi.spyOn(codegenBffClient, "getCodegenJobStatus")
      .mockResolvedValueOnce({ job_run_id: "jr-codegen-1", status: "running", tasks: [] })
      .mockResolvedValueOnce({ job_run_id: "jr-codegen-1", status: "completed", tasks: [] });
    const user = userEvent.setup();

    render(<CodegenApp />);
    await waitFor(() => expect(screen.getByText("Extract PAYROLL01")).toBeInTheDocument());

    await user.click(screen.getByRole("radio", { name: "Java Spring Boot" }));
    await user.click(screen.getByRole("button", { name: "Generate" }));

    expect(triggerSpy).toHaveBeenCalledWith("acme-2026", "story-a", "java_spring_boot");
    await waitFor(() => expect(screen.getByText("jr-codegen-1")).toBeInTheDocument(), { timeout: 3000 });
    await waitFor(() => expect(screen.getByText("completed")).toBeInTheDocument(), { timeout: 3000 });
  });

  it("tolerates a 404 while the job_run doc doesn't exist yet", async () => {
    vi.spyOn(codegenBffClient, "listEligibleStories").mockResolvedValue({ items: [ELIGIBLE_STORY] });
    vi.spyOn(codegenBffClient, "triggerCodeGeneration").mockResolvedValue({
      job_run_id: "jr-codegen-2",
      status: "running",
    });
    vi.spyOn(codegenBffClient, "getCodegenJobStatus")
      .mockRejectedValueOnce(new codegenBffClient.CodegenJobStatusError(404, "job status fetch failed: 404"))
      .mockResolvedValueOnce({ job_run_id: "jr-codegen-2", status: "completed", tasks: [] });
    const user = userEvent.setup();

    render(<CodegenApp />);
    await waitFor(() => expect(screen.getByText("Extract PAYROLL01")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Generate" }));

    await waitFor(() => expect(screen.getByText("completed")).toBeInTheDocument(), { timeout: 3000 });
  });

  it("surfaces an error if triggering generation fails", async () => {
    vi.spyOn(codegenBffClient, "listEligibleStories").mockResolvedValue({ items: [ELIGIBLE_STORY] });
    vi.spyOn(codegenBffClient, "triggerCodeGeneration").mockRejectedValue(new Error("generate code failed: 500"));
    const user = userEvent.setup();

    render(<CodegenApp />);
    await waitFor(() => expect(screen.getByText("Extract PAYROLL01")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Generate" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("generate code failed: 500");
  });
});
