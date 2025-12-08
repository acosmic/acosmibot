"""
Tasks package — contains all recurring background tasks for the bot.
"""

from .daily_reward_task import daily_reward_task
from .streaming_monitor_task import streaming_monitor_task
# Replaced with EventSub webhook-based system (status updates only now)
from .unified_streaming_status_update_task import start_task as unified_streaming_status_update_task
from .unified_streaming_vod_checker import start_task as unified_streaming_vod_checker
from .lottery_end_task import lottery_end_task
from .check_reminders_task import check_reminders_task
from .unified_stats_reconciliation_task import unified_stats_reconciliation_task
from .bank_interest_task import bank_interest_task
from .portal_manager import check_expired_portals

# Deprecated tasks (kept for 30-day transition period)
# Old Twitch-only tasks replaced by unified_streaming_live_task and unified_streaming_vod_checker
# from .twitch_live_task import twitch_live_check_task
# from .twitch_vod_checker import twitch_vod_checker_task
# Deprecated: currency_reconciliation_task (replaced by unified_stats_reconciliation_task)
# from .currency_reconciliation_task import currency_reconciliation_task

__all__ = [
    "daily_reward_task",
    "streaming_monitor_task",
    "unified_streaming_status_update_task",  # EventSub-based (status updates only)
    "unified_streaming_vod_checker",
    "lottery_end_task",
    "check_reminders_task",
    "unified_stats_reconciliation_task",
    "bank_interest_task",
    "portal_manager"
]