import discord
from discord.ext import commands
from discord import app_commands
from Dao.GuildDao import GuildDao
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class CheckBank(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="checkbank", description="Check the amount of Credits in this server's bank!")
    async def checkbank(self, interaction: discord.Interaction):
        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        dao = GuildDao()
        currency = dao.get_vault_currency(interaction.guild.id)
        formatted_currency = "{:,.0f}".format(currency)

        await interaction.response.send_message(
            f"There is currently {formatted_currency} Credits in {interaction.guild.name}'s Bank! 🏦")
        logger.info(f"{interaction.user.name} used /checkvault command in {interaction.guild.name}")


async def setup(bot: commands.Bot):
    await bot.add_cog(CheckBank(bot))