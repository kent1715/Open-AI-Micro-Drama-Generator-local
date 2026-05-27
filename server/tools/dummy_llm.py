import json
from typing import Optional


class DummyLLM:
    """Deterministic LLM stub for offline pipeline tests."""

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: int = 120,
        fallback: Optional[str] = None,
    ) -> str:
        text = f"{system_prompt or ''}\n{prompt}".lower()

        if '"characters"' in text or "extract all characters" in text:
            return json.dumps({
                "characters": [
                    {
                        "idx": 0,
                        "name": "Maya",
                        "static_features": "Woman in her early 30s, focused eyes, short dark hair, practical build.",
                        "dynamic_features": "Blue field jacket, dark shirt, utility belt, worn boots.",
                        "is_visible": True,
                    }
                ]
            })

        if '"shots"' in text or "design a storyboard" in text:
            return json.dumps({
                "shots": [
                    {
                        "idx": 0,
                        "visual_desc": (
                            "A cinematic medium shot of Maya standing in a quiet workshop, "
                            "lit by a warm desk lamp and cool moonlight from a window."
                        ),
                        "motion_desc": "Slow push-in as Maya lifts a small glowing device from the workbench.",
                        "audio_desc": "[Sound Effect] Soft electrical hum and distant city ambience.",
                    }
                ]
            })

        if '"scenes"' in text or "write individual scene scripts" in text:
            return json.dumps({
                "scenes": [
                    {
                        "scene_number": 1,
                        "title": "The Signal",
                        "script": (
                            "INT. SMALL WORKSHOP - NIGHT. Maya discovers a tiny glowing device "
                            "on her desk. The room is quiet except for a gentle electrical hum. "
                            "She reaches for it, and the light reflects in her eyes."
                        ),
                    }
                ]
            })

        return (
            "Maya, a careful inventor, finds a mysterious glowing device in her workshop. "
            "She studies it through the night and realizes it is sending a signal. "
            "The moment is intimate, visual, and simple enough for a short micro-drama."
        )
