from pathlib import Path
from uuid import UUID, uuid4

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.config import INPUT_DIR, OUTPUT_DIR, TEMP_DIR, ensure_directories
from src.services.audio_service import extract_audio_to_mp3, extract_audio_to_wav
from src.services.transcription_service import transcribe_audio_to_txt


app = FastAPI()
templates = Jinja2Templates(directory="src/templates")


def cleanup_generated_files(file_id: str) -> None:
    """
    특정 변환 작업에서 생성된 원본/임시/결과 파일을 삭제합니다.
    file_id는 uuid4().hex로 생성된 값만 허용합니다.
    """
    try:
        UUID(file_id)
    except ValueError:
        return

    target_dirs = [INPUT_DIR, TEMP_DIR, OUTPUT_DIR]

    for target_dir in target_dirs:
        for file_path in target_dir.glob(f"{file_id}*"):
            if file_path.is_file():
                file_path.unlink()


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "transcript": None,
            "mp3_url": None,
            "txt_url": None,
            "cleanup_url": None,
        },
    )


@app.post("/transcribe")
async def transcribe(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form("ko"),
    model_name: str = Form("small"),
    action: str = Form("both"),
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

    transcript = None
    mp3_url = None
    txt_url = None

    print(f"선택된 작업: {action}")

    if action == "mp3_only":
        print("MP3만 생성합니다.")
        extract_audio_to_mp3(input_file, mp3_file)
        mp3_url = f"/download/{mp3_file.name}"

    elif action == "transcript_only":
        print("MP3는 만들지 않고, WAV 생성 후 받아쓰기만 진행합니다.")
        extract_audio_to_wav(input_file, wav_file)

        transcribe_audio_to_txt(
            wav_file,
            txt_file,
            model_name=model_name,
            language=language,
            include_timestamps=True,
        )

        transcript = txt_file.read_text(encoding="utf-8")
        txt_url = f"/download/{txt_file.name}"

    elif action == "both":
        print("MP3 생성과 받아쓰기를 모두 진행합니다.")
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
        mp3_url = f"/download/{mp3_file.name}"
        txt_url = f"/download/{txt_file.name}"

    else:
        print(f"알 수 없는 작업입니다. 기본값 both로 처리합니다: {action}")
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
        mp3_url = f"/download/{mp3_file.name}"
        txt_url = f"/download/{txt_file.name}"

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "transcript": transcript,
            "mp3_url": mp3_url,
            "txt_url": txt_url,
            "cleanup_url": f"/cleanup/{file_id}",
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


@app.get("/cleanup/{file_id}")
def cleanup_files(file_id: str):
    cleanup_generated_files(file_id)
    return RedirectResponse(url="/", status_code=303)