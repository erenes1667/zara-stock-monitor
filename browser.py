from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
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
            
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
    async def get_product_info(self, store: str, url: str) -> dict:
        """Get product information from the URL."""
        try:
            if not self.driver:
                self.setup_driver()
            
            # Wait and navigate
            time.sleep(random.uniform(1, 2))
            self.driver.get(url)
            time.sleep(random.uniform(2, 3))
            
            # Get product name
            wait = WebDriverWait(self.driver, 10)
            product_name = None
            
            try:
                name_elem = wait.until(EC.presence_of_element_located((
                    By.XPATH, '//h1[@data-qa-qualifier="product-detail-info-name"]'
                )))
                product_name = name_elem.text.strip()
            except:
                logger.error("Could not find product name")
                return None
            
            # Get price (if available)
            price = None
            try:
                price_elem = self.driver.find_element(By.XPATH, '//span[@data-qa-qualifier="price"]')
                price = price_elem.text.strip()
            except:
                pass
                
            return {
                'name': product_name,
                'price': price,
                'url': url
            }
            
        except Exception as e:
            logger.error(f"Error getting product info: {str(e)}")
            return None
            
    async def check_stock(self, product):
        """Check if product is in stock in specified sizes."""
        try:
            if not self.driver:
                self.setup_driver()
                
            # Wait and navigate
            time.sleep(random.uniform(1, 2))
            self.driver.get(product.url)
            time.sleep(random.uniform(2, 3))
            
            # Wait for add to cart button and click it
            wait = WebDriverWait(self.driver, 10)
            add_to_cart = wait.until(EC.presence_of_element_located((
                By.XPATH, '//button[@data-qa-action="add-to-cart"]'
            )))
            add_to_cart.click()
            
            # Get available sizes
            available_sizes = []
            size_elements = self.driver.find_elements(By.XPATH, '//button[@data-qa-action="size-in-stock"]')
            
            for element in size_elements:
                size_text = element.text.strip().upper()
                if size_text in [s.upper() for s in product.sizes]:
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