import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from logger import AppLogger

logging = AppLogger(__name__).get_logger()

# Rename role level 1 to Globehead
ROLE_GLOBEHEAD = "Globehead"  # Previously "Microbe"

# List of leveling roles
LEVELING_ROLES = ["Fish", "Monkey", "Human", "Unicorn"]  # Previously defined roles

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

                # Remove leveling roles only
                roles_to_remove = [role for role in member.roles if role.name in LEVELING_ROLES]
                await member.remove_roles(*roles_to_remove)
                logging.info(f"Removed leveling roles from {member.name}")

                # Add the Globehead role
                role = discord.utils.get(member.guild.roles, name=ROLE_GLOBEHEAD)
                if role not in member.roles:
                    await member.add_roles(role)
                    logging.info(f"Added Globehead role to {member.name}")

                # Set nickname to discord username
                await member.edit(nick=member.name)

        await interaction.response.defer()
        await interaction.followup.send(f'You have reset the season', ephemeral=True)


    @app_commands.command(name = "admin-resetnicknames", description = "Reset all nicknames to account names")
    async def resetnicknames(self, interaction: discord.Interaction):
        for member in interaction.guild.members:
            if not member.bot:
                # Set nickname to account name (username)
                await member.edit(nick=member.name)
                logging.info(f"Reset nickname for {member.name}")

        await interaction.response.defer()
        await interaction.followup.send('All nicknames have been reset to account names', ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Reset_Season(bot))