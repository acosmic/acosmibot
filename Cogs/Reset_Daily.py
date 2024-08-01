import discord
from discord.ext import commands
from discord import app_commands

from Dao.UserDao import UserDao
from logger import AppLogger

logging = AppLogger(__name__).get_logger()

class Reset_Daily(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name = "admin-resetdaily", description = "Set RPS match inprogress to False") 
    async def resetrps(self, interaction: discord.Interaction):
        
        role = discord.utils.get(interaction.guild.roles, name="Acosmic")
        userDao = UserDao()
        if role in interaction.user.roles:
            try:
                
                userDao.reset_daily()
                await interaction.response.send_message(f'Daily has been reset for all members.', ephemeral=True)
            except Exception as e:
                logging.info(f'/admin-resetdaily command - {e}.')
        else:
            await interaction.response.send_message(f'You can not use this command', ephemeral=True)
                



async def setup(bot: commands.Bot):
    await bot.add_cog(Reset_Daily(bot))