import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC 
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from discord_webhook import DiscordWebhook, DiscordEmbed
import json
import time
import random
import asyncio
from dataclasses import dataclass
from typing import List, Optional
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
    
class ZaraStockMonitor:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.driver = None
        self.products = []
        self.screenshot_dir = "screenshots"
        self._init_products()
        self._init_screenshot_dir()
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file."""
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def _init_products(self):
        """Initialize product list from config."""
        for product in self.config['products']:
            self.products.append(Product(
                url=product['url'],
                sizes=product['sizes'],
                name=product.get('name'),
                price=product.get('price')
            ))
            
    def _init_screenshot_dir(self):
        """Create screenshots directory if it doesn't exist."""
        if not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)
    
    def _init_driver(self):
        """Initialize Chrome driver with optimal settings."""
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # Add random user agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59 Safari/537.36'
        ]
        options.add_argument(f'user-agent={random.choice(user_agents)}')
        
        self.driver = uc.Chrome(options=options)
        self.driver.implicitly_wait(10)
        
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
            time.sleep(random.uniform(2, 4))  # Random delay to avoid detection
            
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
    
    async def send_discord_notification(self, product: Product, available_sizes: List[str], screenshot_path: Optional[str]):
        """Send notification about available sizes via Discord."""
        try:
            webhook = DiscordWebhook(url=self.config['discord_webhook_url'])
            
            product_name = product.name or "Product"
            embed = DiscordEmbed(
                title="🛍 Stock Alert!",
                description=f"{product_name} is available in sizes: {', '.join(available_sizes)}",
                color=0x2ecc71  # Green color
            )
            
            # Add price if available
            if product.price:
                embed.add_field(name="Price", value=product.price)
                
            # Add last check time
            if product.last_check:
                embed.add_field(name="Last Checked", value=product.last_check.strftime("%Y-%m-%d %H:%M:%S"))
                
            # Add product link
            embed.add_field(name="Product Link", value=product.url)
            
            # Add screenshot if available
            if screenshot_path:
                with open(screenshot_path, "rb") as f:
                    webhook.add_file(file=f.read(), filename=os.path.basename(screenshot_path))
            
            webhook.add_embed(embed)
            webhook.execute()
                
        except Exception as e:
            logger.error(f"Error sending Discord notification: {str(e)}")
    
    async def monitor_stock(self):
        """Main monitoring loop."""
        try:
            self._init_driver()
            
            while True:
                for product in self.products:
                    available_sizes, screenshot_path = self.check_stock(product)
                    
                    if available_sizes:
                        logger.info(f"Found stock for {product.name or 'Product'}: {available_sizes}")
                        await self.send_discord_notification(product, available_sizes, screenshot_path)
                    
                    # Random delay between checks
                    delay = random.uniform(
                        self.config['check_interval_min'],
                        self.config['check_interval_max']
                    )
                    await asyncio.sleep(delay)
                    
                    # Clean up old screenshots
                    if screenshot_path and os.path.exists(screenshot_path):
                        os.remove(screenshot_path)
                    
        except Exception as e:
            logger.error(f"Error in monitor_stock: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
                
    def start(self):
        """Start the stock monitoring."""
        asyncio.run(self.monitor_stock())
        
if __name__ == "__main__":
    config_path = "config.json"
    monitor = ZaraStockMonitor(config_path)
    monitor.start()