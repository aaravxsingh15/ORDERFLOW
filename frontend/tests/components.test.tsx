import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BottleneckCard } from "@/components/analysis/bottleneck-card";
import { ImportanceBars } from "@/components/analysis/importance-bars";
import { DeliveryTimeline } from "@/components/pipeline/delivery-timeline";
import { StatusBadge } from "@/components/ui/badge";
import type { Stage } from "@/lib/types";

const stages: Stage[] = [
  { key: "placed", label: "Order Placed", minutes: 0, cumulative: 0, flag: null, excess_minutes: 0 },
  { key: "accepted", label: "Restaurant Accepted", minutes: 1, cumulative: 1, flag: null, excess_minutes: 0 },
  { key: "preparing", label: "Preparing", minutes: 24, cumulative: 25, flag: "primary", excess_minutes: 8 },
  { key: "assignment", label: "Rider Assigned", minutes: 8, cumulative: 33, flag: "secondary", excess_minutes: 5 },
  { key: "pickup", label: "Pickup", minutes: 6, cumulative: 39, flag: null, excess_minutes: 3 },
  { key: "transit", label: "In Transit", minutes: 18, cumulative: 57, flag: null, excess_minutes: 0 },
  { key: "delivered", label: "Delivered", minutes: 0, cumulative: 57, flag: null, excess_minutes: 0 },
];

describe("delivery timeline", () => {
  it("shows every stage, the minutes spent and the total", () => {
    render(<DeliveryTimeline stages={stages} total={57} />);
    for (const s of stages) expect(screen.getByText(s.label)).toBeInTheDocument();
    expect(screen.getByText("24 min")).toBeInTheDocument();
    expect(screen.getByText("57 min", { selector: "span.num.text-base" })).toBeInTheDocument();
    expect(screen.getAllByLabelText(/contributing stage/i).length).toBeGreaterThanOrEqual(2);
  });
});

describe("explanations", () => {
  it("states that importance is not causation", () => {
    render(<ImportanceBars status="AT RISK" items={[{ label: "Traffic Level", value: "Heavy", delta_probability: 0.2, influence_pct: 60, direction: "increases" }]} />);
    expect(screen.getByText(/why was this order flagged/i)).toBeInTheDocument();
    expect(screen.getByText(/does not prove direct causation/i)).toBeInTheDocument();
  });

  it("uses cautious wording for bottlenecks", () => {
    render(<BottleneckCard b={{ primary: { name: "Restaurant Preparation", contribution_pct: 38, minutes: 9 }, secondary: { name: "Rider Assignment", contribution_pct: 24, minutes: 6 }, contributions: [], method: "" }} />);
    expect(screen.getByText("Restaurant Preparation")).toBeInTheDocument();
    expect(screen.getByText(/not proven causes/i)).toBeInTheDocument();
  });

  it("renders the status badge text", () => {
    render(<StatusBadge status="DELAY LIKELY" />);
    expect(screen.getByText("DELAY LIKELY")).toBeInTheDocument();
  });
});
