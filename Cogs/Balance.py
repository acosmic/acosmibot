from email import message
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
    async def balance(self, interaction: discord.Interaction, user: discord.User = None):
        dao = UserDao()

        if user is None:
            bot_user = dao.get_user(interaction.user.id)
            message_text = f"## Your balance: {bot_user.currency:,.0f} Credits. <:PepeRich:1200265584877772840> {interaction.user.mention}" 
        else:
            bot_user = dao.get_user(user.id)
            message_text = f"## {user.name}'s balance: {bot_user.currency:,.0f} Credits. <:PepeRich:1200265584877772840> {interaction.user.mention}" 
        
            
        await interaction.response.send_message(message_text)
        logger.info(f"{interaction.user.name} used /balance command")

async def setup(bot: commands.Bot):
    await bot.add_cog(Balance(bot))
