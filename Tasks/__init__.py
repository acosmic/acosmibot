"""
Tasks package — contains all recurring background tasks for the bot.
Import tasks directly from this package, e.g.:

    from Tasks import gm_eu_task
"""

from .daily_reward_task import daily_reward_task
# from .lottery_end_task import lottery_end_task
# from .check_if_live_task import check_if_live_task

__all__ = [
    "daily_reward_task",
    "streaming_monitor_task",
    "twitch_live_task",
    "lottery_end_task"
]
