import { Button } from "@harness/design-system";

import type { EligibleStorySummary } from "../api/codegenBffClient";

export interface CodegenStoryListProps {
  items: EligibleStorySummary[];
  generatingStoryId: string | null;
  onGenerate: (storyId: string) => void;
}

const STATUS_LABEL: Record<string, string> = {
  not_generated: "Not generated",
  generating: "Generating…",
  generated: "Generated",
  failed: "Failed",
};

export function CodegenStoryList({ items, generatingStoryId, onGenerate }: CodegenStoryListProps) {
  if (items.length === 0) {
    return <p>No approved stories are available for code generation yet.</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Story</th>
          <th>Epic</th>
          <th>Recommended target</th>
          <th>Status</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {items.map(({ story, epic_title, recommended_targets }) => {
          const isGeneratingThisRow = generatingStoryId === story._id;
          return (
            <tr key={story._id}>
              <td>{story.title}</td>
              <td>{epic_title}</td>
              <td>{recommended_targets.join(", ")}</td>
              <td>
                {STATUS_LABEL[story.code_generation_status] ?? story.code_generation_status}
                {story.code_generation_status === "generated" && story.generated_code_commit_url && (
                  <>
                    {" "}
                    <a href={story.generated_code_commit_url} target="_blank" rel="noreferrer">
                      view commit
                    </a>
                  </>
                )}
                {story.code_generation_status === "failed" && story.code_generation_error && (
                  <p role="alert">{story.code_generation_error}</p>
                )}
              </td>
              <td>
                <Button
                  variant="secondary"
                  onClick={() => onGenerate(story._id)}
                  disabled={generatingStoryId !== null}
                >
                  {isGeneratingThisRow ? "Generating…" : "Generate"}
                </Button>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
