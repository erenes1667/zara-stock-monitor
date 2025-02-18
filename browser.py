from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os
import logging
import time
import random
from datetime import datetime

logger = logging.getLogger(__name__)

class BrowserHandler:
    def __init__(self):
        self.driver = None
        self.setup_driver()
        
    def setup_driver(self):
        """Initialize Chrome WebDriver with appropriate options."""
        if self.driver:
            return
            
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Run in headless mode
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(options=options)
        
    async def get_product_info(self, store: str, url: str) -> dict:
        """Get product information from the URL."""
        try:
            self.setup_driver()
            self.driver.get(url)
            
            # Wait for product title to be visible
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.product-detail-info__header-name"))
            )
            
            # Get product name
            name = self.driver.find_element(By.CSS_SELECTOR, "h1.product-detail-info__header-name").text.strip()
            
            # Get price (if available)
            try:
                price = self.driver.find_element(By.CSS_SELECTOR, "span.money-amount__main").text.strip()
            except NoSuchElementException:
                price = None
                
            return {
                'name': name,
                'price': price,
                'url': url
            }
            
        except Exception as e:
            logger.error(f"Error getting product info: {str(e)}")
            return None
            
    async def check_stock(self, product):
        """Check if product is in stock in specified sizes."""
        try:
            self.setup_driver()
            self.driver.get(product.url)
            
            # Wait for size selector to be visible
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".product-detail-size-selector__size-list"))
            )
            
            # Get all size elements
            size_elements = self.driver.find_elements(By.CSS_SELECTOR, ".product-detail-size-selector__size-list button")
            
            available_sizes = []
            for element in size_elements:
                size_text = element.text.strip().upper()
                if size_text in [s.upper() for s in product.sizes]:
                    # Check if size is available (not disabled/sold out)
                    if not element.get_attribute("disabled"):
                        available_sizes.append(size_text)
            
            # Take screenshot if any monitored size is available
            screenshot_path = None
            if available_sizes:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"screenshots/stock_{timestamp}.png"
                os.makedirs("screenshots", exist_ok=True)
                self.driver.save_screenshot(screenshot_path)
                
            return available_sizes, screenshot_path
            
        except Exception as e:
            logger.error(f"Error checking stock: {str(e)}")
            return [], None
            
    def close(self):
        """Close the browser."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None