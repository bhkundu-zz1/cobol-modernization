import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@harness/design-system";

import {
  getEpicStoryJobStatus,
  JobStatusError,
  listReviewItems,
  triggerEpicStoryGeneration,
  type EpicStoryJobStatus,
  type ReviewItem,
} from "./api/reviewBffClient";
import { ReviewQueueTable } from "./components/ReviewQueueTable";

const PROJECT_ID = import.meta.env.VITE_DEFAULT_PROJECT_ID || "acme-2026";

// Same "not found yet" race as upload-mfe's JobProgress.tsx: the job_run
// document is created lazily by the first task's checkpoint write, so a
// poll landing before that write gets a real, transient 404.
const MAX_NOT_FOUND_RETRIES = 5;
const POLL_INTERVAL_MS = 2000;

export default function ReviewApp() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [generating, setGenerating] = useState(false);
  const [generationJobStatus, setGenerationJobStatus] = useState<EpicStoryJobStatus | null>(null);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout>>();

  const loadItems = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listReviewItems(PROJECT_ID);
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

  function handleDecisionRecorded(recommendationId: string, decision: "approved" | "rejected") {
    setItems((prev) =>
      prev.map((item) =>
        item.recommendation._id === recommendationId ? { ...item, human_review_status: decision } : item
      )
    );
  }

  async function handleGenerateEpicsStories() {
    setGenerating(true);
    setGenerationError(null);
    setGenerationJobStatus(null);
    try {
      const { job_run_id } = await triggerEpicStoryGeneration(PROJECT_ID);
      pollGenerationStatus(job_run_id, 0);
    } catch (err) {
      setGenerationError(err instanceof Error ? err.message : String(err));
      setGenerating(false);
    }
  }

  function pollGenerationStatus(jobRunId: string, notFoundCount: number) {
    getEpicStoryJobStatus(PROJECT_ID, jobRunId)
      .then((status) => {
        setGenerationJobStatus(status);
        if (status.status === "running") {
          pollTimerRef.current = setTimeout(() => pollGenerationStatus(jobRunId, notFoundCount), POLL_INTERVAL_MS);
        } else {
          setGenerating(false);
          if (status.status === "completed") {
            loadItems();
          }
        }
      })
      .catch((err) => {
        if (err instanceof JobStatusError && err.status === 404 && notFoundCount < MAX_NOT_FOUND_RETRIES) {
          pollTimerRef.current = setTimeout(
            () => pollGenerationStatus(jobRunId, notFoundCount + 1),
            POLL_INTERVAL_MS
          );
          return;
        }
        setGenerationError(err instanceof Error ? err.message : String(err));
        setGenerating(false);
      });
  }

  if (loading) {
    return <p>Loading review queue…</p>;
  }

  if (error) {
    return <p role="alert">{error}</p>;
  }

  return (
    <div>
      <h2>Review Queue</h2>

      <div style={{ marginBottom: "1rem" }}>
        <Button variant="secondary" onClick={handleGenerateEpicsStories} disabled={generating}>
          {generating ? "Generating…" : "Generate Epics & Stories"}
        </Button>
        {generationJobStatus && (
          <p>
            Job <code>{generationJobStatus.job_run_id}</code>: <strong>{generationJobStatus.status}</strong>
          </p>
        )}
        {generationError && <p role="alert">{generationError}</p>}
      </div>

      <ReviewQueueTable items={items} onDecisionRecorded={handleDecisionRecorded} />
    </div>
  );
}
