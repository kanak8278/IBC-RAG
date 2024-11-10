import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import json
from datetime import datetime
import hashlib
import logging


@dataclass
class NotificationMetadata:
    registry_number: str
    gazette_number: str
    publication_date: str
    indian_date: str
    ministry: str
    notification_number: str
    notification_date: str
    amendment_details: Optional[Dict[str, str]]
    file_name: str
    processing_timestamp: str
    document_hash: str


@dataclass
class NotificationChunk:
    chunk_id: str
    chunk_type: str  # PREAMBLE, RULE, AMENDMENT, CLOSING
    rule_number: Optional[str]
    sub_rule_number: Optional[str]
    content: str
    references: Dict[str, List[str]]
    context: Dict[str, str]


class NotificationProcessor:
    def __init__(
        self,
        min_chunk_size: int = 100,
        max_chunk_size: int = 1000,
        overlap_size: int = 50,
    ):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        self.metadata = None
        self.chunks = []

    def process_file(self, file_path: Path) -> Dict:
        """Process a single notification MD file"""
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        # Generate document hash
        doc_hash = hashlib.md5(content.encode()).hexdigest()

        # Extract English content
        english_content = self._extract_english_content(content)

        # Extract metadata
        self.metadata = self._extract_metadata(content, file_path, doc_hash)

        # Extract chunks
        self.chunks = self._chunk_content(english_content)

        return {
            "metadata": asdict(self.metadata),
            "chunks": [asdict(chunk) for chunk in self.chunks],
        }

    def _extract_english_content(self, content: str) -> str:
        """
        Extract English portion of the notification handling both bilingual and English-only files.

        Strategy:
        1. First detect if the file is bilingual or English-only
        2. Handle extraction accordingly
        3. Clean and validate the content
        """

        def is_bilingual(text: str) -> bool:
            """Check if the text contains Hindi characters."""
            hindi_pattern = r"[\u0900-\u097F]+"
            return bool(re.search(hindi_pattern, text))

        def has_notification_markers(text: str) -> bool:
            """Check if text has standard notification markers."""
            markers = [
                "EXTRAORDINARY",
                "PUBLISHED BY AUTHORITY",
                "MINISTRY OF",
                "NOTIFICATION",
                "G.S.R.",
                "REGD. NO.",
            ]
            return any(marker in text for marker in markers)

        # First clean any common OCR artifacts from the entire content
        content = self._clean_ocr_artifacts(content)

        # If content is not bilingual, validate and return
        if not is_bilingual(content):
            return self._clean_english_content(content)

        # For bilingual content, find the English section
        english_markers = [
            "MINISTRY OF CORPORATE AFFAIRS",
            "MINISTRY OF",
            "NOTIFICATION",
            "G.S.R.",
            "In exercise of the powers",
        ]

        # Try to find the earliest occurrence of any marker
        start_positions = []
        for marker in english_markers:
            pos = content.find(marker)
            if pos != -1:
                start_positions.append(pos)

        if not start_positions:
            raise ValueError("Could not find English content section")

        # Get the earliest position where English content starts
        english_start = min(start_positions)
        english_content = content[english_start:]

        # Clean up the extracted content
        english_content = self._clean_english_content(english_content)

        return english_content

    def _clean_ocr_artifacts(self, content: str) -> str:
        """Clean common OCR artifacts from the content."""
        # Remove unusual Unicode characters
        content = re.sub(r"[^\x00-\x7F\u0900-\u097F\s]", "", content)

        # Fix common OCR issues
        replacements = {
            "›": "",
            "‹": "",
            "»": "",
            "«": "",
            "¶": "",
            "§": "",
            "†": "",
            "‡": "",
            "•": "",
            "°": "degrees",
            "±": "plus-minus",
            "×": "x",
            "÷": "/",
        }

        for old, new in replacements.items():
            content = content.replace(old, new)

        # Fix common bracket issues
        content = re.sub(r"\[\s*\]", "", content)
        content = re.sub(r"\(\s*\)", "", content)

        return content

    def _clean_english_content(self, content: str) -> str:
        """Clean up extracted English content."""
        # Remove any remaining Hindi characters
        hindi_pattern = r"[\u0900-\u097F]+"
        content = re.sub(hindi_pattern, "", content)

        # Clean up whitespace
        content = re.sub(r"\s+", " ", content)
        content = re.sub(r"\n\s*\n", "\n\n", content)

        # Fix spacing around punctuation
        content = re.sub(r"\s+([.,;:)])", r"\1", content)
        content = re.sub(r"(\()\s+", r"\1", content)

        # Fix common formatting issues
        content = re.sub(r"_+", "", content)  # Remove underscores
        content = re.sub(r"-{2,}", "—", content)  # Fix dashes
        content = re.sub(r"\.{2,}", "...", content)  # Fix ellipsis

        # Fix spacing in common abbreviations
        content = re.sub(r"(?<=G)\.(?=S\.R)", ".", content)
        content = re.sub(r"(?<=S)\.(?=R)", ".", content)

        # Ensure proper spacing after periods
        content = re.sub(r"\.(?=[A-Z])", ". ", content)

        # Remove any duplicate spaces after cleaning
        content = re.sub(r"\s+", " ", content)

        return content.strip()

    def validate_content(self, content: str) -> bool:
        """Validate if the extracted content appears to be a valid notification."""
        required_elements = [
            (r"G\.S\.R\..*?\([A-Z]\)", "Missing G.S.R. number"),
            (r"NOTIFICATION", "Missing NOTIFICATION header"),
            (r"MINISTRY OF", "Missing Ministry reference"),
            (r"In exercise of", "Missing powers exercise reference"),
        ]

        for pattern, message in required_elements:
            if not re.search(pattern, content, re.IGNORECASE):
                logging.warning(f"Validation warning: {message}")
                return False

        return True

    def _extract_metadata(
        self, content: str, file_path: Path, doc_hash: str
    ) -> NotificationMetadata:
        """Extract metadata from the notification"""
        patterns = {
            "registry_number": r"REGD\. NO\. D\. L\.-(\d+/\d+)",
            "gazette_number": r"No\.\s+(\d+)\]",
            "publication_date": r"NEW DELHI,\s+(.*?)(?=\d{4})\d{4}",
            "indian_date": r"/([^/\n]+?)(?=\s*$)",
            "ministry": r"MINISTRY OF[^\n]+",
            "notification_number": r"G\.S\.R\.\s+(\d+)\([A-Z]\)",
            "notification_date": r"New Delhi,\s+the\s+(.*?)(?=\n)",
            "amendment_reference": r"to amend the ([^,]+),\s*(\d{4})",
        }

        matches = {
            key: re.search(pattern, content, re.DOTALL)
            for key, pattern in patterns.items()
        }

        # Extract amendment details if present
        amendment_details = None
        if matches.get("amendment_reference"):
            amendment_details = {
                "amended_rule": matches["amendment_reference"].group(1),
                "year": matches["amendment_reference"].group(2),
            }

        return NotificationMetadata(
            registry_number=(
                matches["registry_number"].group(1)
                if matches["registry_number"]
                else ""
            ),
            gazette_number=(
                matches["gazette_number"].group(1) if matches["gazette_number"] else ""
            ),
            publication_date=(
                matches["publication_date"].group(1).strip()
                if matches["publication_date"]
                else ""
            ),
            indian_date=(
                matches["indian_date"].group(1) if matches["indian_date"] else ""
            ),
            ministry=matches["ministry"].group(0) if matches["ministry"] else "",
            notification_number=(
                matches["notification_number"].group(1)
                if matches["notification_number"]
                else ""
            ),
            notification_date=(
                matches["notification_date"].group(1)
                if matches["notification_date"]
                else ""
            ),
            amendment_details=amendment_details,
            file_name=file_path.name,
            processing_timestamp=datetime.now().isoformat(),
            document_hash=doc_hash,
        )

    def _chunk_content(self, content: str) -> List[NotificationChunk]:
        """Chunk the notification content"""
        chunks = []

        # Split into major sections
        sections = self._split_into_sections(content)

        for section_idx, (section_type, section_content) in enumerate(sections):
            if section_type == "PREAMBLE":
                chunks.extend(self._process_preamble(section_content))
            elif section_type == "RULES":
                chunks.extend(self._process_rules(section_content))
            elif section_type == "CLOSING":
                chunks.extend(self._process_closing(section_content))

        return chunks

    def _split_into_sections(self, content: str) -> List[Tuple[str, str]]:
        """Split content into major sections"""
        sections = []

        # Find preamble (content before first rule)
        preamble_pattern = r"(G\.S\.R\..*?namely:—)"
        preamble_match = re.search(preamble_pattern, content, re.DOTALL)
        if preamble_match:
            sections.append(("PREAMBLE", preamble_match.group(1).strip()))

        # Find rules section
        rules_pattern = r"(?:namely:—\s*)((?:\d+\..*?)(?=\[F\. No\.|$))"
        rules_match = re.search(rules_pattern, content, re.DOTALL)
        if rules_match:
            rules_content = rules_match.group(1).strip()
            # Split individual rules
            rule_splits = re.split(r"(?=\d+\.(?:\s*\(\d+\))?)", rules_content)
            for rule in rule_splits:
                if rule.strip():
                    sections.append(("RULES", rule.strip()))

        # Find closing section
        closing_pattern = r"(\[F\. No\..*?(?:Note\s*:.*?)?)\s*$"
        closing_match = re.search(closing_pattern, content, re.DOTALL)
        if closing_match:
            sections.append(("CLOSING", closing_match.group(1).strip()))

        return sections

    def _process_preamble(self, content: str) -> List[NotificationChunk]:
        """Process preamble section"""
        return [
            NotificationChunk(
                chunk_id="preamble",
                chunk_type="PREAMBLE",
                rule_number=None,
                sub_rule_number=None,
                content=content,
                references=self._extract_references(content),
                context=self._extract_context(content),
            )
        ]

    def _process_rules(self, content: str) -> List[NotificationChunk]:
        """Process rules section"""
        chunks = []

        # Extract rule number
        rule_match = re.match(r"(\d+)\.", content)
        if not rule_match:
            return chunks

        rule_num = rule_match.group(1)

        # Check for sub-rules
        sub_rule_pattern = r"\((\d+)\)(.*?)(?=\(\d+\)|$)"
        sub_rules = list(re.finditer(sub_rule_pattern, content, re.DOTALL))

        if sub_rules:
            # Process each sub-rule
            for sub_rule in sub_rules:
                sub_rule_num = sub_rule.group(1)
                sub_rule_content = sub_rule.group(2).strip()

                # Check if content meets minimum size
                if len(sub_rule_content) >= self.min_chunk_size:
                    chunks.append(
                        NotificationChunk(
                            chunk_id=f"rule_{rule_num}_subrule_{sub_rule_num}",
                            chunk_type="SUB_RULE",
                            rule_number=rule_num,
                            sub_rule_number=sub_rule_num,
                            content=sub_rule_content,
                            references=self._extract_references(sub_rule_content),
                            context=self._extract_context(sub_rule_content),
                        )
                    )
        else:
            # Process as single rule
            chunks.append(
                NotificationChunk(
                    chunk_id=f"rule_{rule_num}",
                    chunk_type="RULE",
                    rule_number=rule_num,
                    sub_rule_number=None,
                    content=content,
                    references=self._extract_references(content),
                    context=self._extract_context(content),
                )
            )

        return chunks

    def _process_closing(self, content: str) -> List[NotificationChunk]:
        """Process closing section"""
        return [
            NotificationChunk(
                chunk_id="closing",
                chunk_type="CLOSING",
                rule_number=None,
                sub_rule_number=None,
                content=content,
                references=self._extract_references(content),
                context=self._extract_context(content),
            )
        ]

    def _extract_references(self, content: str) -> Dict[str, List[str]]:
        """Extract references from content"""
        references = {
            "acts": [],
            "sections": [],
            "rules": [],
            "notifications": [],
            "amendments": [],
        }

        # Extract act references
        act_pattern = r"(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Act,\s+\d{4})"
        references["acts"].extend(re.findall(act_pattern, content))

        # Extract section references
        section_pattern = r"[Ss]ection\s+(\d+(?:\s+read\s+with\s+[Ss]ection\s+\d+)?)"
        references["sections"].extend(re.findall(section_pattern, content))

        # Extract rule references
        rule_pattern = r"[Rr]ule\s+(\d+(?:\s*\(\d+\))?)"
        references["rules"].extend(re.findall(rule_pattern, content))

        # Extract notification references
        notification_pattern = r"G\.S\.R\.\s+\d+\([A-Z]\)"
        references["notifications"].extend(re.findall(notification_pattern, content))

        # Extract amendment references
        amendment_pattern = r"dated\s+the\s+\d+(?:st|nd|rd|th)?\s+\w+,\s+\d{4}"
        references["amendments"].extend(re.findall(amendment_pattern, content))

        return references

    def _extract_context(self, content: str) -> Dict[str, str]:
        """Extract context information"""
        context = {}

        # Identify chunk type
        if "Short title" in content:
            context["type"] = "title_and_commencement"
        elif "shall be substituted" in content:
            context["type"] = "amendment_substitution"
        elif "shall be omitted" in content:
            context["type"] = "amendment_omission"
        elif "shall be inserted" in content:
            context["type"] = "amendment_insertion"

        # Identify effective dates
        date_pattern = r"\d{1,2}(?:st|nd|rd|th)?\s+\w+,\s+\d{4}"
        dates = re.findall(date_pattern, content)
        if dates:
            context["dates"] = dates

        # Identify if it's a definition
        if re.search(r"means|shall mean|defined as", content.lower()):
            context["is_definition"] = "true"

        # Check for conditions
        if re.search(r"provided that|subject to", content.lower()):
            context["has_conditions"] = "true"

        return context
