from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
OUTPUT_DIR=(Path(__file__).resolve().parents[2]/'data'/'outputs').resolve()
router=APIRouter()
@router.get('/api/files/{filename}')
def download_file(filename:str):
    path=(OUTPUT_DIR/Path(filename).name).resolve()
    if Path(filename).name != filename or path.parent != OUTPUT_DIR or not path.is_file(): raise HTTPException(status_code=404,detail='File not found.')
    return FileResponse(path)
