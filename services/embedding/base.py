# services/embedding/base.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import numpy as np


@dataclass
class EmbeddingMetadata:
    """Metadata for embedding generation"""

    model_name: str
    dimension: int
    additional_info: Optional[Dict[str, Any]] = None


class BaseEmbeddingService(ABC):
    """
    Abstract base class for embedding services.
    All embedding implementations must inherit from this class.
    """

    def __init__(self):
        self._model_metadata: Optional[EmbeddingMetadata] = None

    @property
    @abstractmethod
    def embedding_dimension(self) -> int:
        """Return the dimension of the embeddings"""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the name of the embedding model"""
        pass

    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts (List[str]): List of texts to generate embeddings for

        Returns:
            List[List[float]]: List of embedding vectors

        Raises:
            EmbeddingError: If embedding generation fails
        """
        pass

    @abstractmethod
    def generate_single_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text (str): Text to generate embedding for

        Returns:
            List[float]: Embedding vector

        Raises:
            EmbeddingError: If embedding generation fails
        """
        pass

    @abstractmethod
    def validate_embedding(self, embedding: List[float]) -> bool:
        """
        Validate if an embedding vector is valid.

        Args:
            embedding (List[float]): Embedding vector to validate

        Returns:
            bool: True if valid, False otherwise
        """
        pass

    def get_metadata(self) -> EmbeddingMetadata:
        """Get metadata about the embedding service"""
        if not self._model_metadata:
            self._model_metadata = EmbeddingMetadata(
                model_name=self.model_name, dimension=self.embedding_dimension
            )
        return self._model_metadata

    def normalize_embedding(self, embedding: List[float]) -> List[float]:
        """
        Normalize embedding vector to unit length.

        Args:
            embedding (List[float]): Embedding vector to normalize

        Returns:
            List[float]: Normalized embedding vector
        """
        norm = np.linalg.norm(embedding)
        if norm == 0:
            return embedding
        return (np.array(embedding) / norm).tolist()

    def batch_processor(
        self, texts: List[str], batch_size: int = 16
    ) -> List[List[float]]:
        """
        Process texts in batches to generate embeddings.

        Args:
            texts (List[str]): List of texts to process
            batch_size (int): Size of each batch

        Returns:
            List[List[float]]: List of embedding vectors
        """
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_embeddings = self.generate_embeddings(batch)
            all_embeddings.extend(batch_embeddings)
        return all_embeddings

    def validate_input(self, text: str) -> str:
        """
        Validate and preprocess input text.

        Args:
            text (str): Input text to validate

        Returns:
            str: Preprocessed text

        Raises:
            ValueError: If input is invalid
        """
        if not isinstance(text, str):
            raise ValueError("Input must be a string")
        if not text.strip():
            raise ValueError("Input text cannot be empty")
        return text.strip()


class EmbeddingError(Exception):
    """Custom exception for embedding-related errors"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.details = details or {}


class EmbeddingConfig:
    """Configuration class for embedding services"""

    def __init__(
        self,
        model_name: str,
        dimension: int,
        batch_size: int = 16,
        max_retries: int = 3,
        timeout: int = 30,
        **kwargs
    ):
        self.model_name = model_name
        self.dimension = dimension
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.timeout = timeout
        self.additional_config = kwargs

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "model_name": self.model_name,
            "dimension": self.dimension,
            "batch_size": self.batch_size,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            **self.additional_config,
        }
