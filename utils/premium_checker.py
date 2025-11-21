#! /usr/bin/python3.10
"""
Premium feature checker utility

This module provides centralized premium feature gating logic.
All premium checks should go through this utility to ensure consistency.
"""
from typing import Tuple, List, Optional
from Dao.GuildDao import GuildDao
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class PremiumChecker:
    """
    Utility class for checking premium tier access and limits

    All tier limits are defined in TIER_LIMITS constant.
    """

    # Tier limit definitions
    TIER_LIMITS = {
        'free': {
            # Twitch
            'twitch_streamers': 1,

            # Reaction Roles
            'reaction_roles': 1,  # Allow 1 reaction role message

            # Custom Commands
            'custom_commands': 1,  # Allow 1 custom command

            # AI
            'ai_daily_limit': 20,
            'ai_models': ['gpt-3.5-turbo'],
            'image_generation': False,
            'image_monthly_limit': 0,
            'image_analysis': False,  # Image analysis blocked

            # Economy
            'xp_multiplier': 1.0,

            # Features
            'custom_currency_name': False,
            'custom_embed_color': False,
            'custom_level_up_message': False,
        },
        'premium': {
            # Twitch
            'twitch_streamers': 5,

            # Reaction Roles
            'reaction_roles': 10,

            # Custom Commands
            'custom_commands': 25,

            # AI
            'ai_daily_limit': 100,
            'ai_models': ['gpt-3.5-turbo', 'gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo'],
            'image_generation': True,
            'image_monthly_limit': 50,
            'image_analysis': True,  # Image analysis enabled

            # Economy
            'xp_multiplier': 1.2,  # 20% bonus

            # Features
            'custom_currency_name': True,
            'custom_embed_color': True,
            'custom_level_up_message': True,
        }
    }

    @staticmethod
    def get_guild_tier(guild_id: int) -> str:
        """
        Get guild subscription tier from database

        Args:
            guild_id: Discord guild ID

        Returns:
            Tier string ('free' or 'premium')
        """
        try:
            with GuildDao() as dao:
                # Query the subscription_tier column directly from Guilds table
                query = "SELECT subscription_tier FROM Guilds WHERE id = %s"
                results = dao.execute_query(query, (int(guild_id),))

                # execute_query returns a list of dicts, get first result
                if results and len(results) > 0:
                    result = results[0]
                    if result.get('subscription_tier'):
                        return result['subscription_tier']
                return 'free'
        except Exception as e:
            logger.error(f"Error getting guild tier for {guild_id}: {e}")
            return 'free'  # Default to free on error

    @staticmethod
    def has_premium(guild_id: int) -> bool:
        """
        Check if guild has premium subscription

        Args:
            guild_id: Discord guild ID

        Returns:
            True if premium, False otherwise
        """
        tier = PremiumChecker.get_guild_tier(guild_id)
        return tier == 'premium'

    @staticmethod
    def has_feature(guild_id: int, feature: str) -> bool:
        """
        Check if guild has access to a specific feature

        Args:
            guild_id: Discord guild ID
            feature: Feature name (e.g., 'image_generation', 'custom_currency_name')

        Returns:
            True if guild has access, False otherwise
        """
        tier = PremiumChecker.get_guild_tier(guild_id)
        limits = PremiumChecker.TIER_LIMITS.get(tier, PremiumChecker.TIER_LIMITS['free'])
        return limits.get(feature, False)

    @staticmethod
    def get_limit(guild_id: int, limit_name: str) -> int:
        """
        Get numeric limit for a feature

        Args:
            guild_id: Discord guild ID
            limit_name: Limit name (e.g., 'twitch_streamers', 'ai_daily_limit')

        Returns:
            Limit value
        """
        tier = PremiumChecker.get_guild_tier(guild_id)
        limits = PremiumChecker.TIER_LIMITS.get(tier, PremiumChecker.TIER_LIMITS['free'])
        return limits.get(limit_name, 0)

    @staticmethod
    def get_xp_multiplier(guild_id: int) -> float:
        """
        Get XP multiplier for guild

        Args:
            guild_id: Discord guild ID

        Returns:
            XP multiplier (1.0 for free, 1.5 for premium)
        """
        return PremiumChecker.get_limit(guild_id, 'xp_multiplier')

    @staticmethod
    def can_use_ai_model(guild_id: int, model: str) -> Tuple[bool, str]:
        """
        Check if guild can use specific AI model

        Args:
            guild_id: Discord guild ID
            model: Model name (e.g., 'gpt-4', 'gpt-3.5-turbo')

        Returns:
            Tuple of (can_use: bool, error_message: str)
        """
        tier = PremiumChecker.get_guild_tier(guild_id)
        allowed_models = PremiumChecker.TIER_LIMITS[tier]['ai_models']

        if model in allowed_models:
            return True, ""

        # Generate helpful error message
        if tier == 'free':
            return False, (
                f"❌ Model **{model}** requires **Premium** subscription!\n"
                f"Free tier supports: {', '.join(allowed_models)}\n"
                f"Upgrade at https://acosmibot.com/premium"
            )
        else:
            return False, f"❌ Model {model} not available in your tier"

    @staticmethod
    def get_available_ai_models(guild_id: int) -> List[str]:
        """
        Get list of AI models available to guild

        Args:
            guild_id: Discord guild ID

        Returns:
            List of model names
        """
        tier = PremiumChecker.get_guild_tier(guild_id)
        return PremiumChecker.TIER_LIMITS[tier]['ai_models']

    @staticmethod
    def check_twitch_limit(guild_id: int, current_count: int) -> Tuple[bool, str]:
        """
        Check if guild can add more Twitch streamers

        Args:
            guild_id: Discord guild ID
            current_count: Current number of tracked streamers

        Returns:
            Tuple of (can_add: bool, message: str)
        """
        tier = PremiumChecker.get_guild_tier(guild_id)
        max_streamers = PremiumChecker.TIER_LIMITS[tier]['twitch_streamers']

        if current_count < max_streamers:
            return True, ""

        if tier == 'free':
            return False, (
                f"❌ Free tier allows **{max_streamers} streamer** only.\n"
                f"Upgrade to **Premium** for **5 streamers**!\n"
                f"https://acosmibot.com/premium"
            )
        else:
            return False, f"❌ Premium tier allows up to {max_streamers} streamers. Remove one to add another."

    @staticmethod
    def check_reaction_role_limit(guild_id: int, current_count: int) -> Tuple[bool, str]:
        """
        Check if guild can create more reaction roles

        Args:
            guild_id: Discord guild ID
            current_count: Current number of reaction role messages

        Returns:
            Tuple of (can_create: bool, message: str)
        """
        tier = PremiumChecker.get_guild_tier(guild_id)
        max_roles = PremiumChecker.TIER_LIMITS[tier]['reaction_roles']

        if max_roles == 0:
            return False, (
                f"❌ **Reaction Roles** require **Premium** subscription!\n"
                f"Upgrade at https://acosmibot.com/premium"
            )

        if current_count < max_roles:
            return True, ""

        return False, f"❌ Premium tier allows up to {max_roles} reaction role messages. Delete one to create another."

    @staticmethod
    def check_custom_command_limit(guild_id: int, current_count: int) -> Tuple[bool, str]:
        """
        Check if guild can create more custom commands

        Args:
            guild_id: Discord guild ID
            current_count: Current number of custom commands

        Returns:
            Tuple of (can_create: bool, message: str)
        """
        tier = PremiumChecker.get_guild_tier(guild_id)
        max_commands = PremiumChecker.TIER_LIMITS[tier]['custom_commands']

        if max_commands == 0:
            return False, (
                f"❌ **Custom Commands** require **Premium** subscription!\n"
                f"Upgrade at https://acosmibot.com/premium"
            )

        if current_count < max_commands:
            return True, ""

        return False, f"❌ Premium tier allows up to {max_commands} custom commands. Delete one to create another."

    @staticmethod
    def get_ai_daily_limit(guild_id: int) -> int:
        """Get daily AI message limit for guild"""
        return PremiumChecker.get_limit(guild_id, 'ai_daily_limit')

    @staticmethod
    def get_image_monthly_limit(guild_id: int) -> int:
        """Get monthly image generation limit for guild"""
        return PremiumChecker.get_limit(guild_id, 'image_monthly_limit')

    @staticmethod
    def can_generate_images(guild_id: int) -> Tuple[bool, str]:
        """
        Check if guild can generate images

        Args:
            guild_id: Discord guild ID

        Returns:
            Tuple of (can_generate: bool, message: str)
        """
        if not PremiumChecker.has_feature(guild_id, 'image_generation'):
            return False, (
                f"❌ **Image Generation** requires **Premium** subscription!\n"
                f"Upgrade at https://acosmibot.com/premium"
            )
        return True, ""

    @staticmethod
    def get_tier_display_name(tier: str) -> str:
        """Get display-friendly tier name"""
        tier_names = {
            'free': 'Free',
            'premium': 'Premium 💎'
        }
        return tier_names.get(tier, 'Unknown')

    @staticmethod
    def get_upgrade_message(feature_name: str) -> str:
        """Get generic upgrade prompt message"""
        return (
            f"❌ **{feature_name}** requires **Premium** subscription!\n"
            f"Upgrade at https://acosmibot.com/premium for only **$9.99/month**"
        )
