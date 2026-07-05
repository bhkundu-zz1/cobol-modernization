import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Badge } from "../Badge";
import { Button } from "../Button";
import { Table } from "../Table";

describe("Button", () => {
  it("renders children and defaults to the primary variant", () => {
    render(<Button>Approve</Button>);
    const button = screen.getByRole("button", { name: "Approve" });
    expect(button).toBeInTheDocument();
    expect(button.getAttribute("data-variant")).toBe("primary");
  });

  it("applies the requested variant", () => {
    render(<Button variant="danger">Reject</Button>);
    expect(screen.getByRole("button", { name: "Reject" }).getAttribute("data-variant")).toBe("danger");
  });
});

describe("Badge", () => {
  it("renders its content with the requested tone", () => {
    render(<Badge tone="warning">Needs review</Badge>);
    const badge = screen.getByText("Needs review");
    expect(badge.getAttribute("data-tone")).toBe("warning");
  });

  it("defaults to neutral tone", () => {
    render(<Badge>Pending</Badge>);
    expect(screen.getByText("Pending").getAttribute("data-tone")).toBe("neutral");
  });
});

describe("Table", () => {
  const columns = [
    { key: "name", header: "Name", render: (row: { name: string }) => row.name },
  ];

  it("renders rows via the render function", () => {
    render(<Table columns={columns} rows={[{ name: "PAYROLL01" }]} rowKey={(r) => r.name} />);
    expect(screen.getByText("PAYROLL01")).toBeInTheDocument();
  });

  it("shows the empty message when there are no rows", () => {
    render(<Table columns={columns} rows={[]} rowKey={(r: { name: string }) => r.name} emptyMessage="Nothing here" />);
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
  });
});
