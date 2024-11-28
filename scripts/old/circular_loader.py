import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import logging
from dotenv import load_dotenv
from tqdm import tqdm
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AzureConfig, ChromaConfig, VectorDBConfig
from services.embedding import AzureEmbeddingService
from services.vectordb import CircularVectorStore

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CircularLoader:
    def __init__(self, data_dir: str, config: VectorDBConfig):
        self.data_dir = Path(data_dir)
        self.config = config

        # Initialize services
        self.embedding_service = AzureEmbeddingService(self.config.azure)
        self.vector_store = CircularVectorStore(
            self.config.chroma, self.embedding_service
        )

    def load_json_files(self) -> List[Dict[str, Any]]:
        """Load all JSON files from the data directory"""
        json_files = list(self.data_dir.glob("**/*.json"))
        circulars = []

        logger.info(f"Found {len(json_files)} JSON files")

        for json_file in tqdm(json_files, desc="Loading JSON files"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    circular = json.load(f)
                circulars.append(circular)
            except Exception as e:
                logger.error(f"Error loading {json_file}: {str(e)}")

        return circulars

    def process_circulars(self, circulars: List[Dict[str, Any]]):
        """Process and store circulars in vector database"""
        logger.info("Starting to process circulars")

        for circular in tqdm(circulars, desc="Processing circulars"):
            try:
                # Add circular to vector store
                logger.info(
                    f"Adding circular: {circular['metadata']['circular_number']}"
                )
                success = self.vector_store.add_circular(circular)

                if not success:
                    logger.error(
                        f"Failed to add circular: {circular['metadata']['circular_number']}"
                    )

            except Exception as e:
                logger.error(
                    f"Error processing circular "
                    f"{circular.get('metadata', {}).get('circular_number', 'Unknown')}: {str(e)}"
                )
                raise e

    def verify_ingestion(self, circulars: List[Dict[str, Any]]):
        """Verify that all circulars were properly ingested"""
        logger.info("Verifying ingestion")

        for circular in tqdm(circulars, desc="Verifying circulars"):
            circular_number = circular["metadata"]["circular_number"]
            stored_circular = self.vector_store.get_circular_by_number(circular_number)

            if not stored_circular:
                logger.error(f"Circular {circular_number} not found in vector store")
            else:
                logger.debug(f"Verified circular {circular_number}")

    def run(self):
        """Run the complete loading process"""
        try:
            # Load JSON files
            circulars = self.load_json_files()
            logger.info(f"Loaded {len(circulars)} circulars")
            if not circulars:
                logger.error("No circulars found to process")
                return

            # Process circulars
            self.process_circulars(circulars)

            # Verify ingestion
            self.verify_ingestion(circulars)

            logger.info("Circular loading process completed successfully")

        except Exception as e:
            logger.error(f"Error in circular loading process: {str(e)}")


def circular_loader():
    # Load configuration
    config = load_config()

    # Setup paths
    data_dir = Path("data/chunks/circulars")
    if not data_dir.exists():
        raise ValueError(f"Data directory {data_dir} does not exist")

    # Ensure directories exist
    Path(config.chroma.persist_directory).parent.mkdir(parents=True, exist_ok=True)

    # Create loader and run
    loader = CircularLoader(data_dir, config)
    loader.run()


def load_config() -> VectorDBConfig:
    """Load configuration from environment variables"""
    load_dotenv()

    azure_config = AzureConfig(
        api_key=os.getenv("AZURE_API_KEY"),
        api_base=os.getenv("AZURE_API_BASE"),
        api_version=os.getenv("AZURE_API_VERSION"),
        embedding_deployment=os.getenv("AZURE_EMBEDDING_DEPLOYMENT"),
    )

    chroma_config = ChromaConfig(
        persist_directory=os.path.join("storage", "circular_vectordb"),
        collection_name="circulars",
    )

    return VectorDBConfig(azure=azure_config, chroma=chroma_config)


class CircularSearcher:
    def __init__(self, config: VectorDBConfig):
        self.config = config
        self.embedding_service = AzureEmbeddingService(self.config.azure)
        self.vector_store = CircularVectorStore(
            self.config.chroma, self.embedding_service
        )
        stats = self.vector_store.get_stats()
        logger.info(f"Database Stats:")
        logger.info(f"Total documents: {stats['total_documents']}")
        logger.info(f"Collections: {stats['collections']}")

    def search(
        self,
        query: str,
        limit: int = 5,
        chunk_types: List[str] = None,
        date_range: Dict[str, str] = None,
        filter_criteria: Dict[str, Any] = None,
    ):
        """
        Search for circulars with various filters
        """
        logger.info(f"Searching for: '{query}'")

        results = self.vector_store.search_circulars(
            query=query,
            limit=limit,
            chunk_types=chunk_types,
            date_range=date_range,
            filter_criteria=filter_criteria,
        )

        return results

    def display_results(self, results: List[Any], detailed: bool = False):
        """Display search results"""
        if not results:
            logger.info("No results found")
            return

        for i, result in enumerate(results, 1):
            logger.info(f"\nResult {i}:")
            logger.info(f"Circular: {result.metadata.get('circular_number')}")
            logger.info(f"Date: {result.metadata.get('date')}")
            logger.info(f"Type: {result.metadata.get('chunk_type')}")
            logger.info(f"Score: {result.score:.4f}")

            if detailed:
                logger.info(f"Subject: {result.metadata.get('subject')}")
                logger.info(f"Content: {result.content}")
                logger.info(f"References:")
                logger.info(f"  Sections: {result.metadata.get('section_references')}")
                logger.info(
                    f"  Circulars: {result.metadata.get('circular_references')}"
                )
                logger.info(
                    f"  Regulations: {result.metadata.get('regulation_references')}"
                )
            else:
                logger.info(f"Content: {result.content[:200]}...")

    def get_circular_details(self, circular_number: str):
        """Get all chunks of a specific circular"""
        logger.info(f"Fetching details for circular: {circular_number}")

        results = self.vector_store.get_circular_by_number(circular_number)
        if not results:
            logger.info(f"No circular found with number: {circular_number}")
            return None

        return results


def search_circulars():
    # Load configuration
    config = load_config()

    # Initialize searcher
    searcher = CircularSearcher(config)

    # Example searches
    search_examples = [
        {
            "query": "liquidation process",
            "filters": {
                # "chunk_types": ["DIRECTIVE"],
                # "date_range": {"start": "2023-01-01", "end": "2024-12-31"},
            },
        },
        {
            "query": "insolvency professional duties registration",
            "filters": {
                # "chunk_types": ["DIRECTIVE", "CONTEXT"]
            },
        },
    ]

    # Perform searches
    for example in search_examples:
        logger.info(f"\n{'='*50}")
        logger.info(f"Searching: {example['query']}")
        results = searcher.search(
            query=example["query"], limit=5, **example.get("filters", {})
        )
        searcher.display_results(results)

    # # Example: Get specific circular details
    # circular_number = "IBBI/LIQ/78/2024"
    # logger.info(f"\n{'='*50}")
    # logger.info(f"Getting details for circular: {circular_number}")
    # circular_details = searcher.get_circular_details(circular_number)
    # if circular_details:
    #     for chunk in circular_details:
    #         logger.info(f"\nChunk Type: {chunk['chunk_type']}")
    #         logger.info(f"Content: {chunk['content'][:200]}...")


if __name__ == "__main__":
    search_circulars()
