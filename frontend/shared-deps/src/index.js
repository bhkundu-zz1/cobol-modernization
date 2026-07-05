// Shared Module Federation singleton version pins (architecture.md section 8,
// "Shared dependencies governance"). Every MFE's vite.config.ts imports this
// manifest for its `shared` block so all remotes build against the exact
// same React/React-DOM/design-system versions — MF's classic failure mode
// is independently-upgraded shared deps causing silent runtime
// incompatibility; this is the single source of truth a version-drift CI
// check would compare against (that CI check itself is not implemented
// this pass, per docs/deferred_scope.md's Kubernetes/CI-adjacent items).

const sharedDeps = {
  react: { singleton: true, requiredVersion: "^18.3.0" },
  "react-dom": { singleton: true, requiredVersion: "^18.3.0" },
  "@harness/design-system": { singleton: true, requiredVersion: "^0.1.0" },
};

module.exports = { sharedDeps };

