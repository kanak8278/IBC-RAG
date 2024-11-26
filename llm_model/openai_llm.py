from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI
from .base import BaseLLM


class OpenAILLM(BaseLLM):
    """OpenAI-specific LLM implementation."""

    def __init__(self, model: str, api_key: str, **kwargs):
        super().__init__(model, api_key, **kwargs)
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        model: str = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate a response using OpenAI's API."""
        # Prepare messages including system prompt
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})

        # Add conversation messages
        formatted_messages.extend(messages)

        # Generate response
        response = await self.client.chat.completions.create(
            model=model or self.model,
            messages=formatted_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return {
            "content": response.choices[0].message.content,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
        }
