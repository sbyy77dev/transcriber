from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates

from src.config import INPUT_DIR, OUTPUT_DIR, TEMP_DIR, ensure_directories
from src.services.audio_service import extract_audio_to_mp3, extract_audio_to_wav
from src.services.transcription_service import transcribe_audio_to_txt


app = FastAPI()
templates = Jinja2Templates(directory="src/templates")


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "transcript": None,
        },
    )


@app.post("/transcribe")
async def transcribe(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form("ko"),
    model_name: str = Form("small"),
):
    ensure_directories()

    original_suffix = Path(file.filename).suffix
    file_id = uuid4().hex

    input_file = INPUT_DIR / f"{file_id}{original_suffix}"
    wav_file = TEMP_DIR / f"{file_id}.wav"
    mp3_file = OUTPUT_DIR / f"{file_id}.mp3"
    txt_file = OUTPUT_DIR / f"{file_id}_transcript.txt"

    content = await file.read()
    input_file.write_bytes(content)

    extract_audio_to_wav(input_file, wav_file)
    extract_audio_to_mp3(input_file, mp3_file)

    transcribe_audio_to_txt(
        wav_file,
        txt_file,
        model_name=model_name,
        language=language,
        include_timestamps=True,
    )

    transcript = txt_file.read_text(encoding="utf-8")
    
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "transcript": transcript,
            "mp3_url": f"/download/{mp3_file.name}",
            "txt_url": f"/download/{txt_file.name}",
        },
    )


@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = OUTPUT_DIR / filename

    if not file_path.exists():
        return {"error": "파일을 찾을 수 없습니다."}

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream",
    )