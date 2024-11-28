import os
import json
import chromadb
import hashlib
from openai import AzureOpenAI
from dotenv import load_dotenv
from typing import List, Dict, Optional, Union
from chunking_act import chunk_markdown_document, add_context_overlap

load_dotenv()

AZURE_API_KEY = os.getenv("AZURE_API_KEY")
AZURE_API_BASE = os.getenv("AZURE_API_BASE")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION")
AZURE_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_EMBEDDING_DEPLOYMENT")


class DocumentVectorizer:
    def __init__(self, collection_name="markdown_docs", persist_directory="./chromadb"):
        """Initialize ChromaDB and Azure OpenAI client"""
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(path=persist_directory)

        # Initialize Azure OpenAI client
        self.azure_client = AzureOpenAI(
            api_key=AZURE_API_KEY,
            api_version=AZURE_API_VERSION,
            azure_endpoint=AZURE_API_BASE,
        )

        # Create custom embedding function for Azure OpenAI
        self.embedding_fn = self.create_azure_embedding_function()

        # Create or get collection
        self.collection = self.client.create_collection(
            name=collection_name, embedding_function=self.embedding_fn
        )

    def create_azure_embedding_function(self):
        """Create a custom embedding function for Azure OpenAI"""

        class AzureEmbeddingFunction:
            def __init__(self, azure_client):
                self.azure_client = azure_client

            def __call__(self, input: Union[str, list[str]]) -> list[list[float]]:
                # Handle single string input by converting to list
                if isinstance(input, str):
                    input = [input]

                embeddings = []
                for text in input:
                    response = self.azure_client.embeddings.create(
                        model=AZURE_EMBEDDING_DEPLOYMENT, input=text
                    )
                    embeddings.append(response.data[0].embedding)
                return embeddings

        return AzureEmbeddingFunction(self.azure_client)

    def generate_chunk_id(self, chunk, index=0):
        """Generate unique ID for chunk based on content, metadata, and position"""
        content = {
            "content": chunk["content"],
            "metadata": chunk.get("metadata", {}),
            "sections": chunk.get("sections", []),
            # Add position information to ensure uniqueness
            "position": index,
            # Add additional context information if available
            "previous_context": chunk.get("previous_context", ""),
            "next_context": chunk.get("next_context", ""),
        }
        return hashlib.md5(json.dumps(content, sort_keys=True).encode()).hexdigest()

    def prepare_chunk_metadata(self, chunk):
        """Prepare metadata for the chunk"""
        # Combine chunk-specific metadata with section information
        metadata = {
            "section_path": " > ".join([s["title"] for s in chunk["sections"]]),
            "section_levels": ",".join(
                str(s["level"]) for s in chunk["sections"]
            ),  # Convert list to string
            "has_previous_context": bool(chunk.get("previous_context")),
            "has_next_context": bool(chunk.get("next_context")),
            "chunk_type": "content",
        }

        # Add all metadata from the chunk's metadata field
        if "metadata" in chunk:
            # Ensure all metadata values are of supported types
            chunk_metadata = {
                k: str(v) if not isinstance(v, (bool, int, float, str)) else v
                for k, v in chunk["metadata"].items()
                if v is not None
            }
            metadata.update(
                {
                    "chunk_number": chunk_metadata.get("chunk_number"),
                    "total_chunks": chunk_metadata.get("total_chunks"),
                    "start_section": chunk_metadata.get("start_section"),
                    "end_section": chunk_metadata.get("end_section"),
                }
            )

        # Remove None values
        metadata = {k: v for k, v in metadata.items() if v is not None}

        return metadata

    def prepare_chunk_text(self, chunk):
        """Prepare text representation of chunk for embedding"""
        text_parts = []

        # Add previous context if available
        if chunk.get("previous_context"):
            text_parts.append(f"{chunk['previous_context']}")

        # Add main content
        text_parts.append(f"{chunk['content']}")

        # Add next context if available
        if chunk.get("next_context"):
            text_parts.append(f"{chunk['next_context']}")

        return "\n\n".join(text_parts)

    def add_chunks_to_db(self, chunks):
        """Add chunks to ChromaDB"""
        ids = []
        documents = []
        metadatas = []

        # Keep track of generated IDs to ensure uniqueness
        seen_ids = set()

        for index, chunk in enumerate(chunks):
            chunk_id = self.generate_chunk_id(chunk, index)

            # If we somehow still get a duplicate ID, append a unique suffix
            while chunk_id in seen_ids:
                chunk_id = f"{chunk_id}_{index}"

            seen_ids.add(chunk_id)
            chunk_text = self.prepare_chunk_text(chunk)
            chunk_metadata = self.prepare_chunk_metadata(chunk)

            ids.append(chunk_id)
            documents.append(chunk_text)
            metadatas.append(chunk_metadata)

        # Batch add to ChromaDB
        if ids:
            try:
                self.collection.add(ids=ids, documents=documents, metadatas=metadatas)
            except Exception as e:
                print(f"Error adding chunks to database: {str(e)}")
                # Optionally, you might want to add logging here
                raise

    def check_and_add_chunks(self, chunks):
        """Check for existing chunks and only add new ones"""
        existing_ids = (
            set(self.collection.get()["ids"]) if self.collection.count() > 0 else set()
        )

        new_chunks = []
        for chunk in chunks:
            chunk_id = self.generate_chunk_id(chunk)
            if chunk_id not in existing_ids:
                new_chunks.append(chunk)

        if new_chunks:
            self.add_chunks_to_db(new_chunks)
        return len(new_chunks)


