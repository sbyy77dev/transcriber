from pathlib import Path

import whisper


def transcribe_audio_to_txt(
    audio_file: Path,
    output_txt: Path,
    model_name: str = "small",
    language: str = "ko",
) -> Path:
    """
    WAV 음성 파일을 Whisper로 받아쓰기한 뒤 TXT 파일로 저장합니다.

    Args:
        audio_file: 받아쓰기할 WAV 파일 경로
        output_txt: 저장할 TXT 파일 경로
        model_name: Whisper 모델 이름
        language: 받아쓰기 언어 코드, 한국어는 ko

    Returns:
        생성된 TXT 파일 경로
    """
    if not audio_file.exists():
        raise FileNotFoundError(f"음성 파일을 찾을 수 없습니다: {audio_file}")

    output_txt.parent.mkdir(parents=True, exist_ok=True)

    model = whisper.load_model(model_name)
    result = model.transcribe(str(audio_file), language=language)

    text = result["text"].strip()
    output_txt.write_text(text, encoding="utf-8")

    return output_txt