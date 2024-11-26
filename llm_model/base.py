from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class BaseLLM(ABC):
    """Base class for Language Model implementations."""

    def __init__(self, model: str, api_key: str, **kwargs):
        """
        Initialize the LLM.

        Args:
            model: The specific model to use (e.g., "gpt-4", "claude-3-opus-20240229")
            api_key: API key for authentication
            **kwargs: Additional model-specific parameters
        """
        self.model = model
        self.api_key = api_key

        self.kwargs = kwargs

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> Dict[str, Any]:
        """
        Generate a response from the language model.

        Args:
            prompt: The user prompt/message
            system_prompt: Optional system prompt to set context
            temperature: Controls randomness in the response
            max_tokens: Maximum tokens in the response
            stream: Whether to stream the response

        Returns:
            Dictionary containing the response and metadata
        """
        pass
