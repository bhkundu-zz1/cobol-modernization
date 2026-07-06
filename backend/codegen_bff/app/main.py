"""Codegen BFF — backs the Code Generation MFE: lists approved-story
eligibility and proxies generate/status calls to
job-pipeline-control-service (architecture.md sections 8, 9.1)."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.codegen import router as codegen_router

app = FastAPI(title="Codegen BFF", version="0.1.0")

_FRONTEND_ORIGINS = [
    f"http://localhost:{os.environ.get('SHELL_PORT', '3000')}",
    f"http://localhost:{os.environ.get('CODEGEN_MFE_PORT', '3005')}",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_FRONTEND_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(codegen_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "codegen_bff"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("CODEGEN_BFF_PORT", 8008)))
