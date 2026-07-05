"""Recommendation Service — thin read/decision API over migration_recommendation
documents, backing the Review BFF (architecture.md section 2.2)."""

import os

from fastapi import FastAPI

from .routes.recommendations import router as recommendations_router

app = FastAPI(title="Recommendation Service", version="0.1.0")
app.include_router(recommendations_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "recommendation_service"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("RECOMMENDATION_SERVICE_PORT", 8006)))
