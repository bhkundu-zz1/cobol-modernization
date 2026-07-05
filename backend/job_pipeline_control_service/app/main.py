"""Job/Pipeline Control Service — job_run lifecycle + kill-switch admin endpoint
(architecture.md sections 3.3, 7)."""

import os

from fastapi import FastAPI

from .routes.admin import router as admin_router
from .routes.jobs import router as jobs_router

app = FastAPI(title="Job/Pipeline Control Service", version="0.1.0")
app.include_router(jobs_router)
app.include_router(admin_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "job_pipeline_control_service"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("JOB_PIPELINE_CONTROL_SERVICE_PORT", 8005)))
