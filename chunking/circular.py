# import re
# from typing import Dict, List, Optional, Tuple
# from dataclasses import dataclass, asdict
# from pathlib import Path
# import json
# from datetime import datetime
# import hashlib


# @dataclass
# class CircularMetadata:
#     authority: str
#     circular_number: str
#     date: str
#     subject: str
#     total_pages: Optional[int]
#     reference_circulars: List[str]
#     effective_date: Optional[str]
#     power_reference: Optional[str]
#     file_name: str
#     processing_timestamp: str
#     document_hash: str


# @dataclass
# class CircularChunk:
#     chunk_id: str
#     chunk_type: str
#     paragraph_number: Optional[str]
#     content: str
#     references: Dict[str, List[str]]
#     context: Dict[str, str]


# class CircularProcessor:
#     def __init__(
#         self,
#         min_chunk_size: int = 150,
#         max_chunk_size: int = 750,
#         overlap_size: int = 50
#     ):
#         self.min_chunk_size = min_chunk_size
#         self.max_chunk_size = max_chunk_size
#         self.overlap_size = overlap_size
#         self.metadata = None
#         self.chunks = []

#     def process_file(self, file_path: Path) -> Dict:
#         """Process a single circular MD file"""
#         with open(file_path, "r", encoding="utf-8") as file:
#             content = file.read()

#         # Generate document hash
#         doc_hash = hashlib.md5(content.encode()).hexdigest()

#         # Extract metadata
#         self.metadata = self._extract_metadata(content, file_path, doc_hash)

#         # Extract chunks
#         self.chunks = self._chunk_content(content)

#         return {
#             "metadata": asdict(self.metadata),
#             "chunks": [asdict(chunk) for chunk in self.chunks],
#         }

#     def _extract_metadata(
#         self, content: str, file_path: Path, doc_hash: str
#     ) -> CircularMetadata:
#         """Extract metadata from the circular"""
#         # Basic patterns
#         patterns = {
#             "authority": r"\*\*(.*?Board of India)\*\*",
#             "date": [
#                 # Pattern 1: Basic format with optional comma
#                 r"(\d{1,2}\[(?:st|nd|rd|th)\]\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)(?:,)?\s+\d{4})",
#                 # Pattern 2: Handle extra spaces in ordinal brackets
#                 r"(\d{1,2}\[(?:st|nd|rd|th)\s*\]\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)(?:,)?\s+\d{4})",
#                 # Pattern 3: Handle dates on the same line as circular number
#                 r"No.*?\s+(\d{1,2}\[(?:st|nd|rd|th)\s*\]\s*(?:January|February|March|April|May|June|July|August|September|October|November|December)(?:,)?\s+\d{4})",
#                 # Pattern 4: Most flexible pattern (use last)
#                 r"(\d{1,2}\[(?:st|nd|rd|th)\s*\][\s\*]*(?:January|February|March|April|May|June|July|August|September|October|November|December)(?:,)?[\s\*]+\d{4})",
#                 r"(\d{1,2}\[(?:st|nd|rd|th)\]\s+\w+(?:,)?\s+\d{4})",
#             ],
#             "circular_number": [
#                 r"No[.:]\s*((?:IP|IBBI|IBC|LA|RVO)/\d{3}/\d{4})",  # Basic format with colon or dot
#                 r"No[.:]\s*((?:IBBI|IP|IBC|LA|RVO)/[A-Z]+/\d+/\d{4})",  # With department codes
#                 r"No[.:]\s*((?:IBBI|IP|IBC|LA|RVO)/[A-Z]+/[A-Z0-9]+/\d{4})",  # Extended format
#                 r"No[.:]\s*((?:IBBI|IP|IBC|LA|RVO)[-_][A-Z]+/\d+/\d{4})",  # With dash/underscore
#                 r"No[.:]\s*((?:IP|IBBI|IBC|LA|RVO)\([A-Z]+\)/\d{3}/\d{4})",  # With parentheses
#                 r"No[.:]\s*((?:IP|IBBI|IBC|LA|RVO)\([A-Za-z]+\)/[\w-]+/\d{4})",  # More flexible parentheses
#                 r"No[.:]\s*((?:[A-Z]+)/[\w/()]+)",  # Most flexible pattern (use last)
#             ],
#             "subject": r"\*\*(?:Sub(?:ject)?:)(.*?)\*\*(?=\n)",
#             "reference_circulars": r"Circular\s+No\.\s+(IBBI/[\w/]+)",
#             "effective_date": r"(?:come into force|effect)\s+from\s+(\d{1,2}\[(?:st|nd|rd|th)\]\s+\w+(?:,)?\s+\d{4})",
#             "power_reference": r"(?:exercise of|under).*?(?:section|Section)\s+(\d+(?:\s+read\s+with\s+section\s+\d+)?)",
#             "total_pages": r"Page\s+\d+\s+of\s+(\d+)",
#         }

