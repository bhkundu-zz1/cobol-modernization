import { useState } from "react";

import { listMainframeElements, type MainframeElement, pullMainframeElement } from "../api/ingestionBffClient";

export interface MainframeConnectFormProps {
  projectId: string;
  onJobStarted: (jobRunId: string) => void;
}

const TOOLS = ["endevor", "panvalet", "changeman", "mock"] as const;
type Tool = (typeof TOOLS)[number];

export function MainframeConnectForm({ projectId, onJobStarted }: MainframeConnectFormProps) {
  const [tool, setTool] = useState<Tool>("mock");
  const [system, setSystem] = useState("PAYSYS");
  const [subsystem, setSubsystem] = useState("PAYROLL");
  const [elements, setElements] = useState<MainframeElement[]>([]);
  const [selectedElementId, setSelectedElementId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [browsing, setBrowsing] = useState(false);
  const [pulling, setPulling] = useState(false);

  async function handleBrowse() {
    setBrowsing(true);
    setError(null);
    setElements([]);
    try {
      const result = await listMainframeElements({ projectId, tool, system, subsystem });
      setElements(result.elements);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBrowsing(false);
    }
  }

  async function handlePull() {
    if (!selectedElementId) {
      setError("select an element first");
      return;
    }
    setPulling(true);
    setError(null);
    try {
      const result = await pullMainframeElement({ projectId, tool, system, subsystem, elementId: selectedElementId });
      onJobStarted(result.job_run_id);
    } catch (err) {
      // Real (non-mock) tools raise a clean 501 "not yet implemented" error
      // from the backend (see agents/mainframe_ingestion/adapter.py) — this
      // surfaces it verbatim rather than pretending the pull succeeded.
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setPulling(false);
    }
  }

  return (
    <div>
      <h3>Connect to mainframe repo</h3>
      <label htmlFor="tool-select">Tool</label>
      <select id="tool-select" value={tool} onChange={(e) => setTool(e.target.value as Tool)}>
        {TOOLS.map((t) => (
          <option key={t} value={t}>
            {t}
          </option>
        ))}
      </select>

      <label htmlFor="system-input">System</label>
      <input id="system-input" value={system} onChange={(e) => setSystem(e.target.value)} />

      <label htmlFor="subsystem-input">Subsystem</label>
      <input id="subsystem-input" value={subsystem} onChange={(e) => setSubsystem(e.target.value)} />

      <button type="button" onClick={handleBrowse} disabled={browsing}>
        {browsing ? "Browsing…" : "List elements"}
      </button>

      {elements.length > 0 && (
        <ul>
          {elements.map((el) => (
            <li key={el.element_id}>
              <label>
                <input
                  type="radio"
                  name="mainframe-element"
                  value={el.element_id}
                  checked={selectedElementId === el.element_id}
                  onChange={() => setSelectedElementId(el.element_id)}
                />
                {el.element_id} ({el.element_type}
                {el.version ? `, v${el.version}` : ""})
              </label>
            </li>
          ))}
        </ul>
      )}

      <button type="button" onClick={handlePull} disabled={pulling || !selectedElementId}>
        {pulling ? "Pulling…" : "Pull selected"}
      </button>

      {error && <p role="alert">{error}</p>}
    </div>
  );
}
