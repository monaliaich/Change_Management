from typing import Any

class ExampleAgent:
    """A small example agent implementing the canonical `handle_request(context)` pattern.
    This is a minimal, synchronous example. Real agents should call Azure SDK and register async tool calls.
    """
    def handle_request(self, context: dict) -> dict:
        # Minimal behavior: echo context with a status
        return {"status": "ok", "input": context}
