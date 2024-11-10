import argparse
import json
import os
import tiktoken
from typing import Dict, List
from pathlib import Path
from datetime import datetime
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from chunking.circular_merge import merge_chunks


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Process and merge chunks with metadata"
    )
    parser.add_argument(
        "--chunks-dir",
        type=str,
        required=True,
        help="Directory containing chunks files organized by year",
    )
    parser.add_argument(
        "--metadata-dir",
        type=str,
        required=True,
        help="Directory containing metadata files organized by year",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Directory to save processed files",
    )
    parser.add_argument(
        "--years",
        type=str,
        nargs="+",
        default=None,
        help="Specific years to process (e.g., 2018 2019). If not provided, processes all years",
    )
    return parser.parse_args()


def load_json_file(file_path: Path) -> Dict:
    """Load and return JSON file content"""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_file(data: Dict, file_path: Path):
    """Save data to JSON file"""
    os.makedirs(file_path.parent, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def process_files(
    chunks_dir: Path, metadata_dir: Path, output_dir: Path, years: List[str] = None
):
    """Process all matching files in chunks and metadata directories"""

    # Get all years if not specified
    if not years:
        years = [d.name for d in chunks_dir.iterdir() if d.is_dir()]

    for year in years:
        chunks_year_dir = chunks_dir / year
        metadata_year_dir = metadata_dir / year
        output_year_dir = output_dir / year

        if not chunks_year_dir.exists() or not metadata_year_dir.exists():
            print(f"Skipping year {year} - directories not found")
            continue

        # Process each file in the year directory
        for chunks_file in chunks_year_dir.glob("*.json"):
            # Get corresponding metadata file
            chunks_file_name = chunks_file.name.replace(
                "_chunks.json", "_metadata.json"
            )
            metadata_file = metadata_year_dir / chunks_file_name

            if not metadata_file.exists():
                print(f"Skipping {chunks_file_name} - no matching metadata file")
                continue

            try:
                # Load files
                chunks_data = load_json_file(chunks_file)
                metadata_data = load_json_file(metadata_file)

                # Merge chunks
                merged_chunks = merge_chunks(chunks_data, metadata_data)

                # Create output structure
                output_data = {
                    "metadata": metadata_data,
                    "merged_chunks": merged_chunks,
                    "processing_info": {
                        "original_chunks": len(chunks_data),
                        "merged_chunks": len(merged_chunks),
                        "processed_date": str(datetime.now()),
                    },
                }

                # Save processed file
                output_file = output_year_dir / f"processed_{chunks_file.name}"
                save_json_file(output_data, output_file)

                print(f"Successfully processed {chunks_file.name}")

            except Exception as e:
                print(f"Error processing {chunks_file.name}: {str(e)}")


def main():
    args = parse_arguments()

    # Convert string paths to Path objects
    chunks_dir = Path(args.chunks_dir)
    metadata_dir = Path(args.metadata_dir)
    output_dir = Path(args.output_dir)

    # Validate directories
    if not chunks_dir.exists():
        raise ValueError(f"Chunks directory does not exist: {chunks_dir}")
    if not metadata_dir.exists():
        raise ValueError(f"Metadata directory does not exist: {metadata_dir}")

    # Process files
    process_files(chunks_dir, metadata_dir, output_dir, args.years)


if __name__ == "__main__":
    main()
