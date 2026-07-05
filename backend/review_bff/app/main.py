"""Review BFF — backs the Review Queue MFE, fanning out recommendation +
job-progress data, Redis-TTL-cached (architecture.md sections 8, 9.1)."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.review_items import router as review_items_router

app = FastAPI(title="Review BFF", version="0.1.0")

# The browser (shell + review-mfe, served on their own ports per architecture.md
# section 8's micro-frontend topology) calls this BFF directly via fetch() —
# without CORS the request is blocked client-side with no server-side error
# at all, confirmed as a live bug the first time this ran through an actual
# browser rather than curl. Origins are the exact MFE ports, not a wildcard.
_FRONTEND_ORIGINS = [
    f"http://localhost:{os.environ.get('SHELL_PORT', '3000')}",
    f"http://localhost:{os.environ.get('REVIEW_MFE_PORT', '3002')}",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_FRONTEND_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(review_items_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "review_bff"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("REVIEW_BFF_PORT", 8002)))
