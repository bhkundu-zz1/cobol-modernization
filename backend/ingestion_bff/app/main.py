"""Ingestion BFF — backs the Upload MFE, fanning out to source-mgmt-service
and job-pipeline-control-service (architecture.md sections 1a, 8, 9.1)."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.status import router as status_router
from .routes.upload import router as upload_router

app = FastAPI(title="Ingestion BFF", version="0.1.0")

# The browser (shell + upload-mfe) calls this BFF directly via fetch() —
# without CORS the request is blocked client-side, confirmed as a live bug
# the first time this ran through an actual browser rather than curl.
_FRONTEND_ORIGINS = [
    f"http://localhost:{os.environ.get('SHELL_PORT', '3000')}",
    f"http://localhost:{os.environ.get('UPLOAD_MFE_PORT', '3001')}",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_FRONTEND_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(status_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ingestion_bff"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("INGESTION_BFF_PORT", 8001)))
