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
        
        # Initialize browser
        self.browser = BrowserHandler()
        
        # Add commands
        self.add_command(commands.Command(self.add_product, name='monitor'))
        self.add_command(commands.Command(self.list_products, name='list'))
        self.add_command(commands.Command(self.remove_product, name='remove'))
        self.add_command(commands.Command(self.help_command, name='help'))
        
    async def setup_hook(self):
        # Add stock monitoring cog
        await self.add_cog(StockMonitorCog(self, self.browser))
        
    async def on_ready(self):
        logger.info(f'Bot is ready! Logged in as {self.user.name}')
        
    async def add_product(self, ctx, store: str = None, url: str = None, *sizes):
        """Add a product to monitor. Example: !monitor zara https://www.zara.com/... S M L"""
        cog = self.get_cog('StockMonitorCog')
        await cog.add_product(ctx, store, url, *sizes)
        
    async def list_products(self, ctx):
        """List all monitored products in this channel."""
        cog = self.get_cog('StockMonitorCog')
        await cog.list_products(ctx)
        
    async def remove_product(self, ctx, index: int = None):
        """Remove a product from monitoring. Use !list to see indices."""
        cog = self.get_cog('StockMonitorCog')
        await cog.remove_product(ctx, index)
        
    async def help_command(self, ctx):
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
            "!help": "Show this help message"
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
        
    async def close(self):
        """Clean up resources when bot shuts down."""
        self.browser.close()
        await super().close()
        
def run_bot(token: str):
    """Run the bot with the given token."""
    bot = StockBot()
    bot.run(token)