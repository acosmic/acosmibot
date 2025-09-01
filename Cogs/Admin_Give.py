import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from Dao.GuildUserDao import GuildUserDao
from Leveling import Leveling
import typing

from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class Admin_Give(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="admin-give", description="Give Credits or EXP to your target user.")
    @discord.app_commands.default_permissions(manage_guild=True)
    async def admin_give(self, interaction: discord.Interaction, target: discord.Member,
                         stat: typing.Literal['Currency', 'EXP'], amount: int):

        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        # Check for admin permissions (more flexible than hardcoded role)
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only administrators can use this command.", ephemeral=True)
            return

        # Validate amount
        if amount <= 0:
            await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
            return

        try:
            user_dao = UserDao()
            guild_user_dao = GuildUserDao()

            if stat == 'Currency':
                # Get or create guild user for currency (currency is guild-specific)
                target_guild_user = guild_user_dao.get_or_create_guild_user_from_discord(target, interaction.guild.id)

                if not target_guild_user:
                    await interaction.response.send_message("Failed to get user data.", ephemeral=True)
                    return

                # Add currency to guild user
                target_guild_user.currency += amount

                # Update database
                guild_user_dao.update_guild_user(target_guild_user)

                await interaction.response.send_message(
                    f'### {interaction.user.name} has given {target.mention} {amount:,.0f} credits! 🎰'
                )
                logger.info(f'{interaction.user.name} gave {target.name} {amount} credits in {interaction.guild.name}')

            elif stat == 'EXP':
                # Get or create both guild and global users for EXP
                target_guild_user = guild_user_dao.get_or_create_guild_user_from_discord(target, interaction.guild.id)
                target_global_user = user_dao.get_or_create_user_from_discord(target)

                if not target_guild_user or not target_global_user:
                    await interaction.response.send_message("Failed to get user data.", ephemeral=True)
                    return

                # Add EXP to guild user
                target_guild_user.exp += amount
                target_guild_user.exp_gained += amount

                # Calculate new level
                lvl = Leveling()
                new_level = lvl.calc_level(target_guild_user.exp)
                old_level = target_guild_user.level
                target_guild_user.level = new_level

                # Update guild user in database
                guild_user_dao.update_guild_user(target_guild_user)

                # Update global stats (sum of all guild exp)
                total_guild_exp = guild_user_dao.get_user_total_exp_across_guilds(target.id)
                target_global_user.global_exp = total_guild_exp
                target_global_user.global_level = lvl.calc_level(total_guild_exp)
                user_dao.update_user(target_global_user)

                # Create response message
                level_change_msg = ""
                if new_level > old_level:
                    level_change_msg = f" (Level {old_level} → {new_level}! 🎉)"

                await interaction.response.send_message(
                    f'### {interaction.user.name} has given {target.mention} {amount:,.0f} XP! 📈{level_change_msg}'
                )
                logger.info(f'{interaction.user.name} gave {target.name} {amount} EXP in {interaction.guild.name}')

        except Exception as e:
            logger.error(f'/admin-give command - target = {target.name} - {e}')
            await interaction.response.send_message("An error occurred while processing the command.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin_Give(bot))