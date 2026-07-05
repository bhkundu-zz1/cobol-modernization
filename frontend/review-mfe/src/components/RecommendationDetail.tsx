import { Badge } from "@harness/design-system";

import type { ReviewItem, ReviewItemBacklog, ReviewItemSource } from "../api/reviewBffClient";

export interface RecommendationDetailProps {
  item: ReviewItem;
  source: ReviewItemSource | null;
  backlog: ReviewItemBacklog | null;
  loading: boolean;
  error: string | null;
}

function confidenceTone(score: number): "success" | "warning" | "danger" {
  if (score >= 0.8) return "success";
  if (score >= 0.5) return "warning";
  return "danger";
}

export function RecommendationDetail({ item, source, backlog, loading, error }: RecommendationDetailProps) {
  if (loading) {
    return <p>Loading detail…</p>;
  }

  if (error) {
    return <p role="alert">{error}</p>;
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem", padding: "1rem 0" }}>
      <div>
        <h4>Source (COBOL)</h4>
        {source?.relative_path && (
          <p>
            Source: <code>{source.relative_path}</code>
          </p>
        )}
        {source?.source_text ? (
          <pre
            style={{
              maxHeight: "20rem",
              overflow: "auto",
              backgroundColor: "#f9fafb",
              padding: "0.5rem",
              fontSize: "0.75rem",
            }}
          >
            {source.source_text}
          </pre>
        ) : (
          <p>Source not available for this upload — re-upload the file to enable this view.</p>
        )}
      </div>

      <div>
        <h4>Recommendation</h4>
        <p>
          Target: <strong>{item.recommendation.recommended_target}</strong>
        </p>
        <p>{item.recommendation.rationale}</p>
        <p>
          Alternative considered: {item.recommendation.alternative_considered.target} —{" "}
          {item.recommendation.alternative_considered.why_rejected}
        </p>
        <h5>Risk flags</h5>
        {item.recommendation.risk_flags.length === 0 ? (
          <p>None.</p>
        ) : (
          <ul>
            {item.recommendation.risk_flags.map((flag, index) => (
              <li key={index}>{flag}</li>
            ))}
          </ul>
        )}
        {item.recommendation.decision_factors && (
          <>
            <h5>Decision factors</h5>
            <ul>
              {Object.entries(item.recommendation.decision_factors).map(([key, value]) => (
                <li key={key}>
                  {key}: {String(value)}
                </li>
              ))}
            </ul>
          </>
        )}
      </div>

      <div>
        <h4>Epic/Story</h4>
        {backlog?.epic && backlog?.story ? (
          <>
            <p>
              Epic: <strong>{backlog.epic.title}</strong>{" "}
              <Badge tone={confidenceTone(backlog.epic.confidence_score)}>
                {backlog.epic.confidence_score.toFixed(2)}
              </Badge>
            </p>
            <p>{backlog.epic.description}</p>
            <p>
              Story: <strong>{backlog.story.title}</strong>{" "}
              <Badge tone={confidenceTone(backlog.story.confidence_score)}>
                {backlog.story.confidence_score.toFixed(2)}
              </Badge>
            </p>
            <h5>Acceptance criteria</h5>
            <ul>
              {backlog.story.acceptance_criteria.map((criterion, index) => (
                <li key={index}>{criterion}</li>
              ))}
            </ul>
          </>
        ) : (
          <p>Not yet grouped into an epic — click "Generate Epics &amp; Stories" above.</p>
        )}
      </div>
    </div>
  );
}
