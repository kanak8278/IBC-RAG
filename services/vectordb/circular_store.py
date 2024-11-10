# services/vectordb/circular_store.py

from typing import List, Dict, Optional, Any
from datetime import datetime
from .chroma_store import ChromaVectorStore
from .base import SearchResult, VectorDBConfig
from models.circular import Circular, CircularMetadata, CircularChunk

import logging


class CircularVectorStore(ChromaVectorStore):
    def __init__(self, config: VectorDBConfig, embedding_service):
        super().__init__(config, embedding_service)

    # def add_circular(self, circular: Dict[str, Any]) -> bool:
    #     """
    #     Add a circular document to the vector store
    #     """
    #     try:
    #         # Process circular metadata
    #         metadata = self._process_circular_metadata(circular["metadata"])
    #         # Process chunks
    #         for chunk in circular["merged_chunks"]:
    #             chunk_id = chunk["chunk_id"]

    #             # Generate embedding
    #             embedding = self.embedding_service.generate_single_embedding(
    #                 chunk["content"]
    #             )
    #             if not metadata or not isinstance(metadata, dict):
    #                 raise ValueError(
    #                     "Invalid metadata: must be a non-empty dictionary."
    #                 )

    #             # Check for required fields in metadata
    #             required_fields = [
    #                 "circular_number",
    #                 "effective_date",
    #                 "authority",
    #                 "subject",
    #                 "document_hash",
    #             ]
    #             for field in required_fields:
    #                 if field not in metadata:
    #                     raise KeyError(f"Missing required metadata field: {field}")

    #             # Prepare chunk metadata with circular-specific fields
    #             try:
    #                 circular_number = metadata["circular_number"]
    #                 date = metadata["date"]
    #                 effective_date = metadata["effective_date"]
    #                 authority = metadata["authority"]
    #                 subject = metadata["subject"]
    #                 document_hash = metadata["document_hash"]
    #             except Exception as e:
    #                 print(f"Error processing metadata: {str(e)}")
    #                 print(f"Metadata: {metadata}")
    #                 raise e

    #             try:
    #                 chunk_type = chunk["chunk_type"]
    #                 paragraph_numbers = ",".join(
    #                     map(str, chunk.get("paragraph_numbers", []))
    #                 )
    #                 chunk_context = str(chunk.get("context", {}))
    #                 section_references = ",".join(
    #                     chunk["references"].get("sections", [])
    #                 )
    #                 circular_references = ",".join(
    #                     chunk["references"].get("circulars", [])
    #                 )
    #                 regulation_references = ",".join(
    #                     chunk["references"].get("regulations", [])
    #                 )
    #             except Exception as e:
    #                 print(f"Error processing chunk: {str(e)}")
    #                 raise e

    #             chunk_metadata = {
    #                 "circular_number": circular_number,
    #                 "date": date,
    #                 "effective_date": effective_date,
    #                 "authority": authority,
    #                 "subject": subject,
    #                 # Chunk-specific metadata
    #                 "chunk_type": chunk_type,
    #                 "paragraph_numbers": paragraph_numbers,
    #                 "chunk_context": chunk_context,
    #                 # References
    #                 "section_references": section_references,
    #                 "circular_references": circular_references,
    #                 "regulation_references": regulation_references,
    #                 # Document tracking
    #                 "document_hash": document_hash,
    #                 "processing_timestamp": datetime.now().isoformat(),
    #             }

    #             try:
    #                 self.content_collection.add(
    #                     ids=[chunk_id],
    #                     embeddings=[embedding],
    #                     documents=[chunk["content"]],
    #                     metadatas=chunk_metadata,
    #                 )
    #             except Exception as e:
    #                 print(f"Error adding chunk: {str(e)}")
    #                 print(f"Chunk: {chunk}")
    #                 raise e

    #         return True

    #     except Exception as e:
    #         print(f"Error adding circular: {str(e)}")
    #         raise

    def add_circular(self, circular: Dict[str, Any]) -> bool:
        """
        Add a circular document to the vector store
        """
        try:
            # Process circular metadata
            metadata = self._process_circular_metadata(circular["metadata"])

            # Process chunks
            for idx, chunk in enumerate(circular["merged_chunks"]):
                chunk_id = f'{metadata["document_hash"]}_{idx}'

                # Generate embedding
                embedding = self.embedding_service.generate_single_embedding(
                    chunk["content"]
                )

                # Validate metadata
                if not metadata or not isinstance(metadata, dict):
                    raise ValueError(
                        "Invalid metadata: must be a non-empty dictionary."
                    )

                # Clean and prepare chunk metadata
                def clean_value(value: Any) -> str:
                    """Convert any value to string, handling None"""
                    if value is None:
                        return ""
                    if isinstance(value, (list, dict)):
                        return str(value)
                    return str(value)

                chunk_metadata = {
                    # Circular identification
                    "circular_number": clean_value(metadata.get("circular_number")),
                    "date": clean_value(metadata.get("date")),
                    "effective_date": clean_value(metadata.get("effective_date")),
                    "authority": clean_value(metadata.get("authority")),
                    "subject": clean_value(metadata.get("subject")),
                    # Chunk-specific metadata
                    "chunk_type": clean_value(chunk.get("chunk_type")),
                    "paragraph_numbers": clean_value(
                        ",".join(map(str, chunk.get("paragraph_numbers", [])))
                    ),
                    "chunk_context": clean_value(chunk.get("context", {})),
                    # References
                    "section_references": clean_value(
                        ",".join(chunk["references"].get("sections", []))
                    ),
                    "circular_references": clean_value(
                        ",".join(chunk["references"].get("circulars", []))
                    ),
                    "regulation_references": clean_value(
                        ",".join(chunk["references"].get("regulations", []))
                    ),
                    # Document tracking
                    "document_hash": clean_value(metadata.get("document_hash")),
                    "processing_timestamp": clean_value(datetime.now().isoformat()),
                }

                try:
                    self.content_collection.add(
                        ids=[chunk_id],
                        embeddings=[embedding],
                        documents=[chunk["content"]],
                        metadatas=[chunk_metadata],  # Note: metadatas expects a list
                    )
                except Exception as e:
                    print(f"Error adding chunk: {str(e)}")
                    print(f"Chunk metadata: {chunk_metadata}")
                    raise e

            return True

        except Exception as e:
            print(f"Error adding circular: {str(e)}")
            raise

    def search_circulars(
        self,
        query: str,
        filter_criteria: Optional[Dict[str, Any]] = None,
        date_range: Optional[Dict[str, str]] = None,
        chunk_types: Optional[List[str]] = None,
        limit: int = 5,
    ) -> List[SearchResult]:
        """
        Specialized search for circulars with circular-specific filtering
        """
        # Build circular-specific where clause
        where_clause = {}

        if filter_criteria:
            where_clause.update(filter_criteria)

        if date_range:
            where_clause["date"] = {
                "$gte": date_range.get("start"),
                "$lte": date_range.get("end"),
            }

        if chunk_types:
            where_clause["chunk_type"] = {"$in": chunk_types}

        # Perform search
        results = self.search(
            query=query, filter_criteria=where_clause, limit=limit, include_context=True
        )

        return results

    def _process_circular_metadata(self, metadata: Dict) -> Dict:
        """Process and validate circular metadata"""

        def clean_value(value: Any) -> Any:
            """Convert None to empty string and ensure proper types"""
            if value is None:
                return ""
            if isinstance(value, (int, float, bool)):
                return value
            return str(value)

        processed_metadata = {
            "authority": clean_value(metadata.get("authority", "")),
            "circular_number": clean_value(metadata["circular_number"]),
            "date": clean_value(metadata["date"]),
            "subject": clean_value(metadata["subject"]),
            "total_pages": clean_value(metadata.get("total_pages", "")),
            "reference_circulars": clean_value(
                ",".join(metadata.get("reference_circulars", []))
            ),
            "effective_date": clean_value(metadata.get("effective_date", "")),
            "power_reference": clean_value(metadata.get("power_reference", "")),
            "file_name": clean_value(metadata["file_name"]),
            "document_hash": clean_value(metadata["document_hash"]),
            "processing_timestamp": clean_value(metadata["processing_timestamp"]),
        }

        return processed_metadata

    def get_circular_by_number(self, circular_number: str) -> Optional[List[Dict]]:
        """Retrieve all chunks of a specific circular"""
        try:
            results = self.content_collection.get(
                where={"circular_number": circular_number},
                include=["documents", "metadatas"],
            )
            return self._format_circular_results(results)
        except Exception as e:
            print(f"Error retrieving circular: {str(e)}")
            return None

    def _format_circular_results(self, results: Dict) -> List[Dict]:
        """Format circular results with proper structure"""
        formatted_results = []
        for doc, metadata in zip(results["documents"], results["metadatas"]):
            formatted_results.append(
                {
                    "content": doc,
                    "metadata": metadata,
                    "chunk_type": metadata["chunk_type"],
                    "references": self._parse_references(metadata),
                }
            )
        return formatted_results

    def _parse_references(self, metadata: Dict) -> Dict[str, List[str]]:
        """Parse references from metadata"""
        references = {}
        if metadata.get("section_references"):
            references["sections"] = metadata["section_references"].split(",")
        if metadata.get("circular_references"):
            references["circulars"] = metadata["circular_references"].split(",")
        if metadata.get("regulation_references"):
            references["regulations"] = metadata["regulation_references"].split(",")
        return references
