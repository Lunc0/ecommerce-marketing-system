"""
Kafka Trigger for Python Agent.
Listens to high-intent events from the Java fast track pipeline.
"""

import json
import logging
from typing import Optional, Callable, Dict, Any
from kafka import KafkaConsumer
from dotenv import load_dotenv
import os

logger = logging.getLogger(__name__)


class HighIntentTrigger:
    """
    Kafka consumer that listens to 'intent-high' topic for high-value user intents.
    Triggers the agent workflow when high-intent events are received.
    """

    def __init__(self, group_id: str = "python-agent"):
        """
        Initialize the Kafka consumer.

        Args:
            group_id: Consumer group ID for the Kafka consumer
        """
        load_dotenv()

        # Load configuration from environment
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.topic = os.getenv('KAFKA_TOPIC_HIGH_INTENT', 'intent-high')
        self.group_id = group_id

        # Consumer instance
        self.consumer: Optional[KafkaConsumer] = None
        self._running = False

    def _init_consumer(self) -> KafkaConsumer:
        """
        Initialize and return a Kafka consumer.

        Returns:
            Configured KafkaConsumer instance
        """
        consumer = KafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset='latest',
            enable_auto_commit=True,
            value_deserializer=lambda m: m.decode('utf-8'),
            consumer_timeout_ms=1000  # Timeout for polling
        )
        logger.info(f"Kafka consumer initialized for topic '{self.topic}'")
        return consumer

    def parse_message(self, message_value: str) -> Optional[Dict[str, Any]]:
        """
        Parse Kafka message to extract user_id and event_type.

        Args:
            message_value: Raw JSON string from Kafka message

        Returns:
            Dictionary containing parsed event data with keys:
                - user_id: The user identifier
                - event_type: Type of the high-intent event
                - timestamp: Event timestamp (if available)
                - raw_data: Complete raw message
            Returns None if parsing fails
        """
        try:
            event_data = json.loads(message_value)

            # Extract user_id and event_type
            user_id = event_data.get('userId') or event_data.get('user_id')
            event_type = event_data.get('eventType') or event_data.get('event_type', 'HIGH_INTENT')

            if not user_id:
                logger.warning(f"Message missing user_id: {message_value}")
                return None

            parsed = {
                'user_id': str(user_id),
                'event_type': event_type,
                'timestamp': event_data.get('timestamp') or event_data.get('eventTimestamp'),
                'raw_data': event_data
            }

            logger.info(f"Parsed high-intent event: user_id={user_id}, event_type={event_type}")
            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON message: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing message: {e}")
            return None

    def consume_single(self) -> Optional[Dict[str, Any]]:
        """
        Consume a single message from Kafka.

        Returns:
            Parsed event data or None if no message available
        """
        if self.consumer is None:
            self.consumer = self._init_consumer()

        try:
            for message in self.consumer:
                event = self.parse_message(message.value)
                if event:
                    return event
            return None
        except Exception as e:
            logger.error(f"Error consuming message: {e}")
            return None

    def consume_forever(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Continuously consume messages and invoke callback for each event.

        Args:
            callback: Function to call with parsed event data
        """
        if self.consumer is None:
            self.consumer = self._init_consumer()

        self._running = True
        logger.info(f"Starting to consume messages from '{self.topic}' (press Ctrl+C to stop)")

        try:
            while self._running:
                for message in self.consumer:
                    if not self._running:
                        break

                    event = self.parse_message(message.value)
                    if event:
                        try:
                            callback(event)
                        except Exception as e:
                            logger.error(f"Error in callback for user {event['user_id']}: {e}")

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping consumer...")
        except Exception as e:
            logger.error(f"Fatal error in consumer loop: {e}")
        finally:
            self.stop()

    def stop(self):
        """Stop the consumer and close connections."""
        self._running = False
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")

    def __enter__(self):
        """Context manager entry."""
        self.consumer = self._init_consumer()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


# Convenience function for simple usage
def listen_high_intent(callback: Callable[[Dict[str, Any]], None], group_id: str = "python-agent"):
    """
    Start listening to high-intent events with a callback.

    Args:
        callback: Function to call with parsed event data
        group_id: Consumer group ID

    Example:
        def handle_event(event):
            print(f"High intent from user {event['user_id']}: {event['event_type']}")

        listen_high_intent(handle_event)
    """
    trigger = HighIntentTrigger(group_id=group_id)
    try:
        trigger.consume_forever(callback)
    finally:
        trigger.stop()


if __name__ == "__main__":
    # Simple test: print received events
    def print_event(event: Dict[str, Any]):
        print(f"[Received High Intent] User: {event['user_id']}, Type: {event['event_type']}")
        print(f"Raw Data: {json.dumps(event['raw_data'], indent=2)}")

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("Starting High Intent Trigger...")
    print(f"Listening on topic: {os.getenv('KAFKA_TOPIC_HIGH_INTENT', 'intent-high')}")
    print(f"Bootstrap servers: {os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')}")
    print("Press Ctrl+C to stop\n")

    listen_high_intent(print_event)
