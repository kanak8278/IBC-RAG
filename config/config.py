# config.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class AzureConfig:
    api_key: str
    api_base: str
    api_version: str
    embedding_deployment: str
    embedding_model: str = "text-embedding-3-small"
    dimension: int = 1536
    max_retries: int = 3


@dataclass
class ChromaConfig:
    persist_directory: str
    collection_name: str
    distance_metric: str = "cosine"


@dataclass
class VectorDBConfig:
    azure: AzureConfig
    chroma: ChromaConfig
