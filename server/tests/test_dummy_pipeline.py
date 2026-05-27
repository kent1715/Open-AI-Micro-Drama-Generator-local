import asyncio
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
os.environ["LOCAL_VIDEO_BACKEND"] = "dummy"
os.environ["LOCAL_VIDEO_DUMMY_ON_FAILURE"] = "true"

from pipelines.idea2video import Idea2VideoPipeline


async def progress(stage: str, message: str, progress_value: int) -> None:
    print(f"[{progress_value:03d}%] {stage}: {message}")


async def main() -> None:
    pipeline = Idea2VideoPipeline()
    final_path = await pipeline.run(
        idea="A tiny offline test story about a glowing device.",
        user_requirement="Use one simple scene and one shot.",
        style="Cinematic",
        job_id="dummy-e2e-test",
        progress_callback=progress,
    )

    final_file = Path(final_path)
    if not final_file.exists():
        raise FileNotFoundError(f"Expected final video does not exist: {final_path}")

    print(f"FINAL_MP4={final_file.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
