import streamlit as st
import asyncio
import os
from dotenv import load_dotenv
import sys
import re

sys.path.append(".")
from scripts.search import (
    CONFIGS,
    process_documents,
    extract_query,
    extract_summary_and_relevance,
)
from models.web_search import GoogleCustomSearchDownloader
from utils.logging_utils import ResearchLogger


async def run_research(query: str, progress_bar, status_text):
    # Initialize logger
    logger = ResearchLogger(query)
    logger.logger.info(f"Starting research for query: {query}")

    # Load environment variables and setup API credentials
    load_dotenv()
    API_KEY = os.getenv("GCP_API_KEY")
    CUSTOM_SEARCH_ENGINE_ID = os.getenv("CUSTOM_SEARCH_ENGINE_ID")

    # Setup configuration
    kwargs = {
        "max_tokens": 8192,
        "temperature": 0.0,
        "add_history": True,
    }
    config = CONFIGS["gemini"]

    # Initialize agents with the same prompts as search.py
    query_rewriting_agent = config.create_agent(
        "You are an AI assistant specializing in Indian law, tasked with improving and expanding search queries related to Indian legal terms and concepts. Your goal is to transform potentially ill-formed, grammatically incorrect, or misspelled user queries into multiple well-formed, specific search queries that will yield relevant results about Indian law."
    )

    research_note_agent = config.create_agent(
        "You are a legal research assistant tasked with writing a comprehensive Legal Research Note. You will be provided with legal context from various documents and a specific query to address. Your goal is to synthesize this information into a well-structured, professional research note that adheres to legal writing standards."
    )

    summary_agent = config.create_agent(
        "You are a legal research assistant tasked with evaluating the relevance of a legal document to a given search query and extracting pertinent information. Your goal is to determine if the document is relevant to the query and, if so, to extract the main points that are applicable."
    )

    # Load prompts
    progress_bar.progress(10)
    status_text.text("Loading prompts...")

    with open("prompts/query_rewriting.jinja", "r") as file:
        query_rewriting_prompt = file.read().replace("{{USER_QUERY}}", query)

    with open("prompts/research_note.jinja", "r") as file:
        research_note_prompt = file.read()

    with open("prompts/relevance_analysis.jinja", "r") as file:
        relevance_analysis_prompt = file.read()

    # Query rewriting
    progress_bar.progress(20)
    status_text.text("Expanding search queries...")

    response = await query_rewriting_agent.generate(query_rewriting_prompt, **kwargs)
    queries = extract_query(response["content"])
    logger.log_expanded_queries(queries)
    folder = queries[0]
    # make sure the folder name is valid for a file path
    folder = re.sub(r"[^a-zA-Z0-9_]", "_", folder)

    # Web search and download
    progress_bar.progress(30)
    status_text.text("Performing web search...")

    downloader = GoogleCustomSearchDownloader(API_KEY, CUSTOM_SEARCH_ENGINE_ID, folder)
    for expanded_query in queries:
        try:
            downloaded_files = downloader.search_and_download(
                expanded_query,
                num_results=5,
            )
            logger.logger.info(f"Completed search for query: {expanded_query}")
            if len(os.listdir(folder)) > 20:
                break
        except Exception as e:
            logger.logger.error(f"Error in web search for {expanded_query}: {str(e)}")

    # Process documents
    progress_bar.progress(50)
    status_text.text("Processing downloaded documents...")

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

    progress_bar.progress(70)
    status_text.text("Analyzing document relevance...")

    relevant_contents = await process_documents(
        [content for _, content in file_contents],
        summary_agent,
        relevance_analysis_prompt,
        query,
        kwargs,
        logger,
    )

    if not relevant_contents:
        logger.logger.warning("No relevant content found in the downloaded documents.")
        logger.save_final_report()
        return "No relevant content found in the documents."

    # Generate research note
    progress_bar.progress(90)
    status_text.text("Generating research note...")

    try:
        research_note_prompt_final = research_note_prompt.replace(
            "{{LEGAL_CONTEXT}}", "\n\n".join(relevant_contents)
        )
        research_note_prompt_final = research_note_prompt_final.replace(
            "{{QUERY}}", queries[1] if queries else query
        )

        response = await research_note_agent.generate(
            research_note_prompt_final, **kwargs
        )
        research_note = response["content"]

        logger.log_research_note(research_note)
        logger.logger.info("Successfully generated research note")
        logger.save_final_report()

        progress_bar.progress(100)
        status_text.text("Research completed!")

        return research_note

    except Exception as e:
        logger.logger.error(f"Error generating research note: {str(e)}")
        logger.save_final_report()
        return f"An error occurred: {str(e)}"


def main():
    st.set_page_config(
        page_title="Legal Research Assistant", page_icon="⚖️", layout="wide"
    )

    st.title("🔍 Legal Research Assistant")
    st.write("Enter your legal query below to generate a comprehensive research note.")

    # User input
    query = st.text_input("Enter your query:", placeholder="e.g., Sarfesci vs IBC act")

    if st.button("Generate Research Note"):
        if not query:
            st.error("Please enter a query.")
            return

        # Create placeholder for progress bar and status
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Create placeholder for research note
        research_note_placeholder = st.empty()

        try:
            # Run the research process
            research_note = asyncio.run(run_research(query, progress_bar, status_text))

            # Display results
            if research_note.startswith("An error occurred"):
                st.error(research_note)
            else:
                research_note_placeholder.markdown(research_note)

                # Add download button for the research note
                st.download_button(
                    label="Download Research Note",
                    data=research_note,
                    file_name=f"research_note_{query[:30]}.md",
                    mime="text/markdown",
                )

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
        finally:
            # Clean up progress displays
            progress_bar.empty()
            status_text.empty()

    # Add sidebar with information
    with st.sidebar:
        st.header("About")
        st.write(
            """
        This tool helps legal professionals generate comprehensive research notes by:
        1. Expanding and improving search queries
        2. Analyzing relevant documents
        3. Synthesizing information into a structured research note
        """
        )

        st.header("Recent Searches")
        if os.path.exists("research_logs"):
            recent_searches = sorted(
                [
                    d
                    for d in os.listdir("research_logs")
                    if os.path.isdir(os.path.join("research_logs", d))
                ],
                reverse=True,
            )[:5]

            for search in recent_searches:
                st.write(f"• {search[15:]}")  # Skip timestamp in folder name


if __name__ == "__main__":
    main()
