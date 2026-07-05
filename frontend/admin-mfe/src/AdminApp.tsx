// [STUB] Admin/Observability MFE — port 3004.
//
// Real scope (architecture.md section 7, section 8): kill switch button
// (POST /admin/kill), job_run history, model policy per project, links out
// to Langfuse UI, audit log viewer/export. Deferred this pass — see
// docs/deferred_scope.md.
//
// This placeholder component is what the shell's Module Federation remote
// import resolves to today.

export default function AdminApp() {
  return (
    <div style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h2>Admin / Observability</h2>
      <p>Coming soon — see docs/deferred_scope.md.</p>
    </div>
  );
}
