import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
import io
import random
import time
import logging
from datetime import datetime
import os
from settings import USER_AGENTS, SCREENSHOT_DIR
from models import Product

logger = logging.getLogger(__name__)

class BrowserHandler:
    def __init__(self):
        self.driver = None
        self._init_screenshot_dir()
        
    def _init_screenshot_dir(self):
        if not os.path.exists(SCREENSHOT_DIR):
            os.makedirs(SCREENSHOT_DIR)
            
    def _init_driver(self):
        if self.driver is None:
            options = uc.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument(f'user-agent={random.choice(USER_AGENTS)}')
            
            self.driver = uc.Chrome(options=options)
            self.driver.implicitly_wait(10)
            
    def get_product_name(self, store: str) -> str:
        try:
            if store == 'zara':
                elem = self.driver.find_element(By.XPATH, '//h1[@data-qa-qualifier="product-detail-info-name"]')
            elif store == 'bershka':
                elem = self.driver.find_element(By.XPATH, '//h1[contains(@class, "product-detail-info")]')
            elif store == 'pullandbear':
                elem = self.driver.find_element(By.XPATH, '//h1[@id="titleProductCard"]')
            return elem.text.strip()
        except:
            return "Unknown Product"
            
    def check_stock(self, product: Product) -> tuple[list[str], str | None]:
        """Check stock availability for a product."""
        available_sizes = []
        screenshot_path = None
        
        try:
            self._init_driver()
            self.driver.get(product.url)
            time.sleep(random.uniform(2, 4))
            
            if product.store == 'zara':
                available_sizes = self._check_zara(product.sizes)
            elif product.store == 'bershka':
                available_sizes = self._check_bershka(product.sizes)
            elif product.store == 'pullandbear':
                available_sizes = self._check_pullandbear(product.sizes)
            
            if available_sizes:
                screenshot_path = self._take_screenshot(product)
                
        except Exception as e:
            logger.error(f"Error checking {product.url}: {str(e)}")
            
        product.last_check = datetime.now()
        return available_sizes, screenshot_path
        
    def _check_zara(self, sizes: list[str]) -> list[str]:
        available = []
        size_elements = WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-qa-action='size-selector']"))
        )
        
        for element in size_elements:
            size_text = element.text.strip()
            if size_text in sizes:
                try:
                    is_available = not ("OUT OF STOCK" in element.text.upper() or 
                                      "SOLD OUT" in element.text.upper() or
                                      element.get_attribute("disabled"))
                    if is_available:
                        available.append(size_text)
                except Exception as e:
                    logger.error(f"Error checking size {size_text}: {str(e)}")
                    
        return available
        
    def _check_bershka(self, sizes: list[str]) -> list[str]:
        available = []
        size_elements = WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "button[data-qa-anchor='sizeListItem']"))
        )
        
        for element in size_elements:
            try:
                size_text = element.find_element(By.CSS_SELECTOR, "span.text__label").text.strip()
                if size_text in sizes:
                    if not element.get_attribute("class").__contains__("is-disabled"):
                        available.append(size_text)
            except Exception as e:
                logger.error(f"Error checking Bershka size: {str(e)}")
                
        return available
        
    def _check_pullandbear(self, sizes: list[str]) -> list[str]:
        available = []
        size_selector = self.driver.find_element(By.CSS_SELECTOR, "size-selector-with-length")
        shadow_root_1 = self.driver.execute_script("return arguments[0].shadowRoot", size_selector)
        
        size_select = shadow_root_1.find_element(By.CSS_SELECTOR, "size-selector-select")
        shadow_root_2 = self.driver.execute_script("return arguments[0].shadowRoot", size_select)
        
        size_list = shadow_root_2.find_element(By.CSS_SELECTOR, "size-list")
        shadow_root_3 = self.driver.execute_script("return arguments[0].shadowRoot", size_list)
        
        size_elements = shadow_root_3.find_elements(By.CSS_SELECTOR, "button")
        
        for button in size_elements:
            try:
                spans = button.find_elements(By.TAG_NAME, 'span')
                size_text = spans[0].text
                if size_text in sizes:
                    if len(spans) != 2:  # Available if no second span (which would be "OUT OF STOCK")
                        available.append(size_text)
            except Exception as e:
                logger.error(f"Error checking P&B size: {str(e)}")
                
        return available
        
    def _take_screenshot(self, product: Product) -> str | None:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{SCREENSHOT_DIR}/{product.name or 'product'}_{timestamp}.png"
            
            try:
                if product.store == 'zara':
                    element = self.driver.find_element(By.CSS_SELECTOR, "[data-qa-action='size-selector']")
                elif product.store == 'bershka':
                    element = self.driver.find_element(By.CSS_SELECTOR, "div.sizes-selector")
                elif product.store == 'pullandbear':
                    element = self.driver.find_element(By.CSS_SELECTOR, "size-selector-with-length")
                screenshot = element.screenshot_as_png
            except:
                screenshot = self.driver.get_screenshot_as_png()
                
            image = Image.open(io.BytesIO(screenshot))
            image.save(filename, optimize=True, quality=85)
            
            return filename
        except Exception as e:
            logger.error(f"Error taking screenshot: {str(e)}")
            return None
            
    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None