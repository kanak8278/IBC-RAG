from typing import Dict, Any
from dataclasses import dataclass
from .factory import LLMProvider, LLMFactory
from .agent import Agent


@dataclass
class LLMConfig:
    provider: LLMProvider
    model: str
    api_key: str = None
    additional_kwargs: Dict[str, Any] = None

    def create_agent(self, system_prompt: str) -> Agent:
        kwargs = self.additional_kwargs or {}
        return LLMFactory.create_agent(
            provider=self.provider,
            system_prompt=system_prompt,
            api_key=self.api_key,
            model=self.model,
            **kwargs
        )
