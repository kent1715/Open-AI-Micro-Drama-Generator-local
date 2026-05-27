import asyncio
import os
import sys
import types
from pathlib import Path


SERVER_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = SERVER_DIR.parent
sys.path.insert(0, str(SERVER_DIR))
os.chdir(PROJECT_DIR)

os.environ.pop("MUAPI_KEY", None)
os.environ["AI_PROVIDER"] = "dummy"
os.environ["IMAGE_PROVIDER"] = "dummy"
os.environ["VIDEO_PROVIDER"] = "dummy"


def _forbidden_upload(*args, **kwargs):
    raise AssertionError("muapi_uploader must not be called when VIDEO_PROVIDER=dummy")


forbidden_uploader = types.ModuleType("tools.muapi_uploader")
forbidden_uploader.upload_image_from_path = _forbidden_upload
forbidden_uploader.upload_image_from_url = _forbidden_upload
sys.modules["tools.muapi_uploader"] = forbidden_uploader

from pipelines.script2video import Script2VideoPipeline
from interfaces.character import CharacterInScene


async def progress(stage: str, message: str, progress_value: int) -> None:
    print(f"[{progress_value:03d}%] {stage}: {message}")


async def main() -> None:
    pipeline = Script2VideoPipeline()
    final_path = await pipeline.run(
        script="INT. TEST ROOM - NIGHT. Maya looks at a glowing cube.",
        characters=[
            CharacterInScene(
                idx=0,
                name="Maya",
                static_features="Woman in her early 30s with short dark hair.",
                dynamic_features="Blue jacket and utility belt.",
                is_visible=True,
            )
        ],
        user_requirement="One shot only.",
        style="Cinematic",
        working_dir=str(Path("outputs") / "dummy-no-uploader-test" / "scene_00"),
        progress_callback=progress,
    )

    if not Path(final_path).exists():
        raise FileNotFoundError(f"Expected final video does not exist: {final_path}")

    print(f"NO_MUAPI_UPLOADER_FINAL_MP4={Path(final_path).resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
