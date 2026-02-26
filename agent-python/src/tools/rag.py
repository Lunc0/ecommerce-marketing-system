"""
RAG (Retrieval-Augmented Generation) module for product knowledge retrieval.
Provides functions to ingest product data into ChromaDB and search for relevant knowledge.
"""

import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import os

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class ProductRAG:
    """RAG system for product knowledge retrieval using ChromaDB and SentenceTransformers."""

    def __init__(self, collection_name: str = "products", embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize the RAG system.

        Args:
            collection_name: Name of the ChromaDB collection
            embedding_model: Name of the SentenceTransformer model to use
        """
        load_dotenv()

        # ChromaDB connection settings
        self.chroma_host = os.getenv('CHROMA_HOST', 'localhost')
        self.chroma_port = int(os.getenv('CHROMA_PORT', '8000'))

        # Initialize clients
        self.chroma_client = None
        self.collection = None
        self.embedding_model = None
        self.collection_name = collection_name

        # Load embedding model
        self._init_embedding_model(embedding_model)

    def _init_embedding_model(self, model_name: str):
        """Initialize the SentenceTransformer embedding model."""
        try:
            self.embedding_model = SentenceTransformer(model_name)
            logger.info(f"Initialized embedding model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise

    def _init_chroma(self):
        """Initialize ChromaDB client if not already connected."""
        if self.chroma_client is None:
            try:
                # Connect to ChromaDB
                self.chroma_client = chromadb.HttpClient(
                    host=self.chroma_host,
                    port=self.chroma_port,
                    settings=Settings(anonymized_telemetry=False)
                )
                logger.info(f"Connected to ChromaDB at {self.chroma_host}:{self.chroma_port}")

                # Get or create collection
                self.collection = self.chroma_client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"Using collection: {self.collection_name}")

            except Exception as e:
                logger.error(f"Failed to connect to ChromaDB: {e}")
                raise

    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        try:
            embeddings = self.embedding_model.encode(texts, convert_to_numpy=True).tolist()
            return embeddings
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise

    def ingest_product_knowledge(self, products: List[Dict[str, Any]]) -> int:
        """
        Ingest product knowledge data into ChromaDB.

        Args:
            products: List of product dictionaries with fields like:
                - id: Product ID
                - name: Product name
                - description: Product description
                - category: Product category
                - price: Product price
                - selling_points: List of key selling points

        Returns:
            Number of products successfully ingested
        """
        try:
            self._init_chroma()

            if not products:
                logger.warning("No products provided for ingestion")
                return 0

            # Prepare data for ChromaDB
            ids = []
            documents = []
            metadatas = []

            for product in products:
                product_id = str(product.get('id', ''))
                product_name = product.get('name', '')
                product_desc = product.get('description', '')
                product_category = product.get('category', '')
                product_price = product.get('price', 0)
                selling_points = product.get('selling_points', [])

                # Create a comprehensive document text
                # Include all relevant information for better retrieval
                doc_text = f"Product: {product_name}. "
                doc_text += f"Category: {product_category}. "
                doc_text += f"Price: ${product_price:.2f}. "

                if product_desc:
                    doc_text += f"Description: {product_desc}. "

                if selling_points:
                    doc_text += "Selling points: " + "; ".join(selling_points) + "."

                ids.append(product_id)
                documents.append(doc_text)
                metadatas.append({
                    'product_id': product_id,
                    'name': product_name,
                    'category': product_category,
                    'price': str(product_price),
                    'selling_points_count': len(selling_points)
                })

            # Add to collection
            # ChromaDB will handle embeddings automatically
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )

            logger.info(f"Successfully ingested {len(products)} products into ChromaDB")
            return len(products)

        except Exception as e:
            logger.error(f"Failed to ingest product knowledge: {e}")
            raise

    def search_knowledge(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Search for relevant product knowledge based on a query.

        Args:
            query: Search query text
            n_results: Number of results to return

        Returns:
            List of search results with product information and relevance scores
        """
        try:
            self._init_chroma()

            if not query:
                logger.warning("Empty query provided for search")
                return []

            # Query the collection
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )

            # Format results
            formatted_results = []
            if results['ids'] and len(results['ids']) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'product_id': results['ids'][0][i],
                        'document': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i] if 'distances' in results else None
                    })

            logger.info(f"Found {len(formatted_results)} results for query: '{query}'")
            return formatted_results

        except Exception as e:
            logger.error(f"Failed to search knowledge: {e}")
            return []

    def get_product_details(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific product by ID.

        Args:
            product_id: Product ID to retrieve

        Returns:
            Dictionary containing product details or None if not found
        """
        try:
            self._init_chroma()

            # Get specific product by ID
            results = self.collection.get(
                ids=[product_id]
            )

            if results['ids'] and len(results['ids']) > 0:
                return {
                    'product_id': results['ids'][0],
                    'document': results['documents'][0],
                    'metadata': results['metadatas'][0]
                }

            logger.warning(f"Product not found with ID: {product_id}")
            return None

        except Exception as e:
            logger.error(f"Failed to get product details: {e}")
            return None

    def clear_collection(self) -> bool:
        """
        Clear all data from the collection.

        Returns:
            True if successful, False otherwise
        """
        try:
            self._init_chroma()
            self.chroma_client.delete_collection(self.collection_name)
            self.collection = None
            logger.info(f"Cleared collection: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current collection.

        Returns:
            Dictionary containing collection statistics
        """
        try:
            self._init_chroma()
            count = self.collection.count()
            return {
                'collection_name': self.collection_name,
                'document_count': count
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {
                'collection_name': self.collection_name,
                'document_count': 0,
                'error': str(e)
            }


# Convenience functions for direct use
def ingest_product_knowledge(products: List[Dict[str, Any]]) -> int:
    """
    Ingest product knowledge data into ChromaDB.

    Args:
        products: List of product dictionaries

    Returns:
        Number of products successfully ingested
    """
    rag = ProductRAG()
    try:
        return rag.ingest_product_knowledge(products)
    finally:
        # No explicit cleanup needed for HTTP client
        pass


def search_knowledge(query: str, n_results: int = 3) -> List[Dict[str, Any]]:
    """
    Search for relevant product knowledge.

    Args:
        query: Search query text
        n_results: Number of results to return

    Returns:
        List of search results
    """
    rag = ProductRAG()
    try:
        return rag.search_knowledge(query, n_results)
    finally:
        # No explicit cleanup needed for HTTP client
        pass


def get_product_details(product_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information for a specific product.

    Args:
        product_id: Product ID to retrieve

    Returns:
        Dictionary containing product details or None if not found
    """
    rag = ProductRAG()
    try:
        return rag.get_product_details(product_id)
    finally:
        # No explicit cleanup needed for HTTP client
        pass
