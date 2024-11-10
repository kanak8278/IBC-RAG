import tiktoken
from typing import List, Dict, Any
import copy


class ChunkMergeRules:
    MIN_TOKENS = 150
    MAX_TOKENS = 600

    @staticmethod
    def should_merge(chunk1: Dict, chunk2: Dict, combined_tokens: int, encoder) -> bool:
        # Special case for very small chunks
        if combined_tokens < ChunkMergeRules.MIN_TOKENS:
            return True

        # Don't merge if would exceed max tokens
        if combined_tokens > ChunkMergeRules.MAX_TOKENS:
            return False

        # Special cases to always merge:
        # 1. If second chunk is tiny (like year or single line)
        if len(encoder.encode(chunk2["content"])) < 20:
            return True

        # 2. If chunks are consecutive DIRECTIVE paragraphs
        if (
            chunk1["chunk_type"] == chunk2["chunk_type"] == "DIRECTIVE"
            and chunk1.get("paragraph_number")
            and chunk2.get("paragraph_number")
        ):
            try:
                if (
                    abs(
                        int(chunk2["paragraph_number"])
                        - int(chunk1["paragraph_number"])
                    )
                    == 1
                ):
                    return True
            except ValueError:
                # Handle case where paragraph numbers aren't numeric
                pass

        return False


def handle_special_cases(chunks: List[Dict]) -> List[Dict]:
    """Handle special cases like year-only chunks"""
    chunks = copy.deepcopy(chunks)

    # Handle the year-only chunks (like "2016.")
    i = len(chunks) - 1
    while i > 0:
        if chunks[i]["content"].strip() in ["2016.", "2020."]:
            chunks[i - 1]["content"] += " " + chunks[i]["content"]
            chunks.pop(i)
        i -= 1
    return chunks


def merge_references(refs1: Dict, refs2: Dict) -> Dict:
    """Merge two reference dictionaries"""
    return {
        k: list(set(refs1.get(k, []) + refs2.get(k, [])))
        for k in set(refs1.keys()) | set(refs2.keys())
    }


def validate_chunk_size(chunk: Dict, encoder) -> bool:
    """Validate if chunk is within acceptable token limits"""
    tokens = len(encoder.encode(chunk["content"]))
    return ChunkMergeRules.MIN_TOKENS <= tokens <= ChunkMergeRules.MAX_TOKENS


def merge_chunks(chunks: List[Dict], metadata: Dict) -> List[Dict]:
    """Main function to merge chunks according to rules"""
    encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")

    # First handle special cases
    chunks = handle_special_cases(chunks)

    merged_chunks = []
    current_chunk = None

    for chunk in chunks:
        if current_chunk is None:
            current_chunk = copy.deepcopy(chunk)
            continue

        # Calculate combined tokens
        combined_content = current_chunk["content"] + " " + chunk["content"]
        combined_tokens = len(encoder.encode(combined_content))

        if ChunkMergeRules.should_merge(current_chunk, chunk, combined_tokens, encoder):
            # Merge chunks
            current_chunk["content"] = combined_content

            # Merge references
            current_chunk["references"] = merge_references(
                current_chunk["references"], chunk["references"]
            )

            # Update paragraph numbers
            if current_chunk.get("paragraph_number") and chunk.get("paragraph_number"):
                current_chunk["paragraph_numbers"] = [
                    str(current_chunk.get("paragraph_number")),
                    str(chunk.get("paragraph_number")),
                ]
                del current_chunk["paragraph_number"]
        else:
            # Add metadata to chunk before storing
            current_chunk["metadata"] = {
                "circular_number": metadata["circular_number"],
                "date": metadata["date"],
                "subject": metadata["subject"],
            }
            merged_chunks.append(current_chunk)
            current_chunk = copy.deepcopy(chunk)

    if current_chunk is not None:
        current_chunk["metadata"] = {
            "circular_number": metadata["circular_number"],
            "date": metadata["date"],
            "subject": metadata["subject"],
        }
        merged_chunks.append(current_chunk)

    return merged_chunks
