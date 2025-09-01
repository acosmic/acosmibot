import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from logger import AppLogger

logger = AppLogger(__name__).get_logger()

role_level_1 = "Lil Boo"  
role_level_2 = "Discount Dracula"  
role_level_3 = "Wicked Witch"  
role_level_4 = "Goofy Goblin"  
role_level_5 = "Zombie CEO"
role_level_6 = "Lord of Bad Decisions"

level_roles = [role_level_1, role_level_2, role_level_3, role_level_4, role_level_5, role_level_6]

class Admin_Jail(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
      

    # Command-Based Jailing
    @app_commands.command(name="admin-jail", description="Send a user to jail.")
    @discord.app_commands.default_permissions(manage_guild=True)
    async def jail(self, interaction: discord.Interaction, member: discord.Member):
        # Identify all removable roles that the user has
        # removable_roles = [role for role in member.roles if role.name in level_roles]  # Update with actual role names

        # # Remove all identified roles at once
        # if removable_roles:
        #     await member.remove_roles(*removable_roles)

        # else:
        #     await interaction.response.send_message(f"{member.name} is already in Jail!", ephemeral=True)
        #     return

        # Add the 'Inmate' role
        inmate_role = discord.utils.get(interaction.guild.roles, name="Inmate") 
        if inmate_role in member.roles:
            await interaction.response.send_message(f"{member.name} is already in Jail!", ephemeral=True)
            return
        await member.add_roles(inmate_role)
        await interaction.response.send_message(f"🚨 {member.name} has been sent to Jail! No parole! 🚨", ephemeral=False)
        logger.info(f"{member.name} has been sent to Jail by {interaction.user.name}!")


# Add the Cog to the bot
async def setup(bot: commands.Bot):
    await bot.add_cog(Admin_Jail(bot))