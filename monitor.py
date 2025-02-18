import discord
from discord.ext import commands
import asyncio
import logging
import random
import time
import os
from datetime import datetime
from models import Product
from settings import CHECK_INTERVALS

logger = logging.getLogger(__name__)

class StockMonitorCog(commands.Cog):
    def __init__(self, bot, browser):
        self.bot = bot
        self.browser = browser
        self.products = {}  # channel_id -> List[Product]
        self.monitoring_task = None
        self.start_monitoring()
        
    def start_monitoring(self):
        """Start the monitoring loop if not already running."""
        if not self.monitoring_task:
            self.monitoring_task = asyncio.create_task(self.monitor_stock())
            logger.info("Started stock monitoring task")
            
    async def add_product(self, ctx, store: str, url: str, *sizes):
        """Add a product to monitor."""
        try:
            # Initialize product info
            product_info = await self.browser.get_product_info(store, url)
            if not product_info:
                await ctx.send("Error: Could not fetch product information. Please check the URL.")
                return
                
            product = Product(
                store=store,
                url=url,
                name=product_info.get('name', 'Unknown Product'),
                price=product_info.get('price'),
                sizes=list(sizes),
                last_check=datetime.now()
            )
            
            # Add to products dict
            channel_id = ctx.channel.id
            if channel_id not in self.products:
                self.products[channel_id] = []
            self.products[channel_id].append(product)
            
            # Send confirmation
            embed = discord.Embed(
                title="✅ Product Added",
                description=f"Now monitoring {product.name}",
                color=0x2ecc71
            )
            embed.add_field(name="Sizes", value=", ".join(sizes))
            embed.add_field(name="Store", value=store.capitalize())
            if product.price:
                embed.add_field(name="Price", value=product.price)
                
            await ctx.send(embed=embed)
            
            # Start monitoring if not already running
            self.start_monitoring()
            
        except Exception as e:
            logger.error(f"Error adding product: {str(e)}")
            await ctx.send(f"Error adding product: {str(e)}")
            
    async def list_products(self, ctx):
        """List all monitored products in the channel."""
        channel_id = ctx.channel.id
        products = self.products.get(channel_id, [])
        
        if not products:
            await ctx.send("No products being monitored in this channel.")
            return
            
        embed = discord.Embed(
            title="📋 Monitored Products",
            color=0x3498db
        )
        
        for i, product in enumerate(products, 1):
            value = f"Sizes: {', '.join(product.sizes)}\n"
            if product.price:
                value += f"Price: {product.price}\n"
            if product.last_check:
                value += f"Last checked: {product.last_check.strftime('%Y-%m-%d %H:%M:%S')}"
                
            embed.add_field(
                name=f"{i}. {product.name}",
                value=value,
                inline=False
            )
            
        await ctx.send(embed=embed)
        
    async def remove_product(self, ctx, index: int = None):
        """Remove a product from monitoring."""
        channel_id = ctx.channel.id
        products = self.products.get(channel_id, [])
        
        if not products:
            await ctx.send("No products being monitored in this channel.")
            return
            
        if index is None:
            await ctx.send("Please specify the product number to remove (use !list to see numbers)")
            return
            
        try:
            index = int(index)
            if index < 1 or index > len(products):
                await ctx.send(f"Invalid product number. Please use a number between 1 and {len(products)}")
                return
                
            removed_product = products.pop(index - 1)
            
            if not products:
                del self.products[channel_id]
                
            embed = discord.Embed(
                title="❌ Product Removed",
                description=f"Stopped monitoring {removed_product.name}",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            
        except ValueError:
            await ctx.send("Please provide a valid number")
        except Exception as e:
            logger.error(f"Error removing product: {str(e)}")
            await ctx.send(f"Error removing product: {str(e)}")
        
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
                        try:
                            available_sizes, screenshot_path = await self.browser.check_stock(product)
                            product.last_check = datetime.now()
                            
                            if available_sizes:
                                embed = discord.Embed(
                                    title="🛍 Stock Alert!",
                                    description=f"{product.name} is available in sizes: {', '.join(available_sizes)}",
                                    color=0x2ecc71
                                )
                                
                                if product.price:
                                    embed.add_field(name="Price", value=product.price)
                                    
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
                                    except Exception as e:
                                        logger.error(f"Error removing screenshot: {str(e)}")
                                else:
                                    await channel.send(embed=embed)
                                    
                        except Exception as e:
                            logger.error(f"Error checking product {product.name}: {str(e)}")
                            continue
                            
                        # Random delay between product checks
                        await asyncio.sleep(random.uniform(2, 5))
                        
                # Random delay between full cycles
                delay = random.uniform(CHECK_INTERVALS['min'], CHECK_INTERVALS['max'])
                await asyncio.sleep(delay)
                
        except Exception as e:
            logger.error(f"Error in monitor_stock: {str(e)}")
        finally:
            self.monitoring_task = None
            
    def cog_unload(self):
        """Clean up resources when cog is unloaded."""
        if self.monitoring_task:
            self.monitoring_task.cancel()
        self.browser.close()