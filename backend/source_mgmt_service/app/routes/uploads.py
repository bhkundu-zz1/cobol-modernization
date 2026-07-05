"""POST/GET /uploads — manual file upload lifecycle (architecture.md section 2.2)."""

import hashlib
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from agents.common.mcp_client import get_mcp_client

router = APIRouter()


@router.post("/uploads")
async def create_upload(
    project_id: str = Form(...),
    files: list[UploadFile] = File(...),
    relative_paths: list[str] | None = Form(None),
) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="at least one file is required")

    mcp = get_mcp_client()
    upload_batch_id = str(uuid.uuid4())
    total_bytes = 0
    file_summaries = []

    for index, upload_file in enumerate(files):
        content = await upload_file.read()
        total_bytes += len(content)
        source_file_id = str(uuid.uuid4())
        relative_path = relative_paths[index] if relative_paths and index < len(relative_paths) else None
        file_summaries.append(
            {
                "source_file_id": source_file_id,
                "filename": upload_file.filename,
                "sha256": hashlib.sha256(content).hexdigest(),
                "source_text": content.decode("utf-8", errors="replace"),
                "relative_path": relative_path or None,
            }
        )

    write_result = mcp.couchdb_write(
        database="sources",
        doc={
            "type": "source_upload",
            "upload_batch_id": upload_batch_id,
            "uploaded_by": f"user:{project_id}",
            "source_origin": "manual_upload",
            "file_count": len(files),
            "total_bytes": total_bytes,
            "status": "received",
            "secret_scan_result": {"flagged_files": [], "scan_passed": False},
        },
        project_id=project_id,
        created_by=f"user:{project_id}",
        trace_id=upload_batch_id,
    )

    return {
        "upload_batch_id": upload_batch_id,
        "source_upload_id": write_result["id"],
        "files": file_summaries,
    }


@router.get("/uploads/{upload_batch_id}")
def get_upload(upload_batch_id: str, project_id: str) -> dict:
    mcp = get_mcp_client()
    result = mcp.couchdb_read(
        database="sources",
        mango_selector={"project_id": project_id, "type": "source_upload", "upload_batch_id": upload_batch_id},
    )
    docs = result.get("docs", [])
    if not docs:
        raise HTTPException(status_code=404, detail="upload batch not found")
    return docs[0]
