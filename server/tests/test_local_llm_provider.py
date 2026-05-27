import asyncio
import os
import sys
from pathlib import Path


SERVER_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = SERVER_DIR.parent
sys.path.insert(0, str(SERVER_DIR))
os.chdir(PROJECT_DIR)

os.environ["AI_PROVIDER"] = "local"

from tools.llm_provider import get_llm


async def main() -> None:
    try:
        llm = get_llm()
        response = await llm.complete(
            "Reply with one short sentence confirming the local LLM works.",
            timeout=30,
        )
    except Exception as exc:
        raise RuntimeError(
            "Ollama is not reachable. Start Ollama or use AI_PROVIDER=dummy."
        ) from exc

    if not response or not response.strip():
        raise RuntimeError("Local LLM returned an empty response.")

    print("LOCAL_LLM_RESPONSE=", response.strip()[:500])


if __name__ == "__main__":
    asyncio.run(main())
