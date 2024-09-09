import discord
from discord.ext import commands
from discord import app_commands
from Dao.AIDao import AIDao
from logger import AppLogger

logger = AppLogger(__name__).get_logger()

class DeleteAiThread(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="delete-ai-thread", description="Delete a user's thread from database. for testering")
    async def deleteAiThread(self, interaction: discord.Interaction, target: discord.Member):
        aiDao = AIDao()
        aiDao.delete_thread(target.id)
        await interaction.response.send_message(f"{target.name}'s thread has been deleted from database")

async def setup(bot: commands.Bot):
    await bot.add_cog(DeleteAiThread(bot))