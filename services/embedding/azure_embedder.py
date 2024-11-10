# services/embedding/azure_embedder.py

from .base import BaseEmbeddingService, EmbeddingError
from config import AzureConfig
from openai import AzureOpenAI
from typing import List
import time
import logging


class AzureEmbeddingService(BaseEmbeddingService):
    def __init__(self, config: AzureConfig):
        super().__init__()
        self.config = config
        print(config)
        self.client = AzureOpenAI(
            api_key=config.api_key,
            api_version=config.api_version,
            azure_endpoint=config.api_base,
        )

        logging.info(f"Using endpoint: {config.embedding_deployment}")
        logging.info(f"Using model: {config.embedding_deployment}")
        logging.info(f"Using model: {config.embedding_model}")
        self._model_name = config.embedding_model
        self._dimension = config.dimension

    @property
    def embedding_dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        try:
            # Implement retry logic
            for attempt in range(self.config.max_retries):
                try:
                    response = self.client.embeddings.create(
                        model=self.model_name, input=texts
                    )
                    return [item.embedding for item in response.data]
                except Exception as e:
                    logging.error(f"Error generating embeddings: {str(e)}")
                    if attempt == self.config.max_retries - 1:
                        raise e
                    time.sleep(2**attempt)
        except Exception as e:
            raise EmbeddingError(
                f"Failed to generate embeddings: {str(e)}",
                {"model": self.model_name, "texts_count": len(texts)},
            )

    def generate_single_embedding(self, text: str) -> List[float]:
        text = self.validate_input(text)
        return self.generate_embeddings([text])[0]

    def validate_embedding(self, embedding: List[float]) -> bool:
        if len(embedding) != self.embedding_dimension:
            return False
        return all(isinstance(x, (int, float)) for x in embedding)
