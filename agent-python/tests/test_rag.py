"""
Tests for RAG (Retrieval-Augmented Generation) module.
Uses mocking to avoid real ChromaDB connections during tests.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.tools.rag import ProductRAG, ingest_product_knowledge, search_knowledge, get_product_details


class TestProductRAG:
    """Test cases for ProductRAG class."""

    def setup_method(self):
        """Setup test fixtures."""
        # Mock the embedding model during initialization to avoid loading actual model
        with patch('src.tools.rag.SentenceTransformer') as mock_transformer:
            self.rag = ProductRAG(embedding_model='mock-model')
            # Replace with actual mock
            self.rag.embedding_model = mock_transformer.return_value

    def test_init(self):
        """Test ProductRAG initialization."""
        assert self.rag.chroma_host == 'localhost'
        assert self.rag.chroma_port == 8000
        assert self.rag.collection_name == 'products'
        assert self.rag.embedding_model is not None

    @patch('src.tools.rag.chromadb.HttpClient')
    def test_init_chroma_success(self, mock_chroma_client_class):
        """Test successful ChromaDB initialization."""
        # Mock ChromaDB client
        mock_client = Mock()
        mock_collection = Mock()
        mock_chroma_client_class.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        # Initialize ChromaDB
        self.rag._init_chroma()

        # Assertions
        assert self.rag.chroma_client == mock_client
        assert self.rag.collection == mock_collection
        mock_client.get_or_create_collection.assert_called_once_with(
            name='products',
            metadata={"hnsw:space": "cosine"}
        )

    @patch('src.tools.rag.chromadb.HttpClient')
    def test_ingest_product_knowledge_success(self, mock_chroma_client_class):
        """Test successful product knowledge ingestion."""
        # Mock ChromaDB
        mock_client = Mock()
        mock_collection = Mock()
        mock_chroma_client_class.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        # Test products
        test_products = [
            {
                'id': 'prod1',
                'name': 'Premium Wireless Headphones',
                'description': 'High-quality noise-cancelling headphones',
                'category': 'Electronics',
                'price': 299.99,
                'selling_points': ['Noise cancellation', '30-hour battery', 'Premium sound']
            },
            {
                'id': 'prod2',
                'name': 'Ergonomic Office Chair',
                'description': 'Comfortable chair for long work sessions',
                'category': 'Furniture',
                'price': 449.99,
                'selling_points': ['Lumbar support', 'Adjustable height', 'Breathable mesh']
            }
        ]

        # Test ingestion
        result = self.rag.ingest_product_knowledge(test_products)

        # Assertions
        assert result == 2
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        assert len(call_args.kwargs['ids']) == 2
        assert 'prod1' in call_args.kwargs['ids']
        assert 'prod2' in call_args.kwargs['ids']

    @patch('src.tools.rag.chromadb.HttpClient')
    def test_ingest_product_knowledge_empty(self, mock_chroma_client_class):
        """Test ingestion with empty product list."""
        # Mock ChromaDB to avoid real connection
        mock_client = Mock()
        mock_collection = Mock()
        mock_chroma_client_class.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        result = self.rag.ingest_product_knowledge([])
        assert result == 0

    @patch('src.tools.rag.chromadb.HttpClient')
    def test_search_knowledge_success(self, mock_chroma_client_class):
        """Test successful knowledge search."""
        # Mock ChromaDB
        mock_client = Mock()
        mock_collection = Mock()
        mock_chroma_client_class.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        # Mock search results
        mock_collection.query.return_value = {
            'ids': [['prod1', 'prod2']],
            'documents': [
                ['Product: Premium Wireless Headphones. Selling points: Noise cancellation; 30-hour battery.',
                 'Product: Ergonomic Office Chair. Selling points: Lumbar support; Adjustable height.']
            ],
            'metadatas': [
                [{'product_id': 'prod1', 'name': 'Premium Wireless Headphones', 'price': '299.99'},
                 {'product_id': 'prod2', 'name': 'Ergonomic Office Chair', 'price': '449.99'}]
            ],
            'distances': [[0.15, 0.32]]
        }

        # Test search
        results = self.rag.search_knowledge('wireless headphones', n_results=2)

        # Assertions
        assert len(results) == 2
        assert results[0]['product_id'] == 'prod1'
        assert 'Premium Wireless Headphones' in results[0]['document']
        assert results[0]['distance'] == 0.15
        mock_collection.query.assert_called_once_with(
            query_texts=['wireless headphones'],
            n_results=2
        )

    @patch('src.tools.rag.chromadb.HttpClient')
    def test_search_knowledge_empty_query(self, mock_chroma_client_class):
        """Test search with empty query."""
        result = self.rag.search_knowledge('')
        assert result == []

    @patch('src.tools.rag.chromadb.HttpClient')
    def test_search_knowledge_no_results(self, mock_chroma_client_class):
        """Test search with no results."""
        # Mock ChromaDB
        mock_client = Mock()
        mock_collection = Mock()
        mock_chroma_client_class.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        # Mock empty results
        mock_collection.query.return_value = {
            'ids': [[]],
            'documents': [[]],
            'metadatas': [[]],
            'distances': [[]]
        }

        # Test search
        results = self.rag.search_knowledge('nonexistent product')

        # Assertions
        assert len(results) == 0

    @patch('src.tools.rag.chromadb.HttpClient')
    def test_get_product_details_success(self, mock_chroma_client_class):
        """Test successful product details retrieval."""
        # Mock ChromaDB
        mock_client = Mock()
        mock_collection = Mock()
        mock_chroma_client_class.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        # Mock get results
        mock_collection.get.return_value = {
            'ids': ['prod1'],
            'documents': ['Product: Premium Wireless Headphones. Selling points: Noise cancellation.'],
            'metadatas': [{'product_id': 'prod1', 'name': 'Premium Wireless Headphones'}]
        }

        # Test get details
        result = self.rag.get_product_details('prod1')

        # Assertions
        assert result is not None
        assert result['product_id'] == 'prod1'
        assert 'Premium Wireless Headphones' in result['document']
        mock_collection.get.assert_called_once_with(ids=['prod1'])

    @patch('src.tools.rag.chromadb.HttpClient')
    def test_get_product_details_not_found(self, mock_chroma_client_class):
        """Test product details not found."""
        # Mock ChromaDB
        mock_client = Mock()
        mock_collection = Mock()
        mock_chroma_client_class.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection

        # Mock empty results
        mock_collection.get.return_value = {
            'ids': [],
            'documents': [],
            'metadatas': []
        }

        # Test get details
        result = self.rag.get_product_details('nonexistent')

        # Assertions
        assert result is None

    @patch('src.tools.rag.chromadb.HttpClient')
    def test_clear_collection(self, mock_chroma_client_class):
        """Test clearing the collection."""
        # Mock ChromaDB
        mock_client = Mock()
        mock_chroma_client_class.return_value = mock_client

        # Test clear
        result = self.rag.clear_collection()

        # Assertions
        assert result is True
        mock_client.delete_collection.assert_called_once_with('products')
        assert self.rag.collection is None

    @patch('src.tools.rag.chromadb.HttpClient')
    def test_get_collection_stats(self, mock_chroma_client_class):
        """Test getting collection statistics."""
        # Mock ChromaDB
        mock_client = Mock()
        mock_collection = Mock()
        mock_chroma_client_class.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 42

        # Test get stats
        stats = self.rag.get_collection_stats()

        # Assertions
        assert stats['collection_name'] == 'products'
        assert stats['document_count'] == 42

    @patch('src.tools.rag.SentenceTransformer')
    def test_generate_embeddings(self, mock_transformer_class):
        """Test embedding generation."""
        # Mock model
        mock_model = Mock()
        mock_transformer_class.return_value = mock_model
        mock_model.encode.return_value.tolist.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

        # Create new RAG instance
        with patch('src.tools.rag.SentenceTransformer', return_value=mock_model):
            rag = ProductRAG(embedding_model='mock-model')

        # Test embedding generation
        texts = ['hello world', 'test sentence']
        embeddings = rag._generate_embeddings(texts)

        # Assertions
        assert len(embeddings) == 2
        assert len(embeddings[0]) == 3
        mock_model.encode.assert_called_once()

    def test_generate_embeddings_empty(self):
        """Test embedding generation with empty list."""
        embeddings = self.rag._generate_embeddings([])
        assert embeddings == []


class TestConvenienceFunctions:
    """Test convenience functions."""

    @patch('src.tools.rag.ProductRAG')
    def test_ingest_product_knowledge_convenience(self, mock_rag_class):
        """Test convenience function for product ingestion."""
        # Mock
        mock_rag = Mock()
        mock_rag_class.return_value = mock_rag
        mock_rag.ingest_product_knowledge.return_value = 5

        # Test
        test_products = [{'id': 'prod1'}]
        result = ingest_product_knowledge(test_products)

        # Assertions
        assert result == 5
        mock_rag.ingest_product_knowledge.assert_called_once_with(test_products)

    @patch('src.tools.rag.ProductRAG')
    def test_search_knowledge_convenience(self, mock_rag_class):
        """Test convenience function for knowledge search."""
        # Mock
        mock_rag = Mock()
        mock_rag_class.return_value = mock_rag
        expected_results = [{'product_id': 'prod1'}]
        mock_rag.search_knowledge.return_value = expected_results

        # Test
        result = search_knowledge('wireless headphones', n_results=3)

        # Assertions
        assert result == expected_results
        mock_rag.search_knowledge.assert_called_once_with('wireless headphones', 3)

    @patch('src.tools.rag.ProductRAG')
    def test_get_product_details_convenience(self, mock_rag_class):
        """Test convenience function for product details."""
        # Mock
        mock_rag = Mock()
        mock_rag_class.return_value = mock_rag
        expected_details = {'product_id': 'prod1', 'name': 'Test Product'}
        mock_rag.get_product_details.return_value = expected_details

        # Test
        result = get_product_details('prod1')

        # Assertions
        assert result == expected_details
        mock_rag.get_product_details.assert_called_once_with('prod1')


if __name__ == "__main__":
    pytest.main([__file__])
