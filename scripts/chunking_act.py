import json
import re


def identify_section_level(line):
    """Identify the heading level and section number"""
    if line.startswith("#"):
        level = len(re.match(r"^#+", line).group())
        # Extract section number if present
        section_number = re.search(r"\d+\.", line)
        return {
            "level": level,
            "section_number": section_number.group() if section_number else None,
            "text": line.strip("# "),
        }
    return None


def get_section_hierarchy(lines):
    """Build section hierarchy tree"""
    hierarchy = []
    current_path = []

    for line in lines:
        section = identify_section_level(line)
        if section:
            level = section["level"]
            # Adjust current path based on level
            while len(current_path) >= level:
                current_path.pop()
            current_path.append(section)
            hierarchy.append({"path": current_path.copy(), "content": []})
    return hierarchy


def is_paragraph_break(line):
    """Check if line indicates paragraph break"""
    return line.strip() == ""


def is_list_item(line):
    """Check if line is a list item"""
    return bool(re.match(r"^[\*\-\+]\s+|^\d+\.\s+", line.strip()))


def chunk_markdown_document(text, max_chunk_size=1000):
    """
    Chunk markdown document while preserving structure
    """
    chunks = []
    current_chunk = []
    current_size = 0
    section_stack = []

    lines = text.splitlines()

    for i, line in enumerate(lines):
        # Handle section headers
        if line.startswith("#"):
            if current_chunk:
                # Complete current chunk before new section
                chunks.append(
                    {
                        "content": "\n".join(current_chunk),
                        "sections": section_stack.copy(),
                    }
                )
                current_chunk = []
                current_size = 0

            # Update section stack
            level = len(re.match(r"^#+", line).group())
            while section_stack and section_stack[-1]["level"] >= level:
                section_stack.pop()
            section_stack.append({"level": level, "title": line.strip("# ")})

        # Handle paragraph breaks
        if is_paragraph_break(line):
            if current_size >= max_chunk_size:
                chunks.append(
                    {
                        "content": "\n".join(current_chunk),
                        "sections": section_stack.copy(),
                    }
                )
                current_chunk = []
                current_size = 0

        # Handle list items
        if is_list_item(line):
            # Keep list items together
            while i < len(lines) and (is_list_item(lines[i]) or lines[i].strip() == ""):
                current_chunk.append(lines[i])
                current_size += len(lines[i])
                i += 1
            continue

        current_chunk.append(line)
        current_size += len(line)

        # Check size limit while respecting paragraph integrity
        if current_size >= max_chunk_size:
            # Look back for paragraph break
            break_index = len(current_chunk) - 1
            while break_index > 0 and not is_paragraph_break(
                current_chunk[break_index]
            ):
                break_index -= 1

            if break_index > 0:
                chunks.append(
                    {
                        "content": "\n".join(current_chunk[:break_index]),
                        "sections": section_stack.copy(),
                    }
                )
                current_chunk = current_chunk[break_index:]
                current_size = sum(len(line) for line in current_chunk)

    # Add final chunk
    if current_chunk:
        chunks.append({"content": "\n".join(current_chunk), "sections": section_stack})

    return chunks


def add_context_overlap(chunks, overlap_size=100):
    """Add controlled overlap between chunks"""
    processed_chunks = []

    for i in range(len(chunks)):
        chunk = chunks[i]

        # Add previous context
        if i > 0:
            prev_lines = chunks[i - 1]["content"].splitlines()
            context_lines = []
            size = 0
            for line in reversed(prev_lines):
                if size + len(line) > overlap_size:
                    break
                context_lines.insert(0, line)
                size += len(line)
            if context_lines:
                chunk["previous_context"] = "\n".join(context_lines)

        # Add next context
        if i < len(chunks) - 1:
            next_lines = chunks[i + 1]["content"].splitlines()
            context_lines = []
            size = 0
            for line in next_lines:
                if size + len(line) > overlap_size:
                    break
                context_lines.append(line)
                size += len(line)
            if context_lines:
                chunk["next_context"] = "\n".join(context_lines)

        processed_chunks.append(chunk)

    return processed_chunks


if __name__ == "__main__":
    with open("data/ibbi_raw/IBC ACT-2021-indiacode.md", "r") as file:
        text = file.read()
    chunks = chunk_markdown_document(text, 500)
    chunks = add_context_overlap(chunks, 50)
    print(json.dumps(chunks, indent=4))
