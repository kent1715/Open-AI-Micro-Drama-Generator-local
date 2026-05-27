import textwrap
import uuid
from pathlib import Path


OUTPUT_DIR = Path("outputs") / "images"


class DummyImageGenerator:
    """Create local placeholder images for offline pipeline tests."""

    def __init__(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print("[Image] Using dummy image provider")

    async def generate_image(self, prompt: str, aspect_ratio: str = "1:1") -> str:
        return self._write_placeholder(prompt, aspect_ratio)

    async def generate_image_with_reference(
        self,
        prompt: str,
        reference_url: str,
        aspect_ratio: str = "16:9",
    ) -> str:
        return self._write_placeholder(f"{prompt}\nReference: {reference_url}", aspect_ratio)

    def _write_placeholder(self, prompt: str, aspect_ratio: str) -> str:
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError as exc:
            raise RuntimeError("Pillow is required for DummyImageGenerator.") from exc

        width, height = self._size_for_aspect_ratio(aspect_ratio)
        image = Image.new("RGB", (width, height), color=(32, 36, 44))
        draw = ImageDraw.Draw(image)

        title = "Dummy Frame"
        subtitle = f"Aspect: {aspect_ratio}"
        body = "\n".join(textwrap.wrap(prompt[:260], width=56))

        try:
            font_title = ImageFont.truetype("arial.ttf", 42)
            font_body = ImageFont.truetype("arial.ttf", 24)
        except OSError:
            font_title = ImageFont.load_default()
            font_body = ImageFont.load_default()

        draw.rectangle((24, 24, width - 24, height - 24), outline=(120, 160, 220), width=4)
        draw.text((48, 48), title, fill=(230, 238, 255), font=font_title)
        draw.text((48, 104), subtitle, fill=(160, 190, 230), font=font_body)
        draw.text((48, 156), body, fill=(220, 225, 235), font=font_body, spacing=8)

        path = OUTPUT_DIR / f"dummy_image_{uuid.uuid4().hex[:10]}.png"
        image.save(path)
        return str(path)

    def _size_for_aspect_ratio(self, aspect_ratio: str) -> tuple[int, int]:
        sizes = {
            "16:9": (1024, 576),
            "9:16": (576, 1024),
            "2:3": (768, 1152),
            "3:2": (1152, 768),
            "1:1": (768, 768),
        }
        return sizes.get(aspect_ratio, sizes["1:1"])
