"""
E-commerce Real-time Marketing System - Python Agent
Main entry point for the marketing agent.
"""

import logging
from dotenv import load_dotenv
from trigger import KafkaTrigger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the Python agent."""
    logger.info("Starting Python Marketing Agent...")

    # Load environment variables
    load_dotenv()

    # Initialize and start the Kafka trigger
    trigger = KafkaTrigger()
    try:
        trigger.start()
    except KeyboardInterrupt:
        logger.info("Shutting down Python Agent...")
        trigger.stop()

if __name__ == "__main__":
    main()