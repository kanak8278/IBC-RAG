import os
import glob
from dotenv import load_dotenv
import sys
import asyncio
import json
import re
from datetime import datetime

sys.path.append(".")
from llm_model import LLMConfig, LLMProvider

load_dotenv()

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


def extract_and_format_date(filepath):
    # Extract filename from path
    filename = filepath.split("/")[-1]

    # Extract date part using regex
    date_pattern = r"^(\d{2})_([A-Za-z]+)__(\d{4})"
    match = re.search(date_pattern, filename)

    if match:
        day = match.group(1)
        month = match.group(2)
        year = match.group(3)

        # Create a datetime object
        try:
            date_obj = datetime.strptime(f"{day} {month} {year}", "%d %b %Y")
            # Format the date as desired (e.g., "2017-10-05")
            formatted_date = date_obj.strftime("%Y-%m-%d")
            return formatted_date
        except ValueError as e:
            print(f"Error parsing date: {e}")
            return None

    return None


def extract_document_info(text):
    # Pattern for document ID
    doc_id_pattern = r"<document_id>(.*?)</document_id>"

    # Pattern for title
    title_pattern = r"<title>(.*?)</title>"

    # Pattern for summary
    summary_pattern = r"<context_summary>(.*?)</context_summary>"

    # Extract information using regex
    try:
        # Find document ID
        doc_id_match = re.search(doc_id_pattern, text, re.DOTALL)
        document_id = doc_id_match.group(1).strip() if doc_id_match else ""

        # Find title
        title_match = re.search(title_pattern, text, re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""

        # Find summary
        summary_match = re.search(summary_pattern, text, re.DOTALL)
        summary = summary_match.group(1).strip() if summary_match else ""

        return {"document_id": document_id, "title": title, "summary": summary}

    except Exception as e:
        print(f"Error extracting information: {str(e)}")
        return {
            "document_id": None,
            "title": None,
            "summary": None,
        }


kwargs = {
    "max_tokens": 8192,
    "temperature": 0.0,
    "add_history": True,
}

system_prompt = """
You are an AI assistant specialized in analyzing legal documents such as circulars, regulations, rules, among others. Your task is to extract specific metadata and provide a concise summary of the document's context. Accuracy and precision are crucial in this task.
"""

config = CONFIGS["default"]
metadata_extraction_agent = config.create_agent(system_prompt)


def extract_metadata(prompt, content):
    prompt = prompt.replace("{{LEGAL_DOCUMENT}}", content[:20000])
    metadata = asyncio.run(metadata_extraction_agent.generate(prompt, **kwargs))
    return extract_document_info(metadata["content"])


# load prompt prompts/metadata_extraction.jinja
with open("prompts/metadata_extraction.jinja", "r") as file:
    prompt = file.read()

# get all the .md files in data/markdown/regulations
md_files = glob.glob("data/markdown/regulations/**/*.md")

for md_file in md_files:
    with open(md_file, "r") as file:
        content = file.read()
    date = extract_and_format_date(md_file)
    extracted_metadata = extract_metadata(prompt, content)
    extracted_metadata["date"] = date

    # save the extracted metadata to a json file in the same directory as the md file
    with open(md_file.replace(".md", ".json"), "w") as file:
        json.dump(extracted_metadata, file)
