from pathlib import Path

import whisper


def format_timestamp(seconds: float) -> str:
    """
    초 단위 시간을 HH:MM:SS 형식으로 변환합니다.
    """
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def transcribe_audio_to_txt(
    audio_file: Path,
    output_txt: Path,
    model_name: str = "small",
    language: str = "ko",
    include_timestamps: bool = False,
) -> Path:
    """
    WAV 음성 파일을 Whisper로 받아쓰기한 뒤 TXT 파일로 저장합니다.

    Args:
        audio_file: 받아쓰기할 WAV 파일 경로
        output_txt: 저장할 TXT 파일 경로
        model_name: Whisper 모델 이름
        language: 받아쓰기 언어 코드, 한국어는 ko
        include_timestamps: True면 각 문장 앞에 시간 정보를 붙입니다.

    Returns:
        생성된 TXT 파일 경로
    """
    if not audio_file.exists():
        raise FileNotFoundError(f"음성 파일을 찾을 수 없습니다: {audio_file}")

    output_txt.parent.mkdir(parents=True, exist_ok=True)

    model = whisper.load_model(model_name)
    result = model.transcribe(str(audio_file), language=language, fp16=False)

    lines = []

    for segment in result["segments"]:
        text = segment["text"].strip()

        if not text:
            continue

        if include_timestamps:
            start_time = format_timestamp(segment["start"])
            end_time = format_timestamp(segment["end"])
            lines.append(f"[{start_time} → {end_time}] {text}")
        else:
            lines.append(text)

    output_txt.write_text("\n\n".join(lines), encoding="utf-8")

    return output_txt