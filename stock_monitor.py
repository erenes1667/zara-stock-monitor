import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC 
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import discord
from discord.ext import commands
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
    channel_id: Optional[int] = None  # Discord channel ID for notifications

class MonitorBot(commands.Bot):
    def __init__(self, command_prefix="!"):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=command_prefix, intents=intents)
        
        self.products: Dict[str, Product] = {}  # URL -> Product
        self.driver = None
        self.screenshot_dir = "screenshots"
        self.monitor_task = None
        self._init_screenshot_dir()
        
        # Add commands
        self.add_command(commands.Command(self.add_product, name="monitor"))
        self.add_command(commands.Command(self.list_products, name="list"))
        self.add_command(commands.Command(self.remove_product, name="remove"))
        self.add_command(commands.Command(self.help_command, name="help"))
        
    def _init_screenshot_dir(self):
        """Create screenshots directory if it doesn't exist."""
        if not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)
    
    def _init_driver(self):
        """Initialize Chrome driver with optimal settings."""
        if self.driver is None:
            options = uc.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            
            # Add random user agent
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            ]
            options.add_argument(f'user-agent={random.choice(user_agents)}')
            
            self.driver = uc.Chrome(options=options)
            self.driver.implicitly_wait(10)
            
    async def add_product(self, ctx, url: str, *sizes):
        """Add a product to monitor. Usage: !monitor <url> <size1> <size2> ..."""
        if not sizes:
            await ctx.send("❌ Please specify at least one size to monitor!")
            return
            
        # Clean sizes (convert to uppercase and remove duplicates)
        sizes = list(set(size.upper() for size in sizes))
        
        try:
            # Initialize driver if needed
            self._init_driver()
            
            # Visit the URL to get product name and validate
            self.driver.get(url)
            time.sleep(random.uniform(2, 4))
            
            try:
                name_element = self.driver.find_element(By.CSS_SELECTOR, "[data-qa-action='product-name']")
                product_name = name_element.text.strip()
            except:
                product_name = "Unknown Product"
                
            # Create product
            product = Product(
                url=url,
                sizes=sizes,
                name=product_name,
                channel_id=ctx.channel.id
            )
            
            self.products[url] = product
            
            # Start monitoring if not already running
            if self.monitor_task is None or self.monitor_task.done():
                self.monitor_task = asyncio.create_task(self.monitor_stock())
            
            await ctx.send(f"✅ Now monitoring {product_name} for sizes: {', '.join(sizes)}")
            
        except Exception as e:
            logger.error(f"Error adding product {url}: {str(e)}")
            await ctx.send(f"❌ Error adding product: {str(e)}")
            
    async def list_products(self, ctx):
        """List all monitored products."""
        if not self.products:
            await ctx.send("No products are being monitored.")
            return
            
        embed = discord.Embed(title="📋 Monitored Products", color=0x2ecc71)
        
        for url, product in self.products.items():
            embed.add_field(
                name=product.name or "Unknown Product",
                value=f"Sizes: {', '.join(product.sizes)}\nURL: {url}",
                inline=False
            )
            
        await ctx.send(embed=embed)
        
    async def remove_product(self, ctx, url: str):
        """Remove a product from monitoring."""
        if url in self.products:
            product = self.products.pop(url)
            await ctx.send(f"✅ Stopped monitoring {product.name or 'product'}")
        else:
            await ctx.send("❌ Product not found in monitoring list!")
            
    async def help_command(self, ctx):
        """Show help information."""
        help_embed = discord.Embed(
            title="🛍️ Zara Stock Monitor - Commands",
            color=0x2ecc71,
            description="Monitor Zara products for stock availability"
        )
        
        commands = {
            "!monitor <url> <size1> <size2> ...": "Start monitoring a product for specific sizes",
            "!list": "Show all monitored products",
            "!remove <url>": "Stop monitoring a product",
            "!help": "Show this help message"
        }
        
        for cmd, desc in commands.items():
            help_embed.add_field(name=cmd, value=desc, inline=False)
            
        await ctx.send(embed=help_embed)
        
    def take_screenshot(self, product: Product) -> Optional[str]:
        """Take a screenshot of the product page."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.screenshot_dir}/{product.name or 'product'}_{timestamp}.png"
            
            # Take screenshot of the size selector area
            size_selector = self.driver.find_element(By.CSS_SELECTOR, "[data-qa-action='size-selector']")
            screenshot = size_selector.screenshot_as_png
            
            # Save and optimize screenshot
            image = Image.open(io.BytesIO(screenshot))
            image.save(filename, optimize=True, quality=85)
            
            return filename
        except Exception as e:
            logger.error(f"Error taking screenshot: {str(e)}")
            return None
            
    def check_stock(self, product: Product) -> tuple[List[str], Optional[str]]:
        """Check stock availability for a product."""
        available_sizes = []
        screenshot_path = None
        
        try:
            self.driver.get(product.url)
            time.sleep(random.uniform(2, 4))
            
            # Update product price if available
            try:
                price_element = self.driver.find_element(By.CSS_SELECTOR, "[data-qa-action='product-price']")
                product.price = price_element.text.strip()
            except:
                pass
            
            # Wait for size selector to be present
            size_elements = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-qa-action='size-selector']"))
            )
            
            for element in size_elements:
                size_text = element.text.strip()
                if size_text in product.sizes:
                    try:
                        # Check if size is not marked as unavailable
                        is_available = not ("OUT OF STOCK" in element.text.upper() or 
                                         "SOLD OUT" in element.text.upper() or
                                         element.get_attribute("disabled"))
                        if is_available:
                            available_sizes.append(size_text)
                    except Exception as e:
                        logger.error(f"Error checking size {size_text}: {str(e)}")
            
            if available_sizes:
                screenshot_path = self.take_screenshot(product)
                
        except TimeoutException:
            logger.error(f"Timeout while checking product: {product.url}")
        except Exception as e:
            logger.error(f"Error checking product {product.url}: {str(e)}")
            
        product.last_check = datetime.now()
        return available_sizes, screenshot_path
        
    async def send_notification(self, product: Product, available_sizes: List[str], screenshot_path: Optional[str]):
        """Send notification about available sizes via Discord."""
        try:
            channel = self.get_channel(product.channel_id)
            if not channel:
                logger.error(f"Could not find channel {product.channel_id}")
                return
                
            embed = discord.Embed(
                title="🛍 Stock Alert!",
                description=f"{product.name} is available in sizes: {', '.join(available_sizes)}",
                color=0x2ecc71
            )
            
            if product.price:
                embed.add_field(name="Price", value=product.price)
            
            if product.last_check:
                embed.add_field(name="Last Checked", value=product.last_check.strftime("%Y-%m-%d %H:%M:%S"))
                
            embed.add_field(name="Product Link", value=product.url)
            
            # Send screenshot if available
            if screenshot_path and os.path.exists(screenshot_path):
                file = discord.File(screenshot_path)
                await channel.send(embed=embed, file=file)
                # Clean up screenshot
                os.remove(screenshot_path)
            else:
                await channel.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error sending Discord notification: {str(e)}")
            
    async def monitor_stock(self):
        """Main monitoring loop."""
        try:
            self._init_driver()
            
            while self.products:  # Run while there are products to monitor
                for product in list(self.products.values()):
                    available_sizes, screenshot_path = self.check_stock(product)
                    
                    if available_sizes:
                        logger.info(f"Found stock for {product.name or 'Product'}: {available_sizes}")
                        await self.send_notification(product, available_sizes, screenshot_path)
                    
                    # Random delay between checks
                    await asyncio.sleep(random.uniform(300, 600))  # 5-10 minutes
                    
        except Exception as e:
            logger.error(f"Error in monitor_stock: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
                
    async def close(self):
        """Clean up resources when bot is shutting down."""
        if self.driver:
            self.driver.quit()
        await super().close()
        
if __name__ == "__main__":
    bot = MonitorBot()
    bot.run("YOUR_DISCORD_BOT_TOKEN")