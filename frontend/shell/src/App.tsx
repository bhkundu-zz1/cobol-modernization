import { Suspense, useState } from "react";

import { RemoteErrorBoundary } from "./RemoteErrorBoundary";
import { AdminApp, EditorApp, ReviewApp, UploadApp } from "./remotes";

type Section = "upload" | "review" | "editor" | "admin";

const SECTIONS: { id: Section; label: string }[] = [
  { id: "upload", label: "Upload / Ingestion" },
  { id: "review", label: "Review Queue" },
  { id: "editor", label: "Epic/Story Editor" },
  { id: "admin", label: "Admin / Observability" },
];

const REMOTE_BY_SECTION: Record<Section, { name: string; Component: React.ComponentType }> = {
  upload: { name: "Upload/Ingestion", Component: UploadApp },
  review: { name: "Review Queue", Component: ReviewApp },
  editor: { name: "Epic/Story Editor", Component: EditorApp },
  admin: { name: "Admin/Observability", Component: AdminApp },
};

export default function App() {
  const [activeSection, setActiveSection] = useState<Section>("upload");
  const { name, Component } = REMOTE_BY_SECTION[activeSection];

  return (
    <div style={{ minHeight: "100%", display: "flex", flexDirection: "column" }}>
      <header
        style={{
          borderBottom: "1px solid var(--color-border)",
          padding: "1.25rem 2rem",
          backgroundColor: "var(--color-surface)",
        }}
      >
        <div
          style={{
            maxWidth: "72rem",
            margin: "0 auto",
            display: "flex",
            flexDirection: "column",
            gap: "1rem",
          }}
        >
          <h1
            style={{
              margin: 0,
              fontFamily: "var(--font-display)",
              fontSize: "1.5rem",
              fontWeight: 600,
              color: "var(--color-text)",
              letterSpacing: "-0.01em",
            }}
          >
            COBOL<span style={{ color: "var(--color-accent)" }}>/</span>JCL Migration Harness
          </h1>
          <nav style={{ display: "flex", gap: "0.375rem" }}>
            {SECTIONS.map((section) => {
              const isActive = activeSection === section.id;
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  style={{
                    background: isActive ? "var(--color-nav-active-bg)" : "transparent",
                    border: "none",
                    borderRadius: "var(--radius-md)",
                    cursor: "pointer",
                    fontFamily: "var(--font-body)",
                    fontWeight: isActive ? 600 : 500,
                    fontSize: "0.875rem",
                    color: isActive ? "var(--color-text)" : "var(--color-text-muted)",
                    padding: "0.5rem 0.875rem",
                    transition: "background-color 120ms ease, color 120ms ease",
                  }}
                >
                  {section.label}
                </button>
              );
            })}
          </nav>
        </div>
      </header>
      <main style={{ flex: 1, padding: "2rem" }}>
        <div
          style={{
            maxWidth: "72rem",
            margin: "0 auto",
            backgroundColor: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-lg)",
            boxShadow: "var(--shadow-sm)",
            padding: "2rem",
          }}
        >
          {/* Keyed by activeSection so switching tabs mounts a fresh
              RemoteErrorBoundary instance — without this, React reuses the
              same boundary instance across tabs and a caught error's
              hasError state would incorrectly persist onto the next remote
              shown at this mount point. */}
          <RemoteErrorBoundary key={activeSection} remoteName={name}>
            <Suspense fallback={<p style={{ color: "var(--color-text-muted)" }}>Loading {name}…</p>}>
              <Component />
            </Suspense>
          </RemoteErrorBoundary>
        </div>
      </main>
    </div>
  );
}
