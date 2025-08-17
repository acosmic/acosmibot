import discord
from discord.ext import commands
from discord import app_commands
from Dao.LotteryEventDao import LotteryEventDao
from Dao.GuildDao import GuildDao  # Changed from VaultDao to GuildDao
from Entities.LotteryEvent import LotteryEvent
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

from logger import AppLogger

MY_GUILD = discord.Object(id=int(os.getenv('MY_GUILD')))
logger = AppLogger(__name__).get_logger()


class Admin_Start_Lotto(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="admin-start-lotto", description="Start a lottery.")
    async def admin_start_lotto(
            self,
            interaction: discord.Interaction,
            duration: int,
            channel: discord.TextChannel = None  # Optional channel parameter
    ):
        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        # Check for admin permissions (more flexible than hardcoded role)
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only administrators can start lotteries.", ephemeral=True)
            return

        # Use provided channel or current channel as fallback
        target_channel = channel or interaction.channel

        # Validate that the target channel is a text channel
        if not isinstance(target_channel, discord.TextChannel):
            await interaction.response.send_message("Lottery can only be started in text channels.", ephemeral=True)
            return

        try:
            le_dao = LotteryEventDao()
            guild_dao = GuildDao()  # Use GuildDao instead of VaultDao

            # Check if there's already an active lottery in this guild
            current_lottery = le_dao.get_current_event(interaction.guild_id)
            if current_lottery:
                await interaction.response.send_message("There is already an active lottery in this server!", ephemeral=True)
                return

            # Respond to interaction first
            channel_mention = target_channel.mention if target_channel != interaction.channel else "this channel"
            await interaction.response.send_message(
                f'Starting lottery in {channel_mention}! Duration: {duration} hours.',
                ephemeral=True
            )

            # Get guild-specific vault credits
            vault_credits = guild_dao.get_vault_currency(interaction.guild_id)

            # Send lottery announcement to the target channel
            await target_channel.send(
                f'# React with 🎟️ to enter the lottery! '
                f'There is currently {vault_credits:,.0f} Credits in the Vault.\n'
                f'The winner will be announced in {duration} hour(s)! 🎰'
            )

            # You might want to make this image configurable per server or remove it
            # For now, keeping it but you could add it as an optional parameter
            message = await target_channel.send(
                "https://cdn.discordapp.com/attachments/1207159417980588052/1207159812656472104/acosmibot-lottery.png"
            )

            await message.add_reaction('🎟️')
            end_time = datetime.now() + timedelta(hours=duration)

            # Create new lottery event
            new_le = LotteryEvent(
                id=0,
                message_id=message.id,
                start_time=datetime.now(),
                end_time=end_time,
                credits=0,
                winner_id=0,
                guild_id=interaction.guild_id
            )

            await message.pin()
            le_dao.add_new_event(new_le)

            # Send follow-up confirmation
            await interaction.followup.send(
                f'✅ Lottery successfully started! The winner will be announced at {end_time.strftime("%I:%M %p")}.',
                ephemeral=True
            )

        except Exception as e:
            logger.error(f'/admin-start-lotto command error: {e}')
            await interaction.response.send_message(
                "An error occurred while starting the lottery. Please try again.",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin_Start_Lotto(bot))