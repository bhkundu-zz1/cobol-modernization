import type { Story } from "../api/editorBffClient";

export interface StoryDetailProps {
  story: Story;
  onEdit: () => void;
}

export function StoryDetail({ story, onEdit }: StoryDetailProps) {
  return (
    <div>
      <p>{story.description}</p>

      <h4>Acceptance Criteria</h4>
      {story.acceptance_criteria.length === 0 ? (
        <p>None recorded.</p>
      ) : (
        <ul>
          {story.acceptance_criteria.map((criterion, index) => (
            <li key={index}>{criterion}</li>
          ))}
        </ul>
      )}

      <h4>Traceability</h4>
      {story.source_program_ids.length === 0 ? (
        <p>None recorded.</p>
      ) : (
        <ul>
          {story.source_program_ids.map((sourceId) => (
            <li key={sourceId}>{sourceId}</li>
          ))}
        </ul>
      )}

      {story.export_status === "exported" && story.external_issue_url && (
        <p>
          <a href={story.external_issue_url} target="_blank" rel="noreferrer">
            View on {story.export_target === "github" ? "GitHub" : "Jira"} →
          </a>
        </p>
      )}

      <button type="button" onClick={onEdit}>
        Edit
      </button>
    </div>
  );
}
