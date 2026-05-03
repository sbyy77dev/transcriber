from pathlib import Path
from threading import Lock, Thread
from uuid import UUID, uuid4

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.config import INPUT_DIR, OUTPUT_DIR, TEMP_DIR, ensure_directories
from src.services.audio_service import extract_audio_to_mp3, extract_audio_to_wav
from src.services.merge_service import convert_file_to_mp3, merge_mp3_files
from src.services.transcription_service import transcribe_audio_to_txt


app = FastAPI()
app.mount("/static", StaticFiles(directory="src/static"), name="static")

templates = Jinja2Templates(directory="src/templates")

jobs: dict[str, dict] = {}
jobs_lock = Lock()

merge_jobs: dict[str, dict] = {}
merge_jobs_lock = Lock()


def is_valid_uuid_hex(value: str) -> bool:
    """
    uuid4().hex 형식의 작업 ID인지 확인합니다.
    """
    try:
        UUID(value)
        return True
    except ValueError:
        return False


def is_faster_model(model_name: str) -> bool:
    """
    faster-whisper 모델 선택 여부를 확인합니다.
    """
    return model_name.startswith("faster-")


def update_job(job_id: str, **kwargs) -> None:
    """
    단일 파일 변환/받아쓰기 작업 상태를 갱신합니다.
    """
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id].update(kwargs)


def update_merge_job(job_id: str, **kwargs) -> None:
    """
    여러 파일 MP3 병합 작업 상태를 갱신합니다.
    """
    with merge_jobs_lock:
        if job_id in merge_jobs:
            merge_jobs[job_id].update(kwargs)


def append_transcript(job_id: str, line: str) -> None:
    """
    faster-whisper에서 segment가 생성될 때마다 받아쓰기 결과를 누적합니다.
    """
    print(f"받아쓰기 segment 추가: {line}")

    with jobs_lock:
        if job_id not in jobs:
            return

        current_text = jobs[job_id].get("transcript") or ""

        if current_text:
            current_text += "\n\n"

        current_text += line
        jobs[job_id]["transcript"] = current_text

        current_count = jobs[job_id].get("segment_count", 0)
        jobs[job_id]["segment_count"] = current_count + 1

        current_progress = jobs[job_id].get("progress", 55)
        if current_progress < 90:
            jobs[job_id]["progress"] = current_progress + 2


def cleanup_generated_files(file_id: str) -> None:
    """
    특정 변환 작업에서 생성된 원본/임시/결과 파일을 삭제합니다.
    """
    if not is_valid_uuid_hex(file_id):
        return

    target_dirs = [INPUT_DIR, TEMP_DIR, OUTPUT_DIR]

    for target_dir in target_dirs:
        for file_path in target_dir.glob(f"{file_id}*"):
            if file_path.is_file():
                file_path.unlink()

    with jobs_lock:
        jobs.pop(file_id, None)

    with merge_jobs_lock:
        merge_jobs.pop(file_id, None)


def process_job(
    job_id: str,
    input_file: Path,
    wav_file: Path,
    mp3_file: Path,
    txt_file: Path,
    action: str,
    language: str,
    model_name: str,
) -> None:
    """
    별도 스레드에서 단일 파일 변환/받아쓰기 작업을 수행합니다.
    """
    try:
        update_job(
            job_id,
            status="running",
            progress=5,
            step="파일 업로드 완료",
            message="작업을 시작합니다.",
        )

        if action == "mp3_only":
            update_job(
                job_id,
                progress=40,
                step="MP3 생성 중",
                message="사용자 다운로드용 MP3 파일을 생성하고 있습니다.",
            )

            extract_audio_to_mp3(input_file, mp3_file)

            update_job(
                job_id,
                status="complete",
                progress=100,
                step="완료",
                message="MP3 생성이 완료되었습니다.",
                mp3_url=f"/download/{mp3_file.name}",
            )
            return

        update_job(
            job_id,
            progress=20,
            step="WAV 생성 중",
            message="받아쓰기용 WAV 파일을 생성하고 있습니다.",
        )

        extract_audio_to_wav(input_file, wav_file)

        if action == "both":
            update_job(
                job_id,
                progress=35,
                step="MP3 생성 중",
                message="사용자 다운로드용 MP3 파일을 생성하고 있습니다.",
            )

            extract_audio_to_mp3(input_file, mp3_file)

            update_job(
                job_id,
                progress=45,
                mp3_url=f"/download/{mp3_file.name}",
            )

        if is_faster_model(model_name):
            update_job(
                job_id,
                progress=55,
                step="받아쓰기 중",
                message="faster-whisper로 받아쓰기 결과를 한 줄씩 표시하고 있습니다.",
            )

            transcribe_audio_to_txt(
                wav_file,
                txt_file,
                model_name=model_name,
                language=language,
                include_timestamps=True,
                on_segment=lambda line: append_transcript(job_id, line),
            )

            final_transcript = txt_file.read_text(encoding="utf-8")

            update_job(
                job_id,
                status="complete",
                progress=100,
                step="완료",
                message="받아쓰기가 완료되었습니다.",
                transcript=final_transcript,
                txt_url=f"/download/{txt_file.name}",
            )
            return

        update_job(
            job_id,
            progress=60,
            step="받아쓰기 중",
            message="기존 Whisper로 받아쓰기 중입니다. 완료 후 전체 결과가 표시됩니다.",
        )

        transcribe_audio_to_txt(
            wav_file,
            txt_file,
            model_name=model_name,
            language=language,
            include_timestamps=True,
        )

        transcript = txt_file.read_text(encoding="utf-8")

        update_job(
            job_id,
            status="complete",
            progress=100,
            step="완료",
            message="받아쓰기가 완료되었습니다.",
            transcript=transcript,
            txt_url=f"/download/{txt_file.name}",
        )

    except Exception as error:
        update_job(
            job_id,
            status="failed",
            progress=100,
            step="오류 발생",
            message=str(error),
        )


