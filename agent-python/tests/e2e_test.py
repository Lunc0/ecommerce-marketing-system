"""
End-to-end Integration Test for Marketing System.
Tests the complete flow from Java Kafka Producer to Python Agent.
"""

import time
import json
import logging
from kafka import KafkaProducer
from dotenv import load_dotenv
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
BEHAVIOR_TOPIC = 'behavior-normal'


class E2ETestRunner:
    """End-to-end test runner for marketing system."""

    def __init__(self, user_id: str = "e2e-test-user"):
        """
        Initialize the test runner.

        Args:
            user_id: The user ID to use for testing
        """
        self.user_id = user_id
        self.producer = None

    def setup_kafka_producer(self):
        """Initialize Kafka producer."""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                request_timeout_ms=10000
            )
            logger.info(f"Kafka producer connected to {KAFKA_BOOTSTRAP_SERVERS}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            return False

    def send_user_click_events(self, count: int = 15):
        """
        Send user click events to Kafka.

        Args:
            count: Number of click events to send
        """
        logger.info(f"Sending {count} click events for user {self.user_id}...")

        events_sent = 0
        for i in range(count):
            event = {
                "userId": self.user_id,
                "eventType": "CLICK",
                "skuId": f"SKU-{(i % 5) + 100}",
                "price": 99 + (i % 5) * 50,
                "timestamp": time.time()
            }

            try:
                # Send with userId as key for ordering
                future = self.producer.send(
                    BEHAVIOR_TOPIC,
                    key=self.user_id,
                    value=event
                )
                future.get(timeout=5)
                events_sent += 1
                logger.info(f"  [{i+1}/{count}] Sent CLICK event for SKU-{(i % 5) + 100}")
            except Exception as e:
                logger.error(f"Failed to send event {i+1}: {e}")

        self.producer.flush()
        logger.info(f"Successfully sent {events_sent}/{count} events")
        return events_sent

    def run_test(self):
        """Run the end-to-end test."""
        logger.info("=" * 60)
        logger.info("E2E Integration Test - Marketing System")
        logger.info("=" * 60)

        # Step 1: Setup Kafka Producer
        logger.info("\n[Step 1] Setting up Kafka Producer...")
        if not self.setup_kafka_producer():
            logger.error("Failed to setup Kafka producer. Test aborted.")
            return False

        # Step 2: Send User Click Events
        logger.info("\n[Step 2] Sending User Click Events...")
        sent_count = self.send_user_click_events(count=15)

        if sent_count < 15:
            logger.warning(f"Only {sent_count}/15 events sent. Test may not trigger high intent.")

        # Step 3: Wait for processing
        logger.info("\n[Step 3] Waiting for system processing...")
        logger.info("Please check Java Backend and Python Agent logs:")
        logger.info("  Expected Java log: 'Threshold reached, promoting event'")
        logger.info("  Expected Python log: 'Received High Intent'")
        logger.info("  Expected Python log: 'SMS Sent'")

        for i in range(10, 0, -1):
            time.sleep(1)
            logger.info(f"  Waiting... {i}s remaining")

        # Step 4: Summary
        logger.info("\n" + "=" * 60)
        logger.info("Test Summary:")
        logger.info(f"  - User ID: {self.user_id}")
        logger.info(f"  - Events sent: {sent_count}/15")
        logger.info(f"  - Topic: {BEHAVIOR_TOPIC}")
        logger.info(f"  - Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
        logger.info("=" * 60)

        # Cleanup
        self.producer.close()
        logger.info("Test completed. Check logs for verification points.")

        return True


def main():
    """Main entry point."""
    import sys

    # Get user_id from command line or use default
    user_id = sys.argv[1] if len(sys.argv) > 1 else "e2e-test-user"

    runner = E2ETestRunner(user_id=user_id)

    try:
        success = runner.run_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
