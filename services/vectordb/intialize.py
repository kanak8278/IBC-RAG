# vectordb/initialize.py
import chromadb
from chromadb.config import Settings
from typing import Dict, List
from config.config import VectorDBConfig
from services.embedding.azure_embedder import AzureEmbeddingService


class LegalVectorDB:
    def __init__(self, config: VectorDBConfig):
        self.config = config
        self.embedding_service = AzureEmbeddingService(config.azure)

        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=config.chroma.persist_directory,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

        # Initialize collections
        self._initialize_collections()

    def _initialize_collections(self):
        """Initialize all required collections"""
        # Main content collection
        self.content_collection = self.chroma_client.get_or_create_collection(
            name=f"{self.config.chroma.collection_name}_content",
            metadata={"description": "Legal document contents with embeddings"},
            embedding_function=self.embedding_service.generate_embeddings,
        )

        # Metadata collection
        self.metadata_collection = self.chroma_client.get_or_create_collection(
            name=f"{self.config.chroma.collection_name}_metadata",
            metadata={"description": "Document metadata index"},
        )

        # Reference collection
        self.reference_collection = self.chroma_client.get_or_create_collection(
            name=f"{self.config.chroma.collection_name}_references",
            metadata={"description": "Citation and reference mapping"},
        )

    def reset_collections(self):
        """Reset all collections - useful during development"""
        self.chroma_client.reset()
        self._initialize_collections()
