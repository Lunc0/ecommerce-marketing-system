"""
Database tools for Python Agent to retrieve user context data.
Provides functions to read user profiles from Redis and MySQL.
"""

import json
import logging
import redis
import mysql.connector
from mysql.connector import Error
from typing import Dict, Optional, Any
from dotenv import load_dotenv
import os

logger = logging.getLogger(__name__)

class DatabaseTools:
    """Database tools for accessing user profile data."""

    def __init__(self):
        """Initialize database connections."""
        load_dotenv()

        # Redis connection
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', '6379'))
        self.redis_db = int(os.getenv('REDIS_DB', '0'))

        # MySQL connection
        self.mysql_host = os.getenv('MYSQL_HOST', 'localhost')
        self.mysql_port = int(os.getenv('MYSQL_PORT', '3306'))
        self.mysql_user = os.getenv('MYSQL_USER', 'root')
        self.mysql_password = os.getenv('MYSQL_PASSWORD', '')
        self.mysql_database = os.getenv('MYSQL_DATABASE', 'ecommerce')

        # Initialize connections
        self.redis_client = None
        self.mysql_connection = None

    def _init_redis(self):
        """Initialize Redis connection if not already connected."""
        if self.redis_client is None:
            try:
                self.redis_client = redis.Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    db=self.redis_db,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Connected to Redis successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise

    def _init_mysql(self):
        """Initialize MySQL connection if not already connected."""
        if self.mysql_connection is None:
            try:
                self.mysql_connection = mysql.connector.connect(
                    host=self.mysql_host,
                    port=self.mysql_port,
                    user=self.mysql_user,
                    password=self.mysql_password,
                    database=self.mysql_database,
                    connect_timeout=5
                )
                logger.info("Connected to MySQL successfully")
            except Error as e:
                logger.error(f"Failed to connect to MySQL: {e}")
                raise

    def get_redis_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Read user profile from Redis (preheated by Java backend).

        Args:
            user_id: The user ID to retrieve profile for

        Returns:
            Dictionary containing user profile data or None if not found
        """
        try:
            self._init_redis()

            # Get user profile from Redis
            profile_key = f"user:profile:{user_id}"
            profile_json = self.redis_client.get(profile_key)

            if profile_json:
                profile = json.loads(profile_json)
                logger.info(f"Retrieved Redis profile for user {user_id}")
                return profile
            else:
                logger.warning(f"Redis profile not found for user {user_id}")
                return None

        except Exception as e:
            logger.error(f"Error reading Redis profile for user {user_id}: {e}")
            return None

    def get_mysql_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Read detailed user profile from MySQL.

        Args:
            user_id: The user ID to retrieve profile for

        Returns:
            Dictionary containing detailed user profile data or None if not found
        """
        try:
            self._init_mysql()

            cursor = self.mysql_connection.cursor(dictionary=True)

            # Query user basic info
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()

            if not user_data:
                logger.warning(f"MySQL user not found for ID {user_id}")
                return None

            # Build profile dictionary
            profile = {
                'id': user_data['id'],
                'name': user_data['name'],
                'spending_tier': user_data['spending_tier'],
                'identity_tags': json.loads(user_data['identity_tags']) if user_data['identity_tags'] else [],
                'detailed_info': user_data
            }

            # Add historical behavior if needed (could be extended)
            cursor.execute("""
                SELECT COUNT(*) as total_clicks, COUNT(DISTINCT sku_id) as unique_products
                FROM user_behavior
                WHERE user_id = %s
                AND timestamp >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """, (user_id,))
            behavior_data = cursor.fetchone()

            if behavior_data:
                profile['recent_activity'] = {
                    'total_clicks_30d': behavior_data['total_clicks'],
                    'unique_products_viewed_30d': behavior_data['unique_products']
                }

            logger.info(f"Retrieved MySQL profile for user {user_id}")
            return profile

        except Error as e:
            logger.error(f"Error reading MySQL profile for user {user_id}: {e}")
            return None
        finally:
            if cursor:
                cursor.close()

    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get complete user context by combining Redis and MySQL data.

        Args:
            user_id: The user ID to retrieve context for

        Returns:
            Dictionary containing complete user context
        """
        context = {
            'user_id': user_id,
            'redis_profile': None,
            'mysql_profile': None,
            'combined_context': None
        }

        # Get Redis profile (cached/quick data)
        context['redis_profile'] = self.get_redis_profile(user_id)

        # Get MySQL profile (detailed data)
        context['mysql_profile'] = self.get_mysql_profile(user_id)

        # Combine context if both sources have data
        if context['redis_profile'] and context['mysql_profile']:
            context['combined_context'] = {
                **context['mysql_profile'],  # MySQL has priority for basic info
                'cached_tags': context['redis_profile'].get('identity_tags', []),
                'cached_spending_tier': context['redis_profile'].get('spending_tier')
            }

        return context

    def close(self):
        """Close all database connections."""
        if self.redis_client:
            self.redis_client.close()
            logger.info("Redis connection closed")

        if self.mysql_connection and self.mysql_connection.is_connected():
            self.mysql_connection.close()
            logger.info("MySQL connection closed")


# Convenience functions for direct use
def get_redis_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user profile from Redis."""
    tools = DatabaseTools()
    try:
        return tools.get_redis_profile(user_id)
    finally:
        tools.close()


def get_mysql_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user profile from MySQL."""
    tools = DatabaseTools()
    try:
        return tools.get_mysql_profile(user_id)
    finally:
        tools.close()


def get_user_context(user_id: str) -> Dict[str, Any]:
    """Get complete user context from both sources."""
    tools = DatabaseTools()
    try:
        return tools.get_user_context(user_id)
    finally:
        tools.close()