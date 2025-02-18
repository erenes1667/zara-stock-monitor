import discord
from discord.ext import commands
import logging
from models import Product
from browser import BrowserHandler
from monitor import StockMonitorCog
from settings import STORES

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class StockBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        
        # Remove default help command to use our custom one
        self.remove_command('help')
        
        # Initialize browser
        self.browser = BrowserHandler()
        
    async def setup_hook(self):
        # Add stock monitoring cog
        await self.add_cog(StockMonitorCog(self, self.browser))
        
    async def on_ready(self):
        logger.info(f'Bot is ready! Logged in as {self.user.name}')
        
    async def close(self):
        """Clean up resources when bot shuts down."""
        self.browser.close()
        await super().close()

class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='monitor')
    async def add_product(self, ctx, store: str = None, url: str = None, *sizes):
        """Add a product to monitor. Example: !monitor zara https://www.zara.com/... S M L"""
        if not store:
            stores_list = '\n'.join([f"• {name}" for code, name in STORES.items()])
            await ctx.send(f"Please specify a store. Available stores:\n{stores_list}\n\nExample: !monitor zara https://zara.com/... S M L")
            return
            
        store = store.lower()
        if store not in STORES:
            await ctx.send(f"Invalid store. Available stores: {', '.join(STORES.values())}")
            return
            
        if not url:
            await ctx.send("Please provide the product URL.")
            return
            
        if not sizes:
            await ctx.send("Please specify at least one size to monitor.")
            return
            
        monitor_cog = self.bot.get_cog('StockMonitorCog')
        if monitor_cog:
            await monitor_cog.add_product(ctx, store, url, *sizes)
        else:
            await ctx.send("Error: Monitor system not initialized!")
    
    @commands.command(name='list')
    async def list_products(self, ctx):
        """List all monitored products in this channel."""
        monitor_cog = self.bot.get_cog('StockMonitorCog')
        if monitor_cog:
            await monitor_cog.list_products(ctx)
        else:
            await ctx.send("Error: Monitor system not initialized!")
    
    @commands.command(name='remove')
    async def remove_product(self, ctx, index: int = None):
        """Remove a product from monitoring. Use !list to see indices."""
        monitor_cog = self.bot.get_cog('StockMonitorCog')
        if monitor_cog:
            await monitor_cog.remove_product(ctx, index)
        else:
            await ctx.send("Error: Monitor system not initialized!")
    
    @commands.command(name='info')
    async def info_command(self, ctx):
        """Show help information."""
        help_embed = discord.Embed(
            title="🛍️ Stock Monitor - Commands",
            color=0x2ecc71,
            description="Monitor products for stock availability"
        )
        
        commands = {
            "!monitor <store> <url> <sizes...>": "Start monitoring a product\nExample: !monitor zara https://zara.com/... S M L",
            "!list": "Show all monitored products",
            "!remove [number]": "Stop monitoring a product (use !list to see numbers)",
            "!info": "Show this help message"
        }
        
        for cmd, desc in commands.items():
            help_embed.add_field(name=cmd, value=desc, inline=False)
            
        stores_list = '\n'.join([f"• {name}" for code, name in STORES.items()])
        help_embed.add_field(
            name="Available Stores",
            value=stores_list,
            inline=False
        )
            
        await ctx.send(embed=help_embed)
        
def run_bot(token: str):
    """Run the bot with the given token."""
    bot = StockBot()
    
    @bot.event
    async def setup_hook():
        await bot.add_cog(Commands(bot))
        await bot.add_cog(StockMonitorCog(bot, bot.browser))
    
    bot.run(token)