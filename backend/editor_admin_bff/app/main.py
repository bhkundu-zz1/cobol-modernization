"""Editor/Admin BFF — backs the Epic/Story Editor MFE (:3003), proxying
epic/story CRUD and export to epic_story_service (architecture.md sections
8, 9.1).

Admin/Observability MFE (:3004) fan-out (job-pipeline-control, audit-log
export) is still deferred — see docs/deferred_scope.md.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.editor_items import router as editor_items_router

app = FastAPI(title="Editor/Admin BFF", version="0.1.0")

# Same rationale as review_bff: the browser calls this BFF directly via
# fetch(), so it needs CORS scoped to the exact MFE ports, never a wildcard.
_FRONTEND_ORIGINS = [
    f"http://localhost:{os.environ.get('SHELL_PORT', '3000')}",
    f"http://localhost:{os.environ.get('EDITOR_MFE_PORT', '3003')}",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_FRONTEND_ORIGINS,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)

app.include_router(editor_items_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "editor_admin_bff"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("EDITOR_ADMIN_BFF_PORT", 8003)))
