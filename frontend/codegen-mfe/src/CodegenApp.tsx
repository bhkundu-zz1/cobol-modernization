import { useCallback, useEffect, useRef, useState } from "react";

import {
  CodegenJobStatusError,
  getCodegenJobStatus,
  listEligibleStories,
  triggerCodeGeneration,
  type CodeGenTarget,
  type CodegenJobStatus,
  type EligibleStorySummary,
} from "./api/codegenBffClient";
import { CodegenStoryList } from "./components/CodegenStoryList";
import { LanguagePicker } from "./components/LanguagePicker";

const PROJECT_ID = import.meta.env.VITE_DEFAULT_PROJECT_ID || "acme-2026";

// Same "not found yet" race as review-mfe's ReviewApp.tsx and upload-mfe's
// JobProgress.tsx: the job_run document is created lazily by the first
// task's checkpoint write, so a poll landing before that write gets a
// real, transient 404.
const MAX_NOT_FOUND_RETRIES = 5;
const POLL_INTERVAL_MS = 2000;

export default function CodegenApp() {
  const [items, setItems] = useState<EligibleStorySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [targetLanguage, setTargetLanguage] = useState<CodeGenTarget>("python");
  const [generatingStoryId, setGeneratingStoryId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<CodegenJobStatus | null>(null);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout>>();

  const loadItems = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listEligibleStories(PROJECT_ID);
      setItems(result.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadItems();
    return () => clearTimeout(pollTimerRef.current);
  }, [loadItems]);

  async function handleGenerate(storyId: string) {
    setGeneratingStoryId(storyId);
    setGenerationError(null);
    setJobStatus(null);
    try {
      const { job_run_id } = await triggerCodeGeneration(PROJECT_ID, storyId, targetLanguage);
      pollGenerationStatus(job_run_id, 0);
    } catch (err) {
      setGenerationError(err instanceof Error ? err.message : String(err));
      setGeneratingStoryId(null);
    }
  }

  function pollGenerationStatus(jobRunId: string, notFoundCount: number) {
    getCodegenJobStatus(PROJECT_ID, jobRunId)
      .then((status) => {
        setJobStatus(status);
        if (status.status === "running") {
          pollTimerRef.current = setTimeout(() => pollGenerationStatus(jobRunId, notFoundCount), POLL_INTERVAL_MS);
        } else {
          setGeneratingStoryId(null);
          // Story.code_generation_status/generated_code_commit_url stay
          // the single source of truth for display — reload from the BFF
          // rather than trusting the job payload for that.
          loadItems();
        }
      })
      .catch((err) => {
        if (err instanceof CodegenJobStatusError && err.status === 404 && notFoundCount < MAX_NOT_FOUND_RETRIES) {
          pollTimerRef.current = setTimeout(
            () => pollGenerationStatus(jobRunId, notFoundCount + 1),
            POLL_INTERVAL_MS
          );
          return;
        }
        setGenerationError(err instanceof Error ? err.message : String(err));
        setGeneratingStoryId(null);
      });
  }

  if (loading) {
    return <p>Loading approved stories…</p>;
  }

  if (error) {
    return <p role="alert">{error}</p>;
  }

  return (
    <div>
      <h2>Code Generation</h2>
      <p>Approved stories only.</p>

      <div style={{ marginBottom: "1rem" }}>
        <LanguagePicker value={targetLanguage} onChange={setTargetLanguage} disabled={generatingStoryId !== null} />
        {jobStatus && (
          <p>
            Job <code>{jobStatus.job_run_id}</code>: <strong>{jobStatus.status}</strong>
          </p>
        )}
        {generationError && <p role="alert">{generationError}</p>}
      </div>

      <CodegenStoryList items={items} generatingStoryId={generatingStoryId} onGenerate={handleGenerate} />
    </div>
  );
}
