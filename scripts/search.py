from dotenv import load_dotenv
import os
import sys
import re
import asyncio
import json

sys.path.append(".")
from llm_model import LLMConfig, LLMProvider, AnthropicLLM, Agent
from models.web_search import GoogleCustomSearchDownloader
from utils.logging_utils import ResearchLogger

CONFIGS = {
    "default": LLMConfig(
        provider=LLMProvider.ANTHROPIC,
        model="claude-3-5-sonnet-20241022",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    ),
    "gemini": LLMConfig(
        provider=LLMProvider.GEMINI,
        model="gemini-1.5-flash",
        api_key=os.getenv("GOOGLE_API_KEY"),
    ),
}


def extract_query(text: str):
    return [
        query.strip()
        for query in re.findall(r"<query\d+>(.*?)</query\d+>", text, re.DOTALL)
    ]


def extract_summary_and_relevance(text: str):
    # Extract summary
    summary_match = re.search(r"<summary>(.*?)</summary>", text, re.DOTALL)
    if not summary_match:
        return "", False

    summary = summary_match.group(1).strip()

    # Check if explicitly marked as not relevant
    if summary.lower() == "not relevant":
        return summary, False

    return summary, True


async def process_documents(
    file_contents, summary_agent, relevance_analysis_prompt, base_query, kwargs, logger
):
    relevant_contents = []
    for file_content in file_contents:
        current_relevance_prompt = relevance_analysis_prompt
        current_relevance_prompt = current_relevance_prompt.replace(
            "{{DOCUMENT}}", file_content
        )
        current_relevance_prompt = current_relevance_prompt.replace(
            "{{QUERY}}", base_query
        )
        try:
            response = await summary_agent.generate(current_relevance_prompt, **kwargs)
            summary, is_relevant = extract_summary_and_relevance(response["content"])

            # Log the summary
            logger.log_document_summary(
                "document_content",  # You might want to pass the actual filename here
                summary,
                is_relevant,
            )

            if is_relevant:
                relevant_contents.append(summary)
                logger.log_relevant_content(summary)
        except Exception as e:
            logger.logger.error(f"Error processing document: {str(e)}")
    return relevant_contents


async def main():
    # Add command line argument parsing
    if len(sys.argv) > 1:
        base_query = " ".join(sys.argv[1:])
    else:
        base_query = "Sarfesci vs IBC act"

    # Initialize logger at the start
    logger = ResearchLogger(base_query)
    logger.logger.info(f"Starting research for query: {base_query}")

    # Your Google Cloud API credentials
    load_dotenv()
    API_KEY = os.getenv("GCP_API_KEY")
    CUSTOM_SEARCH_ENGINE_ID = os.getenv("CUSTOM_SEARCH_ENGINE_ID")
    kwargs = {
        "max_tokens": 8192,
        "temperature": 0.0,
        "add_history": True,
    }
    config = CONFIGS["gemini"]
    query_rewriting_agent = config.create_agent(
        "You are an AI assistant specializing in Indian law, tasked with improving and expanding search queries related to Indian legal terms and concepts. Your goal is to transform potentially ill-formed, grammatically incorrect, or misspelled user queries into multiple well-formed, specific search queries that will yield relevant results about Indian law."
    )

    research_note_agent = config.create_agent(
        "You are a legal research assistant tasked with writing a comprehensive Legal Research Note. You will be provided with legal context from various documents and a specific query to address. Your goal is to synthesize this information into a well-structured, professional research note that adheres to legal writing standards."
    )

    summary_agent = config.create_agent(
        "You are a legal research assistant tasked with evaluating the relevance of a legal document to a given search query and extracting pertinent information. Your goal is to determine if the document is relevant to the query and, if so, to extract the main points that are applicable."
    )

    # load prompts/query_rewriting.jinja and replace USER_QUERY with the query
    with open("prompts/query_rewriting.jinja", "r") as file:
        query_rewriting_prompt = file.read()
    query_rewriting_prompt = query_rewriting_prompt.replace(
        "{{USER_QUERY}}", base_query
    )

    with open("prompts/research_note.jinja", "r") as file:
        research_note_prompt = file.read()

    with open("prompts/relevance_analysis.jinja", "r") as file:
        relevance_analysis_prompt = file.read()

    # Query rewriting
    response = await query_rewriting_agent.generate(
        query_rewriting_prompt,
        **kwargs,
    )
    queries = extract_query(response["content"])
    logger.log_expanded_queries(queries)

    downloaded_files = os.listdir("gcp_search_results")
    logger.logger.info(f"Found {len(downloaded_files)} files in gcp_search_results")

    file_contents = []
    # filter out the files .md
    for file_path in downloaded_files[:8]:
        full_path = os.path.join("gcp_search_results", file_path)
        if full_path.endswith(".md"):
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    file_contents.append(
                        (full_path, content)
                    )  # Store tuple of path and content
                logger.logger.info(f"Successfully read file: {full_path}")
            except Exception as e:
                logger.logger.error(f"Error reading file {full_path}: {str(e)}")

    content_to_process = [content for _, content in file_contents]
    # Process documents
    relevant_contents = await process_documents(
        content_to_process,  # Pass only the content
        summary_agent,
        relevance_analysis_prompt,
        base_query,
        kwargs,
        logger,
    )

    if not relevant_contents:
        logger.logger.warning("No relevant content found in the downloaded documents.")
        logger.save_final_report()
        return

    # Generate research note
    try:
        research_note_prompt_final = research_note_prompt.replace(
            "{{LEGAL_CONTEXT}}", "\n\n".join(relevant_contents)
        )
        research_note_prompt_final = research_note_prompt_final.replace(
            "{{QUERY}}", queries[1] if queries else base_query
        )

        response = await research_note_agent.generate(
            research_note_prompt_final, **kwargs
        )
        logger.log_research_note(response["content"])
        logger.logger.info("Successfully generated research note")

        # Save all data at the end
        logger.save_final_report()
        logger.logger.info("Research session completed successfully")

    except Exception as e:
        logger.logger.error(f"Error generating research note: {str(e)}")
        logger.save_final_report()


if __name__ == "__main__":
    asyncio.run(main())
