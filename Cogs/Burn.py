import typing
import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from logger import AppLogger


logger = AppLogger(__name__).get_logger()
class Burn(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name = "admin-burn", description = "set attribute to 0 for target")
    @discord.app_commands.default_permissions(manage_guild=True)
    async def burn(self, interaction: discord.Interaction, target: discord.Member, column: typing.Literal['currency', 'exp', 'daily', 'streak', "level"]):
        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return
        role = discord.utils.get(interaction.guild.roles, name="Acosmic")
        dao = UserDao()
        if role in interaction.user.roles:
            target_user = dao.get_user(target.id)

            if column == "currency":
                target_user.currency = 0

            if column == "exp":
                target_user.exp = 0

            if column == "daily":
                target_user.daily = 0

            if column == "streak":
                target_user.daily = 0

            if column == "level":
                target_user.level = 0            

            try:
                dao.update_user(target_user)
                await interaction.response.send_message(f"{interaction.user.name} has burned {target.mention}'s {column} to 0! <a:pepesith:1165101386921418792>")
            except Exception as e:
                logger.info(f'/give command - target = {target.name} - {e}.')
        else:
            await interaction.response.send_message(f'only {role} can run this command. <:FeelsNaughty:1199732493792858214>', ephemeral=True)
   
                
async def setup(bot: commands.Bot):
    await bot.add_cog(Burn(bot))