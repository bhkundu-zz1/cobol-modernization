"""Epic/Story Service — real CRUD + export endpoints over `epic`/`story`
documents (architecture.md section 2.2), backing the Editor MFE via the
Editor/Admin BFF (:8003).

Epic/story *generation* (grouping migration_recommendation docs into epics
by call-graph/copybook clustering, drafting stories) is still deferred —
see docs/deferred_scope.md. This service is built and tested against
manually-seeded fixtures (scripts/seed_epics_stories.py), not
agent-generated documents.
"""

import os

from fastapi import FastAPI

from .routes.epics import router as epics_router
from .routes.export import router as export_router
from .routes.stories import router as stories_router

app = FastAPI(title="Epic/Story Service", version="0.1.0")
app.include_router(epics_router)
app.include_router(stories_router)
app.include_router(export_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "epic_story_service"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("EPIC_STORY_SERVICE_PORT", 8007)))
