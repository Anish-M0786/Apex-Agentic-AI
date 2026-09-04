"""Safe document upload endpoint for the local workspace."""
from __future__ import annotations
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter(prefix='/api/documents', tags=['documents'])
UPLOAD_DIR = Path(__file__).resolve().parents[2] / 'data' / 'uploads'

@router.post('/upload')
async def upload_document(file: UploadFile = File(...)):
    if file.content_type != 'application/pdf' or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(415, 'Only PDF documents are supported.')
    contents = await file.read()
    if not contents or len(contents) > 25 * 1024 * 1024:
        raise HTTPException(413, 'Document must be between 1 byte and 25 MB.')
    document_id = uuid4().hex
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / f'{document_id}.pdf').write_bytes(contents)
    return {'document_id': document_id, 'filename': Path(file.filename).name}