#         # Extract values with special handling for circular number
#         matches = {}
#         for key, pattern in patterns.items():
#             if key == "date":
#                 # Try each pattern in order until a match is found
#                 for date_pattern in pattern:
#                     if match := re.search(date_pattern, content, re.DOTALL):
#                         matches[key] = match
#                         break
#             elif key == "circular_number":
#                 # Try each pattern in order until a match is found
#                 for circular_pattern in pattern:
#                     if match := re.search(circular_pattern, content, re.DOTALL):
#                         matches[key] = match
#                         break
#                 if key not in matches:
#                     matches[key] = None
#             else:
#                 matches[key] = re.search(pattern, content, re.DOTALL)

#         # Find reference circulars
#         reference_circulars = re.findall(patterns["reference_circulars"], content)

#         return CircularMetadata(
#             authority=matches["authority"].group(1) if matches["authority"] else "",
#             circular_number=(
#                 matches["circular_number"].group(1)
#                 if matches["circular_number"]
#                 else ""
#             ),
#             date=matches["date"].group(1) if matches["date"] else "",
#             subject=matches["subject"].group(1).strip() if matches["subject"] else "",
#             total_pages=(
#                 int(matches["total_pages"].group(1)) if matches["total_pages"] else None
#             ),
#             reference_circulars=reference_circulars,
#             effective_date=(
#                 matches["effective_date"].group(1)
#                 if matches["effective_date"]
#                 else None
#             ),
#             power_reference=(
#                 matches["power_reference"].group(1)
#                 if matches["power_reference"]
#                 else None
#             ),
#             file_name=file_path.name,
#             processing_timestamp=datetime.now().isoformat(),
#             document_hash=doc_hash,
#         )

#     def _chunk_content(self, content: str) -> List[CircularChunk]:
#         """Chunk the circular content"""
#         chunks = []

#         # Remove header and metadata section
#         main_content = self._remove_header_section(content)

#         # Split into major sections
#         sections = self._split_into_sections(main_content)

#         for section_type, section_content in sections:
#             if section_type == "CONTEXT":
#                 chunks.extend(self._process_context_section(section_content))
#             elif section_type == "DIRECTIVE":
#                 chunks.extend(self._process_directive_section(section_content))
#             elif section_type == "CLOSING":
#                 chunks.extend(self._process_closing_section(section_content))

#         return chunks

#     def _chunk_text(self, text: str) -> List[str]:
#         """Split text into chunks respecting size constraints and overlap"""
#         words = text.split()
#         chunks = []

#         if len(words) <= self.min_chunk_size:
#             return [text]

#         current_pos = 0

#         while current_pos < len(words):
#             # Calculate end position for current chunk
#             chunk_end = min(
#                 current_pos + self.max_chunk_size,
#                 len(words)
#             )

#             # If this is not the last chunk and we're not at minimum size
#             if chunk_end < len(words) and chunk_end - current_pos > self.min_chunk_size:
#                 # Look for a sentence boundary
#                 for i in range(chunk_end - 1, current_pos + self.min_chunk_size - 1, -1):
#                     if i < len(words) and words[i].endswith(('.', '?', '!')):
#                         chunk_end = i + 1
#                         break

#             # Create chunk
#             chunk = ' '.join(words[current_pos:chunk_end])
#             chunks.append(chunk)

