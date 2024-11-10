# models/circular.py

from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime


@dataclass
class CircularMetadata:
    authority: str
    circular_number: str
    date: str
    subject: str
    total_pages: Optional[int]
    reference_circulars: List[str]
    effective_date: Optional[str]
    power_reference: str
    file_name: str
    processing_timestamp: str
    document_hash: str


@dataclass
class CircularChunk:
    chunk_id: str
    chunk_type: str
    content: str
    paragraph_numbers: Optional[List[str]]
    references: Dict[str, List[str]]
    context: Dict[str, Any]
    metadata: Dict[str, str]


@dataclass
class Circular:
    metadata: CircularMetadata
    merged_chunks: List[CircularChunk]
    processing_info: Dict[str, Any]
