import os
from typing import Optional


def get_video_generator(api_key: Optional[str] = None):
    provider = os.environ.get("VIDEO_PROVIDER", "muapi").strip().lower()
    print(f"[Video] VIDEO_PROVIDER={provider}")

    if provider == "dummy":
        from tools.dummy_video_generator import DummyVideoGenerator

        return DummyVideoGenerator()
    if provider == "local":
        from tools.local_video_generator import LocalVideoGenerator

        return LocalVideoGenerator()
    if provider == "muapi":
        from tools.muapi_video_generator import MuAPIVideoGenerator

        return MuAPIVideoGenerator(api_key=api_key)

    raise ValueError("VIDEO_PROVIDER must be 'muapi', 'local', or 'dummy'")
