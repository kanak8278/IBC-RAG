from typing import Optional, Dict, Any, AsyncGenerator, List
from anthropic import AsyncAnthropic
from .base import BaseLLM


class AnthropicLLM(BaseLLM):
    """Anthropic-specific LLM implementation."""

    def __init__(self, model: str, api_key: str, **kwargs):
        super().__init__(model, api_key, **kwargs)
        self.client = AsyncAnthropic(api_key=api_key)

    async def generate(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        model: str = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        if not system_prompt:
            system_prompt = ""

        if model == None:
            model = self.model
        response = await self.client.messages.create(
            model=model,
            system=system_prompt,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return {
            "content": response.content[0].text,
            "model": response.model,
            "usage": response.usage,
        }
