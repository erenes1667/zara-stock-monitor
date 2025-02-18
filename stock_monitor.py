import discord
from discord.ext import commands, tasks
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC 
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import time
import random
import asyncio
from dataclasses import dataclass
from typing import List, Optional, Dict
import logging
import os
from datetime import datetime
from PIL import Image
import io

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('stock_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class Product:
    url: str
    sizes: List[str]
    name: Optional[str] = None
    price: Optional[str] = None
    last_check: Optional[datetime] = None

class ZaraStockMonitor(commands.Bot):
    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.products: Dict[str, Product] = {}  # URL -> Product
        self.driver = None
        self.screenshot_dir = "screenshots"
        self._init_screenshot_dir()
        self.monitoring_task = None
        
        # Add commands
        self.add_commands()
        
    def _init_screenshot_dir(self):
        """Create screenshots directory if it doesn't exist."""
        if not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)
            
    def add_commands(self):
        @self.command(name='add')
        async def add_product(ctx, url: str, *sizes):
            """Add a product to monitor. Example: !add https://zara.com/product XS S M"""
            if not url.startswith('https://www.zara.com'):
                await ctx.send("❌ Invalid URL. Please provide a valid Zara product URL.")
                return
                
            if not sizes:
                await ctx.send("❌ Please specify at least one size to monitor.")
                return
                
            # Initialize driver if needed
            if not self.driver:
                self._init_driver()
                
            try:
                # Get product name from URL
                self.driver.get(url)
                time.sleep(2)  # Wait for page load
                name_element = self.driver.find_element(By.CSS