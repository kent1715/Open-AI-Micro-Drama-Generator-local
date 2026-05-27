import asyncio
import os
import sys
from pathlib import Path


SERVER_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = SERVER_DIR.parent
sys.path.insert(0, str(SERVER_DIR))
os.chdir(PROJECT_DIR)

os.environ.setdefault("IMAGE_PROVIDER", "zimage")

from tools.image_provider import get_image_generator


async def main() -> None:
    provider = os.environ.get("IMAGE_PROVIDER", "zimage").strip().lower()
    if provider not in ("zimage", "local", "comfyui"):
        raise RuntimeError("Set IMAGE_PROVIDER=zimage or IMAGE_PROVIDER=comfyui for this test.")

    try:
        image_gen = get_image_generator()
        image_path = await image_gen.generate_image(
            "A simple cinematic test frame of a glowing cube on a table.",
            aspect_ratio="16:9",
        )
    except Exception as exc:
        raise RuntimeError(
            f"Local image backend is not reachable for IMAGE_PROVIDER={provider}. "
            "Start the image backend or use IMAGE_PROVIDER=dummy."
        ) from exc

    if not Path(image_path).exists():
        raise FileNotFoundError(f"Image output does not exist: {image_path}")

    print(f"LOCAL_IMAGE_PATH={Path(image_path).resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
