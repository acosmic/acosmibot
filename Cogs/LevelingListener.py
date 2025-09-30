from Leveling import LevelingSystem
from discord.ext import commands
from logger import AppLogger
import discord


logger = AppLogger(__name__).get_logger()

class LevelingListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.leveling_system = LevelingSystem(bot)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages to award experience"""
        await self.leveling_system.process_message_exp(message)

async def setup(bot):
    await bot.add_cog(LevelingListener(bot))