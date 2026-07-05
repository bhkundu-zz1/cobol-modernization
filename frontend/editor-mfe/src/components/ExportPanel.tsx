import { useState } from "react";

import { Badge, Button } from "@harness/design-system";

import { exportItems, type ExportResult } from "../api/editorBffClient";
import { GitHubConnectForm } from "./GitHubConnectForm";
import { JiraConnectForm } from "./JiraConnectForm";

const PROJECT_ID = import.meta.env.VITE_DEFAULT_PROJECT_ID || "acme-2026";

export interface ExportPanelProps {
  selectedEpicIds: string[];
  selectedStoryIds: string[];
  onExported: (result: ExportResult) => void;
}

type Destination = "github" | "jira";

export function ExportPanel({ selectedEpicIds, selectedStoryIds, onExported }: ExportPanelProps) {
  const [destination, setDestination] = useState<Destination>("github");
  const [connectionConfig, setConnectionConfig] = useState<Record<string, string>>({});
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ExportResult | null>(null);

  if (selectedStoryIds.length === 0) {
    return null;
  }

  async function handleExport() {
    setExporting(true);
    setError(null);
    setResult(null);
    try {
      const response = await exportItems({
        project_id: PROJECT_ID,
        tool: destination,
        connection_config: connectionConfig,
        epic_ids: selectedEpicIds,
        story_ids: selectedStoryIds,
      });
      setResult(response);
      onExported(response);
    } catch (err) {
      // Jira surfaces a real 501 "not yet implemented" error verbatim here —
      // the same failure path the mainframe connector already proves out
      // for real (non-mock) tools, rather than silently faking success.
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setExporting(false);
    }
  }

  return (
    <div>
      <h3>{selectedStoryIds.length} item(s) selected — Export</h3>

      <fieldset>
        <legend>Destination</legend>
        <label>
          <input
            type="radio"
            name="destination"
            value="github"
            checked={destination === "github"}
            onChange={() => {
              setDestination("github");
              setConnectionConfig({});
            }}
          />
          GitHub
        </label>
        <label>
          <input
            type="radio"
            name="destination"
            value="jira"
            checked={destination === "jira"}
            onChange={() => {
              setDestination("jira");
              setConnectionConfig({});
            }}
          />
          Jira
        </label>
      </fieldset>

      {destination === "github" ? (
        <GitHubConnectForm onChange={setConnectionConfig} />
      ) : (
        <JiraConnectForm onChange={setConnectionConfig} />
      )}

      <Button variant="primary" onClick={handleExport} disabled={exporting}>
        {exporting ? "Exporting…" : `Export ${selectedStoryIds.length} item(s)`}
      </Button>

      {error && <p role="alert">{error}</p>}

      {result && (
        <div>
          {result.epic_milestones.length > 0 && (
            <p>{result.epic_milestones.length} milestone(s) created/reused.</p>
          )}

          <h4>Exported</h4>
          {result.exported.length === 0 ? (
            <p>None.</p>
          ) : (
            <ul>
              {result.exported.map((item) => (
                <li key={item.story_id}>
                  <Badge tone="success">exported</Badge>{" "}
                  <a href={item.external_issue_url} target="_blank" rel="noreferrer">
                    {item.external_issue_key}
                  </a>
                </li>
              ))}
            </ul>
          )}

          <h4>Failed</h4>
          {result.failed.length === 0 ? (
            <p>None.</p>
          ) : (
            <ul>
              {result.failed.map((item) => (
                <li key={item.story_id}>
                  <Badge tone="danger">failed</Badge> {item.story_id}: {item.reason}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
