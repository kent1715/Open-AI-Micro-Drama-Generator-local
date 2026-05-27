import base64
import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional


DEFAULT_LOCAL_VIDEO_BASE_URL = "http://127.0.0.1:7860"
OUTPUT_DIR = Path("outputs") / "videos"
TRUE_VALUES = {"1", "true", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "no", "n", "off"}


class LocalVideoGenerationError(RuntimeError):
    pass


class LocalVideoGenerator:
    """Generate image-to-video clips through a local backend or dummy fallback."""

    requires_public_image_url = False

    def __init__(self, base_url: Optional[str] = None, backend: Optional[str] = None):
        self.backend = (backend or os.environ.get("LOCAL_VIDEO_BACKEND", "wangp")).strip().lower()
        self.base_url = (base_url or os.environ.get("LOCAL_VIDEO_BASE_URL", DEFAULT_LOCAL_VIDEO_BASE_URL)).rstrip("/")
        self.timeout = int(os.environ.get("LOCAL_VIDEO_TIMEOUT", "900"))
        self.dummy_on_failure = self._parse_bool(
            os.environ.get("LOCAL_VIDEO_DUMMY_ON_FAILURE", "true"),
            default=True,
        )
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(
            "[Video] Using local video provider: "
            f"backend={self.backend}, base_url={self.base_url}, "
            f"dummy_on_failure={self.dummy_on_failure}"
        )

    def _parse_bool(self, value: str, default: bool = False) -> bool:
        normalized = str(value).strip().lower()
        if normalized in TRUE_VALUES:
            return True
        if normalized in FALSE_VALUES:
            return False
        print(f"[Video] Invalid boolean value '{value}', using default={default}")
        return default

    async def generate_video_from_image(
        self,
        prompt: str,
        image_url: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
    ) -> str:
        """Generate a local mp4 from an image/reference frame and motion prompt."""
        if self.backend == "dummy":
            return await self._generate_dummy_video(image_url, duration, aspect_ratio)

        try:
            return await self._generate_with_backend(prompt, image_url, duration, aspect_ratio)
        except Exception as exc:
            if not self.dummy_on_failure:
                raise LocalVideoGenerationError(f"Local video backend failed: {exc}") from exc

            print(f"[Video] Local backend unavailable, using dummy fallback clip: {exc}")
            return await self._generate_dummy_video(image_url, duration, aspect_ratio)

    async def _generate_with_backend(
        self,
        prompt: str,
        image_url: str,
        duration: int,
        aspect_ratio: str,
    ) -> str:
        payload = {
            "backend": self.backend,
            "prompt": prompt,
            "image_path": image_url,
            "image": image_url,
            "reference_frame": image_url,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
        }

        data = await self._post_generate(payload)
        return await self._save_result(data)

    async def _post_generate(self, payload: dict) -> Any:
        import httpx

        errors = []
        endpoints = ("/generate", "/api/generate", "/video")

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for endpoint in endpoints:
                url = f"{self.base_url}{endpoint}"
                try:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 404:
                        errors.append(f"{endpoint}: HTTP 404")
                        continue
                    if resp.status_code >= 400:
                        raise LocalVideoGenerationError(
                            f"Local video backend rejected the request at {url}: "
                            f"HTTP {resp.status_code} {resp.text}"
                        )
                    data = resp.json()
                    return await self._maybe_poll_result(client, data)
                except LocalVideoGenerationError:
                    raise
                except Exception as exc:
                    errors.append(f"{endpoint}: {exc}")

        raise LocalVideoGenerationError(
            f"Local video backend is not available at {self.base_url}. Tried: {', '.join(errors)}"
        )

    async def _maybe_poll_result(self, client, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        immediate = self._extract_video_value(data)
        if immediate:
            return data

        job_id = data.get("job_id") or data.get("id") or data.get("task_id")
        if not job_id:
            return data

        deadline = time.monotonic() + self.timeout
        poll_paths = (
            f"/result/{job_id}",
            f"/api/result/{job_id}",
            f"/status/{job_id}",
            f"/api/status/{job_id}",
        )

        while time.monotonic() < deadline:
            for path in poll_paths:
                resp = await client.get(f"{self.base_url}{path}")
                if resp.status_code == 404:
                    continue
                if resp.status_code >= 400:
                    raise LocalVideoGenerationError(
                        f"Local video polling failed at {path}: HTTP {resp.status_code} {resp.text}"
                    )
                poll_data = resp.json()
                status = str(poll_data.get("status", "")).lower()
                if status in ("failed", "error"):
                    raise LocalVideoGenerationError(f"Local video job failed: {poll_data}")
                if self._extract_video_value(poll_data):
                    return poll_data

            await self._sleep(3)

        raise LocalVideoGenerationError(f"Timed out waiting for local video job {job_id}")

    async def _save_result(self, data: Any) -> str:
        video_value = self._extract_video_value(data)
        if not video_value:
            raise LocalVideoGenerationError(f"Local video backend returned no video output: {data}")

        if isinstance(video_value, str) and video_value.startswith(("http://", "https://")):
            return await self._download_url(video_value)

        if isinstance(video_value, str) and self._looks_like_existing_file(video_value):
            return str(Path(video_value))

        if isinstance(video_value, str):
            return self._save_base64(video_value)

        raise LocalVideoGenerationError(f"Unsupported local video output: {video_value}")

    def _extract_video_value(self, data: Any) -> Any:
        if isinstance(data, str):
            return data
        if not isinstance(data, dict):
            return None

        for key in ("video", "video_url", "url", "path", "file", "output"):
            value = data.get(key)
            if value:
                return value

        videos = data.get("videos")
        if isinstance(videos, list) and videos:
            first = videos[0]
            if isinstance(first, dict):
                return self._extract_video_value(first)
            return first

        outputs = data.get("outputs")
        if isinstance(outputs, list) and outputs:
            first = outputs[0]
            if isinstance(first, dict):
                return self._extract_video_value(first)
            return first

        return None

    def _looks_like_existing_file(self, value: str) -> bool:
        try:
            return Path(value).exists()
        except OSError:
            return False

    async def _download_url(self, url: str) -> str:
        import httpx

        local_path = OUTPUT_DIR / f"local_video_{uuid.uuid4().hex[:10]}.mp4"
        async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code >= 400:
                raise LocalVideoGenerationError(
                    f"Failed to download local video output: HTTP {resp.status_code} {resp.text}"
                )
            local_path.write_bytes(resp.content)
        return str(local_path)

    def _save_base64(self, value: str) -> str:
        if value.startswith("data:video"):
            _, value = value.split(",", 1)
        try:
            video_bytes = base64.b64decode(value, validate=False)
        except Exception as exc:
            raise LocalVideoGenerationError(
                "Local video backend returned a string that is not a URL, file path, or valid base64 video."
            ) from exc

        local_path = OUTPUT_DIR / f"local_video_{uuid.uuid4().hex[:10]}.mp4"
        local_path.write_bytes(video_bytes)
        return str(local_path)

    async def _generate_dummy_video(self, image_url: str, duration: int, aspect_ratio: str) -> str:
        image_path = await self._ensure_local_image(image_url)
        output_path = str(OUTPUT_DIR / f"dummy_video_{uuid.uuid4().hex[:10]}.mp4")

        import asyncio

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._write_dummy_video_sync,
            image_path,
            output_path,
            duration,
            aspect_ratio,
        )
        return output_path

    async def _ensure_local_image(self, image_url: str) -> str:
        if image_url.startswith(("http://", "https://")):
            import httpx

            suffix = Path(image_url.split("?")[0]).suffix or ".png"
            local_path = OUTPUT_DIR / f"dummy_frame_{uuid.uuid4().hex[:10]}{suffix}"
            async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
                resp = await client.get(image_url)
                if resp.status_code >= 400:
                    raise LocalVideoGenerationError(
                        f"Failed to download reference frame for dummy video: HTTP {resp.status_code} {resp.text}"
                    )
                local_path.write_bytes(resp.content)
            return str(local_path)

        if Path(image_url).exists():
            return image_url

        raise LocalVideoGenerationError(f"Reference frame does not exist: {image_url}")

    def _write_dummy_video_sync(
        self,
        image_path: str,
        output_path: str,
        duration: int,
        aspect_ratio: str,
    ) -> None:
        try:
            self._write_dummy_with_moviepy(image_path, output_path, duration, aspect_ratio)
            return
        except ImportError:
            self._write_dummy_with_ffmpeg(image_path, output_path, duration, aspect_ratio)

    def _write_dummy_with_moviepy(
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

    def _write_dummy_with_ffmpeg(
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
            raise LocalVideoGenerationError(f"ffmpeg failed to create local dummy video: {result.stderr}")

    def _size_for_aspect_ratio(self, aspect_ratio: str) -> tuple[int, int]:
        sizes = {
            "16:9": (1024, 576),
            "9:16": (576, 1024),
            "1:1": (768, 768),
        }
        return sizes.get(aspect_ratio, sizes["16:9"])

    async def _sleep(self, seconds: int) -> None:
        import asyncio

        await asyncio.sleep(seconds)
