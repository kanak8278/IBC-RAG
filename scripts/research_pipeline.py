import asyncio
import os
from dotenv import load_dotenv
import sys
import re
from typing import List, Tuple, Optional

sys.path.append(".")
from scripts.search import (
    CONFIGS,
    process_documents,
    extract_query,
)
from scripts.act_hybrid_search import HybridSearch
from models.web_search import GoogleCustomSearchDownloader
from utils.logging_utils import ResearchLogger


class ResearchPipeline:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("GCP_API_KEY")
        self.search_engine_id = os.getenv("CUSTOM_SEARCH_ENGINE_ID")
        self.act_chunks_file = "insolvency_code_structured.json"

        self.act_searcher = HybridSearch(self.act_chunks_file)

        # Initialize logger first
        self.logger = ResearchLogger("initialization")

        # LLM configuration
        self.kwargs = {
            "max_tokens": 8192,
            "temperature": 0.0,
            "add_history": True,
        }
        self.config = CONFIGS["gemini"]

        # Initialize agents
        self.query_rewriting_agent = self.config.create_agent(
            "You are an AI assistant specializing in Indian law, tasked with improving and expanding search queries related to Indian legal terms and concepts. Your goal is to transform potentially ill-formed, grammatically incorrect, or misspelled user queries into multiple well-formed, specific search queries that will yield relevant results about Indian law."
        )

        self.research_note_agent = self.config.create_agent(
            "You are a legal research assistant tasked with writing a comprehensive Legal Research Note. You will be provided with legal context from various documents and a specific query to address. Your goal is to synthesize this information into a well-structured, professional research note that adheres to legal writing standards."
        )

        self.summary_agent = self.config.create_agent(
            "You are a legal research assistant tasked with evaluating the relevance of a legal document to a given search query and extracting pertinent information. Your goal is to determine if the document is relevant to the query and, if so, to extract the main points that are applicable."
        )

        # Load prompts at the end
        self.load_prompts()

    def load_prompts(self):
        """Load all required prompts from files."""
        try:
            with open("prompts/query_rewriting.jinja", "r") as file:
                self.query_rewriting_template = file.read()

            with open("prompts/research_note.jinja", "r") as file:
                self.research_note_template = file.read()

            with open("prompts/relevance_analysis.jinja", "r") as file:
                self.relevance_analysis_template = file.read()

            self.logger.logger.info("Successfully loaded all prompt templates")
        except Exception as e:
            self.logger.logger.error(f"Error loading prompts: {str(e)}")
            raise

    async def expand_queries(self, query: str, logger: ResearchLogger) -> List[str]:
        """Expand the original query into multiple specific queries."""
        query_rewriting_prompt = self.query_rewriting_template.replace(
            "{{USER_QUERY}}", query
        )
        response = await self.query_rewriting_agent.generate(
            query_rewriting_prompt, **self.kwargs
        )
        queries = extract_query(response["content"])
        logger.log_expanded_queries(queries)
        return queries

    async def perform_web_search(
        self, queries: List[str], folder: str, logger: ResearchLogger
    ) -> None:
        """Perform web search for each expanded query."""
        logger.logger.info(f"Starting web search with {len(queries)} queries")

        downloader = GoogleCustomSearchDownloader(
            self.api_key, self.search_engine_id, folder, True, logger=logger.logger
        )
        total_downloaded = 0

        for expanded_query in queries:
            try:
                downloaded = downloader.search_and_download(
                    expanded_query, num_results=5
                )
                total_downloaded += len(downloaded)
                logger.logger.info(
                    f"Downloaded {len(downloaded)} files for query: {expanded_query}"
                )

                if len(os.listdir(folder)) > 20:
                    logger.logger.info(
                        "Reached maximum file limit (20). Stopping web search."
                    )
                    break
            except Exception as e:
                logger.logger.error(
                    f"Error in web search for {expanded_query}: {str(e)}"
                )

        logger.logger.info(
            f"Web search completed. Total files downloaded: {total_downloaded}"
        )

    def perform_act_search(
        self, query: str, logger: ResearchLogger
    ) -> Tuple[List[dict], str]:
        """Perform hybrid search on IBC Act and format results."""
        logger.logger.info("Starting Act hybrid search")

        try:
            act_results = self.act_searcher.search(
                query, max_results=5, use_hybrid=True
            )

            # Log search results details
            self.logger.logger.info(
                f"Found {len(act_results)} relevant sections in IBC Act"
            )
            # Format content for processing
            act_contents = [result["content"] for result in act_results]
            act_content_text = (
                "Extracted from IBC Act 2016, updated in 2021"
                + "\n\n"
                + "\n\n".join(act_contents)
            )

            # Log the formatted content
            logger.logger.info(
                f"Formatted Act content length: {len(act_content_text)} characters"
            )

            return act_results, act_content_text

        except Exception as e:
            logger.logger.error(f"Error in Act hybrid search: {str(e)}")
            raise

    def read_downloaded_files(
        self, folder: str, logger: ResearchLogger
    ) -> List[Tuple[str, str]]:
        """Read contents of downloaded files."""
        downloaded_files = os.listdir(folder)
        logger.logger.info(f"Found {len(downloaded_files)} files in {folder}")

        file_contents = []
        for file_path in downloaded_files[:8]:
            full_path = os.path.join(folder, file_path)
            if full_path.endswith(".md"):
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        file_contents.append((full_path, content))
                    logger.logger.info(f"Successfully read file: {full_path}")
                except Exception as e:
                    logger.logger.error(f"Error reading file {full_path}: {str(e)}")
        return file_contents

    async def generate_research_note(
        self,
        query: str,
        relevant_contents: List[str],
        queries: List[str],
        logger: ResearchLogger,
    ) -> str:
        """Generate the final research note."""
        try:
            research_note_prompt = self.research_note_template.replace(
                "{{LEGAL_CONTEXT}}", "\n\n".join(relevant_contents)
            )
            research_note_prompt = research_note_prompt.replace(
                "{{QUERY}}", queries[1] if queries else query
            )

            response = await self.research_note_agent.generate(
                research_note_prompt, **self.kwargs
            )
            research_note = response["content"]
            logger.log_research_note(research_note)
            logger.logger.info("Successfully generated research note")
            return research_note

        except Exception as e:
            logger.logger.error(f"Error generating research note: {str(e)}")
            raise

    async def run(self, query: str) -> Optional[str]:
        """Run the complete research pipeline."""
        # Initialize logger
        self.logger = ResearchLogger(query)
        self.logger.logger.info(f"Starting research pipeline for query: {query}")

        try:
            # Expand queries
            self.logger.logger.info("Starting query expansion")
            queries = await self.expand_queries(query, self.logger)
            if not queries:
                self.logger.logger.error(
                    "Query expansion failed - no queries generated"
                )
                return None

            # Create folder for downloads
            folder = re.sub(r"[^a-zA-Z0-9_]", "_", queries[0])
            self.logger.logger.info(f"Created download folder: {folder}")

            # Perform web search
            await self.perform_web_search(queries, folder, self.logger)

            # Read downloaded files
            file_contents = self.read_downloaded_files(folder, self.logger)
            if not file_contents:
                self.logger.logger.error("No files downloaded or read successfully")
                return None

            content_to_process = [content for _, content in file_contents]
            self.logger.logger.info(
                f"Prepared {len(content_to_process)} web documents for processing"
            )

            # Act hybrid search
            self.logger.logger.info("Starting Act hybrid search")
            act_results, act_content_text = self.perform_act_search(query, self.logger)

            # Log act search results to the research log
            self.logger.log_act_search_results(act_results)

            # Add act content to processing queue
            content_to_process.append(act_content_text)
            self.logger.logger.info("Added Act content to processing queue")

            # Process documents
            self.logger.logger.info(f"Processing {len(content_to_process)} documents")
            relevant_contents = await process_documents(
                content_to_process,
                self.summary_agent,
                self.relevance_analysis_template,
                query,
                self.kwargs,
                self.logger,
            )

            if not relevant_contents:
                self.logger.logger.warning("No relevant content found in any documents")
                self.logger.save_final_report()
                return "No relevant content found in the documents."

            # Generate research note
            self.logger.logger.info("Generating final research note")
            research_note = await self.generate_research_note(
                query, relevant_contents, queries, self.logger
            )

            self.logger.save_final_report()
            self.logger.logger.info("Research pipeline completed successfully")
            return research_note

        except Exception as e:
            self.logger.logger.error(f"Pipeline error: {str(e)}")
            self.logger.save_final_report()
            return f"An error occurred: {str(e)}"


async def main():
    # Example usage
    pipeline = ResearchPipeline()
    query = "Sarfesci vs IBC act"
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])

    result = await pipeline.run(query)
    if result:
        print("\nResearch Note:")
        print("-" * 80)
        print(result)
        print("-" * 80)


if __name__ == "__main__":
    asyncio.run(main())
