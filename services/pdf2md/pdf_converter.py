import os
import fitz
import pymupdf4llm
from pathlib import Path
from typing import List, Optional


class PDFConverter:
    def __init__(self, input_dir: str, output_dir: Optional[str] = None):
        """Initialize the PDF converter with input and output directories

        Args:
            input_dir: Directory containing PDF files
            output_dir: Directory to save markdown files (defaults to input_dir/markdown)
        """
        self.input_dir = Path(input_dir)
        if output_dir:
            self.output_dir = Path(output_dir)
            os.makedirs(self.output_dir, exist_ok=True)
        else:
            raise ValueError("Output directory is required")

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def find_pdf_files(self) -> List[Path]:
        """Find all PDF files in the input directory recursively

        Returns:
            List of paths to PDF files
        """
        pdf_files = []
        for file in self.input_dir.rglob("*.pdf"):
            pdf_files.append(file)
        return pdf_files

    def convert_pdf_to_markdown(self, pdf_path: Path) -> str:
        """Convert a single PDF file to markdown

        Args:
            pdf_path: Path to PDF file

        Returns:
            Markdown text content
        """
        try:
            # Convert PDF to markdown using pymupdf4llm
            md_text = pymupdf4llm.to_markdown(str(pdf_path))
            return md_text
        except Exception as e:
            print(f"Error converting {pdf_path}: {str(e)}")
            return ""

    def save_markdown(self, md_text: str, original_pdf: Path):
        """Save markdown text to a file, preserving the input folder structure

        Args:
            md_text: Markdown text content
            original_pdf: Path to original PDF file
        """
        # Create relative path for the markdown file based on the input directory
        relative_path = original_pdf.relative_to(self.input_dir)
        output_path = self.output_dir / relative_path.with_suffix('.md')

        # Create the output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Save markdown content
            output_path.write_text(md_text, encoding="utf-8")
            print(f"Saved markdown to {output_path}")
        except Exception as e:
            print(f"Error saving {output_path}: {str(e)}")

    def process_directory(self):
        """Process all PDF files in the input directory"""
        pdf_files = self.find_pdf_files()

        if not pdf_files:
            print(f"No PDF files found in {self.input_dir}")
            return

        print(f"Found {len(pdf_files)} PDF files")

        for pdf_file in pdf_files:
            print(f"Converting {pdf_file}")
            md_text = self.convert_pdf_to_markdown(pdf_file)
            if md_text:
                self.save_markdown(md_text, pdf_file)
