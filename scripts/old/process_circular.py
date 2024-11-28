import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Now import your module
from chunking.circular import CircularProcessor

# Rest of your imports
import argparse
import logging
import json
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            f"circular_processor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
        logging.StreamHandler(),
    ],
)


def process_folder(input_folder: str, output_folder: str):
    """Process all MD files in a folder while preserving directory structure."""
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create base folders for different output types
    chunks_folder = output_path / "chunks"
    metadata_folder = output_path / "metadata"

    for folder in [chunks_folder, metadata_folder]:
        folder.mkdir(exist_ok=True)

    processor = CircularProcessor()

    # Track processing statistics
    stats = {"total_files": 0, "successful": 0, "failed": 0, "total_chunks": 0}

    # Process each MD file
    for md_file in input_path.glob("**/*.md"):
        stats["total_files"] += 1
        try:
            logging.info(f"Processing file: {md_file}")

            # Get relative path from input folder to preserve structure
            relative_path = md_file.relative_to(input_path)
            parent_dirs = relative_path.parent

            # Create corresponding output directories
            chunks_output_dir = chunks_folder / parent_dirs
            metadata_output_dir = metadata_folder / parent_dirs

            # Create directories if they don't exist
            chunks_output_dir.mkdir(parents=True, exist_ok=True)
            metadata_output_dir.mkdir(parents=True, exist_ok=True)

            # Process the file
            result = processor.process_file(md_file)

            # Generate output filenames with preserved path structure
            base_filename = md_file.stem

            # Save metadata
            metadata_file = metadata_output_dir / f"{base_filename}_metadata.json"
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(result["metadata"], f, indent=2, ensure_ascii=False)

            # Save chunks
            chunks_file = chunks_output_dir / f"{base_filename}_chunks.json"
            with open(chunks_file, "w", encoding="utf-8") as f:
                json.dump(result["chunks"], f, indent=2, ensure_ascii=False)

            stats["successful"] += 1
            stats["total_chunks"] += len(result["chunks"])

            logging.info(f"Successfully processed {md_file}")
            logging.info(f"Generated {len(result['chunks'])} chunks")
            logging.info(f"Saved to: {chunks_file.parent}")

        except Exception as e:
            stats["failed"] += 1
            logging.error(f"Error processing {md_file}: {str(e)}")
            continue

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Process IBBI circular MD files into structured chunks."
    )
    parser.add_argument("-i", "--input-folder", help="Input folder containing MD files")
    parser.add_argument(
        "-o", "--output-folder", help="Output folder for processed files"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=512,
        help="Target chunk size in characters (default: 512)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logging.info("Starting circular processing")
    logging.info(f"Input folder: {args.input_folder}")
    logging.info(f"Output folder: {args.output_folder}")
    logging.info(f"Target chunk size: {args.chunk_size}")

    # Process files and get statistics
    stats = process_folder(args.input_folder, args.output_folder)

    # Log processing summary
    logging.info("\nProcessing Summary:")
    logging.info(f"Total files processed: {stats['total_files']}")
    logging.info(f"Successfully processed: {stats['successful']}")
    logging.info(f"Failed to process: {stats['failed']}")
    logging.info(f"Total chunks generated: {stats['total_chunks']}")

    if stats["failed"] > 0:
        logging.warning(
            f"Failed to process {stats['failed']} files. Check the log for details."
        )

    logging.info("Completed circular processing")


if __name__ == "__main__":
    main()
