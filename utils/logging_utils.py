import json
import os
from datetime import datetime
import logging


class ResearchLogger:
    def __init__(self, base_query):
        # Create logs directory if it doesn't exist
        self.logs_dir = "research_logs"
        os.makedirs(self.logs_dir, exist_ok=True)

        # Create a timestamped directory for this research session
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(self.logs_dir, f"{timestamp}_{base_query[:30]}")
        os.makedirs(self.session_dir, exist_ok=True)

        # Set up logging
        self.logger = logging.getLogger(f"research_{timestamp}")
        self.logger.setLevel(logging.INFO)

        # File handler
        log_file = os.path.join(self.session_dir, "research.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        self.research_data = {
            "base_query": base_query,
            "timestamp": timestamp,
            "expanded_queries": [],
            "document_summaries": [],
            "relevant_contents": [],
            "final_research_note": None,
        }

    def log_expanded_queries(self, queries):
        self.research_data["expanded_queries"] = queries
        self.logger.info(f"Generated {len(queries)} expanded queries")
        self._save_json("expanded_queries.json", queries)

    def log_document_summary(self, file_path, summary, is_relevant):
        summary_data = {
            "file": file_path,
            "summary": summary,
            "is_relevant": is_relevant,
        }
        self.research_data["document_summaries"].append(summary_data)
        self.logger.info(f"Processed document: {file_path} (Relevant: {is_relevant})")

    def log_relevant_content(self, content):
        self.research_data["relevant_contents"].append(content)
        self._save_json(
            "relevant_contents.json", self.research_data["relevant_contents"]
        )

    def log_research_note(self, research_note):
        self.research_data["final_research_note"] = research_note
        self._save_json("final_research_note.json", {"research_note": research_note})

        # Also save as plain text for easier reading
        with open(
            os.path.join(self.session_dir, "research_note.txt"), "w", encoding="utf-8"
        ) as f:
            f.write(research_note)

    def _save_json(self, filename, data):
        filepath = os.path.join(self.session_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save_final_report(self):
        self._save_json("complete_research_data.json", self.research_data)