def process_merge_job(
    job_id: str,
    input_files: list[Path],
    output_file: Path,
) -> None:
    """
    별도 스레드에서 여러 파일을 순서대로 MP3로 변환한 뒤 하나로 병합합니다.
    """
    try:
        total_files = len(input_files)

        if total_files == 0:
            raise ValueError("병합할 파일이 없습니다.")

        update_merge_job(
            job_id,
            status="running",
            progress=5,
            step="파일 업로드 완료",
            message="MP3 병합 작업을 시작합니다.",
        )

        converted_mp3_files: list[Path] = []

        for index, input_file in enumerate(input_files, start=1):
            progress = 10 + int((index - 1) / total_files * 65)

            update_merge_job(
                job_id,
                progress=progress,
                step=f"{index}/{total_files}번 파일 변환 중",
                message=f"{input_file.name} 파일에서 MP3를 추출하고 있습니다.",
            )

            converted_mp3 = TEMP_DIR / f"{job_id}_{index:03d}.mp3"
            convert_file_to_mp3(input_file, converted_mp3)
            converted_mp3_files.append(converted_mp3)

        update_merge_job(
            job_id,
            progress=80,
            step="MP3 병합 중",
            message="변환된 MP3 파일들을 순서대로 하나로 합치고 있습니다.",
        )

        list_file = TEMP_DIR / f"{job_id}_merge_list.txt"

        merge_mp3_files(
            mp3_files=converted_mp3_files,
            output_file=output_file,
            list_file=list_file,
        )

        update_merge_job(
            job_id,
            status="complete",
            progress=100,
            step="완료",
            message="MP3 병합이 완료되었습니다.",
            merged_mp3_url=f"/download/{output_file.name}",
        )

    except Exception as error:
        update_merge_job(
            job_id,
            status="failed",
            progress=100,
            step="오류 발생",
            message=str(error),
        )


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )


@app.get("/merge")
def merge_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="merge.html",
        context={},
    )


@app.post("/jobs")
async def create_job(
    file: UploadFile = File(...),
    language: str = Form("ko"),
    model_name: str = Form("small"),
    action: str = Form("both"),
):
    ensure_directories()

    original_suffix = Path(file.filename).suffix
    job_id = uuid4().hex

    input_file = INPUT_DIR / f"{job_id}{original_suffix}"
    wav_file = TEMP_DIR / f"{job_id}.wav"
    mp3_file = OUTPUT_DIR / f"{job_id}.mp3"
    txt_file = OUTPUT_DIR / f"{job_id}_transcript.txt"

    content = await file.read()
    input_file.write_bytes(content)

    with jobs_lock:
        jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress": 0,
            "step": "대기 중",
            "message": "작업을 준비하고 있습니다.",
            "transcript": "",
            "segment_count": 0,
            "mp3_url": None,
            "txt_url": None,
            "cleanup_url": f"/cleanup/{job_id}",
        }

    worker = Thread(
        target=process_job,
        args=(
            job_id,
            input_file,
            wav_file,
            mp3_file,
            txt_file,
            action,
            language,
            model_name,
        ),
        daemon=True,
    )
    worker.start()

    return JSONResponse(
        {
            "job_id": job_id,
        }
    )


@app.post("/merge/jobs")
async def create_merge_job(
    files: list[UploadFile] = File(...),
):
    ensure_directories()

    if not files:
        return JSONResponse(
            {
                "error": "업로드된 파일이 없습니다.",
            },
            status_code=400,
        )

    job_id = uuid4().hex
    input_files: list[Path] = []

    for index, file in enumerate(files, start=1):
        original_suffix = Path(file.filename).suffix
        input_file = INPUT_DIR / f"{job_id}_{index:03d}{original_suffix}"

        content = await file.read()
        input_file.write_bytes(content)

        input_files.append(input_file)

    output_file = OUTPUT_DIR / f"{job_id}_merged.mp3"

    with merge_jobs_lock:
        merge_jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress": 0,
            "step": "대기 중",
            "message": "MP3 병합 작업을 준비하고 있습니다.",
            "merged_mp3_url": None,
            "cleanup_url": f"/cleanup/{job_id}",
        }

    worker = Thread(
        target=process_merge_job,
        args=(
            job_id,
            input_files,
            output_file,
        ),
        daemon=True,
    )
    worker.start()

    return JSONResponse(
        {
            "job_id": job_id,
        }
    )


@app.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)

        if job is not None:
            job = job.copy()

    if job is None:
        return JSONResponse(
            {
                "status": "not_found",
                "progress": 100,
                "step": "작업 없음",
                "message": "작업 정보를 찾을 수 없습니다.",
                "transcript": "",
                "segment_count": 0,
                "mp3_url": None,
                "txt_url": None,
                "cleanup_url": None,
            },
            status_code=404,
        )

    return JSONResponse(job)


@app.get("/merge/jobs/{job_id}")
def get_merge_job_status(job_id: str):
    with merge_jobs_lock:
        job = merge_jobs.get(job_id)

        if job is not None:
            job = job.copy()

    if job is None:
        return JSONResponse(
            {
                "status": "not_found",
                "progress": 100,
                "step": "작업 없음",
                "message": "병합 작업 정보를 찾을 수 없습니다.",
                "merged_mp3_url": None,
                "cleanup_url": None,
            },
            status_code=404,
        )

    return JSONResponse(job)


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