#             # Move position considering overlap
#             current_pos = max(
#                 current_pos + 1,  # Ensure we make progress
#                 chunk_end - self.overlap_size
#             )

#         return chunks

#     def _remove_header_section(self, content: str) -> str:
#         """Remove header and metadata section"""
#         subject_pattern = r"\*\*(?:Sub(?:ject)?:.*?\*\*\n\n)(.*)"
#         match = re.search(subject_pattern, content, re.DOTALL)
#         return match.group(1) if match else content

#     def _split_into_sections(self, content: str) -> List[Tuple[str, str]]:
#         """Split content into major sections"""
#         sections = []

#         # Find initial context (non-numbered paragraphs)
#         context_pattern = r"^(.*?)(?=\d+\.)"
#         context_match = re.search(context_pattern, content, re.DOTALL)
#         if context_match and context_match.group(1).strip():
#             sections.append(("CONTEXT", context_match.group(1).strip()))

#         # Find numbered paragraphs (directives)
#         directive_pattern = r"(\d+\.(.*?)(?=(?:\d+\.|This is issued|Yours faithfully)))"
#         directive_matches = re.finditer(directive_pattern, content, re.DOTALL)
#         for match in directive_matches:
#             sections.append(("DIRECTIVE", match.group(0).strip()))

#         # Find closing section
#         closing_pattern = r"(This is issued.*?$)"
#         closing_match = re.search(closing_pattern, content, re.DOTALL)
#         if closing_match:
#             sections.append(("CLOSING", closing_match.group(1).strip()))

#         return sections

#     def _process_context_section(self, content: str) -> List[CircularChunk]:
#         """Process context section with chunking"""
#         chunks = self._chunk_text(content)
#         return [
#             CircularChunk(
#                 chunk_id=f"context_{i+1}",
#                 chunk_type="CONTEXT",
#                 paragraph_number=None,
#                 content=chunk,
#                 references=self._extract_references(chunk),
#                 context=self._extract_context(chunk),
#             )
#             for i, chunk in enumerate(chunks)
#         ]

#     def _process_directive_section(self, content: str) -> List[CircularChunk]:
#         """Process directive section with chunking"""
#         # Extract paragraph number
#         para_num = re.match(r"(\d+)\.", content).group(1)

#         # Check if it contains sub-points
#         if re.search(r"\([a-z]\)", content):
#             # For content with sub-points, chunk while keeping sub-points together
#             sub_points = re.split(r"(?=\([a-z]\))", content)
#             current_chunk = []
#             chunks = []

#             for point in sub_points:
#                 current_chunk.append(point)
#                 combined = " ".join(current_chunk)

#                 if len(combined.split()) >= self.max_chunk_size:
#                     # Save current chunk and start new one
#                     chunks.append(" ".join(current_chunk[:-1]))
#                     current_chunk = [point]

#             if current_chunk:
#                 chunks.append(" ".join(current_chunk))
#         else:
#             # For regular content, use standard chunking
#             chunks = self._chunk_text(content)

#         return [
#             CircularChunk(
#                 chunk_id=f"directive_{para_num}_{i+1}",
#                 chunk_type="DIRECTIVE",
#                 paragraph_number=para_num,
#                 content=chunk,
#                 references=self._extract_references(chunk),
#                 context=self._extract_context(chunk),
#             )
#             for i, chunk in enumerate(chunks)
#         ]

#     def _process_closing_section(self, content: str) -> List[CircularChunk]:
#         """Process closing section with chunking"""
#         chunks = self._chunk_text(content)
#         return [
#             CircularChunk(
#                 chunk_id=f"closing_{i+1}",
#                 chunk_type="POWER_CITATION",
#                 paragraph_number=None,
#                 content=chunk,
#                 references=self._extract_references(chunk),
#                 context=self._extract_context(chunk),
#             )
#             for i, chunk in enumerate(chunks)
#         ]

#     def _extract_references(self, content: str) -> Dict[str, List[str]]:
#         """Extract references from content"""
#         references = {
#             "circulars": [],
#             "sections": [],
#             "regulations": [],
#             "external_links": [],
#         }

