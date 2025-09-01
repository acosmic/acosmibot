import discord
from discord.ext import commands
from discord import app_commands
from Dao.GamesDao import GamesDao
from logger import AppLogger

logging = AppLogger(__name__).get_logger()

class Reset_RPS(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name = "admin-resetrps", description = "Set RPS match inprogress to False")
    @discord.app_commands.default_permissions(manage_guild=True)
    async def resetrps(self, interaction: discord.Interaction):
        
        role = discord.utils.get(interaction.guild.roles, name="Acosmic")
        gamesDao = GamesDao()
        if role in interaction.user.roles:
            try:
                gamesDao.set_game_inprogress(game_name="rps", inprogress=0)
                await interaction.response.send_message(f'You have set RPS inprogress to 0', ephemeral=True)
            except Exception as e:
                logging.info(f'/resetrps command - {e}.')
        else:
            await interaction.response.send_message(f'You can not use this command', ephemeral=True)
                



async def setup(bot: commands.Bot):
    await bot.add_cog(Reset_RPS(bot))
        