import os
import logging
from dotenv import load_dotenv
from bot import run_bot

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('stock_monitor.log'),
        logging.StreamHandler()
    ]
)

def main():
    # Get Discord bot token from environment variable
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        raise ValueError("Please set the DISCORD_TOKEN environment variable")
        
    # Run the bot
    run_bot(token)

if __name__ == "__main__":
    main()