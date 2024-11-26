from typing import List, Dict, Any, Optional, Union
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import logging
from .base import BaseLLM


class Agent:
    """Agent class that can work with different LLM implementations."""

    def __init__(
        self,
        llm: BaseLLM,
        system_prompt: str,
    ):
        """
        Initialize the Agent.

        Args:
            llm: An instance of a BaseLLM implementation (OpenAILLM or AnthropicLLM)
            system_prompt: The system prompt to use for all conversations
        """
        self.llm = llm
        self.system_prompt = system_prompt
        self.conversation_history: List[Dict[str, Any]] = []

    def _add_to_history(self, role: str, content: Any):
        """Add a message to the conversation history."""
        self.conversation_history.append({"role": role, "content": content})

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(
            TimeoutError
        ),  # You might want to be more specific about exceptions
    )
    async def generate(
        self,
        prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        add_history: bool = True,
        max_tokens: Optional[int] = None,
        temperature: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Generate a response using the LLM.

        Args:
            prompt: The user prompt
            tools: Optional list of tools available to the LLM
            add_history: Whether to add the interaction to conversation history
            max_tokens: Maximum tokens in the response
            temperature: Controls randomness in the response

        Returns:
            Dictionary containing the response and metadata
        """
        messages = self.conversation_history.copy()
        try:
            messages = self.conversation_history.copy()
            if prompt:
                messages.append({"role": "user", "content": prompt})
                if add_history:
                    self._add_to_history("user", prompt)

            if tools:
                raise "Tools feature is not yet implemented in the Agent"
            else:
                response = await self.llm.generate(
                    system_prompt=self.system_prompt,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

            # Log token usage if available
            if "usage" in response:
                logging.info(f"Token usage: {response['usage']}")

            result = {
                "content": response["content"],
                "model": response.get("model"),
                "tool_use": None,
            }

            if add_history:
                self._add_to_history("assistant", result["content"])
            return result

        except Exception as e:
            logging.error(f"Error in generate: {str(e)}")
            raise
