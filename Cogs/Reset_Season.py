import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from logger import AppLogger

logging = AppLogger(__name__).get_logger()

class Reset_Season(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name = "admin-resetseason", description = "Reset All Users seasonal values")
    async def resetseason(self, interaction: discord.Interaction):
        for member in interaction.guild.members:
            if member.bot == False:
                dao = UserDao()
                user = dao.get_user(member.id)
                user.season_exp = 0
                user.season_level = 1
                dao.update_user(user)
                roles = member.roles
                await member.remove_roles(*[role for role in roles if "Milk" in role.name])
                logging.info(f"Removed all Milk roles from {member.name}")
                role = discord.utils.get(member.guild.roles, name="Bacteria")
                await member.add_roles(role)
        await interaction.response.defer()
        await interaction.followup.send(f'You have reset the season', ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Reset_Season(bot))
