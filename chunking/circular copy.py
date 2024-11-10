import re
from typing import Dict, List, Optional
from dataclasses import dataclass
import hashlib
from datetime import datetime
from pathlib import Path
from sentence_transformers import SentenceTransformer
import numpy as np


@dataclass
class DocumentMetadata:
    document_type: str
    title: str
    notification_number: str
    date: str
    publication: str
    authority: str
    file_name: str
    processing_timestamp: str
    document_hash: str


@dataclass
class Chunk:
    chunk_id: str
    chunk_type: str
    content: str
    metadata: Dict
    embedding: Optional[List[float]] = None


class RegulationProcessor:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.chunks = []
        self.metadata = None

    def process_file(self, file_path: Path) -> Dict:
        """Process a single MD file and return structured content."""
        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()

        # Generate document hash
        doc_hash = hashlib.md5(text.encode()).hexdigest()

        # Extract metadata
        self.metadata = self._extract_metadata(text, file_path, doc_hash)

        # Process content into chunks
        self._process_content(text)

        return {
            "metadata": self.metadata.__dict__,
            "chunks": [chunk.__dict__ for chunk in self.chunks],
        }

    def _extract_metadata(
        self, text: str, file_path: Path, doc_hash: str
    ) -> DocumentMetadata:
        """Extract metadata from the document."""
        title_pattern = r"**([^*]+)**"
        notification_pattern = r"No\.\s*(SEBI/[^.]+)"
        date_pattern = r"(\d{1,2}\[\w+\]\s+\w+,\s+\d{4})"

        title_match = re.search(title_pattern, text)
        notification_match = re.search(notification_pattern, text)
        date_match = re.search(date_pattern, text)

        return DocumentMetadata(
            document_type="SEBI Regulation",
            title=title_match.group(1) if title_match else "",
            notification_number=(
                notification_match.group(1) if notification_match else ""
            ),
            date=date_match.group(1) if date_match else "",
            publication="THE GAZETTE OF INDIA EXTRAORDINARY PART III - SECTION 4",
            authority="SECURITIES AND EXCHANGE BOARD OF INDIA",
            file_name=file_path.name,
            processing_timestamp=datetime.now().isoformat(),
            document_hash=doc_hash,
        )

    def _process_content(self, text: str):
        """Process content into chunks with embeddings."""
        self._process_chapters(text)
        self._process_definitions(text)
        self._process_regulations(text)

    def _process_chapters(self, text: str):
        """Extract and process chapters."""
        chapter_pattern = r"**CHAPTER\s+([IVX]+)**\s*\n\s*([^*]+)"

        for match in re.finditer(chapter_pattern, text):
            chapter_content = {
                "chapter_number": match.group(1),
                "chapter_title": match.group(2).strip(),
            }

            chunk_text = f"Chapter {chapter_content['chapter_number']}: {chapter_content['chapter_title']}"
            embedding = self.model.encode(chunk_text).tolist()

            self.chunks.append(
                Chunk(
                    chunk_id=f"chapter_{chapter_content['chapter_number']}",
                    chunk_type="chapter",
                    content=chunk_text,
                    metadata=chapter_content,
                    embedding=embedding,
                )
            )

    def _process_definitions(self, text: str):
        """Extract and process definitions."""
        definition_section = re.search(
            r"**Definitions\.**.*?(?=\*\*\d+\.)", text, re.DOTALL
        )

        if definition_section:
            definition_text = definition_section.group(0)
            definition_pattern = r"([a-z])\)\s*\"([^\"]+)\"\s*means\s*([^;]+);"

            for match in re.finditer(definition_pattern, definition_text):
                definition_content = {
                    "term": match.group(2),
                    "definition": match.group(3),
                    "section_reference": f"2(1)({match.group(1)})",
                }

                chunk_text = (
                    f"{definition_content['term']}: {definition_content['definition']}"
                )
                embedding = self.model.encode(chunk_text).tolist()

                self.chunks.append(
                    Chunk(
                        chunk_id=f"def_{hashlib.md5(chunk_text.encode()).hexdigest()[:8]}",
                        chunk_type="definition",
                        content=chunk_text,
                        metadata=definition_content,
                        embedding=embedding,
                    )
                )

    def _process_regulations(self, text: str):
        """Extract and process regulations."""
        regulation_pattern = r"\*\*(\d+)\.\s*([^*]+)\*\*\s*([^*]+)"

        for match in re.finditer(regulation_pattern, text):
            regulation_content = {
                "regulation_number": match.group(1),
                "regulation_title": match.group(2).strip(),
                "regulation_text": match.group(3).strip(),
            }

            chunk_text = f"Regulation {regulation_content['regulation_number']}: {regulation_content['regulation_title']}\n{regulation_content['regulation_text']}"
            embedding = self.model.encode(chunk_text).tolist()

            self.chunks.append(
                Chunk(
                    chunk_id=f"reg_{regulation_content['regulation_number']}",
                    chunk_type="regulation",
                    content=chunk_text,
                    metadata=regulation_content,
                    embedding=embedding,
                )
            )
