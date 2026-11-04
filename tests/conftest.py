"""Keep unit tests independent from the optional LLM SDK."""
import sys
import types

if "openai" not in sys.modules:
    openai_stub = types.ModuleType("openai")
    class OpenAI:  # pragma: no cover - used only as an import-time type
        pass
    openai_stub.OpenAI = OpenAI
    openai_stub.BadRequestError = type("BadRequestError", (Exception,), {})
    sys.modules["openai"] = openai_stub
