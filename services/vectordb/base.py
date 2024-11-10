# services/vectordb/base.py

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass


@dataclass
class SearchResult:
    """Standardized search result format"""

    content: str
    metadata: Dict[str, Any]
    score: float
    chunk_id: str
    context_chunks: Optional[Dict[str, Any]] = None


@dataclass
class VectorDBConfig:
    persist_directory: str
    collection_name: str
    distance_metric: str = "cosine"
    additional_config: Optional[Dict[str, Any]] = None


class BaseVectorStore(ABC):
    """
    Abstract base class for vector store implementations.
    Defines the interface that all vector stores must implement.
    """

    def __init__(self, config: VectorDBConfig):
        self.config = config

    @abstractmethod
    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: Optional[List[List[float]]] = None,
    ) -> bool:
        """
        Add multiple documents to the vector store.

        Args:
            documents: List of document dictionaries
            embeddings: Optional pre-computed embeddings
        """
        pass

    @abstractmethod
    def add_single_document(
        self, document: Dict[str, Any], embedding: Optional[List[float]] = None
    ) -> bool:
        """Add a single document to the vector store"""
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        filter_criteria: Optional[Dict[str, Any]] = None,
        time_range: Optional[Dict[str, datetime]] = None,
        limit: int = 5,
        include_context: bool = True,
    ) -> List[SearchResult]:
        """
        Search for documents in the vector store.

        Args:
            query: Search query
            filter_criteria: Metadata filters
            time_range: Time-based filters
            limit: Maximum number of results
            include_context: Whether to include context chunks
        """
        pass

    @abstractmethod
    def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents from the vector store"""
        pass

    @abstractmethod
    def update_document(
        self,
        document_id: str,
        new_content: Dict[str, Any],
        new_embedding: Optional[List[float]] = None,
    ) -> bool:
        """Update an existing document"""
        pass

    @abstractmethod
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific document"""
        pass

    @abstractmethod
    def get_nearest_neighbors(self, document_id: str, k: int = 5) -> List[SearchResult]:
        """Find nearest neighbors for a document"""
        pass

    @abstractmethod
    def clear(self) -> bool:
        """Clear all documents from the store"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store"""
        pass
