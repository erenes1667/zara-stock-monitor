import discord
from discord.ext import commands
import asyncio
import logging
import random
import time
from settings import CHECK_INTERVALS

logger = logging.getLogger(__name__)

class StockMonitorCog(commands.Cog):
    def __init__(self, bot, browser):
        self.bot = bot
        self.browser = browser
        self.products = {}  # channel_id -> List[Product]
        self.monitoring_task = None
        
    async def monitor_stock(self):
        """Main monitoring loop."""
        try:
            while any(self.products.values()):  # While there are products to monitor
                for channel_id, products in self.products.items():
                    channel = self.bot.get_channel(channel_id)
                    if not channel:
                        logger.error(f"Could not find channel {channel_id}")
                        continue
                        
                    for product in products:
                        available_sizes, screenshot_path = self.browser.check_stock(product)
                        
                        if available_sizes:
                            try:
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
                                
                                # Send message with screenshot if available
                                if screenshot_path:
                                    file = discord.File(screenshot_path)
                                    await channel.send(embed=embed, file=file)
                                    # Clean up screenshot
                                    try:
                                        if os.path.exists(screenshot_path):
                                            os.remove(screenshot_path)
                                    except:
                                        pass
                                else:
                                    await channel.send(embed=embed)
                                    
                            except Exception as e:
                                logger.error(f"Error sending notification: {str(e)}")
                        
                        # Random delay between product checks
                        await asyncio.sleep(random.uniform(2, 5))
                        
                # Random delay between full cycles
                delay = random.uniform(CHECK_INTERVALS['min'], CHECK_INTERVALS['max'])
                await asyncio.sleep(delay)
                
        except Exception as e:
            logger.error(f"Error in monitor_stock: {str(e)}")
        finally:
            self.browser.close()
            
    def cog_unload(self):
        """Clean up resources when cog is unloaded."""
        if self.monitoring_task:
            self.monitoring_task.cancel()
        self.browser.close()