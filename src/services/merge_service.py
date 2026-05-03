import subprocess
from pathlib import Path


def convert_file_to_mp3(
    input_file: Path,
    output_mp3: Path,
    bitrate: str = "192k",
) -> Path:
    """
    영상 또는 음성 파일 하나를 MP3 파일로 변환합니다.

    Args:
        input_file: 원본 영상/음성 파일 경로
        output_mp3: 생성할 MP3 파일 경로
        bitrate: MP3 비트레이트

    Returns:
        생성된 MP3 파일 경로
    """
    if not input_file.exists():
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_file}")

    output_mp3.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg",
        "-y",
        "-i", str(input_file),
        "-vn",
        "-ac", "2",
        "-ar", "44100",
        "-codec:a", "libmp3lame",
        "-b:a", bitrate,
        str(output_mp3),
    ]

    subprocess.run(command, check=True)

    return output_mp3


def create_concat_list_file(
    mp3_files: list[Path],
    list_file: Path,
) -> Path:
    """
    FFmpeg concat 기능에서 사용할 파일 목록 txt를 생성합니다.

    Args:
        mp3_files: 병합할 MP3 파일 경로 목록
        list_file: 생성할 목록 파일 경로

    Returns:
        생성된 목록 파일 경로
    """
    if not mp3_files:
        raise ValueError("병합할 MP3 파일이 없습니다.")

    list_file.parent.mkdir(parents=True, exist_ok=True)

    lines = []

    for mp3_file in mp3_files:
        if not mp3_file.exists():
            raise FileNotFoundError(f"MP3 파일을 찾을 수 없습니다: {mp3_file}")

        safe_path = mp3_file.resolve().as_posix()
        lines.append(f"file '{safe_path}'")

    list_file.write_text("\n".join(lines), encoding="utf-8")

    return list_file


def merge_mp3_files(
    mp3_files: list[Path],
    output_file: Path,
    list_file: Path,
) -> Path:
    """
    여러 MP3 파일을 순서대로 하나의 MP3 파일로 병합합니다.

    Args:
        mp3_files: 병합할 MP3 파일 목록
        output_file: 최종 병합 MP3 파일 경로
        list_file: FFmpeg concat 목록 파일 경로

    Returns:
        최종 병합 MP3 파일 경로
    """
    if not mp3_files:
        raise ValueError("병합할 MP3 파일이 없습니다.")

    output_file.parent.mkdir(parents=True, exist_ok=True)

    create_concat_list_file(mp3_files, list_file)

    command = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_file),
    ]

    subprocess.run(command, check=True)

    return output_file


def convert_and_merge_to_mp3(
    input_files: list[Path],
    temp_dir: Path,
    output_file: Path,
    job_id: str,
) -> Path:
    """
    여러 영상/음성 파일을 각각 MP3로 변환한 뒤 하나의 MP3로 병합합니다.

    Args:
        input_files: 사용자가 지정한 순서의 원본 파일 목록
        temp_dir: 중간 MP3와 목록 파일을 저장할 임시 폴더
        output_file: 최종 병합 MP3 파일 경로
        job_id: 작업 ID

    Returns:
        최종 병합 MP3 파일 경로
    """
    if not input_files:
        raise ValueError("입력 파일이 없습니다.")

    temp_dir.mkdir(parents=True, exist_ok=True)

    converted_mp3_files = []

    for index, input_file in enumerate(input_files, start=1):
        converted_mp3 = temp_dir / f"{job_id}_{index:03d}.mp3"
        convert_file_to_mp3(input_file, converted_mp3)
        converted_mp3_files.append(converted_mp3)

    list_file = temp_dir / f"{job_id}_merge_list.txt"

    return merge_mp3_files(
        mp3_files=converted_mp3_files,
        output_file=output_file,
        list_file=list_file,
    )