import streamlit as st
import asyncio
import os
import sys

sys.path.append(".")
from scripts.research_pipeline import ResearchPipeline


async def run_research(query: str, progress_bar, status_text):
    # Initialize research pipeline outside try block
    pipeline = ResearchPipeline()

    try:
        # Execute research steps
        progress_bar.progress(10)
        status_text.text("Initializing research pipeline...")

        progress_bar.progress(30)
        status_text.text("Performing research...")

        research_note = await pipeline.run(query)

        progress_bar.progress(100)
        status_text.text("Research completed!")

        return research_note

    except Exception as e:
        pipeline.logger.logger.error(f"Error in research pipeline: {str(e)}")
        return f"An error occurred: {str(e)}"


def update_progress(progress_bar, status_text, progress, status):
    """Update the Streamlit progress indicators"""
    progress_bar.progress(progress)
    status_text.text(status)


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
