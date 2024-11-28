import re
import json


class CodeParser:
    def __init__(self):
        self.code_structure = {
            "code_name": "",
            "code_number": "",
            "date": "",
            "parts": [],
        }
        self.current_part = None
        self.current_chapter = None
        self.current_section = None
        self.current_content = []

    def parse_code(self, text):
        lines = text.split("\n")
        i = 0

        # Parse header
        while i < len(lines) and i < 10:
            line = lines[i].strip()
            if "THE INSOLVENCY AND BANKRUPTCY CODE" in line:
                self.code_structure["code_name"] = line
            elif "ACT NO." in line:
                self.code_structure["code_number"] = line
            elif "[" in line and "]" in line and "." in line:
                self.code_structure["date"] = line
            i += 1

        # Parse main content
        while i < len(lines):
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            # Part detection
            if re.match(r"^PART\s+[I|V|X]+", line):
                self.save_current_section()
                self.parse_part(line)
                # Create default chapter for parts without explicit chapters
                self.create_default_chapter()

            # Chapter detection
            elif re.match(r"^CHAPTER\s+[I|V|X]+", line):
                self.save_current_section()
                self.parse_chapter(line)

            # Section detection
            elif re.match(r"^\d+\.\s*[A-Z]", line):
                self.save_current_section()
                if not self.current_chapter:
                    self.create_default_chapter()
                self.parse_section(line)

            # Content line
            elif self.current_section:
                self.current_content.append(line)

            i += 1

        # Save the last section
        self.save_current_section()

    def create_default_chapter(self):
        """Create a default chapter if part has no explicit chapters"""
        if self.current_part and not self.current_part["chapters"]:
            chapter = {
                "chapter_number": "CHAPTER I",
                "chapter_name": "General",
                "sections": [],
            }
            self.current_part["chapters"].append(chapter)
            self.current_chapter = chapter

    def save_current_section(self):
        """Save accumulated content to current section"""
        if self.current_section and self.current_content:
            # Clean and join the content
            content = " ".join(self.current_content)
            content = re.sub(r"\s+", " ", content).strip()  # Remove extra whitespace
            self.current_section["content"] = content
            self.current_content = []

    def parse_part(self, line):
        """Parse part header and create new part structure"""
        part_match = re.match(r"^(PART\s+[I|V|X]+)\s*(.*)", line)
        if part_match:
            part = {
                "part_number": part_match.group(1),
                "part_name": part_match.group(2),
                "chapters": [],
            }
            self.code_structure["parts"].append(part)
            self.current_part = part
            self.current_chapter = None

    def parse_chapter(self, line):
        """Parse chapter header and create new chapter structure"""
        if not self.current_part:
            return

        chapter_match = re.match(r"^(CHAPTER\s+[I|V|X]+)\s*(.*)", line)
        if chapter_match:
            chapter = {
                "chapter_number": chapter_match.group(1),
                "chapter_name": chapter_match.group(2),
                "sections": [],
            }
            self.current_part["chapters"].append(chapter)
            self.current_chapter = chapter

    def parse_section(self, line):
        """Parse section header and create new section structure"""
        if not self.current_chapter:
            return

        # Handle various section header formats
        section_match = re.match(r"^(\d+)\.\s*(.*?)(?:\.—|\.|\-)\s*(.*)", line)
        if section_match:
            section = {
                "section_number": section_match.group(1),
                "section_name": section_match.group(2).strip(),
                "content": "",
            }
            if section_match.group(3):  # If there's content on the same line
                self.current_content.append(section_match.group(3))

            self.current_chapter["sections"].append(section)
            self.current_section = section

    def save_to_json(self, filename):
        """Save parsed structure to JSON file"""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.code_structure, f, indent=4, ensure_ascii=False)


def main():
    # Read the code text from file
    act_file = "data/ibbi_raw/IBC ACT-2021-indiacode.md"

    with open(act_file, "r", encoding="utf-8") as f:
        code_text = f.read()

    # Create parser instance and parse
    parser = CodeParser()
    parser.parse_code(code_text)

    # Save structured content to JSON
    parser.save_to_json("insolvency_code_structured.json")


if __name__ == "__main__":
    main()
