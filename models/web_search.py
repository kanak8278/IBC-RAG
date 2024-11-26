from googleapiclient.discovery import build
import requests
from bs4 import BeautifulSoup
import os
import urllib.parse
from typing import List, Tuple
import time
import logging
from datetime import datetime
from markdownify import markdownify as md


class GoogleCustomSearchDownloader:
    def __init__(
        self,
        api_key: str,
        custom_search_engine_id: str,
        output_directory: str = "downloaded_content",
    ):
        """
        Initialize the Google Custom Search Downloader

        Args:
            api_key (str): Google Cloud API Key
            custom_search_engine_id (str): Custom Search Engine ID
            output_directory (str): Directory to save downloaded content
        """
        self.api_key = api_key
        self.custom_search_engine_id = custom_search_engine_id
        self.output_directory = output_directory
        self.service = build("customsearch", "v1", developerKey=api_key)

        # Setup logging
        self._setup_logging()

        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
            self.logger.info(f"Created output directory: {output_directory}")

    def _setup_logging(self):
        """Setup logging configuration"""
        # Create logs directory if it doesn't exist
        if not os.path.exists("logs"):
            os.makedirs("logs")

        # Create a timestamp for the log filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file = f"logs/search_log_{timestamp}.log"

        # Configure logging
        self.logger = logging.getLogger("GoogleCustomSearch")
        self.logger.setLevel(logging.INFO)

        # Create file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        self.logger.info("Logging initialized")

    def search_google(
        self,
        query: str,
        num_results: int = 10,
        date_restrict: str = None,
        file_type: str = None,
        site: str = None,
        sort: str = None,
        language: str = None,
    ) -> List[dict]:
        """
        Perform Google Custom Search with advanced filters

        Args:
            query (str): Search query
            num_results (int): Number of results to return (max 10 per request)
            date_restrict (str): Date restriction (e.g., 'd[number]' for days, 'w[number]' for weeks,
                               'm[number]' for months, 'y[number]' for years)
            file_type (str): Specific file type to search for (e.g., 'pdf', 'doc', 'docx')
            site (str): Limit search to specific site or domain
            sort (str): Sort order ('date' for sorting by date)
            language (str): Language restriction (e.g., 'lang_en' for English)

        Returns:
            List[dict]: List of search results
        """
        self.logger.info(
            f"Starting search for query: '{query}' with {num_results} results"
        )

        # Build the modified query with filters
        modified_query = query

        if file_type:
            modified_query += f" filetype:{file_type}"
        if site:
            modified_query += f" site:{site}"

        results = []
        pages = (num_results + 9) // 10

        try:
            for page in range(pages):
                start_index = page * 10 + 1
                self.logger.debug(
                    f"Fetching page {page + 1}, start_index: {start_index}"
                )

                # Build search parameters
                search_params = {
                    "q": modified_query,
                    "cx": self.custom_search_engine_id,
                    "start": start_index,
                    "num": min(10, num_results - len(results)),
                }

                # Add optional parameters
                if date_restrict:
                    search_params["dateRestrict"] = date_restrict
                if sort:
                    search_params["sort"] = sort
                if language:
                    search_params["lr"] = language

                # Perform the search
                result = self.service.cse().list(**search_params).execute()

                if "items" in result:
                    results.extend(result["items"])
                    self.logger.debug(f"Retrieved {len(result['items'])} results")

                if len(results) >= num_results:
                    break

                time.sleep(1)  # Delay between requests

            self.logger.info(f"Search completed. Found {len(results)} results")
            return results[:num_results]

        except Exception as e:
            self.logger.error(f"Error during search: {str(e)}")
            return []

    def download_content(self, url: str, file_type: str = None) -> Tuple[str, str]:
        """
        Download content from a URL and convert HTML to Markdown when applicable

        Args:
            url (str): URL to download content from
            file_type (str): Type of file to download (pdf, doc, etc.)

        Returns:
            Tuple[str, str]: Tuple containing filename and content
        """
        self.logger.info(f"Attempting to download content from: {url}")

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            self.logger.debug(f"Content-Type: {content_type}")

            # Handle different content types
            if "application/pdf" in content_type:
                # Save as PDF
                filename = urllib.parse.quote_plus(url) + ".pdf"
                self.logger.info(f"Downloaded PDF content: {filename}")
                return filename, response.content
            elif "text/html" in content_type:
                # Parse HTML content with BeautifulSoup
                soup = BeautifulSoup(response.content, "html.parser")

                # Remove unwanted elements
                for element in soup.find_all(
                    ["script", "style", "nav", "footer", "header", "aside"]
                ):
                    element.decompose()

                # Convert to markdown while preserving structure
                markdown_content = md(
                    str(soup),
                    heading_style="ATX",
                    # strip=["script", "style", "nav", "footer", "header", "aside"],
                    convert=[
                        "p",
                        "h1",
                        "h2",
                        "h3",
                        "h4",
                        "h5",
                        "h6",
                        "li",
                        "ul",
                        "ol",
                        "a",
                        "b",
                        "strong",
                        "i",
                        "em",
                        "table",
                        "tr",
                        "td",
                        "th",
                        "blockquote",
                        "pre",
                        "code",
                    ],
                    bullets="-",  # Use - for unordered lists
                )
                # strip the spaces from content
                markdown_content = markdown_content.strip()
                filename = (
                    urllib.parse.quote_plus(url) + ".md"
                )  # Changed extension to .md
                self.logger.info(
                    f"Downloaded and converted HTML content to Markdown: {filename}"
                )
                return filename, markdown_content
            else:
                # Save as binary content
                extension = content_type.split("/")[-1]
                filename = urllib.parse.quote_plus(url) + f".{extension}"
                self.logger.info(f"Downloaded binary content: {filename}")
                return filename, response.content

        except Exception as e:
            self.logger.error(f"Error downloading {url}: {str(e)}")
            return None, None

    def save_content(self, filename: str, content: str) -> bool:
        """
        Save content to file

        Args:
            filename (str): Name of the file
            content (str): Content to save

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            filepath = os.path.join(self.output_directory, filename)

            # Determine write mode based on content type
            write_mode = "wb" if isinstance(content, bytes) else "w"
            encoding = None if isinstance(content, bytes) else "utf-8"

            with open(filepath, write_mode, encoding=encoding) as f:
                f.write(content)

            self.logger.info(f"Successfully saved content to: {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving file {filename}: {str(e)}")
            return False

    def search_and_download(
        self,
        query: str,
        num_results: int = 10,
        file_type: str = None,
        date_restrict: str = None,
        site: str = None,
        sort: str = None,
        language: str = None,
    ) -> List[str]:
        """
        Search Google and download content from results with advanced filters

        Args:
            query (str): Search query
            num_results (int): Number of results to process
            file_type (str): Specific file type to search for
            date_restrict (str): Date restriction (e.g., 'd[number]' for days)
            site (str): Limit search to specific site or domain
            sort (str): Sort order ('date' for sorting by date)
            language (str): Language restriction (e.g., 'lang_en' for English)

        Returns:
            List[str]: List of downloaded file paths
        """
        self.logger.info(f"Starting search and download process for query: '{query}'")
        downloaded_files = []

        # List of preferred legal websites
        preferred_domains = [
            "scconline.com",
            "manupatra.com",
            "cyrilamarchandblogs.com",
            "indiacorplaw.in",
            "mondaq.com",
            "livelaw.in",
            "lexology.com",
            "scobserver.in",
            "barandbench.com",
            "theleaflet.in",
            "nishithdesai.com",
            "indconlawphil.wordpress.com",
            "indiankanoon.org",
            "ibbi.gov.in",
            "ibclaw.in",
            "ibclawreporter.in",
        ]

        # List of excluded domains
        excluded_domains = [
            "wikipedia.org",
            "blog.ipleaders.in",
            "quora.com",
            "linkedin.com",
        ]

        while len(downloaded_files) < num_results:
            current_batch = max(num_results - len(downloaded_files), 10) * 3
            results = self.search_google(
                query=query,
                num_results=current_batch,
                date_restrict=date_restrict,
                file_type=file_type,
                site=site,
                sort=sort,
                language=language,
            )

            if not results:
                self.logger.warning("No more results available")
                break

            self.logger.info(f"Retrieved {len(results)} search results")

            # Filter and sort results
            filtered_results = []
            preferred_results = []
            other_results = []

            for result in results:
                url = result["link"]
                domain = urllib.parse.urlparse(url).netloc.lower()

                # Skip excluded domains
                if any(excluded in domain for excluded in excluded_domains):
                    self.logger.debug(f"Skipping excluded domain: {domain}")
                    continue

                # Skip already processed URLs
                if any(url in file for file in downloaded_files):
                    continue

                # Categorize results
                if any(preferred in domain for preferred in preferred_domains):
                    preferred_results.append(result)
                else:
                    other_results.append(result)

            # First try preferred results
            filtered_results = preferred_results

            # If we don't have enough preferred results, add other results
            if len(filtered_results) < num_results:
                self.logger.info(
                    "Not enough preferred domain results, including other non-excluded domains"
                )
                filtered_results.extend(other_results)

            self.logger.info(f"Processing {len(filtered_results)} filtered results")
            self.logger.info(
                f"Found {len(preferred_results)} results from preferred domains and {len(other_results)} from other domains"
            )

            # Download content from filtered results
            for result in filtered_results:
                if len(downloaded_files) >= num_results:
                    break

                url = result["link"]
                domain = urllib.parse.urlparse(url).netloc
                self.logger.info(f"Processing content from: {domain}")

                filename, content = self.download_content(url, file_type)

                if filename and content:
                    if self.save_content(filename, content):
                        downloaded_files.append(
                            os.path.join(self.output_directory, filename)
                        )
                        print(f"Successfully downloaded and saved content from {url}")

                time.sleep(1)  # Delay between downloads

        self.logger.info(
            f"Download process completed. Downloaded {len(downloaded_files)} files"
        )
        return downloaded_files
