"""Source Management Service — manual upload + mainframe-pull ingestion entrypoints
(architecture.md sections 1a, 2.2)."""

import os

from fastapi import FastAPI

from .routes.mainframe_pulls import router as mainframe_pulls_router
from .routes.source_files import router as source_files_router
from .routes.uploads import router as uploads_router

app = FastAPI(title="Source Management Service", version="0.1.0")
app.include_router(uploads_router)
app.include_router(mainframe_pulls_router)
app.include_router(source_files_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "source_mgmt_service"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("SOURCE_MGMT_SERVICE_PORT", 8004)))
