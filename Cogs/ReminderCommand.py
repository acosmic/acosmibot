import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta, timezone
from Dao.ReminderDao import ReminderDao
from Entities.Reminder import Reminder
from logger import AppLogger
import re

logger = AppLogger(__name__).get_logger()


class ReminderCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.reminder_dao = ReminderDao()

    @app_commands.command(name="remind", description="Set a reminder for yourself")
    @app_commands.describe(
        time="Time until reminder (e.g., 5m, 2h, 1d, 30s)",
        message="What to remind you about"
    )
    async def remind(self, interaction: discord.Interaction, time: str, message: str):
        """
        Set a reminder for yourself.
        Supports: seconds (s), minutes (m/min), hours (h/hr), days (d)
        Examples: 5m, 2h30m, 1d, 45s
        """

        # Parse the time string
        try:
            remind_at = self.parse_time(time)
        except ValueError as e:
            await interaction.response.send_message(
                f"❌ Invalid time format: {str(e)}\n"
                f"Examples: `5m`, `2h`, `1d`, `30s`, `2h30m`",
                ephemeral=True
            )
            logger.info(f"{interaction.user.name} used /remind with invalid time: {time}")
            return

        # Check if time is too far in the future (max 30 days)
        if remind_at > datetime.now(timezone.utc) + timedelta(days=1825):
            await interaction.response.send_message(
                "❌ Reminders can only be set up to 5 years in the future.",
                ephemeral=True
            )
            return

        # Check if time is in the past
        if remind_at <= datetime.now(timezone.utc):
            await interaction.response.send_message(
                "❌ You can't set a reminder in the past!",
                ephemeral=True
            )
            return

        # Truncate message if too long
        if len(message) > 1000:
            message = message[:997] + "..."

        # Create message URL
        message_url = f"https://discord.com/channels/{interaction.guild_id}/{interaction.channel_id}"

        remind_at = remind_at.replace(microsecond=0)

        # Create reminder object
        reminder = Reminder(
            user_id=interaction.user.id,
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            message=message,
            remind_at=remind_at,
            message_url=message_url
        )

        # Save to database
        success = self.reminder_dao.add_reminder(reminder)

        if success:
            # Calculate time difference for display
            time_diff = remind_at - datetime.now(timezone.utc)
            time_str = self.format_timedelta(time_diff)

            embed = discord.Embed(
                title="⏰ Reminder Set!",
                description=f"I'll remind you in **{time_str}**",
                color=interaction.user.color,
            )
            embed.add_field(name="Reminder", value=message, inline=False)
            embed.add_field(name="When", value=f"<t:{int(remind_at.timestamp())}:F>", inline=False)
            embed.set_footer(text="You'll receive a DM when it's time!")

            await interaction.response.send_message(embed=embed)
            logger.info(f"{interaction.user.name} set a reminder for {remind_at}")
        else:
            await interaction.response.send_message(
                "❌ Failed to set reminder. Please try again.",
                ephemeral=True
            )
            logger.error(f"Failed to save reminder for {interaction.user.name}")

    @app_commands.command(name="reminders", description="View your active reminders")
    async def reminders(self, interaction: discord.Interaction):
        """View all your active reminders in this server"""

        reminders = self.reminder_dao.get_user_reminders(
            interaction.user.id,
            interaction.guild_id,
            include_completed=False
        )

        if not reminders:
            await interaction.response.send_message(
                "You don't have any active reminders in this server.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"⏰ Your Reminders ({len(reminders)})",
            color=discord.Color.blue()
        )

        for i, reminder in enumerate(reminders, 1):
            time_str = f"<t:{int(reminder.remind_at.timestamp())}:R>"
            value = f"**Message:** {reminder.message[:100]}{'...' if len(reminder.message) > 100 else ''}\n"
            value += f"**When:** {time_str}\n"
            value += f"**ID:** `{reminder.id}`"

            embed.add_field(
                name=f"{i}. Reminder",
                value=value,
                inline=False
            )

        embed.set_footer(text="Use /cancelreminder <id> to cancel a reminder")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"{interaction.user.name} viewed their reminders")

    @app_commands.command(name="cancelreminder", description="Cancel a reminder")
    @app_commands.describe(reminder_id="The ID of the reminder to cancel")
    async def cancel_reminder(self, interaction: discord.Interaction, reminder_id: int):
        """Cancel a specific reminder by ID"""

        success = self.reminder_dao.delete_reminder(reminder_id, interaction.user.id)

        if success:
            await interaction.response.send_message(
                f"✅ Reminder #{reminder_id} has been cancelled.",
                ephemeral=True
            )
            logger.info(f"{interaction.user.name} cancelled reminder #{reminder_id}")
        else:
            await interaction.response.send_message(
                f"❌ Could not find reminder #{reminder_id} or you don't have permission to cancel it.",
                ephemeral=True
            )

    def parse_time(self, time_str: str) -> datetime:
        """
        Parse a time string like '5m', '2h', '1d', '1y', '2h30m' into a datetime.

        Args:
            time_str: Time string to parse

        Returns:
            datetime: When the reminder should trigger

        Raises:
            ValueError: If the time string is invalid
        """
        time_str = time_str.lower().strip()

        # Pattern to match time components - ADDED YEAR SUPPORT
        pattern = r'(\d+)\s*(s|sec|second|seconds|m|min|minute|minutes|h|hr|hour|hours|d|day|days|w|week|weeks|y|yr|year|years)'
        matches = re.findall(pattern, time_str)

        if not matches:
            raise ValueError("No valid time found. Use format like: 5m, 2h, 1d, 1w, 1y")

        total_seconds = 0

        for amount, unit in matches:
            amount = int(amount)

            # Convert to seconds
            if unit in ['s', 'sec', 'second', 'seconds']:
                total_seconds += amount
            elif unit in ['m', 'min', 'minute', 'minutes']:
                total_seconds += amount * 60
            elif unit in ['h', 'hr', 'hour', 'hours']:
                total_seconds += amount * 3600
            elif unit in ['d', 'day', 'days']:
                total_seconds += amount * 86400
            elif unit in ['w', 'week', 'weeks']:
                total_seconds += amount * 604800  # 7 days
            elif unit in ['y', 'yr', 'year', 'years']:
                total_seconds += amount * 31536000  # 365 days

        if total_seconds <= 0:
            raise ValueError("Time must be greater than 0")

        return datetime.now(timezone.utc) + timedelta(seconds=total_seconds)

    def format_timedelta(self, td: timedelta) -> str:
        """
        Format a timedelta into a human-readable string.

        Args:
            td: Timedelta to format

        Returns:
            str: Formatted string like "2 hours, 30 minutes"
        """
        total_seconds = int(td.total_seconds())

        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0 and not parts:  # Only show seconds if nothing else
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

        return ", ".join(parts) if parts else "0 seconds"


async def setup(bot: commands.Bot):
    await bot.add_cog(ReminderCommand(bot))