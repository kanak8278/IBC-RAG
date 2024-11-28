from rank_bm25 import BM25Okapi
import numpy as np
from typing import List, Dict
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import json
import re
import spacy
from collections import defaultdict


class HybridSearch:
    def __init__(self, json_file):
        # Load the parsed code structure
        with open(json_file, "r", encoding="utf-8") as f:
            self.code_structure = json.load(f)

        # Load spaCy model for semantic analysis
        self.nlp = spacy.load("en_core_web_md")

        # Initialize NLTK resources
        try:
            nltk.data.find("tokenizers/punkt")
            nltk.data.find("corpora/stopwords")
        except LookupError:
            nltk.download("punkt")
            nltk.download("stopwords")

        self.stop_words = set(stopwords.words("english"))

        # Create indices
        self.section_index = self._create_section_index()
        self.bm25_index = self._create_bm25_index()

    def _create_section_index(self):
        """Create an index mapping section numbers to their content"""
        section_index = {}
        for part in self.code_structure["parts"]:
            for chapter in part["chapters"]:
                for section in chapter["sections"]:
                    section_index[section["section_number"]] = {
                        "part": part["part_number"],
                        "chapter": chapter["chapter_number"],
                        "section_name": section["section_name"],
                        "content": section["content"],
                    }
        return section_index

    def _tokenize_and_preprocess(self, text: str) -> List[str]:
        """Tokenize and preprocess text for BM25"""
        # Convert to lowercase and tokenize
        tokens = word_tokenize(text.lower())
        # Remove stopwords and non-alphabetic tokens
        tokens = [
            token
            for token in tokens
            if token not in self.stop_words and token.isalpha()
        ]
        return tokens

    def _create_bm25_index(self) -> Dict:
        """Create BM25 index from section contents"""
        # Prepare documents for BM25
        documents = []
        section_map = []

        for section_number, section_info in self.section_index.items():
            # Combine section name and content for better matching
            section_text = f"{section_info['section_name']} {section_info['content']}"
            tokenized_text = self._tokenize_and_preprocess(section_text)

            if tokenized_text:  # Only add if there are tokens
                documents.append(tokenized_text)
                section_map.append(section_number)

        return {
            "bm25": BM25Okapi(documents),
            "documents": documents,
            "section_map": section_map,
        }

    def _extract_section_numbers(self, query):
        """Extract section numbers from the query"""
        section_numbers = re.findall(r"section\s+(\d+)", query.lower())
        return section_numbers

    def _preprocess_text(self, text):
        """Preprocess text for better matching"""
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _bm25_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Perform BM25 search"""
        tokenized_query = self._tokenize_and_preprocess(query)

        # Get BM25 scores
        scores = self.bm25_index["bm25"].get_scores(tokenized_query)

        # Get top-k results
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include results with positive scores
                section_number = self.bm25_index["section_map"][idx]
                section_info = self.section_index[section_number]

                results.append(
                    {
                        "match_type": "bm25_match",
                        "section_number": section_number,
                        "part": section_info["part"],
                        "chapter": section_info["chapter"],
                        "section_name": section_info["section_name"],
                        "content": section_info["content"],
                        "relevance_score": float(scores[idx]),
                    }
                )

        return results

    def search(
        self,
        query: str,
        context_size: int = 2,
        max_results: int = 5,
        use_hybrid: bool = True,
    ) -> List[Dict]:
        """
        Enhanced search implementation with BM25
        Args:
            query: Search query string
            context_size: Number of surrounding sections to include in context
            max_results: Maximum number of results to return
            use_hybrid: Whether to combine BM25 and semantic search results
        Returns:
            List of relevant results with context
        """
        results = []

        # First, handle direct section references
        section_numbers = self._extract_section_numbers(query)
        if section_numbers:
            for section_number in section_numbers:
                if section_number in self.section_index:
                    section_info = self.section_index[section_number]
                    context = self._get_context_sections(
                        int(section_number), context_size
                    )

                    results.append(
                        {
                            "match_type": "direct_section_reference",
                            "section_number": section_number,
                            "part": section_info["part"],
                            "chapter": section_info["chapter"],
                            "section_name": section_info["section_name"],
                            "content": section_info["content"],
                            "context": context,
                            "relevance_score": 1.0,
                        }
                    )

        # Get BM25 results
        bm25_results = self._bm25_search(query, top_k=max_results)

        if use_hybrid:
            # Get semantic search results
            semantic_results = []
            query_doc = self.nlp(self._preprocess_text(query))

            for section_number, section_info in self.section_index.items():
                if section_number not in section_numbers:
                    section_text = (
                        f"{section_info['section_name']} {section_info['content']}"
                    )
                    section_doc = self.nlp(self._preprocess_text(section_text))

                    similarity_score = query_doc.similarity(section_doc)

                    if similarity_score > 0.5:
                        semantic_results.append(
                            {
                                "match_type": "semantic_match",
                                "section_number": section_number,
                                "part": section_info["part"],
                                "chapter": section_info["chapter"],
                                "section_name": section_info["section_name"],
                                "content": section_info["content"],
                                "relevance_score": similarity_score,
                            }
                        )

            # Combine and normalize scores
            all_results = results + bm25_results + semantic_results

            # Normalize scores within each match type
            for match_type in ["bm25_match", "semantic_match"]:
                type_results = [r for r in all_results if r["match_type"] == match_type]
                if type_results:
                    max_score = max(r["relevance_score"] for r in type_results)
                    for r in type_results:
                        r["relevance_score"] = r["relevance_score"] / max_score
        else:
            all_results = results + bm25_results

        # Sort by relevance score and return top results
        all_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return all_results[:max_results]

    def _get_context_sections(self, section_num: int, context_size: int) -> Dict:
        """Get surrounding sections for context"""
        context = {}
        for i in range(section_num - context_size, section_num + context_size + 1):
            section_str = str(i)
            if section_str in self.section_index and i != section_num:
                context[section_str] = {
                    "section_name": self.section_index[section_str]["section_name"],
                    "content": self.section_index[section_str]["content"],
                }
        return context

    def format_results(self, results):
        """Format search results for better readability"""
        formatted_output = []
        for result in results:
            output = f"\nSection {result['section_number']}: {result['section_name']}\n"
            output += f"Location: {result['part']}, {result['chapter']}\n"
            output += f"Relevance Score: {result['relevance_score']:.2f}\n"
            output += f"Match Type: {result['match_type']}\n"
            output += f"\nContent:\n{result['content']}\n"

            if "context" in result:
                output += "\nRelated Sections:\n"
                for context_section, context_info in result["context"].items():
                    output += (
                        f"Section {context_section}: {context_info['section_name']}\n"
                    )

            formatted_output.append(output)

        return "\n---\n".join(formatted_output)


def main():
    searcher = HybridSearch("insolvency_code_structured.json")

    while True:
        query = input("Enter a query: ")
        print(f"\nSearch Query: {query}")
        print("=" * 80)

        # Choose search mode:
        # BM25 only
        # results = searcher.search(query, max_results=5, use_hybrid=False)

        # Or use hybrid search (BM25 + Semantic)
        results = searcher.search(query, max_results=5, use_hybrid=True)

        formatted_results = searcher.format_results(results)
        print(formatted_results)


if __name__ == "__main__":
    main()
