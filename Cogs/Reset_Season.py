import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from logger import AppLogger

logging = AppLogger(__name__).get_logger()

# Rename role level 1 to Globehead
NEW_LEVEL_1 = "Santa's Helper"  # Previously "Microbe"

role_level_1 = "Globehead"  
role_level_2 = "Discount Dracula"  
role_level_3 = "Wicked Witch"  
role_level_4 = "Goofy Goblin"  
role_level_5 = "Zombie CEO"
role_level_6 = "Lord of Bad Decisions"  

# List of leveling roles
LEVELING_ROLES = [role_level_2, role_level_3, role_level_4, role_level_5, role_level_6]  # Previously defined roles

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
                role = discord.utils.get(member.guild.roles, name=NEW_LEVEL_1)
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