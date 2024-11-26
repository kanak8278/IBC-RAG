from dotenv import load_dotenv
import os
import sys
import re
import asyncio
import json

sys.path.append(".")
from llm_model import LLMConfig, LLMProvider, AnthropicLLM, Agent
from models.web_search import GoogleCustomSearchDownloader

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


def main():
    base_query = "Sarfesci vs IBC act"
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
    agent = config.create_agent(
        "You are an AI assistant specializing in Indian law, tasked with improving and expanding search queries related to Indian legal terms and concepts. Your goal is to transform potentially ill-formed, grammatically incorrect, or misspelled user queries into multiple well-formed, specific search queries that will yield relevant results about Indian law."
    )
    # load prompts/query_rewriting.jinja and replace USER_QUERY with the query
    with open("prompts/query_rewriting.jinja", "r") as file:
        prompt = file.read()
    prompt = prompt.replace("{{USER_QUERY}}", base_query)

    response = asyncio.run(
        agent.generate(
            prompt,
            **kwargs,
        )
    )
    queries = extract_query(response["content"])
    print(json.dumps(queries, indent=4))

    # Create downloader instance
    downloader = GoogleCustomSearchDownloader(
        api_key=API_KEY,
        custom_search_engine_id=CUSTOM_SEARCH_ENGINE_ID,
        output_directory="gcp_search_results",
    )

    # Search query with filters
    for query in queries:
        print(f"Searching for: {query}")
        print(f"Fetching results from preferred legal websites...")

        # Perform search and download with filters
        downloaded_files = downloader.search_and_download(
            query=query,
            num_results=10,
            file_type=None,  # Search for PDFs only
            # search only for websites from india
            # site_restrict="site_in",
            date_restrict="y1",  # Results from the last year
            # sort="date",  # Sort by date
            language="lang_en",  # English language results only
        )

        print("\nDownloaded files:")
        for file in downloaded_files:
            print(f"- {file}")


if __name__ == "__main__":
    main()
