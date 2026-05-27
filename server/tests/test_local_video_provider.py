import asyncio
import os
import sys
from pathlib import Path


SERVER_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = SERVER_DIR.parent
sys.path.insert(0, str(SERVER_DIR))
os.chdir(PROJECT_DIR)

os.environ["VIDEO_PROVIDER"] = "local"
os.environ.setdefault("LOCAL_VIDEO_DUMMY_ON_FAILURE", "true")

from tools.dummy_image_generator import DummyImageGenerator
from tools.video_provider import get_video_generator


async def main() -> None:
    image_path = await DummyImageGenerator().generate_image(
        "A local video provider test frame.",
        aspect_ratio="16:9",
    )

    video_gen = get_video_generator()
    video_path = await video_gen.generate_video_from_image(
        "Slow cinematic push-in toward the test frame.",
        image_path,
        duration=2,
        aspect_ratio="16:9",
    )

    if not Path(video_path).exists():
        raise FileNotFoundError(f"Video output does not exist: {video_path}")

    if getattr(video_gen, "dummy_on_failure", False):
        print(
            "LOCAL_VIDEO_NOTE=If WanGP/local backend was unreachable, "
            "LOCAL_VIDEO_DUMMY_ON_FAILURE=true allows dummy fallback."
        )

    print(f"LOCAL_VIDEO_PATH={Path(video_path).resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