#         # Extract circular references
#         circular_refs = re.findall(r"Circular\s+No\.\s+(IBBI/[\w/]+)", content)
#         references["circulars"].extend(circular_refs)

#         # Extract section references
#         section_refs = re.findall(
#             r"[Ss]ection\s+(\d+(?:\s+read\s+with\s+section\s+\d+)?)", content
#         )
#         references["sections"].extend(section_refs)

#         # Extract regulation references
#         regulation_refs = re.findall(r"Regulation\s+(\d+(?:\s*\(\d+\))?)", content)
#         references["regulations"].extend(regulation_refs)

#         # Extract URLs
#         urls = re.findall(r"https?://[^\s\]]+", content)
#         references["external_links"].extend(urls)

#         return references

#     def _extract_context(self, content: str) -> Dict[str, str]:
#         """Extract context information"""
#         context = {}

#         # Identify directive type
#         if "shall" in content.lower():
#             context["directive_type"] = "mandatory"
#         elif "may" in content.lower():
#             context["directive_type"] = "optional"

#         # Identify if there are deadlines
#         date_matches = re.findall(r"\d{2}\.\d{2}\.\d{4}", content)
#         if date_matches:
#             context["deadlines"] = date_matches

#         # Identify if there are conditions
#         if "subject to" in content.lower():
#             context["has_conditions"] = "true"

#         # Identify if there are examples
#         if "example" in content.lower():
#             context["has_examples"] = "true"

#         return context


import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import json
from datetime import datetime
import hashlib


@dataclass
class CircularMetadata:
    authority: str
    circular_number: str
    date: str
    subject: str
    total_pages: Optional[int]
    reference_circulars: List[str]
    effective_date: Optional[str]
    power_reference: Optional[str]
    file_name: str
    processing_timestamp: str
    document_hash: str


@dataclass
class CircularChunk:
    chunk_id: str
    chunk_type: str
    paragraph_number: Optional[str]
    content: str
    references: Dict[str, List[str]]
    context: Dict[str, str]


