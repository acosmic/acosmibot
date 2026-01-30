"""
Tasks package — contains all recurring background tasks for the bot.
"""

from .daily_reward_task import daily_reward_task
from .streaming_monitor_task import streaming_monitor_task
from .lottery_end_task import lottery_end_task
from .check_reminders_task import check_reminders_task
# from .bank_interest_task import bank_interest_task  # DISABLED - using daily reward interest instead
from .portal_manager import check_expired_portals

# Twitch tasks (decoupled)
from .twitch_status_update_task import start_task as twitch_status_update_task
from .twitch_vod_checker_task import start_task as twitch_vod_checker_task

# YouTube tasks (decoupled)
from .process_youtube_events_task import start_task as process_youtube_events_task
from .youtube_rss_poll_task import start_task as youtube_rss_poll_task
from .youtube_vod_checker_task import start_task as youtube_vod_checker_task

# Kick tasks (decoupled)
from .kick_status_update_task import start_task as kick_status_update_task
from .kick_vod_checker_task import start_task as kick_vod_checker_task

__all__ = [
    "daily_reward_task",
    "streaming_monitor_task",
    "lottery_end_task",
    "check_reminders_task",
    # "bank_interest_task",  # DISABLED - using daily reward interest instead
    "portal_manager",
    # Twitch tasks
    "twitch_status_update_task",
    "twitch_vod_checker_task",
    # YouTube tasks
    "process_youtube_events_task",
    "youtube_rss_poll_task",
    "youtube_vod_checker_task",
    # Kick tasks
    "kick_status_update_task",
    "kick_vod_checker_task",
]