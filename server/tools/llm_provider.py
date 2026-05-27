import os


def get_llm():
    provider = os.environ.get("AI_PROVIDER", "muapi").strip().lower()
    print(f"[LLM] AI_PROVIDER={provider}")

    if provider == "dummy":
        from tools.dummy_llm import DummyLLM

        return DummyLLM()
    if provider == "local":
        from tools.local_llm import LocalLLM

        return LocalLLM()
    if provider == "muapi":
        from tools.muapi_llm import MuAPILLM

        return MuAPILLM()

    raise ValueError("AI_PROVIDER must be 'muapi', 'local', or 'dummy'")
