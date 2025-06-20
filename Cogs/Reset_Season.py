import discord
import asyncio
import time
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
import os
from dotenv import load_dotenv
from logger import AppLogger

logging = AppLogger(__name__).get_logger()

# Load environment variables
load_dotenv()

# Get role names from environment variables
role_level_1 = os.getenv('ROLE_LEVEL_1', 'Egg Hunter')  
role_level_2 = os.getenv('ROLE_LEVEL_2', 'Basket Weaver')  
role_level_3 = os.getenv('ROLE_LEVEL_3', 'Chocolate Connoisseur')  
role_level_4 = os.getenv('ROLE_LEVEL_4', 'Bunny Whisperer')  
role_level_5 = os.getenv('ROLE_LEVEL_5', 'Egg Artisan')
role_level_6 = os.getenv('ROLE_LEVEL_6', 'Spring Sorcerer')  
role_level_7 = os.getenv('ROLE_LEVEL_7', 'Easter Legend')

# Old role names to be removed
old_role_names = ["Santa's Helper", "Naughty List", "Nice List", "Grinch Patrol", "Cold Guy"]

# New role names for creation with colors
new_roles_config = [
    {'name': role_level_1, 'color': discord.Color.from_rgb(255, 223, 186)},  # Light peach
    {'name': role_level_2, 'color': discord.Color.from_rgb(204, 255, 204)},  # Light green
    {'name': role_level_3, 'color': discord.Color.from_rgb(160, 82, 45)},    # Brown (chocolate)
    {'name': role_level_4, 'color': discord.Color.from_rgb(255, 255, 204)},  # Light yellow
    {'name': role_level_5, 'color': discord.Color.from_rgb(135, 206, 250)},  # Light blue
    {'name': role_level_6, 'color': discord.Color.from_rgb(221, 160, 221)},  # Plum
    {'name': role_level_7, 'color': discord.Color.from_rgb(255, 215, 0)}     # Gold
]

def chunks(lst, n):
    """Split a list into chunks of size n"""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

class Reset_Season(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="admin-resetseason", description="Reset All Users seasonal values and update to Easter-themed roles")
    async def resetseason(self, interaction: discord.Interaction):
        await interaction.response.defer()
        start_time = time.time()
        
        # Create new roles if they don't exist
        roles_created = 0
        roles_start_time = time.time()
        for i, role_config in enumerate(new_roles_config):
            role_name = role_config['name']
            if not discord.utils.get(interaction.guild.roles, name=role_name):
                # Create role without position parameter
                new_role = await interaction.guild.create_role(
                    name=role_name,
                    color=role_config['color']
                )
                # Set position separately after creation
                try:
                    await new_role.edit(position=len(interaction.guild.roles) - i - 5)
                except Exception as e:
                    logging.warning(f"Could not set position for role {role_name}: {e}")
                
                roles_created += 1
                logging.info(f"Created new role: {role_name}")
        roles_time = time.time() - roles_start_time
        
        # Get all role objects
        roles_to_remove = [role for role in interaction.guild.roles if role.name in old_role_names]
        egg_hunter_role = discord.utils.get(interaction.guild.roles, name=role_level_1)
        
        # Process members' database entries
        db_start_time = time.time()
        dao = UserDao()
        non_bot_members = [member for member in interaction.guild.members if not member.bot]
        for member in non_bot_members:
            user = dao.get_user(member.id)
            if user:
                user.season_exp = 0
                user.season_level = 1
                dao.update_user(user)
        db_time = time.time() - db_start_time
                
        # Process role removals in batches
        role_removal_start_time = time.time()
        members_with_old_roles = {}
        for member in non_bot_members:
            old_roles = [role for role in member.roles if role in roles_to_remove]
            if old_roles:
                members_with_old_roles[member] = old_roles
        
        for batch in chunks(list(members_with_old_roles.items()), 10):  # Process in batches of 10
            tasks = []
            for member, old_roles in batch:
                tasks.append(member.remove_roles(*old_roles))
            if tasks:
                await asyncio.gather(*tasks)
                logging.info(f"Removed old roles from batch of {len(tasks)} members")
        role_removal_time = time.time() - role_removal_start_time
        
        # Process role additions in batches
        role_addition_start_time = time.time()
        members_needing_egg_hunter = [
            member for member in non_bot_members 
            if egg_hunter_role not in member.roles
        ]
        
        for batch in chunks(members_needing_egg_hunter, 10):  # Process in batches of 10
            tasks = [member.add_roles(egg_hunter_role) for member in batch]
            if tasks:
                await asyncio.gather(*tasks)
                logging.info(f"Added {role_level_1} role to batch of {len(tasks)} members")
        role_addition_time = time.time() - role_addition_start_time
        
        # Reset nicknames in batches
        nickname_start_time = time.time()
        for batch in chunks(non_bot_members, 5):  # Smaller batches for nicknames due to higher rate limits
            tasks = []
            for member in batch:
                if member.nick != member.name:
                    tasks.append(member.edit(nick=member.name))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)  # Ignore errors for nickname changes
                logging.info(f"Reset nicknames for batch of {len(tasks)} members")
        nickname_time = time.time() - nickname_start_time
        
        # Delete old roles if not assigned to any members
        role_delete_start_time = time.time()
        roles_deleted = 0
        for old_role in roles_to_remove:
            try:
                if old_role and len(old_role.members) == 0:
                    await old_role.delete()
                    roles_deleted += 1
                    logging.info(f"Deleted old role: {old_role.name}")
            except Exception as e:
                logging.error(f"Could not delete role {old_role.name}: {e}")
        role_delete_time = time.time() - role_delete_start_time
        
        total_time = time.time() - start_time
        
        # Performance metrics message
        performance_msg = (
            f"Season reset completed in {total_time:.2f} seconds!\n\n"
            f"• Created {roles_created} new roles in {roles_time:.2f}s\n"
            f"• Updated {len(non_bot_members)} user database entries in {db_time:.2f}s\n"
            f"• Removed old roles from {len(members_with_old_roles)} members in {role_removal_time:.2f}s\n"
            f"• Added new roles to {len(members_needing_egg_hunter)} members in {role_addition_time:.2f}s\n"
            f"• Reset nicknames in {nickname_time:.2f}s\n"
            f"• Deleted {roles_deleted} old roles in {role_delete_time:.2f}s"
        )
        
        logging.info(performance_msg)
        await interaction.followup.send(performance_msg, ephemeral=True)

    @app_commands.command(name="admin-resetnicknames", description="Reset all nicknames to account names")
    async def resetnicknames(self, interaction: discord.Interaction):
        await interaction.response.defer()
        start_time = time.time()
        
        non_bot_members = [member for member in interaction.guild.members if not member.bot]
        batches_processed = 0
        
        for batch in chunks(non_bot_members, 5):  # Process in batches of 5
            tasks = []
            for member in batch:
                if member.nick != member.name:
                    tasks.append(member.edit(nick=member.name))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)  # Use return_exceptions to continue even if some fail
                batches_processed += 1
        
        total_time = time.time() - start_time
        
        performance_msg = (
            f"Reset all nicknames in {total_time:.2f} seconds!\n"
            f"• Processed {len(non_bot_members)} members in {batches_processed} batches"
        )
        
        logging.info(performance_msg)
        await interaction.followup.send(performance_msg, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Reset_Season(bot))