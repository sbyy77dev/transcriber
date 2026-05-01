from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"


def ensure_directories() -> None:
    """
    프로그램 실행에 필요한 기본 폴더가 없으면 생성
    웹 서버에서 실행할 때도 같은 폴더 구조 사용 가능
    """
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    TEMP_DIR.mkdir(exist_ok=True)