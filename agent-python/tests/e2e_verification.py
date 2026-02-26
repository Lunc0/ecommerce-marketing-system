"""
End-to-End Verification Script for Marketing System.
Verifies the complete flow from Kafka to Agent.
"""

import time
import json
import logging
from kafka import KafkaConsumer
from dotenv import load_dotenv
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
BEHAVIOR_TOPIC = 'behavior-normal'
INTENT_TOPIC = 'intent-high'


class E2EVerifier:
    """Verifies the end-to-end marketing system flow."""

    def __init__(self, user_id: str = "e2e-test-user", timeout: int = 30):
        """
        Initialize the verifier.

        Args:
            user_id: User ID to track
            timeout: Maximum time to wait for events (seconds)
        """
        self.user_id = user_id
        self.timeout = timeout
        self.high_intent_received = False

    def verify_kafka_topics(self):
        """Verify that Kafka topics exist."""
        logger.info("=" * 60)
        logger.info("E2E Verification - Marketing System")
        logger.info("=" * 60)

        logger.info(f"\n[Verification 1] Kafka Topics")
        logger.info(f"  Bootstrap: {KAFKA_BOOTSTRAP_SERVERS}")
        logger.info(f"  Behavior Topic: {BEHAVIOR_TOPIC}")
        logger.info(f"  Intent Topic: {INTENT_TOPIC}")

        # Check if we can connect to Kafka
        try:
            consumer = KafkaConsumer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                consumer_timeout_ms=5000
            )
            # Use subscription to check topic existence
            try:
                consumer.subscribe([BEHAVIOR_TOPIC, INTENT_TOPIC])
                logger.info(f"  ✓ Successfully subscribed to topics")
                logger.info(f"  - {BEHAVIOR_TOPIC}")
                logger.info(f"  - {INTENT_TOPIC}")
            except Exception as e:
                logger.warning(f"  ✗ Failed to subscribe: {e}")

            consumer.close()
        except Exception as e:
            logger.error(f"  ✗ Failed to connect to Kafka: {e}")
            return False

        return True

    def listen_for_high_intent(self):
        """Listen for high-intent events from Java backend."""
        logger.info(f"\n[Verification 2] Listening for High Intent Events")
        logger.info(f"  Topic: {INTENT_TOPIC}")
        logger.info(f"  User ID: {self.user_id}")
        logger.info(f"  Timeout: {self.timeout}s")

        try:
            consumer = KafkaConsumer(
                INTENT_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id='e2e-verifier',
                auto_offset_reset='earliest',
                value_deserializer=lambda m: m.decode('utf-8'),
                consumer_timeout_ms=5000
            )

            start_time = time.time()
            logger.info("  Listening for events...")

            for message in consumer:
                elapsed = time.time() - start_time
                if elapsed > self.timeout:
                    logger.info(f"  Timeout reached ({self.timeout}s)")
                    break

                try:
                    event_data = json.loads(message.value)
                    event_user_id = event_data.get('userId') or event_data.get('user_id')

                    if event_user_id == self.user_id:
                        self.high_intent_received = True
                        logger.info(f"  ✓ Received High Intent for user {self.user_id}")
                        logger.info(f"    Event Type: {event_data.get('eventType', 'HIGH_INTENT')}")
                        logger.info(f"    Timestamp: {event_data.get('timestamp')}")
                        logger.info(f"    Latency: {elapsed:.2f}s")
                        logger.info(f"    Full Event: {json.dumps(event_data, indent=4, ensure_ascii=False)}")
                        break

                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    logger.warning(f"  Error processing message: {e}")

            consumer.close()

            if self.high_intent_received:
                logger.info(f"  ✓ Verification PASSED: High Intent event received")
                return True
            else:
                logger.warning(f"  ✗ Verification FAILED: No High Intent event received for user {self.user_id}")
                logger.info(f"    Hint: Make sure Java Backend is running and processed the behavior events")
                return False

        except Exception as e:
            logger.error(f"  ✗ Error listening to Kafka: {e}")
            return False

    def generate_test_report(self):
        """Generate final test report."""
        logger.info("\n" + "=" * 60)
        logger.info("Test Report")
        logger.info("=" * 60)
        logger.info(f"  User ID: {self.user_id}")
        logger.info(f"  High Intent Received: {'✓ YES' if self.high_intent_received else '✗ NO'}")
        logger.info(f"  Kafka Bootstrap: {KAFKA_BOOTSTRAP_SERVERS}")
        logger.info("=" * 60)

        return self.high_intent_received


def main():
    """Main entry point."""
    import sys

    user_id = sys.argv[1] if len(sys.argv) > 1 else "e2e-test-user"

    verifier = E2EVerifier(user_id=user_id)

    # Step 1: Verify Kafka Topics
    if not verifier.verify_kafka_topics():
        logger.error("Kafka verification failed. Exiting.")
        sys.exit(1)

    # Step 2: Listen for High Intent
    success = verifier.listen_for_high_intent()

    # Step 3: Generate Report
    verifier.generate_test_report()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
