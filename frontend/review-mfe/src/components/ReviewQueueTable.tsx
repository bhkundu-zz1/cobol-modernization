import { Fragment, useState } from "react";

import { Badge } from "@harness/design-system";

import {
  getReviewItemBacklog,
  getReviewItemSource,
  type ReviewItem,
  type ReviewItemBacklog,
  type ReviewItemSource,
} from "../api/reviewBffClient";
import { ApproveRejectControls } from "./ApproveRejectControls";
import { RecommendationDetail } from "./RecommendationDetail";

const PROJECT_ID = import.meta.env.VITE_DEFAULT_PROJECT_ID || "acme-2026";

export interface ReviewQueueTableProps {
  items: ReviewItem[];
  onDecisionRecorded: (recommendationId: string, decision: "approved" | "rejected") => void;
}

function confidenceTone(score: number): "success" | "warning" | "danger" {
  if (score >= 0.8) return "success";
  if (score >= 0.5) return "warning";
  return "danger";
}

// Table<T> (design-system) renders one flat <tr> per row with no nested/
// expand slot — same limitation the Editor MFE's EpicList.tsx hit, solved
// there by hand-rolling the list instead. Reused here for the same reason:
// each row can expand into a 3-panel detail view.
export function ReviewQueueTable({ items, onDecisionRecorded }: ReviewQueueTableProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [sourceByRecommendationId, setSourceByRecommendationId] = useState<Record<string, ReviewItemSource>>({});
  const [backlogByRecommendationId, setBacklogByRecommendationId] = useState<Record<string, ReviewItemBacklog>>({});
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  async function toggleExpand(recommendationId: string) {
    if (expandedId === recommendationId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(recommendationId);

    if (!sourceByRecommendationId[recommendationId] || !backlogByRecommendationId[recommendationId]) {
      setLoadingId(recommendationId);
      setDetailError(null);
      try {
        const [source, backlog] = await Promise.all([
          getReviewItemSource(PROJECT_ID, recommendationId),
          getReviewItemBacklog(PROJECT_ID, recommendationId),
        ]);
        setSourceByRecommendationId((prev) => ({ ...prev, [recommendationId]: source }));
        setBacklogByRecommendationId((prev) => ({ ...prev, [recommendationId]: backlog }));
      } catch (err) {
        setDetailError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoadingId(null);
      }
    }
  }

  if (items.length === 0) {
    return <p>No items in the review queue yet.</p>;
  }

  return (
    <table style={{ width: "100%", borderCollapse: "collapse" }}>
      <thead>
        <tr>
          {["", "Program", "Recommended target", "Confidence", "Review status", "Job status", "Decision"].map(
            (header) => (
              <th key={header} style={{ textAlign: "left", borderBottom: "2px solid #e5e7eb", padding: "0.5rem" }}>
                {header}
              </th>
            )
          )}
        </tr>
      </thead>
      <tbody>
        {items.map((item) => {
          const recommendationId = item.recommendation._id;
          const isExpanded = expandedId === recommendationId;
          return (
            <Fragment key={recommendationId}>
              <tr>
                <td style={{ borderBottom: "1px solid #f3f4f6", padding: "0.5rem" }}>
                  <button type="button" onClick={() => toggleExpand(recommendationId)}>
                    {isExpanded ? "▾" : "▸"}
                  </button>
                </td>
                <td style={{ borderBottom: "1px solid #f3f4f6", padding: "0.5rem" }}>
                  {item.subject_filename ?? item.subject_id}
                </td>
                <td style={{ borderBottom: "1px solid #f3f4f6", padding: "0.5rem" }}>
                  {item.recommendation.recommended_target}
                </td>
                <td style={{ borderBottom: "1px solid #f3f4f6", padding: "0.5rem" }}>
                  <Badge tone={confidenceTone(item.confidence_score)}>{item.confidence_score.toFixed(2)}</Badge>
                </td>
                <td style={{ borderBottom: "1px solid #f3f4f6", padding: "0.5rem" }}>
                  <Badge tone={item.human_review_status === "pending" ? "neutral" : "success"}>
                    {item.human_review_status}
                  </Badge>
                </td>
                <td style={{ borderBottom: "1px solid #f3f4f6", padding: "0.5rem" }}>{item.job_run_status ?? "—"}</td>
                <td style={{ borderBottom: "1px solid #f3f4f6", padding: "0.5rem" }}>
                  <ApproveRejectControls
                    recommendationId={recommendationId}
                    currentStatus={item.human_review_status}
                    onDecisionRecorded={(decision) => onDecisionRecorded(recommendationId, decision)}
                  />
                </td>
              </tr>
              {isExpanded && (
                <tr>
                  <td colSpan={7} style={{ borderBottom: "1px solid #f3f4f6", padding: "0 0.5rem" }}>
                    <RecommendationDetail
                      item={item}
                      source={sourceByRecommendationId[recommendationId] ?? null}
                      backlog={backlogByRecommendationId[recommendationId] ?? null}
                      loading={loadingId === recommendationId}
                      error={detailError}
                    />
                  </td>
                </tr>
              )}
            </Fragment>
          );
        })}
      </tbody>
    </table>
  );
}