class DocumentRetriever:
    def __init__(self, persist_directory="./chromadb", collection_name="markdown_docs"):
        """Initialize retriever with ChromaDB connection"""
        self.azure_client = AzureOpenAI(
            api_key=AZURE_API_KEY,
            api_version=AZURE_API_VERSION,
            azure_endpoint=AZURE_API_BASE,
        )
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.embedding_fn = self.create_azure_embedding_function()
        # Get collection with the same embedding function
        self.collection = self.client.get_collection(
            name=collection_name, embedding_function=self.embedding_fn
        )

    def create_azure_embedding_function(self):
        """Create a custom embedding function for Azure OpenAI"""

        class AzureEmbeddingFunction:
            def __init__(self, azure_client):
                self.azure_client = azure_client

            def __call__(self, input: Union[str, list[str]]) -> list[list[float]]:
                # Handle single string input by converting to list
                if isinstance(input, str):
                    input = [input]

                embeddings = []
                for text in input:
                    response = self.azure_client.embeddings.create(
                        model=AZURE_EMBEDDING_DEPLOYMENT, input=text
                    )
                    embeddings.append(response.data[0].embedding)
                return embeddings

        return AzureEmbeddingFunction(self.azure_client)

    def retrieve_chunks(
        self,
        query: str,
        k: int = 3,
        include_adjacent: bool = False,
        min_relevance_score: float = 0.0,
        metadata_filters: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Retrieve most relevant chunks for a given query.

        Args:
            query: Search query text
            k: Number of chunks to retrieve
            include_adjacent: Whether to include previous and next chunks
            min_relevance_score: Minimum relevance score (0 to 1) for chunks
            metadata_filters: Optional filters for metadata fields

        Returns:
            List of dictionaries containing chunks and their metadata
        """
        # Query ChromaDB
        results = self.collection.query(
            query_texts=[query],
            n_results=k,
            where=metadata_filters,
            include=["metadatas", "documents", "distances"],
        )

        # Process results
        processed_results = []

        for idx, (doc, metadata, distance) in enumerate(
            zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ):
            # Convert distance to similarity score (0 to 1)
            relevance_score = 1 - (distance / 2)  # Assuming distance is normalized

            # Skip if below minimum relevance score
            if relevance_score < min_relevance_score:
                continue

            chunk_result = {
                "content": doc,
                "metadata": metadata,
                "relevance_score": relevance_score,
            }

            # Get adjacent chunks if requested
            if include_adjacent:
                adjacent_chunks = self._get_adjacent_chunks(metadata)
                chunk_result.update(adjacent_chunks)

            processed_results.append(chunk_result)

        return processed_results

    def _get_adjacent_chunks(self, chunk_metadata: Dict) -> Dict:
        """
        Retrieve adjacent chunks based on chunk number.

        Args:
            chunk_metadata: Metadata of the current chunk

        Returns:
            Dictionary containing previous and next chunks
        """
        adjacent_chunks = {"previous_chunk": None, "next_chunk": None}

        chunk_number = chunk_metadata.get("chunk_number")
        total_chunks = chunk_metadata.get("total_chunks")

        if not (chunk_number and total_chunks):
            return adjacent_chunks

        # Get previous chunk
        if chunk_number > 1:
            prev_results = self.collection.query(
                query_texts=[""],  # Empty query for exact match
                n_results=1,
                where={"chunk_number": chunk_number - 1},
            )
            if prev_results["documents"][0]:
                adjacent_chunks["previous_chunk"] = {
                    "content": prev_results["documents"][0][0],
                    "metadata": prev_results["metadatas"][0][0],
                }

        # Get next chunk
        if chunk_number < total_chunks:
            next_results = self.collection.query(
                query_texts=[""],  # Empty query for exact match
                n_results=1,
                where={"chunk_number": chunk_number + 1},
            )
            if next_results["documents"][0]:
                adjacent_chunks["next_chunk"] = {
                    "content": next_results["documents"][0][0],
                    "metadata": next_results["metadatas"][0][0],
                }

        return adjacent_chunks

    def search_by_metadata(
        self, metadata_filters: Dict, k: int = 3, include_adjacent: bool = False
    ) -> List[Dict]:
        """
        Search chunks by metadata filters.

        Args:
            metadata_filters: Filters for metadata fields
            k: Number of chunks to retrieve
            include_adjacent: Whether to include previous and next chunks

        Returns:
            List of matching chunks
        """
        results = self.collection.query(
            query_texts=[""],  # Empty query for metadata-only search
            n_results=k,
            where=metadata_filters,
            include=["metadatas", "documents"],
        )

        processed_results = []

        for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
            chunk_result = {"content": doc, "metadata": metadata}

            if include_adjacent:
                adjacent_chunks = self._get_adjacent_chunks(metadata)
                chunk_result.update(adjacent_chunks)

            processed_results.append(chunk_result)

        return processed_results


def vectorize_act(act_file):
    with open(act_file, "r") as file:
        text = file.read()
    chunks = chunk_markdown_document(text, 1000)
    chunks = add_context_overlap(chunks, 100)

    # save chunks on the same path as act_file
    with open(act_file.replace(".md", "_chunks.json"), "w") as file:
        json.dump(chunks, file)

    vectorizer = DocumentVectorizer(
        collection_name="act_db", persist_directory="./storage/act_db"
    )
    vectorizer.check_and_add_chunks(chunks)


def retrieve_content(query):
    retriever = DocumentRetriever(
        persist_directory="./storage/act_db", collection_name="act_db"
    )
    return retriever.retrieve_chunks(query)


if __name__ == "__main__":
    act_file = "data/ibbi_raw/IBC ACT-2021-indiacode.md"
    vectorize_act(act_file)

    while True:
        query = input("Enter a query: ")
        print(json.dumps(retrieve_content(query), indent=4))
