import { useState } from "react";

import { Button } from "@harness/design-system";

import { recordDecision } from "../api/reviewBffClient";

const PROJECT_ID = import.meta.env.VITE_DEFAULT_PROJECT_ID || "acme-2026";
const REVIEWED_BY = import.meta.env.VITE_CURRENT_USER_EMAIL || "reviewer@example.com";

export interface ApproveRejectControlsProps {
  recommendationId: string;
  currentStatus: string;
  onDecisionRecorded: (decision: "approved" | "rejected") => void;
}

export function ApproveRejectControls({ recommendationId, currentStatus, onDecisionRecorded }: ApproveRejectControlsProps) {
  const [submitting, setSubmitting] = useState<"approved" | "rejected" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleDecision(decision: "approved" | "rejected") {
    setSubmitting(decision);
    setError(null);
    try {
      await recordDecision(PROJECT_ID, recommendationId, decision, REVIEWED_BY);
      onDecisionRecorded(decision);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(null);
    }
  }

  if (currentStatus !== "pending") {
    return <span>{currentStatus}</span>;
  }

  return (
    <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
      <Button variant="primary" onClick={() => handleDecision("approved")} disabled={submitting !== null}>
        {submitting === "approved" ? "Approving…" : "Approve"}
      </Button>
      <Button variant="danger" onClick={() => handleDecision("rejected")} disabled={submitting !== null}>
        {submitting === "rejected" ? "Rejecting…" : "Reject"}
      </Button>
      {error && <span role="alert">{error}</span>}
    </div>
  );
}
