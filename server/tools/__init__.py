__all__ = [
    "LocalImageGenerator",
    "LocalLLM",
    "LocalVideoGenerator",
    "DummyImageGenerator",
    "DummyLLM",
    "DummyVideoGenerator",
    "MuAPILLM",
    "MuAPIImageGenerator",
    "MuAPIVideoGenerator",
    "get_image_generator",
    "get_llm",
    "get_video_generator",
    "upload_image_from_url",
    "upload_image_from_path",
]


def __getattr__(name):
    if name == "get_image_generator":
        from .image_provider import get_image_generator

        return get_image_generator
    if name == "get_llm":
        from .llm_provider import get_llm

        return get_llm
    if name == "get_video_generator":
        from .video_provider import get_video_generator

        return get_video_generator
    if name == "DummyImageGenerator":
        from .dummy_image_generator import DummyImageGenerator

        return DummyImageGenerator
    if name == "DummyLLM":
        from .dummy_llm import DummyLLM

        return DummyLLM
    if name == "DummyVideoGenerator":
        from .dummy_video_generator import DummyVideoGenerator

        return DummyVideoGenerator
    if name == "LocalImageGenerator":
        from .local_image_generator import LocalImageGenerator

        return LocalImageGenerator
    if name == "LocalLLM":
        from .local_llm import LocalLLM

        return LocalLLM
    if name == "LocalVideoGenerator":
        from .local_video_generator import LocalVideoGenerator

        return LocalVideoGenerator
    if name == "MuAPILLM":
        from .muapi_llm import MuAPILLM

        return MuAPILLM
    if name == "MuAPIImageGenerator":
        from .muapi_image_generator import MuAPIImageGenerator

        return MuAPIImageGenerator
    if name == "MuAPIVideoGenerator":
        from .muapi_video_generator import MuAPIVideoGenerator

        return MuAPIVideoGenerator
    if name in ("upload_image_from_url", "upload_image_from_path"):
        from .muapi_uploader import upload_image_from_path, upload_image_from_url

        return {
            "upload_image_from_url": upload_image_from_url,
            "upload_image_from_path": upload_image_from_path,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
