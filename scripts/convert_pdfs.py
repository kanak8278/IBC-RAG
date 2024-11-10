#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

# Add parent directory to path so we can import the module
sys.path.append(str(Path(__file__).parent.parent))

from services.pdf2md.pdf_converter import PDFConverter


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Convert PDF files to markdown")
    parser.add_argument("-i", "--input_dir", help="Directory containing PDF files")
    parser.add_argument(
        "-o", "--output_dir", help="Output directory for markdown files"
    )

    args = parser.parse_args()

    # Create converter instance
    converter = PDFConverter(args.input_dir, args.output_dir)

    # Process all PDFs in directory
    converter.process_directory()


if __name__ == "__main__":
    main()
