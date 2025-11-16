"""Lightweight Gemini (Google GenAI) wrapper used by the project.

This module tries to use whichever GenAI client is available in the
environment (the new `google.generativeai` helper or the older
`google.ai.generativelanguage` client). It exposes a minimal `GeminiLLM`
class with a `generate(prompt, **kwargs)` method that returns text.

The wrapper intentionally keeps the surface area small to avoid pulling in
LangChain or OpenAI dependencies.
"""
from typing import Optional, Dict, Any
import os


class GeminiUnavailable(Exception):
    pass


class GeminiLLM:
    """Wrapper for calling Google Gemini/GenAI directly (not through LiteLLM).

    IMPORTANT: This wrapper calls Google's SDK directly.
    Model name should NOT include the 'gemini/' prefix (that's only for LiteLLM).
    Use just the model name, e.g., 'gemini-2.5-flash', not 'gemini/gemini-2.5-flash'.

    Methods:
      - generate(prompt, **kwargs) -> str
    """
    def __init__(self, model: str = "gemini-2.5-flash", temperature: float = 0.0, api_key: Optional[str] = None):
        self.model = model
        self.temperature = temperature

        # Allow explicit API key or rely on environment ADC
        if api_key:
            os.environ.setdefault("GEMINI_API_KEY", api_key)

        # Try different GenAI client imports
        self._client = None
        try:
            # Newer google.generativeai helper
            import google.generativeai as generativeai
            self._client = ("generativeai", generativeai)
        except Exception:
            try:
                # google.ai.generativelanguage (lower-level client)
                from google.ai import generativelanguage as genai
                self._client = ("genai", genai)
            except Exception:
                self._client = None

        if self._client is None:
            raise GeminiUnavailable("No Google GenAI (Gemini) client found in the environment. Install the official SDK or set up ADC.")

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text from Gemini. Returns the generated text string.

        kwargs are forwarded to the underlying client where supported.
        """
        kind, client = self._client
        if kind == "generativeai":
            # The helper typically exposes a `generate_text` or `responses` API.
            try:
                # Prefer `responses.generate` if available
                if hasattr(client, "responses"):
                    resp = client.responses.generate(model=self.model, input=prompt, temperature=self.temperature, **kwargs)
                    # Attempt to extract text from common response shapes
                    if hasattr(resp, "text"):
                        return resp.text
                    # Some wrappers return a structured object
                    try:
                        return resp.output_text
                    except Exception:
                        return str(resp)
                # Fallback to generate_text
                elif hasattr(client, "generate"):
                    resp = client.generate(model=self.model, prompt=prompt, temperature=self.temperature, **kwargs)
                    return getattr(resp, "output", str(resp))
                else:
                    return str(client)
            except Exception as e:
                raise
        else:
            # genai low-level client
            try:
                # genai may expose a `TextGeneration` or `Text` endpoint
                if hasattr(client, "TextGenerationServiceClient"):
                    svc = client.TextGenerationServiceClient()
                    resp = svc.generate_text(model=self.model, prompt=prompt)
                    # Extract output
                    if hasattr(resp, "candidates") and resp.candidates:
                        return resp.candidates[0].content
                    return str(resp)
                elif hasattr(client, "generate_text"):
                    resp = client.generate_text(model=self.model, prompt=prompt)
                    return getattr(resp, "text", str(resp))
                else:
                    return str(client)
            except Exception:
                raise
