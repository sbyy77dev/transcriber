from pathlib import Path
from typing import Callable

import whisper
from faster_whisper import WhisperModel


def format_timestamp(seconds: float) -> str:
    """
    초 단위 시간을 HH:MM:SS 형식으로 변환합니다.
    """
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_transcript_line(
    text: str,
    start: float,
    end: float,
    include_timestamps: bool,
) -> str:
    """
    받아쓰기 한 줄을 시간 표시 옵션에 맞게 포맷합니다.
    """
    cleaned_text = text.strip()

    if include_timestamps:
        start_time = format_timestamp(start)
        end_time = format_timestamp(end)
        return f"[{start_time} → {end_time}] {cleaned_text}"

    return cleaned_text


def normalize_model_name(model_name: str) -> tuple[str, bool]:
    """
    모델 이름에서 faster-whisper 사용 여부와 실제 모델명을 분리합니다.

    예:
        base -> ("base", False)
        small -> ("small", False)
        faster-base -> ("base", True)
        faster-small -> ("small", True)
    """
    if model_name.startswith("faster-"):
        return model_name.replace("faster-", "", 1), True

    return model_name, False


def transcribe_audio_with_whisper(
    audio_file: Path,
    output_txt: Path,
    model_name: str = "small",
    language: str = "ko",
    include_timestamps: bool = False,
) -> Path:
    """
    기존 openai-whisper로 WAV 음성 파일을 받아쓰기합니다.
    이 방식은 transcribe가 끝난 뒤 segments 결과를 한 번에 반환합니다.
    """
    model = whisper.load_model(model_name)
    result = model.transcribe(str(audio_file), language=language, fp16=False)

    lines = []

    for segment in result["segments"]:
        text = segment["text"].strip()

        if not text:
            continue

        line = format_transcript_line(
            text=text,
            start=segment["start"],
            end=segment["end"],
            include_timestamps=include_timestamps,
        )
        lines.append(line)

    output_txt.write_text("\n\n".join(lines), encoding="utf-8")

    return output_txt


def transcribe_audio_with_faster_whisper(
    audio_file: Path,
    output_txt: Path,
    model_name: str = "base",
    language: str = "ko",
    include_timestamps: bool = False,
    on_segment: Callable[[str], None] | None = None,
) -> Path:
    """
    faster-whisper로 WAV 음성 파일을 받아쓰기합니다.
    segment가 생성될 때마다 on_segment 콜백으로 중간 결과를 전달할 수 있습니다.
    """
    model = WhisperModel(
        model_name,
        device="cpu",
        compute_type="int8",
    )

    segments, _ = model.transcribe(
        str(audio_file),
        language=language,
        vad_filter=True,
    )

    lines = []

    for segment in segments:
        text = segment.text.strip()

        if not text:
            continue

        line = format_transcript_line(
            text=text,
            start=segment.start,
            end=segment.end,
            include_timestamps=include_timestamps,
        )

        lines.append(line)

        if on_segment is not None:
            on_segment(line)

    output_txt.write_text("\n\n".join(lines), encoding="utf-8")

    return output_txt


def transcribe_audio_to_txt(
    audio_file: Path,
    output_txt: Path,
    model_name: str = "small",
    language: str = "ko",
    include_timestamps: bool = False,
    on_segment: Callable[[str], None] | None = None,
) -> Path:
    """
    WAV 음성 파일을 받아쓰기한 뒤 TXT 파일로 저장합니다.

    model_name 규칙:
        base / small / medium
            -> 기존 openai-whisper 사용

        faster-base / faster-small / faster-medium
            -> faster-whisper 사용

    Args:
        audio_file: 받아쓰기할 WAV 파일 경로
        output_txt: 저장할 TXT 파일 경로
        model_name: Whisper 모델 이름
        language: 받아쓰기 언어 코드, 한국어는 ko
        include_timestamps: True면 각 문장 앞에 시간 정보를 붙입니다.
        on_segment: faster-whisper 사용 시 segment 단위 결과를 받을 콜백입니다.

    Returns:
        생성된 TXT 파일 경로
    """
    if not audio_file.exists():
        raise FileNotFoundError(f"음성 파일을 찾을 수 없습니다: {audio_file}")

    output_txt.parent.mkdir(parents=True, exist_ok=True)

    normalized_model_name, use_faster_whisper = normalize_model_name(model_name)

    if use_faster_whisper:
        return transcribe_audio_with_faster_whisper(
            audio_file=audio_file,
            output_txt=output_txt,
            model_name=normalized_model_name,
            language=language,
            include_timestamps=include_timestamps,
            on_segment=on_segment,
        )

    return transcribe_audio_with_whisper(
        audio_file=audio_file,
        output_txt=output_txt,
        model_name=normalized_model_name,
        language=language,
        include_timestamps=include_timestamps,
    )