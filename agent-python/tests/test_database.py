"""
Tests for database tools module.
Uses mocking to avoid real database connections during tests.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from src.tools.database import DatabaseTools, get_redis_profile, get_mysql_profile, get_user_context


class TestDatabaseTools:
    """Test cases for DatabaseTools class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.tools = DatabaseTools()

    def test_init(self):
        """Test DatabaseTools initialization."""
        assert self.tools.redis_host == 'localhost'
        assert self.tools.redis_port == 6379
        assert self.tools.mysql_host == 'localhost'
        assert self.tools.mysql_port == 3306
        assert self.tools.mysql_user == 'root'
        assert self.tools.mysql_database == 'ecommerce'

    @patch('src.tools.database.redis.Redis')
    def test_get_redis_profile_success(self, mock_redis_class):
        """Test successful Redis profile retrieval."""
        # Mock Redis connection
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_redis.ping.return_value = 'PONG'

        # Mock profile data
        test_user_id = 'user123'
        expected_profile = {
            'id': test_user_id,
            'name': 'Test User',
            'spending_tier': 'HIGH',
            'identity_tags': ['vip', 'frequent_buyer']
        }
        mock_redis.get.return_value = json.dumps(expected_profile)

        # Test
        result = self.tools.get_redis_profile(test_user_id)

        # Assertions
        assert result == expected_profile
        mock_redis.get.assert_called_once_with(f'user:profile:{test_user_id}')

    @patch('src.tools.database.redis.Redis')
    def test_get_redis_profile_not_found(self, mock_redis_class):
        """Test Redis profile not found."""
        # Mock Redis connection
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        mock_redis.ping.return_value = 'PONG'
        mock_redis.get.return_value = None

        # Test
        result = self.tools.get_redis_profile('nonexistent_user')

        # Assertions
        assert result is None

    @patch('src.tools.database.mysql.connector.connect')
    def test_get_mysql_profile_success(self, mock_connect):
        """Test successful MySQL profile retrieval."""
        # Mock MySQL connection
        mock_connection = Mock()
        mock_connect.return_value = mock_connection

        # Mock cursor
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor

        # Mock user data
        test_user_id = 'user123'
        mock_user_data = {
            'id': test_user_id,
            'name': 'Test User',
            'spending_tier': 'HIGH',
            'identity_tags': '["vip", "frequent_buyer"]'
        }
        mock_cursor.fetchone.side_effect = [
            mock_user_data,  # User info query
            {'total_clicks': 15, 'unique_products': 5}  # Activity query
        ]

        # Test
        result = self.tools.get_mysql_profile(test_user_id)

        # Assertions
        assert result is not None
        assert result['id'] == test_user_id
        assert result['name'] == 'Test User'
        assert result['spending_tier'] == 'HIGH'
        assert result['identity_tags'] == ['vip', 'frequent_buyer']
        assert result['recent_activity']['total_clicks_30d'] == 15
        assert result['recent_activity']['unique_products_viewed_30d'] == 5

    @patch('src.tools.database.mysql.connector.connect')
    def test_get_mysql_profile_user_not_found(self, mock_connect):
        """Test MySQL user not found."""
        # Mock MySQL connection
        mock_connection = Mock()
        mock_connect.return_value = mock_connection

        # Mock cursor
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # User not found

        # Test
        result = self.tools.get_mysql_profile('nonexistent_user')

        # Assertions
        assert result is None

    @patch('src.tools.database.DatabaseTools.get_redis_profile')
    @patch('src.tools.database.DatabaseTools.get_mysql_profile')
    def test_get_user_context_combined(self, mock_mysql, mock_redis):
        """Test combined user context retrieval."""
        test_user_id = 'user123'

        # Mock data
        redis_data = {'identity_tags': ['vip'], 'spending_tier': 'HIGH'}
        mysql_data = {
            'id': test_user_id,
            'name': 'Test User',
            'spending_tier': 'HIGH',
            'identity_tags': ['vip', 'frequent_buyer'],
            'detailed_info': {'some_field': 'value'},
            'recent_activity': {'total_clicks': 10}
        }

        mock_redis.return_value = redis_data
        mock_mysql.return_value = mysql_data

        # Test
        result = self.tools.get_user_context(test_user_id)

        # Assertions
        assert result['user_id'] == test_user_id
        assert result['redis_profile'] == redis_data
        assert result['mysql_profile'] == mysql_data
        assert result['combined_context'] is not None
        assert result['combined_context']['id'] == test_user_id
        assert result['combined_context']['cached_tags'] == ['vip']
        assert result['combined_context']['cached_spending_tier'] == 'HIGH'

    def test_close_connections(self):
        """Test closing database connections."""
        # Mock connections
        self.tools.redis_client = Mock()
        self.tools.mysql_connection = Mock()
        self.tools.mysql_connection.is_connected.return_value = True

        # Test close
        self.tools.close()

        # Assertions
        self.tools.redis_client.close.assert_called_once()
        self.tools.mysql_connection.close.assert_called_once()


class TestConvenienceFunctions:
    """Test convenience functions."""

    @patch('src.tools.database.DatabaseTools')
    def test_get_redis_profile_convenience(self, mock_db_tools_class):
        """Test convenience function for Redis profile."""
        # Mock
        mock_tools = Mock()
        mock_db_tools_class.return_value = mock_tools
        expected_data = {'id': 'user123'}
        mock_tools.get_redis_profile.return_value = expected_data

        # Test
        result = get_redis_profile('user123')

        # Assertions
        assert result == expected_data
        mock_tools.get_redis_profile.assert_called_once_with('user123')
        mock_tools.close.assert_called_once()

    @patch('src.tools.database.DatabaseTools')
    def test_get_mysql_profile_convenience(self, mock_db_tools_class):
        """Test convenience function for MySQL profile."""
        # Mock
        mock_tools = Mock()
        mock_db_tools_class.return_value = mock_tools
        expected_data = {'id': 'user123'}
        mock_tools.get_mysql_profile.return_value = expected_data

        # Test
        result = get_mysql_profile('user123')

        # Assertions
        assert result == expected_data
        mock_tools.get_mysql_profile.assert_called_once_with('user123')
        mock_tools.close.assert_called_once()

    @patch('src.tools.database.DatabaseTools')
    def test_get_user_context_convenience(self, mock_db_tools_class):
        """Test convenience function for user context."""
        # Mock
        mock_tools = Mock()
        mock_db_tools_class.return_value = mock_tools
        expected_data = {'user_id': 'user123', 'combined_context': {}}
        mock_tools.get_user_context.return_value = expected_data

        # Test
        result = get_user_context('user123')

        # Assertions
        assert result == expected_data
        mock_tools.get_user_context.assert_called_once_with('user123')
        mock_tools.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])