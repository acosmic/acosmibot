import asyncio
import discord
from Dao.ReminderDao import ReminderDao
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


async def start_task(bot):
    """Entry point function that the task manager expects."""
    logger.info("=== REMINDER TASK: start_task() called ===")
    await check_reminders_task(bot)


async def check_reminders_task(bot):
    """Check for due reminders and send DMs every 30 seconds."""
    logger.info("=== REMINDER TASK: check_reminders_task() started, waiting for bot ready ===")
    await bot.wait_until_ready()
    logger.info("=== REMINDER TASK: Bot is ready, starting reminder loop ===")

    reminder_dao = ReminderDao()
    logger.info("=== REMINDER TASK: ReminderDao initialized ===")

    iteration = 0
    while not bot.is_closed():
        # iteration += 1
        # logger.info(f'=== REMINDER TASK: Iteration {iteration} - Checking for due reminders ===')
        try:
            due_reminders = reminder_dao.get_due_reminders()
            # logger.info(f'=== REMINDER TASK: Found {len(due_reminders)} due reminder(s) ===')

            for reminder in due_reminders:
                # logger.info(f'=== REMINDER TASK: Processing reminder ID {reminder.id} for user {reminder.user_id} ===')
                try:
                    # Get the user
                    logger.debug(f'Fetching user {reminder.user_id}...')
                    user = await bot.fetch_user(reminder.user_id)

                    if not user:
                        logger.warning(f"Could not find user {reminder.user_id} for reminder {reminder.id}")
                        reminder_dao.mark_completed(reminder.id)
                        continue

                    logger.debug(f'User {user.name} fetched successfully')

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
                        logger.debug(f'Attempting to send DM to user {user.name}...')
                        await user.send(embed=embed)
                        logger.info(f"✅ Successfully sent reminder {reminder.id} to user {reminder.user_id} ({user.name})")
                    except discord.Forbidden:
                        logger.warning(f"❌ Could not DM user {reminder.user_id} - DMs may be disabled")
                    except Exception as e:
                        logger.error(f"❌ Error sending DM to user {reminder.user_id}: {e}")

                    # Mark as completed
                    logger.debug(f'Marking reminder {reminder.id} as completed...')
                    mark_result = reminder_dao.mark_completed(reminder.id)
                    logger.info(f"Reminder {reminder.id} marked as completed: {mark_result}")

                except Exception as e:
                    logger.error(f"❌ Error processing reminder {reminder.id}: {e}", exc_info=True)
                    # Mark as completed anyway to avoid getting stuck
                    reminder_dao.mark_completed(reminder.id)
                    logger.info(f"Reminder {reminder.id} marked as completed despite error")

            if due_reminders:
                logger.info(f"=== REMINDER TASK: Processed {len(due_reminders)} reminder(s) ===")
            else:
                logger.debug("=== REMINDER TASK: No due reminders found ===")

        except Exception as e:
            logger.error(f"❌ CRITICAL ERROR in reminder check task: {e}", exc_info=True)

        # Check every 30 seconds
        # logger.debug(f"=== REMINDER TASK: Sleeping for 30 seconds (iteration {iteration} complete) ===")
        await asyncio.sleep(30)