import { useState } from "react";

import type { UploadedJob } from "./api/ingestionBffClient";
import { JobProgress } from "./components/JobProgress";
import { MainframeConnectForm } from "./components/MainframeConnectForm";
import { UploadForm } from "./components/UploadForm";

const PROJECT_ID = import.meta.env.VITE_DEFAULT_PROJECT_ID || "acme-2026";

type SourceMode = "manual" | "mainframe";

const MANUAL_COLOR = "var(--color-accent, #c15f3c)";
const MAINFRAME_COLOR = "var(--color-mainframe-accent, #3b6ea5)";

export default function UploadApp() {
  const [mode, setMode] = useState<SourceMode>("manual");
  const [activeJobs, setActiveJobs] = useState<UploadedJob[]>([]);

  function handleMainframeJobStarted(jobRunId: string) {
    setActiveJobs([{ filename: "mainframe pull", job_run_id: jobRunId }]);
  }

  const accentColor = mode === "manual" ? MANUAL_COLOR : MAINFRAME_COLOR;

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Upload / Ingestion</h2>
      <div role="tablist" style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem" }}>
        <button
          role="tab"
          aria-selected={mode === "manual"}
          onClick={() => setMode("manual")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            padding: "0.625rem 1rem",
            borderRadius: "10px",
            border: mode === "manual" ? `1.5px solid ${MANUAL_COLOR}` : "1.5px solid transparent",
            background: mode === "manual" ? "var(--color-accent-soft, #f3e3d8)" : "transparent",
            color: mode === "manual" ? MANUAL_COLOR : "var(--color-text-muted, #6b6558)",
            fontWeight: mode === "manual" ? 600 : 500,
            fontFamily: "inherit",
            cursor: "pointer",
          }}
        >
          <span aria-hidden="true" style={{ fontSize: "1rem" }}>
            📄
          </span>
          Manual Upload
        </button>
        <button
          role="tab"
          aria-selected={mode === "mainframe"}
          onClick={() => setMode("mainframe")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            padding: "0.625rem 1rem",
            borderRadius: "10px",
            border: mode === "mainframe" ? `1.5px solid ${MAINFRAME_COLOR}` : "1.5px solid transparent",
            background: mode === "mainframe" ? "var(--color-mainframe-accent-soft, rgba(59, 110, 165, 0.1))" : "transparent",
            color: mode === "mainframe" ? MAINFRAME_COLOR : "var(--color-text-muted, #6b6558)",
            fontWeight: mode === "mainframe" ? 600 : 500,
            fontFamily: "inherit",
            cursor: "pointer",
          }}
        >
          <span aria-hidden="true" style={{ fontSize: "1rem" }}>
            🖥️
          </span>
          Connect to mainframe repo
        </button>
      </div>

      {mode === "manual" ? (
        <UploadForm projectId={PROJECT_ID} onJobsStarted={setActiveJobs} accentColor={MANUAL_COLOR} />
      ) : (
        <MainframeConnectForm projectId={PROJECT_ID} onJobStarted={handleMainframeJobStarted} />
      )}

      {activeJobs.length > 0 && (
        <div style={{ marginTop: "1.5rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {activeJobs.map((job) => (
            <div
              key={job.job_run_id}
              style={{
                border: "1px solid var(--color-border, #e8e4dc)",
                borderRadius: "10px",
                padding: "0.875rem 1rem",
              }}
            >
              <p style={{ margin: "0 0 0.5rem", fontWeight: 600, color: accentColor }}>{job.filename}</p>
              <JobProgress projectId={PROJECT_ID} jobRunId={job.job_run_id} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
