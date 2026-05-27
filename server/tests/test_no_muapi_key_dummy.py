import os
import sys
from pathlib import Path


SERVER_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = SERVER_DIR.parent
sys.path.insert(0, str(SERVER_DIR))
os.chdir(PROJECT_DIR)

os.environ.pop("MUAPI_KEY", None)
os.environ["AI_PROVIDER"] = "dummy"
os.environ["IMAGE_PROVIDER"] = "dummy"
os.environ["VIDEO_PROVIDER"] = "dummy"

from tools.image_provider import get_image_generator
from tools.llm_provider import get_llm
from tools.video_provider import get_video_generator


def main() -> None:
    llm = get_llm()
    image_gen = get_image_generator()
    video_gen = get_video_generator()

    print(f"NO_MUAPI_DUMMY_LLM={type(llm).__name__}")
    print(f"NO_MUAPI_DUMMY_IMAGE={type(image_gen).__name__}")
    print(f"NO_MUAPI_DUMMY_VIDEO={type(video_gen).__name__}")


if __name__ == "__main__":
    main()
