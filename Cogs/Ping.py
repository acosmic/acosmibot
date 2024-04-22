import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from logger import AppLogger

logging = AppLogger(__name__).get_logger()

class Ping(commands.Cog):
    def __init__(self, bot:commands.Bot):
        super().__init__()
        self.bot = bot
        
    @app_commands.command(name = "ping", description = "Returns the bot's latency.")
    async def ping(self, interaction: discord.Interaction):
        
        await interaction.response.send_message(f"Pong! {round(self.bot.latency * 1000)}ms")
        logging.info(f"{interaction.user.name} used /ping command")

async def setup(bot: commands.Bot):
    await bot.add_cog(Ping(bot))