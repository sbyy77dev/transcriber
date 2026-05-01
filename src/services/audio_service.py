import subprocess
from pathlib import Path


def extract_audio_to_wav(input_file: Path, output_audio: Path) -> Path:
    """
    영상 또는 음성 파일에서 받아쓰기용 WAV 파일을 생성합니다.
    Whisper 처리에 적합하도록 16kHz mono 형태로 변환합니다.
    """
    if not input_file.exists():
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_file}")

    output_audio.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg",
        "-y",
        "-i", str(input_file),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        str(output_audio),
    ]

    subprocess.run(command, check=True)

    return output_audio


def extract_audio_to_mp3(input_file: Path, output_audio: Path) -> Path:
    """
    영상 또는 음성 파일에서 사용자 제공용 MP3 파일을 생성합니다.
    웹 서비스에서는 이 파일을 다운로드 링크로 제공할 수 있습니다.
    """
    if not input_file.exists():
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_file}")

    output_audio.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg",
        "-y",
        "-i", str(input_file),
        "-vn",
        "-codec:a", "libmp3lame",
        "-b:a", "192k",
        str(output_audio),
    ]

    subprocess.run(command, check=True)

    return output_audio