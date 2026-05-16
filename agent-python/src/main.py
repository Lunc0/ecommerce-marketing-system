"""
E-commerce Real-time Marketing System - Python Agent
Main entry point for the marketing agent.
"""

import logging
import os
from dotenv import load_dotenv
from trigger import HighIntentTrigger
from agent import MarketingAgent
from langchain_openai import ChatOpenAI

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

    # Initialize the LLM (ensure OPENAI_API_KEY is set in .env)
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo"),
        temperature=0.2
    )

    # Initialize the Marketing Agent
    agent = MarketingAgent(llm=llm)

    # Initialize the Kafka trigger
    trigger = HighIntentTrigger()
    
    try:
        # Start consuming and pass the agent's process_event method as the callback
        trigger.consume_forever(callback=agent.process_event)
    except KeyboardInterrupt:
        logger.info("Shutting down Python Agent...")
        trigger.stop()

if __name__ == "__main__":
    main()