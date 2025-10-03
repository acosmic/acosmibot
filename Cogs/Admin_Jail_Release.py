import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from logger import AppLogger

logger = AppLogger(__name__).get_logger()

role_level_1 = "Globehead"  
role_level_2 = "Antivaxxer"  
role_level_3 = "Moon Landing Hoax"  
role_level_4 = "Abducted and Probed"  
role_level_5 = "Flat Gang Baby!"
role_level_6 = "Shungite Chewer"  
role_level_7 = "Illuminaughty"
level_roles = [role_level_1, role_level_2, role_level_3, role_level_4, role_level_5, role_level_6, role_level_7]

class Admin_Jail_Release(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
      

    # Command-Based Jailing
    @app_commands.command(name="admin-jail-release", description="Release a user from jail.")
    @discord.app_commands.default_permissions(manage_guild=True)
    async def jail(self, interaction: discord.Interaction, member: discord.Member):
        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return
        # Identify all removable roles that the user has
        # removable_roles = [role for role in member.roles if role.name in level_roles]  # Update with actual role names

        # # Remove all identified roles at once
        # if removable_roles:
        #     await member.remove_roles(*removable_roles)

        # else:
        #     await interaction.response.send_message(f"{member.name} is already in Jail!", ephemeral=True)
        #     return

        # Remove the 'Inmate' role
        inmate_role = discord.utils.get(interaction.guild.roles, name="Inmate") 
        if inmate_role in member.roles:
            await interaction.response.send_message(f"{member.name} has been released from Jail!", ephemeral=False)
            await member.remove_roles(inmate_role)
            logger.info(f"{member.name} has been released from Jail by {interaction.user.name}!")
        else:
            await interaction.response.send_message(f"{member.name} is not in Jail.", ephemeral=True)
        
        


# Add the Cog to the bot
async def setup(bot: commands.Bot):
    await bot.add_cog(Admin_Jail_Release(bot))