import subprocess

from config import INPUT_DIR, OUTPUT_DIR, TEMP_DIR, ensure_directories
from services.audio_service import extract_audio_to_mp3, extract_audio_to_wav
from services.transcription_service import transcribe_audio_to_txt


def main() -> None:
    ensure_directories()

    input_file = INPUT_DIR / "sample.mkv"
    wav_file = TEMP_DIR / "sample.wav"
    mp3_file = OUTPUT_DIR / "sample.mp3"
    transcript_file = OUTPUT_DIR / "sample_transcript.txt"

    if not input_file.exists():
        print(f"입력 파일이 없습니다: {input_file}")
        print("input 폴더에 sample.mkv 파일을 넣고 다시 실행하세요.")
        return

    try:
        print("1단계: 받아쓰기용 WAV 파일 생성 중...")
        extract_audio_to_wav(input_file, wav_file)
        print(f"WAV 생성 완료: {wav_file}")

        print("2단계: 사용자 제공용 MP3 파일 생성 중...")
        extract_audio_to_mp3(input_file, mp3_file)
        print(f"MP3 생성 완료: {mp3_file}")

        print("3단계: Whisper 받아쓰기 진행 중...")
        transcribe_audio_to_txt(wav_file, transcript_file)
        print(f"받아쓰기 완료: {transcript_file}")

    except FileNotFoundError as error:
        print(error)
    except subprocess.CalledProcessError:
        print("FFmpeg 실행 중 오류가 발생했습니다.")
        print("ffmpeg -version 명령어로 FFmpeg 설치 여부를 확인하세요.")


if __name__ == "__main__":
    main()