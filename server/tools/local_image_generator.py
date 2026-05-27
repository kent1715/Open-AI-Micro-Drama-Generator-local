import base64
import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import httpx


DEFAULT_Z_IMAGE_BASE_URL = "http://127.0.0.1:9000"
OUTPUT_DIR = Path("outputs") / "images"


class LocalImageGenerationError(RuntimeError):
    pass


class LocalImageGenerator:
    """Generate images through a local Z-Image Turbo API."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or os.environ.get("Z_IMAGE_BASE_URL", DEFAULT_Z_IMAGE_BASE_URL)).rstrip("/")
        self.timeout = int(os.environ.get("Z_IMAGE_TIMEOUT", "300"))
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"[Image] Using Z-Image Turbo local API: {self.base_url}")

    async def generate_image(self, prompt: str, aspect_ratio: str = "1:1") -> str:
        """Generate an image from a prompt and return the local file path."""
        width, height = self._size_for_aspect_ratio(aspect_ratio)
        payload = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "steps": int(os.environ.get("Z_IMAGE_STEPS", "8")),
            "cfg": float(os.environ.get("Z_IMAGE_CFG", "1.5")),
            "seed": int(time.time() * 1000) % 2_147_483_647,
        }

        data = await self._post_generate(payload)
        return await self._save_result(data)

    async def generate_image_with_reference(
        self,
        prompt: str,
        reference_url: str,
        aspect_ratio: str = "16:9",
    ) -> str:
        """Keep the MuAPI-compatible method signature for reference generation.

        The initial Z-Image Turbo local API path is treated as text-to-image.
        The reference is passed through in the payload when the API supports it
        and also folded into the prompt for simple endpoints that ignore it.
        """
        width, height = self._size_for_aspect_ratio(aspect_ratio)
        prompt_with_reference = (
            f"{prompt}. Preserve character identity and visual continuity "
            f"from this reference if supported: {reference_url}"
        )
        payload = {
            "prompt": prompt_with_reference,
            "reference_image": reference_url,
            "image": reference_url,
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "steps": int(os.environ.get("Z_IMAGE_STEPS", "8")),
            "cfg": float(os.environ.get("Z_IMAGE_CFG", "1.5")),
            "seed": int(time.time() * 1000) % 2_147_483_647,
        }

        data = await self._post_generate(payload)
        return await self._save_result(data)

    def _size_for_aspect_ratio(self, aspect_ratio: str) -> tuple[int, int]:
        sizes = {
            "16:9": (1024, 576),
            "9:16": (576, 1024),
            "2:3": (768, 1152),
            "3:2": (1152, 768),
            "1:1": (1024, 1024),
        }
        return sizes.get(aspect_ratio, sizes["1:1"])

    async def _post_generate(self, payload: dict) -> Any:
        errors = []
        endpoints = [
            ("/generate", payload),
            (
                "/v1/images/generations",
                {
                    "model": os.environ.get("Z_IMAGE_MODEL", "z-image-turbo"),
                    "prompt": payload["prompt"],
                    "size": f"{payload['width']}x{payload['height']}",
                    "n": 1,
                    "response_format": "b64_json",
                },
            ),
        ]

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for endpoint, body in endpoints:
                url = f"{self.base_url}{endpoint}"
                try:
                    resp = await client.post(url, json=body)
                    if resp.status_code == 404:
                        errors.append(f"{endpoint}: HTTP 404")
                        continue
                    if resp.status_code >= 400:
                        raise LocalImageGenerationError(
                            f"Z-Image Turbo API rejected the request at {url}: "
                            f"HTTP {resp.status_code} {resp.text}"
                        )
                    return resp.json()
                except LocalImageGenerationError:
                    raise
                except Exception as exc:
                    errors.append(f"{endpoint}: {exc}")

        raise LocalImageGenerationError(
            "Z-Image Turbo image request failed. "
            f"Is the local API running at {self.base_url}? Tried: {', '.join(errors)}"
        )

    async def _save_result(self, data: Any) -> str:
        image_value = self._extract_image_value(data)
        if not image_value:
            raise LocalImageGenerationError(f"Z-Image Turbo returned no image output: {data}")

        if isinstance(image_value, str) and image_value.startswith(("http://", "https://")):
            return await self._download_url(image_value)

        if isinstance(image_value, str) and self._looks_like_existing_file(image_value):
            return str(Path(image_value))

        if isinstance(image_value, str):
            return self._save_base64(image_value)

        raise LocalImageGenerationError(f"Unsupported Z-Image Turbo image output: {image_value}")

    def _extract_image_value(self, data: Any) -> Any:
        if isinstance(data, str):
            return data

        if not isinstance(data, dict):
            return None

        for key in ("image", "image_url", "url", "path", "file", "output"):
            value = data.get(key)
            if value:
                return value

        images = data.get("images")
        if isinstance(images, list) and images:
            first = images[0]
            if isinstance(first, dict):
                return self._extract_image_value(first)
            return first

        openai_data = data.get("data")
        if isinstance(openai_data, list) and openai_data:
            first = openai_data[0]
            if isinstance(first, dict):
                return first.get("b64_json") or first.get("url") or first.get("path")
            return first

        return None

    def _looks_like_existing_file(self, value: str) -> bool:
        try:
            return Path(value).exists()
        except OSError:
            return False

    async def _download_url(self, url: str) -> str:
        suffix = Path(url.split("?")[0]).suffix or ".png"
        local_path = OUTPUT_DIR / f"zimage_{uuid.uuid4().hex[:10]}{suffix}"
        try:
            async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code >= 400:
                    raise LocalImageGenerationError(
                        f"Failed to download Z-Image output: HTTP {resp.status_code} {resp.text}"
                    )
                local_path.write_bytes(resp.content)
        except LocalImageGenerationError:
            raise
        except Exception as exc:
            raise LocalImageGenerationError(f"Failed to download Z-Image output: {exc}") from exc
        return str(local_path)

    def _save_base64(self, value: str) -> str:
        if value.startswith("data:image"):
            header, value = value.split(",", 1)
            suffix = ".jpg" if "jpeg" in header or "jpg" in header else ".png"
        else:
            suffix = ".png"

        try:
            image_bytes = base64.b64decode(value, validate=False)
        except Exception as exc:
            raise LocalImageGenerationError(
                "Z-Image Turbo returned a string that is not a URL, file path, or valid base64 image."
            ) from exc

        local_path = OUTPUT_DIR / f"zimage_{uuid.uuid4().hex[:10]}{suffix}"
        local_path.write_bytes(image_bytes)
        return str(local_path)
