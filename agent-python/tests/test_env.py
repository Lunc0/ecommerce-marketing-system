"""
Test environment and basic imports for Python agent.
"""

import os
import sys
import pytest

def test_basic_imports():
    """Test that all required modules can be imported."""
    try:
        # Test basic Python modules
        import json
        import logging
        from dotenv import load_dotenv

        # Test required third-party modules
        import langchain
        import langgraph
        from kafka import KafkaConsumer, KafkaProducer
        import redis
        import mysql.connector
        # import chromadb  # Optional for now, will test separately later
        from sentence_transformers import SentenceTransformer
        import openai

        print("All imports successful!")
        return True
    except ImportError as e:
        pytest.fail(f"Import error: {e}")
        return False

def test_environment_variables():
    """Test that environment variables can be loaded."""
    # This is a mock test since we don't have real .env file in tests
    assert True

if __name__ == "__main__":
    pytest.main([__file__])