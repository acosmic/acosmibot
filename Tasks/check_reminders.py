import asyncio
import discord
from Dao.ReminderDao import ReminderDao
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


async def start_task(bot):
    """Entry point function that the task manager expects."""
    await check_reminders_task(bot)


async def check_reminders_task(bot):
    """Check for due reminders and send DMs every 30 seconds."""
    await bot.wait_until_ready()

    reminder_dao = ReminderDao()
    logger.info("Reminder check task started")

    while not bot.is_closed():
        logger.info('Running check_reminders_task')  # ✅ ADD THIS LINE
        try:
            due_reminders = reminder_dao.get_due_reminders()

            for reminder in due_reminders:
                try:
                    # Get the user
                    user = await bot.fetch_user(reminder.user_id)

                    if not user:
                        logger.warning(f"Could not find user {reminder.user_id} for reminder {reminder.id}")
                        reminder_dao.mark_completed(reminder.id)
                        continue

                    # Create embed for the reminder
                    embed = discord.Embed(
                        title="⏰ Reminder!",
                        description=f"# {reminder.message}",
                        color=discord.Color.blue(),
                        timestamp=reminder.created_at
                    )

                    # Add context about when it was set
                    embed.add_field(
                        name="Set",
                        value=f"<t:{int(reminder.created_at.timestamp())}:R>",
                        inline=True
                    )

                    # Try to get guild and channel names for context
                    try:
                        guild = bot.get_guild(reminder.guild_id)
                        if guild:
                            channel = guild.get_channel(reminder.channel_id)
                            context = f"in #{channel.name}" if channel else f"in {guild.name}"
                            embed.add_field(
                                name="From",
                                value=context,
                                inline=True
                            )

                            # Add jump link if message URL exists
                            if reminder.message_url:
                                embed.add_field(
                                    name="Original Message",
                                    value=f"[Jump to message]({reminder.message_url})",
                                    inline=False
                                )
                    except Exception as e:
                        logger.debug(f"Could not get guild/channel context: {e}")

                    embed.set_footer(text="Reminder System")

                    # Send DM
                    try:
                        await user.send(embed=embed)
                        logger.info(f"Sent reminder {reminder.id} to user {reminder.user_id}")
                    except discord.Forbidden:
                        logger.warning(f"Could not DM user {reminder.user_id} - DMs may be disabled")
                    except Exception as e:
                        logger.error(f"Error sending DM to user {reminder.user_id}: {e}")

                    # Mark as completed
                    reminder_dao.mark_completed(reminder.id)

                except Exception as e:
                    logger.error(f"Error processing reminder {reminder.id}: {e}")
                    # Mark as completed anyway to avoid getting stuck
                    reminder_dao.mark_completed(reminder.id)

            if due_reminders:
                logger.info(f"Processed {len(due_reminders)} reminder(s)")

        except Exception as e:
            logger.error(f"Error in reminder check task: {e}")

        # Check every 30 seconds
        await asyncio.sleep(30)