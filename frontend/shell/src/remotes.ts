import { lazy } from "react";

// Each remote is a separately fetched bundle (dynamic import), so a failure
// loading one doesn't block the others from loading — combined with each
// remote's RemoteErrorBoundary wrapper in App.tsx, this is how MF's
// failure-isolation guarantee (architecture.md section 8) is implemented.

// @ts-expect-error - module federation remote, resolved at build/dev-server time
export const UploadApp = lazy(() => import("upload_mfe/UploadApp"));
// @ts-expect-error - module federation remote, resolved at build/dev-server time
export const ReviewApp = lazy(() => import("review_mfe/ReviewApp"));
// @ts-expect-error - module federation remote, resolved at build/dev-server time
export const EditorApp = lazy(() => import("editor_mfe/EditorApp"));
// @ts-expect-error - module federation remote, resolved at build/dev-server time
export const AdminApp = lazy(() => import("admin_mfe/AdminApp"));
// @ts-expect-error - module federation remote, resolved at build/dev-server time
export const CodegenApp = lazy(() => import("codegen_mfe/CodegenApp"));
