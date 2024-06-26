import discord
from discord.ext import commands
from discord import app_commands
from Dao.VaultDao import VaultDao
from logger import AppLogger

logger = AppLogger(__name__).get_logger()

class CheckVault(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name = "checkvault", description = "Check the amount of Credits in the vault!") 
    async def checkvault(self, interaction: discord.Interaction):
        
        dao = VaultDao()
        currency = dao.get_currency()
        formatted_currency = "{:,.0f}".format(currency)

        await interaction.response.send_message("There is currently " + str(formatted_currency) + " Credits in the vault! 🏦")
        logger.info(f"{interaction.user.name} used /checkvault command")

async def setup(bot: commands.Bot):
    await bot.add_cog(CheckVault(bot))