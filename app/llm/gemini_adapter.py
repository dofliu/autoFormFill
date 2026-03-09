import json
from collections.abc import AsyncIterator

from google import genai
from google.genai import types

from app.config import settings
from app.llm.base import LLMAdapter
from app.llm.retry import with_retry


class GeminiAdapter(LLMAdapter):
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model
        self.embed_model = settings.gemini_embedding_model

    @with_retry()
    async def generate_text(self, prompt: str, **kwargs) -> str:
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=kwargs.get("temperature", 0.3),
                max_output_tokens=kwargs.get("max_tokens", 2048),
            ),
        )
        return response.text

    async def generate_text_stream(
        self, prompt: str, **kwargs
    ) -> AsyncIterator[str]:
        """Stream text response from Gemini, yielding chunks as they arrive."""
        async for chunk in await self.client.aio.models.generate_content_stream(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=kwargs.get("temperature", 0.3),
                max_output_tokens=kwargs.get("max_tokens", 2048),
            ),
        ):
            if chunk.text:
                yield chunk.text

    @with_retry()
    async def generate_json(
        self, prompt: str, schema: dict | None = None
    ) -> dict | list:
        config = types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
        )
        if schema:
            config.response_schema = schema
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        return json.loads(response.text)

    def embed_text(self, text: str) -> list[float]:
        response = self.client.models.embed_content(
            model=self.embed_model,
            contents=text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        return list(response.embeddings[0].values)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = self.client.models.embed_content(
            model=self.embed_model,
            contents=texts,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        return [list(e.values) for e in response.embeddings]
