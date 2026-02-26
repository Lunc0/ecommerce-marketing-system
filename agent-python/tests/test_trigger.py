"""
Unit tests for Kafka Trigger module.
Tests message parsing and consumer initialization using mocks.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from kafka import KafkaConsumer

from src.trigger import HighIntentTrigger, listen_high_intent


class TestHighIntentTrigger:
    """Test cases for HighIntentTrigger class."""

    @pytest.fixture
    def trigger(self):
        """Create a HighIntentTrigger instance for testing."""
        return HighIntentTrigger(group_id="test-group")

    @pytest.fixture
    def sample_message_value(self):
        """Sample Kafka message value as JSON string."""
        event = {
            "userId": "test-user-123",
            "eventType": "HIGH_INTENT",
            "eventTimestamp": "2024-02-26T12:00:00Z",
            "clickCount": 11,
            "timeWindow": "5min"
        }
        return json.dumps(event)

    def test_init(self, trigger):
        """Test trigger initialization with default values."""
        assert trigger.group_id == "test-group"
        assert trigger.topic == "intent-high"
        assert trigger.bootstrap_servers == "localhost:9092"
        assert trigger._running is False
        assert trigger.consumer is None

    def test_init_custom_servers(self):
        """Test trigger initialization with custom bootstrap servers."""
        with patch.dict('os.environ', {'KAFKA_BOOTSTRAP_SERVERS': 'kafka-broker:9092'}):
            trigger = HighIntentTrigger(group_id="custom-group")
            assert trigger.bootstrap_servers == "kafka-broker:9092"

    @patch('src.trigger.KafkaConsumer')
    def test_init_consumer(self, mock_kafka_consumer, trigger):
        """Test Kafka consumer initialization."""
        mock_consumer_instance = Mock()
        mock_kafka_consumer.return_value = mock_consumer_instance

        consumer = trigger._init_consumer()

        mock_kafka_consumer.assert_called_once()
        assert consumer == mock_consumer_instance

    def test_parse_message_success(self, trigger, sample_message_value):
        """Test successful message parsing."""
        result = trigger.parse_message(sample_message_value)

        assert result is not None
        assert result['user_id'] == "test-user-123"
        assert result['event_type'] == "HIGH_INTENT"
        assert result['timestamp'] == "2024-02-26T12:00:00Z"
        assert result['raw_data']['clickCount'] == 11

    def test_parse_message_with_lowercase_fields(self, trigger):
        """Test message parsing with lowercase field names."""
        event = {
            "user_id": "test-user-456",
            "event_type": "PURCHASE_INTENT",
            "timestamp": "2024-02-26T13:30:00Z"
        }
        message_value = json.dumps(event)

        result = trigger.parse_message(message_value)

        assert result is not None
        assert result['user_id'] == "test-user-456"
        assert result['event_type'] == "PURCHASE_INTENT"

    def test_parse_message_missing_user_id(self, trigger):
        """Test message parsing when user_id is missing."""
        event = {
            "eventType": "HIGH_INTENT",
            "timestamp": "2024-02-26T12:00:00Z"
        }
        message_value = json.dumps(event)

        result = trigger.parse_message(message_value)

        assert result is None

    def test_parse_message_invalid_json(self, trigger):
        """Test message parsing with invalid JSON."""
        result = trigger.parse_message("not valid json")

        assert result is None

    def test_parse_message_default_event_type(self, trigger):
        """Test message parsing with missing event_type (should default)."""
        event = {
            "userId": "test-user-789",
            "timestamp": "2024-02-26T14:00:00Z"
        }
        message_value = json.dumps(event)

        result = trigger.parse_message(message_value)

        assert result is not None
        assert result['event_type'] == "HIGH_INTENT"

    @patch('src.trigger.KafkaConsumer')
    def test_consume_single_no_message(self, mock_kafka_consumer, trigger):
        """Test consuming when no messages are available."""
        mock_consumer_instance = Mock()
        mock_consumer_instance.__iter__ = Mock(return_value=iter([]))
        mock_kafka_consumer.return_value = mock_consumer_instance

        result = trigger.consume_single()

        assert result is None

    @patch('src.trigger.KafkaConsumer')
    def test_consume_single_with_message(self, mock_kafka_consumer, trigger, sample_message_value):
        """Test consuming a single message."""
        mock_message = Mock()
        mock_message.value = sample_message_value

        mock_consumer_instance = Mock()
        mock_consumer_instance.__iter__ = Mock(return_value=iter([mock_message]))
        mock_kafka_consumer.return_value = mock_consumer_instance

        result = trigger.consume_single()

        assert result is not None
        assert result['user_id'] == "test-user-123"

    @patch('src.trigger.KafkaConsumer')
    def test_consume_single_with_invalid_message(self, mock_kafka_consumer, trigger):
        """Test consuming an invalid message."""
        mock_message = Mock()
        mock_message.value = "invalid json"

        mock_consumer_instance = Mock()
        mock_consumer_instance.__iter__ = Mock(return_value=iter([mock_message]))
        mock_kafka_consumer.return_value = mock_consumer_instance

        result = trigger.consume_single()

        assert result is None

    @patch('src.trigger.KafkaConsumer')
    def test_context_manager(self, mock_kafka_consumer):
        """Test using trigger as a context manager."""
        mock_consumer_instance = Mock()
        mock_kafka_consumer.return_value = mock_consumer_instance

        with HighIntentTrigger(group_id="ctx-test") as trigger:
            assert trigger.consumer is not None

        mock_consumer_instance.close.assert_called_once()


class TestListenHighIntent:
    """Test cases for listen_high_intent convenience function."""

    @patch('src.trigger.HighIntentTrigger')
    def test_listen_with_callback(self, mock_trigger_class):
        """Test listen_high_intent with a callback function."""
        mock_trigger_instance = Mock()
        mock_trigger_class.return_value = mock_trigger_instance

        callback = Mock()
        mock_trigger_instance.consume_forever.side_effect = KeyboardInterrupt()

        try:
            listen_high_intent(callback, group_id="listener-test")
        except KeyboardInterrupt:
            pass

        mock_trigger_class.assert_called_once_with(group_id="listener-test")
        mock_trigger_instance.consume_forever.assert_called_once_with(callback)
        mock_trigger_instance.stop.assert_called_once()


class TestTriggerMessageFormats:
    """Test various message formats that might be received from Java."""

    @pytest.fixture
    def trigger(self):
        """Create a HighIntentTrigger instance for testing."""
        return HighIntentTrigger(group_id="test-group")

    def test_java_style_message(self, trigger):
        """Test parsing Java-style message (camelCase)."""
        event = {
            "userId": "user-001",
            "eventType": "HIGH_INTENT_CLICKS",
            "eventTimestamp": "2024-02-26T10:00:00.000Z",
            "metadata": {
                "threshold": 10,
                "actualClicks": 12
            }
        }
        result = trigger.parse_message(json.dumps(event))

        assert result['user_id'] == "user-001"
        assert result['event_type'] == "HIGH_INTENT_CLICKS"
        assert result['raw_data']['metadata']['actualClicks'] == 12

    def test_python_style_message(self, trigger):
        """Test parsing Python-style message (snake_case)."""
        event = {
            "user_id": "user-002",
            "event_type": "ADD_TO_CART",
            "timestamp": "2024-02-26T11:00:00.000Z",
            "product_id": "prod-12345",
            "value": 99.99
        }
        result = trigger.parse_message(json.dumps(event))

        assert result['user_id'] == "user-002"
        assert result['event_type'] == "ADD_TO_CART"

    def test_mixed_style_message(self, trigger):
        """Test parsing mixed-style message."""
        event = {
            "userId": "user-003",
            "event_type": "CHECKOUT_START",
            "timestamp": "2024-02-26T12:00:00.000Z"
        }
        result = trigger.parse_message(json.dumps(event))

        assert result['user_id'] == "user-003"
        assert result['event_type'] == "CHECKOUT_START"
