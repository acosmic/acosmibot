import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from logger import AppLogger

logger = AppLogger(__name__).get_logger()

class Balance(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    @app_commands.command(name="balance", description="Check your Credit balance.")
    async def balance(self, interaction: discord.Interaction):
        
        dao = UserDao()
        user = dao.get_user(interaction.user.id)
        await interaction.response.send_message(f"## Your balance: {user.currency:,.0f} Credits. <:PepeRich:1200265584877772840> {interaction.user.mention}")
        logger.info(f"{interaction.user.name} used /balance command")

async def setup(bot: commands.Bot):
    await bot.add_cog(Balance(bot))
