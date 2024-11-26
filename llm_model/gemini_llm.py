from typing import Optional, Dict, Any, List
import google.generativeai as genai
from .base import BaseLLM


class GeminiLLM(BaseLLM):
    """Google Gemini-specific LLM implementation."""

    def __init__(self, model: str, api_key: str, **kwargs):
        super().__init__(model, api_key, **kwargs)
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model_name=model)

    async def generate(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        model: str = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        # Combine system prompt and messages into Gemini's format
        combined_prompt = ""
        if system_prompt:
            combined_prompt += f"{system_prompt}\n\n"

        for message in messages:
            role = message["role"]
            content = message["content"]
            # Format based on role
            if role == "user":
                combined_prompt += f"User: {content}\n"
            elif role == "assistant":
                combined_prompt += f"Assistant: {content}\n"

        # Generate response
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens if max_tokens else 2048,
        }

        response = await self.client.generate_content_async(
            combined_prompt, generation_config=generation_config
        )

        # Extract the response text
        response_text = response.text

        # Construct response in the expected format
        return {"content": response_text, "model": model or self.model, "usage": None}
