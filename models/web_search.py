from googleapiclient.discovery import build
import requests
from bs4 import BeautifulSoup
import os
import urllib.parse
from typing import List, Tuple, Optional
import time
import logging
from datetime import datetime
from markdownify import markdownify as md
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import hashlib
from functools import partial
import queue
import threading


class GoogleCustomSearchDownloader:
    def __init__(
        self,
        api_key: str,
        custom_search_engine_id: str,
        output_directory: str = "downloaded_content",
        websites_only: bool = False,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the Google Custom Search Downloader

        Args:
            api_key (str): Google Cloud API Key
            custom_search_engine_id (str): Custom Search Engine ID
            output_directory (str): Directory to save downloaded content
            websites_only (bool): If True, only download HTML websites, ignore PDFs and other files
            logger (Optional[logging.Logger]): External logger instance to use
        """
        self.api_key = api_key
        self.custom_search_engine_id = custom_search_engine_id
        self.output_directory = output_directory
        self.websites_only = websites_only
        self.service = build("customsearch", "v1", developerKey=api_key)

        # Use provided logger or create a new one
        if logger:
            self.logger = logger
        else:
            self.logger = self._setup_logging()

        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
            self.logger.info(f"Created output directory: {output_directory}")

        # Modified retry strategy to exclude DNS errors
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],  # Specify allowed methods
            raise_on_status=False,  # Don't raise exceptions on status
            # Don't retry on connection or DNS errors
            connect=0,
            raise_on_redirect=False,
        )

        # Use custom transport adapter with longer timeouts
        adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Add download queue and results cache
        self.download_queue = queue.Queue()
        self.results_cache = {}

        # Configure thread and process pools
        self.max_workers = min(32, os.cpu_count() * 4)  # Adjust based on your needs
        self.download_semaphore = threading.Semaphore(10)  # Limit concurrent downloads

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration - only used if no logger is provided"""
        # Create logs directory if it doesn't exist
        if not os.path.exists("logs"):
            os.makedirs("logs")

        # Create a timestamp for the log filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file = f"logs/search_log_{timestamp}.log"

        # Configure logging
        logger = logging.getLogger("GoogleCustomSearch")
        logger.setLevel(logging.INFO)

        # Only add handlers if they don't exist
        if not logger.handlers:
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
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)

        return logger

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

    def _download_worker(self, url: str, file_type: str = None) -> Tuple[str, str, str]:
        """Worker function for downloading content"""
        with self.download_semaphore:
            filename, content = self.download_content(url, file_type)
            return url, filename, content

    def search_and_download(
        self, query: str, num_results: int = 10, **kwargs
    ) -> List[str]:
        """Optimized search and download with parallel processing and better error handling"""
        self.logger.info(f"Starting parallel search and download for query: '{query}'")

        results = self.search_google(query=query, num_results=num_results, **kwargs)
        if not results:
            return []

        downloaded_files = []
        urls_to_download = [result["link"] for result in results]

        # Use a smaller thread pool to avoid overwhelming connections
        max_concurrent = min(5, self.max_workers)

        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            future_to_url = {
                executor.submit(
                    self._download_worker, url, kwargs.get("file_type")
                ): url
                for url in urls_to_download
            }

            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result(timeout=10)
                    if result:
                        url, filename, content = result
                        if filename and content:
                            # Save content immediately after download
                            if self.save_content(filename, content):
                                downloaded_files.append(
                                    os.path.join(self.output_directory, filename)
                                )
                except TimeoutError:
                    self.logger.warning(f"Download worker timeout for {url}")
                    continue
                except Exception as e:
                    self.logger.error(f"Error in download worker for {url}: {str(e)}")
                    continue

        return downloaded_files

    def download_content(self, url: str, file_type: str = None) -> Tuple[str, str]:
        """Optimized content download with caching and better error handling"""
        # Check cache first
        cache_key = hashlib.md5(url.encode()).hexdigest()
        if cache_key in self.results_cache:
            return self.results_cache[cache_key]

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            response = self.session.get(url, headers=headers, timeout=5)

            if response.status_code >= 400:
                self.logger.warning(f"HTTP {response.status_code} error for {url}")
                return None, None

            content_type = response.headers.get("content-type", "")
            self.logger.debug(f"Content-Type: {content_type}")

            # If websites_only is True, skip non-HTML content
            if self.websites_only and "text/html" not in content_type:
                self.logger.info(f"Skipping non-HTML content: {url}")
                return None, None

            # Handle different content types
            if "application/pdf" in content_type and not self.websites_only:
                filename = urllib.parse.quote_plus(url) + ".pdf"
                content = response.content
                self.logger.info(f"Downloaded PDF content: {filename}")
            elif "text/html" in content_type:
                # Process HTML content immediately
                soup = BeautifulSoup(response.content, "html.parser")
                for element in soup.find_all(
                    ["script", "style", "nav", "footer", "header", "aside"]
                ):
                    element.decompose()

                content = md(
                    str(soup),
                    heading_style="ATX",
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
                    bullets="-",
                ).strip()

                filename = urllib.parse.quote_plus(url) + ".md"
                self.logger.info(
                    f"Downloaded and converted HTML content to Markdown: {filename}"
                )
            elif not self.websites_only:
                # Save as binary content only if websites_only is False
                extension = content_type.split("/")[-1].split(";")[0]
                if not extension or len(extension) > 5:
                    extension = "bin"
                filename = urllib.parse.quote_plus(url) + f".{extension}"
                content = response.content
                self.logger.info(f"Downloaded binary content: {filename}")
            else:
                # Skip non-HTML content when websites_only is True
                return None, None

            # Store result in cache before returning
            result = (filename, content)
            self.results_cache[cache_key] = result
            return result

        except requests.exceptions.ConnectTimeout:
            self.logger.warning(f"Connection timeout for {url}")
            return None, None
        except requests.exceptions.ReadTimeout:
            self.logger.warning(f"Read timeout for {url}")
            return None, None
        except requests.exceptions.ConnectionError as e:
            if "NameResolutionError" in str(e):
                self.logger.warning(f"DNS resolution failed for {url}")
            else:
                self.logger.warning(f"Connection error for {url}: {str(e)}")
            return None, None
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
