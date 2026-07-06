import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { LanguagePicker } from "../components/LanguagePicker";

describe("LanguagePicker", () => {
  it("marks the current value as checked", () => {
    render(<LanguagePicker value="python" onChange={vi.fn()} />);
    expect(screen.getByRole("radio", { name: "Python" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Java Spring Boot" })).not.toBeChecked();
  });

  it("calls onChange with the newly selected language", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<LanguagePicker value="python" onChange={onChange} />);

    await user.click(screen.getByRole("radio", { name: "Java Spring Boot" }));

    expect(onChange).toHaveBeenCalledWith("java_spring_boot");
  });

  it("disables both options when disabled", () => {
    render(<LanguagePicker value="python" onChange={vi.fn()} disabled />);
    expect(screen.getByRole("radio", { name: "Python" })).toBeDisabled();
    expect(screen.getByRole("radio", { name: "Java Spring Boot" })).toBeDisabled();
  });
});
