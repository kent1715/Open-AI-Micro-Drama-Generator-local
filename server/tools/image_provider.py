import os
from typing import Optional


def get_image_generator(api_key: Optional[str] = None):
    provider = os.environ.get("IMAGE_PROVIDER", "muapi").strip().lower()
    print(f"[Image] IMAGE_PROVIDER={provider}")

    if provider == "dummy":
        from tools.dummy_image_generator import DummyImageGenerator

        return DummyImageGenerator()
    if provider in ("local", "zimage", "comfyui"):
        from tools.local_image_generator import LocalImageGenerator

        return LocalImageGenerator()
    if provider == "muapi":
        from tools.muapi_image_generator import MuAPIImageGenerator

        return MuAPIImageGenerator(api_key=api_key)

    raise ValueError("IMAGE_PROVIDER must be 'muapi', 'local', 'zimage', 'comfyui', or 'dummy'")
