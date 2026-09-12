"""Gemini embedding client with retry and dimensionality guarantees."""
from __future__ import annotations
import math
import time
from typing import Any, Sequence
from google import genai
from google.genai import errors, types
from services.config import Settings

class EmbeddingError(RuntimeError):
    """Raised when Gemini cannot produce a valid embedding."""

class EmbeddingService:
    """Generate normalized document/query vectors in one embedding space."""
    def __init__(self, settings: Settings | None = None, client: Any | None = None, max_retries: int = 3):
        self.settings = settings or Settings.from_env()
        self.settings.validate(["gemini_api_key"])
        self.client = client or genai.Client(api_key=self.settings.gemini_api_key, vertexai=False)
        self.max_retries = max_retries

    def _embed(self, texts: Sequence[str], task_type: str) -> list[list[float]]:
        values = [str(text).strip() for text in texts]
        if not values or any(not value for value in values):
            raise EmbeddingError("Embedding input must contain non-empty text.")
        for attempt in range(self.max_retries):
            try:
                response = self.client.models.embed_content(
                    model=self.settings.embedding_model, contents=values,
                    config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=self.settings.embedding_dimension),
                )
                vectors = [self._normalize(list(item.values)) for item in (getattr(response, "embeddings", None) or [])]
                if len(vectors) != len(values) or any(len(vector) != self.settings.embedding_dimension for vector in vectors):
                    raise EmbeddingError("Gemini returned an unexpected embedding count or dimension.")
                return vectors
            except EmbeddingError:
                raise
            except errors.APIError as exc:
                if getattr(exc, "code", None) not in {408, 429, 500, 502, 503, 504} or attempt + 1 >= self.max_retries:
                    raise EmbeddingError("Gemini embedding request failed.") from exc
                time.sleep(2**attempt)
            except Exception as exc:
                if attempt + 1 >= self.max_retries:
                    raise EmbeddingError("Gemini embedding request failed.") from exc
                time.sleep(2**attempt)
        raise EmbeddingError("Gemini embedding request failed.")

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(value * value for value in vector))
        if not norm:
            raise EmbeddingError("Gemini returned a zero-length embedding vector.")
        return [value / norm for value in vector]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed(texts, "RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "RETRIEVAL_QUERY")[0]
