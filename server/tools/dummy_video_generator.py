import uuid
from pathlib import Path


OUTPUT_DIR = Path("outputs") / "videos"


class DummyVideoGenerator:
    """Create short mp4 clips from placeholder frames for offline tests."""

    requires_public_image_url = False

    def __init__(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print("[Video] Using dummy video provider")

    async def generate_video_from_image(
        self,
        prompt: str,
        image_url: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
    ) -> str:
        output_path = str(OUTPUT_DIR / f"dummy_video_{uuid.uuid4().hex[:10]}.mp4")

        import asyncio

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._write_video_sync,
            image_url,
            output_path,
            duration,
            aspect_ratio,
        )
        return output_path

    def _write_video_sync(
        self,
        image_path: str,
        output_path: str,
        duration: int,
        aspect_ratio: str,
    ) -> None:
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Dummy video reference frame not found: {image_path}")

        try:
            self._write_with_moviepy(image_path, output_path, duration, aspect_ratio)
            return
        except ImportError:
            self._write_with_ffmpeg(image_path, output_path, duration, aspect_ratio)

    def _write_with_moviepy(
        self,
        image_path: str,
        output_path: str,
        duration: int,
        aspect_ratio: str,
    ) -> None:
        try:
            from moviepy.editor import ImageClip
        except ImportError:
            from moviepy import ImageClip

        size = self._size_for_aspect_ratio(aspect_ratio)
        clip = ImageClip(image_path)
        if hasattr(clip, "set_duration"):
            clip = clip.set_duration(max(1, duration))
        else:
            clip = clip.with_duration(max(1, duration))

        if hasattr(clip, "resize"):
            clip = clip.resize(newsize=size)
        else:
            clip = clip.resized(new_size=size)

        try:
            clip.write_videofile(
                output_path,
                fps=24,
                codec="libx264",
                audio=False,
                logger=None,
            )
        finally:
            clip.close()

    def _write_with_ffmpeg(
        self,
        image_path: str,
        output_path: str,
        duration: int,
        aspect_ratio: str,
    ) -> None:
        import subprocess

        width, height = self._size_for_aspect_ratio(aspect_ratio)
        cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            image_path,
            "-t",
            str(max(1, duration)),
            "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            "-r",
            "24",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed to create dummy video: {result.stderr}")

    def _size_for_aspect_ratio(self, aspect_ratio: str) -> tuple[int, int]:
        sizes = {
            "16:9": (1024, 576),
            "9:16": (576, 1024),
            "1:1": (768, 768),
        }
        return sizes.get(aspect_ratio, sizes["16:9"])