class CircularProcessor:
    def __init__(self, target_chunk_size: int = 512):
        self.target_chunk_size = target_chunk_size
        self.metadata = None
        self.chunks = []

    def process_file(self, file_path: Path) -> Dict:
        """Process a single circular MD file"""
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        # Generate document hash
        doc_hash = hashlib.md5(content.encode()).hexdigest()

        # Extract metadata
        self.metadata = self._extract_metadata(content, file_path, doc_hash)

        # Extract chunks
        self.chunks = self._chunk_content(content)

        return {
            "metadata": asdict(self.metadata),
            "chunks": [asdict(chunk) for chunk in self.chunks],
        }

    def _extract_metadata(
        self, content: str, file_path: Path, doc_hash: str
    ) -> CircularMetadata:
        """Extract metadata from the circular"""
        # Basic patterns
        patterns = {
            "authority": r"\*\*(.*?Board of India)\*\*",
            "date": [
                # Pattern 1: Basic format with optional comma
                r"(\d{1,2}\[(?:st|nd|rd|th)\]\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)(?:,)?\s+\d{4})",
                # Pattern 2: Handle extra spaces in ordinal brackets
                r"(\d{1,2}\[(?:st|nd|rd|th)\s*\]\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)(?:,)?\s+\d{4})",
                # Pattern 3: Handle dates on the same line as circular number
                r"No.*?\s+(\d{1,2}\[(?:st|nd|rd|th)\s*\]\s*(?:January|February|March|April|May|June|July|August|September|October|November|December)(?:,)?\s+\d{4})",
                # Pattern 4: Most flexible pattern (use last)
                r"(\d{1,2}\[(?:st|nd|rd|th)\s*\][\s\*]*(?:January|February|March|April|May|June|July|August|September|October|November|December)(?:,)?[\s\*]+\d{4})",
                r"(\d{1,2}\[(?:st|nd|rd|th)\]\s+\w+(?:,)?\s+\d{4})",
            ],
            "circular_number": [
                r"No[.:]\s*((?:IP|IBBI|IBC|LA|RVO)/\d{3}/\d{4})",  # Basic format with colon or dot
                r"No[.:]\s*((?:IBBI|IP|IBC|LA|RVO)/[A-Z]+/\d+/\d{4})",  # With department codes
                r"No[.:]\s*((?:IBBI|IP|IBC|LA|RVO)/[A-Z]+/[A-Z0-9]+/\d{4})",  # Extended format
                r"No[.:]\s*((?:IBBI|IP|IBC|LA|RVO)[-_][A-Z]+/\d+/\d{4})",  # With dash/underscore
                r"No[.:]\s*((?:IP|IBBI|IBC|LA|RVO)\([A-Z]+\)/\d{3}/\d{4})",  # With parentheses
                r"No[.:]\s*((?:IP|IBBI|IBC|LA|RVO)\([A-Za-z]+\)/[\w-]+/\d{4})",  # More flexible parentheses
                r"No[.:]\s*((?:[A-Z]+)/[\w/()]+)",  # Most flexible pattern (use last)
            ],
            "subject": r"\*\*(?:Sub(?:ject)?:)(.*?)\*\*(?=\n)",
            "reference_circulars": r"Circular\s+No\.\s+(IBBI/[\w/]+)",
            "effective_date": r"(?:come into force|effect)\s+from\s+(\d{1,2}\[(?:st|nd|rd|th)\]\s+\w+(?:,)?\s+\d{4})",
            "power_reference": r"(?:exercise of|under).*?(?:section|Section)\s+(\d+(?:\s+read\s+with\s+section\s+\d+)?)",
            "total_pages": r"Page\s+\d+\s+of\s+(\d+)",
        }

        # Extract values with special handling for circular number
        matches = {}
        for key, pattern in patterns.items():
            if key == "date":
                # Try each pattern in order until a match is found
                for date_pattern in pattern:
                    if match := re.search(date_pattern, content, re.DOTALL):
                        matches[key] = match
                        break
            elif key == "circular_number":
                # Try each pattern in order until a match is found
                for circular_pattern in pattern:
                    if match := re.search(circular_pattern, content, re.DOTALL):
                        matches[key] = match
                        break
                if key not in matches:
                    matches[key] = None
            else:
                matches[key] = re.search(pattern, content, re.DOTALL)

        # Find reference circulars
        reference_circulars = re.findall(patterns["reference_circulars"], content)

        return CircularMetadata(
            authority=matches["authority"].group(1) if matches["authority"] else "",
            circular_number=(
                matches["circular_number"].group(1)
                if matches["circular_number"]
                else ""
            ),
            date=matches["date"].group(1) if matches["date"] else "",
            subject=matches["subject"].group(1).strip() if matches["subject"] else "",
            total_pages=(
                int(matches["total_pages"].group(1)) if matches["total_pages"] else None
            ),
            reference_circulars=reference_circulars,
            effective_date=(
                matches["effective_date"].group(1)
                if matches["effective_date"]
                else None
            ),
            power_reference=(
                matches["power_reference"].group(1)
                if matches["power_reference"]
                else None
            ),
            file_name=file_path.name,
            processing_timestamp=datetime.now().isoformat(),
            document_hash=doc_hash,
        )

    def _chunk_content(self, content: str) -> List[CircularChunk]:
        """Chunk the circular content"""
        chunks = []

        # Remove header and metadata section
        main_content = self._remove_header_section(content)

        # Split into major sections
        sections = self._split_into_sections(main_content)

        for section_type, section_content in sections:
            if section_type == "CONTEXT":
                chunks.extend(self._process_context_section(section_content))
            elif section_type == "DIRECTIVE":
                chunks.extend(self._process_directive_section(section_content))
            elif section_type == "CLOSING":
                chunks.extend(self._process_closing_section(section_content))

        return chunks

    def _remove_header_section(self, content: str) -> str:
        """Remove header and metadata section"""
        subject_pattern = r"\*\*(?:Sub(?:ject)?:.*?\*\*\n\n)(.*)"
        match = re.search(subject_pattern, content, re.DOTALL)
        return match.group(1) if match else content

    def _split_into_sections(self, content: str) -> List[Tuple[str, str]]:
        """Split content into major sections"""
        sections = []

        # Find initial context (non-numbered paragraphs)
        context_pattern = r"^(.*?)(?=\d+\.)"
        context_match = re.search(context_pattern, content, re.DOTALL)
        if context_match and context_match.group(1).strip():
            sections.append(("CONTEXT", context_match.group(1).strip()))

        # Find numbered paragraphs (directives)
        directive_pattern = r"(\d+\.(.*?)(?=(?:\d+\.|This is issued|Yours faithfully)))"
        directive_matches = re.finditer(directive_pattern, content, re.DOTALL)
        for match in directive_matches:
            sections.append(("DIRECTIVE", match.group(0).strip()))

        # Find closing section
        closing_pattern = r"(This is issued.*?$)"
        closing_match = re.search(closing_pattern, content, re.DOTALL)
        if closing_match:
            sections.append(("CLOSING", closing_match.group(1).strip()))

        return sections

    def _process_context_section(self, content: str) -> List[CircularChunk]:
        """Process context section"""
        return [
            CircularChunk(
                chunk_id=f"context_1",
                chunk_type="CONTEXT",
                paragraph_number=None,
                content=content,
                references=self._extract_references(content),
                context=self._extract_context(content),
            )
        ]

    def _process_directive_section(self, content: str) -> List[CircularChunk]:
        """Process directive section"""
        # Extract paragraph number
        para_num = re.match(r"(\d+)\.", content).group(1)

        # Check if it contains sub-points
        if re.search(r"\([a-z]\)", content):
            # Keep all sub-points together
            return [
                CircularChunk(
                    chunk_id=f"directive_{para_num}",
                    chunk_type="DIRECTIVE",
                    paragraph_number=para_num,
                    content=content,
                    references=self._extract_references(content),
                    context=self._extract_context(content),
                )
            ]
        else:
            # Single directive
            return [
                CircularChunk(
                    chunk_id=f"para_{para_num}",
                    chunk_type="DIRECTIVE",
                    paragraph_number=para_num,
                    content=content,
                    references=self._extract_references(content),
                    context=self._extract_context(content),
                )
            ]

    def _process_closing_section(self, content: str) -> List[CircularChunk]:
        """Process closing section"""
        return [
            CircularChunk(
                chunk_id="closing",
                chunk_type="POWER_CITATION",
                paragraph_number=None,
                content=content,
                references=self._extract_references(content),
                context=self._extract_context(content),
            )
        ]

    def _extract_references(self, content: str) -> Dict[str, List[str]]:
        """Extract references from content"""
        references = {
            "circulars": [],
            "sections": [],
            "regulations": [],
            "external_links": [],
        }

        # Extract circular references
        circular_refs = re.findall(r"Circular\s+No\.\s+(IBBI/[\w/]+)", content)
        references["circulars"].extend(circular_refs)

        # Extract section references
        section_refs = re.findall(
            r"[Ss]ection\s+(\d+(?:\s+read\s+with\s+section\s+\d+)?)", content
        )
        references["sections"].extend(section_refs)

        # Extract regulation references
        regulation_refs = re.findall(r"Regulation\s+(\d+(?:\s*\(\d+\))?)", content)
        references["regulations"].extend(regulation_refs)

        # Extract URLs
        urls = re.findall(r"https?://[^\s\]]+", content)
        references["external_links"].extend(urls)

        return references

    def _extract_context(self, content: str) -> Dict[str, str]:
        """Extract context information"""
        context = {}

        # Identify directive type
        if "shall" in content.lower():
            context["directive_type"] = "mandatory"
        elif "may" in content.lower():
            context["directive_type"] = "optional"

        # Identify if there are deadlines
        date_matches = re.findall(r"\d{2}\.\d{2}\.\d{4}", content)
        if date_matches:
            context["deadlines"] = date_matches

        # Identify if there are conditions
        if "subject to" in content.lower():
            context["has_conditions"] = "true"

        # Identify if there are examples
        if "example" in content.lower():
            context["has_examples"] = "true"

        return context
