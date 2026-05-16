"""
Kafka Trigger for Python Agent.
Listens to high-intent events from the Java fast track pipeline.
"""

import json
import logging
import threading
import time
from typing import Optional, Callable, Dict, Any
from kafka import KafkaConsumer, KafkaProducer
from kafka.structs import TopicPartition
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
        self.retry_topic = os.getenv('KAFKA_TOPIC_HIGH_INTENT_RETRY', f'{self.topic}-retry')
        self.dead_letter_topic = os.getenv('KAFKA_TOPIC_HIGH_INTENT_DLQ', f'{self.topic}-dlq')
        self.max_retries = int(os.getenv("KAFKA_PROCESS_MAX_RETRIES", "3"))
        self.retry_backoff_base_seconds = float(os.getenv("KAFKA_PROCESS_RETRY_BACKOFF_BASE_SECONDS", "1"))
        self.retry_backoff_max_seconds = float(os.getenv("KAFKA_PROCESS_RETRY_BACKOFF_MAX_SECONDS", "60"))

        # Consumer instance
        self.consumer: Optional[KafkaConsumer] = None
        self.retry_consumer: Optional[KafkaConsumer] = None
        self.producer: Optional[KafkaProducer] = None
        self._running = False
        self._retry_thread: Optional[threading.Thread] = None

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
            enable_auto_commit=False,  # Changed to False for manual offset management
            value_deserializer=lambda m: m.decode('utf-8'),
            consumer_timeout_ms=1000  # Timeout for polling
        )
        logger.info(f"Kafka consumer initialized for topic '{self.topic}'")
        return consumer

    def _init_retry_consumer(self) -> KafkaConsumer:
        consumer = KafkaConsumer(
            self.retry_topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=f"{self.group_id}-retry",
            auto_offset_reset='latest',
            enable_auto_commit=False,
            value_deserializer=lambda m: m.decode('utf-8'),
            consumer_timeout_ms=1000
        )
        logger.info(f"Kafka retry consumer initialized for topic '{self.retry_topic}'")
        return consumer

    def _init_producer(self) -> KafkaProducer:
        producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
        )
        logger.info("Kafka producer initialized")
        return producer

    def _backoff_seconds(self, attempt: int) -> float:
        if attempt <= 0:
            return 0.0
        value = self.retry_backoff_base_seconds * (2 ** (attempt - 1))
        return min(self.retry_backoff_max_seconds, value)

    def _publish(self, topic: str, payload: Dict[str, Any]):
        if self.producer is None:
            self.producer = self._init_producer()
        self.producer.send(topic, value=payload).get(timeout=10)

    def _consume_retry_forever(self, callback: Callable[[Dict[str, Any]], Dict[str, Any]]):
        if self.retry_consumer is None:
            self.retry_consumer = self._init_retry_consumer()
        if self.producer is None:
            self.producer = self._init_producer()

        while self._running:
            for message in self.retry_consumer:
                if not self._running:
                    break
                try:
                    payload = json.loads(message.value)
                except Exception as e:
                    logger.error(f"Failed to parse retry message: {e}")
                    self.retry_consumer.commit()
                    continue

                next_retry_at = payload.get("next_retry_at") or 0
                now_ms = int(time.time() * 1000)
                if next_retry_at > now_ms:
                    sleep_seconds = max(0.0, (next_retry_at - now_ms) / 1000.0)
                    sleep_seconds = min(sleep_seconds, 1.0)
                    time.sleep(sleep_seconds)
                    self.retry_consumer.seek(TopicPartition(message.topic, message.partition), message.offset)
                    break

                event = payload.get("event")
                attempt = int(payload.get("attempt") or 0)
                last_error = payload.get("last_error")
                if not isinstance(event, dict):
                    logger.error("Retry message missing event payload")
                    self.retry_consumer.commit()
                    continue

                error: Optional[Exception] = None
                result: Optional[Dict[str, Any]] = None
                try:
                    result = callback(event)
                except Exception as e:
                    error = e

                processed_ok = bool(result and result.get("success", False)) and error is None
                if processed_ok:
                    self.retry_consumer.commit()
                    logger.info(f"Retry succeeded and committed for user {event.get('user_id')}")
                    continue

                new_attempt = attempt + 1
                err_text = str(error) if error is not None else str(result)
                if new_attempt > self.max_retries:
                    dlq_payload = {
                        "event": event,
                        "attempt": new_attempt,
                        "failed_at": int(time.time() * 1000),
                        "last_error": err_text or last_error,
                        "source": "retry",
                    }
                    self._publish(self.dead_letter_topic, dlq_payload)
                    self.retry_consumer.commit()
                    logger.error(f"Retry exceeded max retries; sent to DLQ for user {event.get('user_id')}")
                    continue

                delay_seconds = self._backoff_seconds(new_attempt)
                retry_payload = {
                    "event": event,
                    "attempt": new_attempt,
                    "next_retry_at": int(time.time() * 1000 + delay_seconds * 1000),
                    "last_error": err_text or last_error,
                }
                self._publish(self.retry_topic, retry_payload)
                self.retry_consumer.commit()
                logger.warning(f"Retry scheduled attempt {new_attempt}/{self.max_retries} for user {event.get('user_id')}")

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

    def consume_forever(self, callback: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """
        Continuously consume messages and invoke callback for each event.

        Args:
            callback: Function to call with parsed event data, should return a dict with a 'success' boolean.
        """
        if self.consumer is None:
            self.consumer = self._init_consumer()

        self._running = True
        logger.info(f"Starting to consume messages from '{self.topic}' (press Ctrl+C to stop)")

        try:
            if self._retry_thread is None:
                self._retry_thread = threading.Thread(
                    target=self._consume_retry_forever,
                    args=(callback,),
                    daemon=True
                )
                self._retry_thread.start()

            while self._running:
                for message in self.consumer:
                    if not self._running:
                        break

                    event = self.parse_message(message.value)
                    if event:
                        try:
                            result = callback(event)
                            if result and result.get('success', False):
                                self.consumer.commit()
                                logger.info(f"Successfully processed and committed message for user {event['user_id']}")
                            else:
                                delay_seconds = self._backoff_seconds(1)
                                retry_payload = {
                                    "event": event,
                                    "attempt": 1,
                                    "next_retry_at": int(time.time() * 1000 + delay_seconds * 1000),
                                    "last_error": str(result),
                                    "source": "main",
                                }
                                self._publish(self.retry_topic, retry_payload)
                                self.consumer.commit()
                                logger.warning(f"Processing failed; forwarded to retry topic for user {event['user_id']}. Result: {result}")
                        except Exception as e:
                            delay_seconds = self._backoff_seconds(1)
                            retry_payload = {
                                "event": event,
                                "attempt": 1,
                                "next_retry_at": int(time.time() * 1000 + delay_seconds * 1000),
                                "last_error": str(e),
                                "source": "main",
                            }
                            self._publish(self.retry_topic, retry_payload)
                            self.consumer.commit()
                            logger.error(f"Error in callback; forwarded to retry topic for user {event['user_id']}: {e}")

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
        if self.retry_consumer:
            self.retry_consumer.close()
            logger.info("Kafka retry consumer closed")
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer closed")

    def __enter__(self):
        """Context manager entry."""
        self.consumer = self._init_consumer()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


# Convenience function for simple usage
def listen_high_intent(callback: Callable[[Dict[str, Any]], Dict[str, Any]], group_id: str = "python-agent"):
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
    def print_event(event: Dict[str, Any]) -> Dict[str, Any]:
        print(f"[Received High Intent] User: {event['user_id']}, Type: {event['event_type']}")
        print(f"Raw Data: {json.dumps(event['raw_data'], indent=2)}")
        return {"success": True}

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
