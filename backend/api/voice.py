import os
import tempfile
import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import edge_tts
from faster_whisper import WhisperModel
from backend.utils.text_normalizer import normalize_for_tts

router = APIRouter(prefix="/api/voice", tags=["Voice"])

whisper_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        try:
            whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load Whisper model: {e}")
    return whisper_model

class SynthesizeRequest(BaseModel):
    text: str
    voice: str = "en-IN-NeerjaNeural"

@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    try:
        model = get_whisper_model()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        segments, info = model.transcribe(tmp_path, beam_size=5)
        text = " ".join([segment.text for segment in segments])
        
        os.remove(tmp_path)
        
        return {"transcript": text.strip()}
    except Exception as e:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/synthesize")
async def synthesize(req: SynthesizeRequest):
    normalized_text = normalize_for_tts(req.text)
    if not normalized_text.strip():
        raise HTTPException(status_code=400, detail="Text is empty")
    
    try:
        communicate = edge_tts.Communicate(normalized_text, req.voice, rate='+10%')
        
        async def audio_stream():
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
                    
        return StreamingResponse(audio_stream(), media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
