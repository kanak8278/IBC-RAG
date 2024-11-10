# services/vectordb/chroma_store.py

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional, Any
from datetime import datetime
import json

from .base import BaseVectorStore, SearchResult, VectorDBConfig
from ..embedding.base import BaseEmbeddingService
import traceback


class ChromaVectorStore(BaseVectorStore):
    def __init__(self, config: VectorDBConfig, embedding_service: BaseEmbeddingService):
        super().__init__(config)
        self.embedding_service = embedding_service

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=config.persist_directory,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

        # Initialize collections
        self._initialize_collections()

    def _initialize_collections(self):
        """Initialize all required collections"""
        # Main content collection
        self.content_collection = self.client.get_or_create_collection(
            name=f"{self.config.collection_name}_content",
            metadata={
                "description": "Legal document contents with embeddings",
                "embedding_model": self.embedding_service.model_name,
                "embedding_dimension": self.embedding_service.embedding_dimension,
            },
        )

        # Metadata collection for quick filtering
        self.metadata_collection = self.client.get_or_create_collection(
            name=f"{self.config.collection_name}_metadata"
        )

    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: Optional[List[List[float]]] = None,
    ) -> bool:
        try:
            for doc in documents:
                self.add_single_document(doc)
            return True
        except Exception as e:
            print(f"Error adding documents: {str(e)}")
            return False

    def add_single_document(
        self, document: Dict[str, Any], embedding: Optional[List[float]] = None
    ) -> bool:
        try:
            # Process document metadata
            metadata = self._process_metadata(document["metadata"])

            # Process chunks
            for chunk in document["merged_chunks"]:
                chunk_id = chunk["chunk_id"]

                # Generate embedding if not provided
                if not embedding:
                    embedding = self.embedding_service.generate_single_embedding(
                        chunk["content"]
                    )

                # Prepare chunk metadata
                chunk_metadata = {
                    **metadata,
                    "chunk_type": chunk["chunk_type"],
                    "paragraph_numbers": json.dumps(chunk["paragraph_numbers"]),
                    "processing_timestamp": datetime.now().isoformat(),
                }

                # Add to content collection
                self.content_collection.add(
                    ids=[chunk_id],
                    embeddings=[embedding] if embedding else None,
                    documents=[chunk["content"]],
                    metadatas=[chunk_metadata],
                )

            return True
        except Exception as e:
            print(f"Error adding document: {str(e)}")
            return False

    # def search(
    #     self,
    #     query: str,
    #     filter_criteria: Optional[Dict[str, Any]] = None,
    #     time_range: Optional[Dict[str, datetime]] = None,
    #     limit: int = 5,
    #     include_context: bool = True,
    # ) -> List[SearchResult]:
    #     try:
    #         # Build where clause for filtering
    #         where_clause = self._build_where_clause(filter_criteria, time_range)

    #         # Generate query embedding
    #         query_embedding = self.embedding_service.generate_single_embedding(query)

    #         # Perform search
    #         results = self.content_collection.query(
    #             query_embeddings=[query_embedding], n_results=limit, where=where_clause
    #         )

    #         # Process results
    #         search_results = []
    #         for i, (doc, metadata, distance) in enumerate(
    #             zip(
    #                 results["documents"][0],
    #                 results["metadatas"][0],
    #                 results["distances"][0],
    #             )
    #         ):
    #             # Get context chunks if required
    #             context_chunks = None
    #             if include_context:
    #                 context_chunks = self._get_context_chunks(
    #                     chunk_id=results["ids"][0][i], metadata=metadata
    #                 )

    #             search_results.append(
    #                 SearchResult(
    #                     content=doc,
    #                     metadata=metadata,
    #                     score=1 - distance,  # Convert distance to similarity score
    #                     chunk_id=results["ids"][0][i],
    #                     context_chunks=context_chunks,
    #                 )
    #             )

    #         return search_results
    #     except Exception as e:
    #         print(f"Error during search: {str(e)}")
    #         print(traceback.format_exc())
    #         return []

    def search(
        self,
        query: str,
        filter_criteria: Optional[Dict[str, Any]] = None,
        time_range: Optional[Dict[str, datetime]] = None,
        limit: int = 5,
        include_context: bool = True,
    ) -> List[SearchResult]:
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.generate_single_embedding(query)

            # Build where clause for filtering
            where_clause = self._build_where_clause(filter_criteria, time_range)

            # Perform search
            query_params = {"query_embeddings": [query_embedding], "n_results": limit}

            # Only add where clause if there are actual filters
            if where_clause:
                query_params["where"] = where_clause

            # print(f"Query params: {query_params['where']}")
            # Execute search
            results = self.content_collection.query(**query_params)
            

            # Process results
            search_results = []
            if results["ids"][0]:  # Check if we have any results
                for i, (doc, metadata, distance) in enumerate(
                    zip(
                        results["documents"][0],
                        results["metadatas"][0],
                        results["distances"][0],
                    )
                ):
                    # Get context chunks if required
                    context_chunks = None
                    if include_context:
                        context_chunks = self._get_context_chunks(
                            chunk_id=results["ids"][0][i], metadata=metadata
                        )

                    search_results.append(
                        SearchResult(
                            content=doc,
                            metadata=metadata,
                            score=1 - distance,  # Convert distance to similarity score
                            chunk_id=results["ids"][0][i],
                            context_chunks=context_chunks,
                        )
                    )

            return search_results
        except Exception as e:
            print(f"Error during search: {str(e)}")
            print(traceback.format_exc())
            return []

    # def _build_where_clause(
    #     self,
    #     filter_criteria: Optional[Dict[str, Any]],
    #     time_range: Optional[Dict[str, datetime]],
    # ) -> Dict[str, Any]:
    #     where_clause = {}

    #     if filter_criteria:
    #         where_clause.update(filter_criteria)

    #     if time_range:
    #         where_clause.update(
    #             {
    #                 "processing_timestamp": {
    #                     "$gte": time_range.get("start").isoformat(),
    #                     "$lte": time_range.get("end").isoformat(),
    #                 }
    #             }
    #         )

    #     return where_clause

    def _build_where_clause(
        self,
        filter_criteria: Optional[Dict[str, Any]],
        time_range: Optional[Dict[str, datetime]],
    ) -> Optional[Dict[str, Any]]:
        where_clause = {}

        if filter_criteria:
            where_clause.update(filter_criteria)

        if time_range:
            where_clause.update(
                {
                    "processing_timestamp": {
                        "$gte": time_range.get("start").isoformat(),
                        "$lte": time_range.get("end").isoformat(),
                    }
                }
            )

        # Return None if no filters are applied
        return where_clause if where_clause else None

    def _get_context_chunks(
        self, chunk_id: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get context chunks for a given chunk"""
        context = {}

        # Get previous and next chunks if they exist
        prev_id = metadata.get("previous_chunk_id")
        next_id = metadata.get("next_chunk_id")

        if prev_id:
            prev_result = self.content_collection.get(
                ids=[prev_id], include=["documents", "metadatas"]
            )
            if prev_result["documents"]:
                context["previous"] = {
                    "content": prev_result["documents"][0],
                    "metadata": prev_result["metadatas"][0],
                }

        if next_id:
            next_result = self.content_collection.get(
                ids=[next_id], include=["documents", "metadatas"]
            )
            if next_result["documents"]:
                context["next"] = {
                    "content": next_result["documents"][0],
                    "metadata": next_result["metadatas"][0],
                }

        return context

    # Implement other required methods...
    def delete_documents(self, document_ids: List[str]) -> bool:
        try:
            self.content_collection.delete(ids=document_ids)
            return True
        except Exception as e:
            print(f"Error deleting documents: {str(e)}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_documents": self.content_collection.count(),
            "collections": {
                "content": self.content_collection.count(),
                "metadata": self.metadata_collection.count(),
            },
        }

    def clear(self) -> bool:
        """Clear all documents from the store"""
        try:
            self.content_collection.delete(where={})
            self.metadata_collection.delete(where={})
            return True
        except Exception as e:
            print(f"Error clearing collections: {str(e)}")
            return False

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific document"""
        try:
            result = self.content_collection.get(
                ids=[document_id], include=["documents", "metadatas", "embeddings"]
            )

            if not result["documents"]:
                return None

            return {
                "content": result["documents"][0],
                "metadata": result["metadatas"][0],
                "embedding": (
                    result["embeddings"][0] if result.get("embeddings") else None
                ),
            }
        except Exception as e:
            print(f"Error retrieving document: {str(e)}")
            return None

    def get_nearest_neighbors(self, document_id: str, k: int = 5) -> List[SearchResult]:
        """Find nearest neighbors for a document"""
        try:
            # Get the document's embedding
            doc = self.get_document(document_id)
            if not doc or not doc.get("embedding"):
                return []

            # Search using the document's embedding
            results = self.content_collection.query(
                query_embeddings=[doc["embedding"]],
                n_results=k + 1,
            )

            # Process results
            search_results = []
            for i, (doc, metadata, distance) in enumerate(
                zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                )
            ):
                search_results.append(
                    SearchResult(
                        content=doc,
                        metadata=metadata,
                        score=1 - distance,
                        chunk_id=results["ids"][0][i],
                    )
                )

            return search_results
        except Exception as e:
            print(f"Error finding nearest neighbors: {str(e)}")
            return []

    def update_document(
        self,
        document_id: str,
        new_content: Dict[str, Any],
        new_embedding: Optional[List[float]] = None,
    ) -> bool:
        """Update an existing document"""
        try:
            # Check if document exists
            existing_doc = self.get_document(document_id)
            if not existing_doc:
                return False

            # Generate new embedding if not provided
            if not new_embedding and new_content.get("content"):
                new_embedding = self.embedding_service.generate_single_embedding(
                    new_content["content"]
                )

            # Update the document
            self.content_collection.update(
                ids=[document_id],
                embeddings=[new_embedding] if new_embedding else None,
                documents=(
                    [new_content.get("content")] if new_content.get("content") else None
                ),
                metadatas=(
                    [new_content.get("metadata")]
                    if new_content.get("metadata")
                    else None
                ),
            )

            return True
        except Exception as e:
            print(f"Error updating document: {str(e)}")
            return False
