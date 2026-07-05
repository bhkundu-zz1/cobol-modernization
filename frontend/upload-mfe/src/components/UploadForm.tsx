import { useState } from "react";

import { uploadFiles, type UploadedJob } from "../api/ingestionBffClient";

export interface UploadFormProps {
  projectId: string;
  onJobsStarted: (jobs: UploadedJob[]) => void;
  accentColor?: string;
}

// webkitRelativePath is non-standard but universally supported (Chrome,
// Edge, Firefox) on <input webkitdirectory>-selected files. Not in the
// standard File type, so it's read defensively here.
function relativePathOf(file: File): string | undefined {
  return (file as unknown as { webkitRelativePath?: string }).webkitRelativePath || undefined;
}

type PickMode = "file" | "folder" | null;

export function UploadForm({ projectId, onJobsStarted, accentColor = "#c15f3c" }: UploadFormProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [pickMode, setPickMode] = useState<PickMode>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (files.length === 0) {
      setError("choose a file first");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const result = await uploadFiles(
        projectId,
        files.map((file) => ({ file, relativePath: relativePathOf(file) }))
      );
      onJobsStarted(result.jobs);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  function handleFileListChange(fileList: FileList | null, mode: PickMode) {
    setFiles(fileList ? Array.from(fileList) : []);
    setPickMode(fileList && fileList.length > 0 ? mode : null);
  }

  const cardBaseStyle = (isActive: boolean): React.CSSProperties => ({
    position: "relative",
    flex: 1,
    border: isActive ? `1.5px solid ${accentColor}` : "1.5px solid var(--color-border, #e8e4dc)",
    borderRadius: "12px",
    padding: "1.25rem",
    backgroundColor: isActive ? "var(--color-accent-soft, #f3e3d8)" : "var(--color-surface, #fff)",
    display: "flex",
    flexDirection: "column",
    gap: "0.5rem",
    transition: "border-color 120ms ease, background-color 120ms ease",
  });

  return (
    <form onSubmit={handleSubmit}>
      <p style={{ color: "var(--color-text-muted, #6b6558)", marginTop: 0 }}>
        Choose <strong>one</strong> of the two options below, then click Upload.
      </p>

      <div style={{ display: "flex", gap: "1rem", marginBottom: "1.25rem", alignItems: "stretch" }}>
        <label htmlFor="cobol-file-input" style={{ ...cardBaseStyle(pickMode === "file"), cursor: "pointer" }}>
          <span style={{ fontSize: "1.5rem" }} aria-hidden="true">
            📄
          </span>
          <span style={{ fontWeight: 600, color: "var(--color-text, #2b2823)" }}>Choose a single file</span>
          <span style={{ fontSize: "0.8125rem", color: "var(--color-text-muted, #6b6558)" }}>
            Pick one COBOL, JCL, or copybook file from your computer.
          </span>
          <input
            id="cobol-file-input"
            type="file"
            onChange={(e) => handleFileListChange(e.target.files, "file")}
            data-testid="file-input"
            style={{ marginTop: "0.5rem" }}
          />
        </label>

        <label htmlFor="cobol-folder-input" style={{ ...cardBaseStyle(pickMode === "folder"), cursor: "pointer" }}>
          <span style={{ fontSize: "1.5rem" }} aria-hidden="true">
            🗂️
          </span>
          <span style={{ fontWeight: 600, color: "var(--color-text, #2b2823)" }}>Choose a whole folder</span>
          <span style={{ fontSize: "0.8125rem", color: "var(--color-text-muted, #6b6558)" }}>
            Every COBOL/JCL/copybook file inside is uploaded and analyzed together. Each file's path within the
            folder is kept for reference (browsers can't expose a true local OS path).
          </span>
          <span
            style={{
              marginTop: "0.5rem",
              alignSelf: "flex-start",
              padding: "0.375rem 0.75rem",
              borderRadius: "6px",
              border: "1px solid var(--color-border-strong, #d9d3c7)",
              backgroundColor: "var(--color-surface, #fff)",
              fontSize: "0.8125rem",
              fontWeight: 500,
              color: "var(--color-text, #2b2823)",
            }}
          >
            Choose Folder
          </span>
          <input
            id="cobol-folder-input"
            type="file"
            multiple
            // @ts-expect-error -- webkitdirectory is non-standard but supported by all major browsers
            webkitdirectory=""
            onChange={(e) => handleFileListChange(e.target.files, "folder")}
            data-testid="folder-input"
            style={{
              position: "absolute",
              width: "1px",
              height: "1px",
              padding: 0,
              margin: "-1px",
              overflow: "hidden",
              clip: "rect(0, 0, 0, 0)",
              whiteSpace: "nowrap",
              border: 0,
            }}
          />
        </label>
      </div>

      {files.length > 0 && (
        <div
          style={{
            border: "1px solid var(--color-border, #e8e4dc)",
            borderRadius: "10px",
            padding: "0.75rem 1rem",
            marginBottom: "1.25rem",
          }}
        >
          <p style={{ margin: "0 0 0.5rem", fontWeight: 600, fontSize: "0.875rem", color: accentColor }}>
            {files.length === 1 ? "1 file selected" : `${files.length} files selected`}
          </p>
          <ul style={{ margin: 0, paddingLeft: "1.25rem" }}>
            {files.map((file) => (
              <li key={relativePathOf(file) || file.name} style={{ fontSize: "0.8125rem" }}>
                <code>{relativePathOf(file) || file.name}</code>
              </li>
            ))}
          </ul>
        </div>
      )}

      <button
        type="submit"
        disabled={submitting}
        style={{
          backgroundColor: accentColor,
          color: "#fff",
          border: "none",
          borderRadius: "8px",
          padding: "0.625rem 1.25rem",
          fontFamily: "inherit",
          fontWeight: 600,
          fontSize: "0.875rem",
          cursor: submitting ? "default" : "pointer",
          opacity: submitting ? 0.7 : 1,
        }}
      >
        {submitting ? "Uploading…" : files.length > 1 ? `Upload ${files.length} files` : "Upload"}
      </button>
      {error && (
        <p role="alert" style={{ color: "#b3261e" }}>
          {error}
        </p>
      )}
    </form>
  );
}
