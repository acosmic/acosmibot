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
            # Streaming (platform-specific limits)
            'twitch_streamers': 1,
            'youtube_streamers': 1,

            # Reaction Roles
            'reaction_roles': 1,  # Allow 1 reaction role message

            # Custom Commands
            'custom_commands': 1,  # Allow 1 custom command

            # Embeds
            'embeds': 5,  # Allow 5 embeds

            # AI
            'ai_daily_limit': 20,
            'ai_models': ['gpt-3.5-turbo'],
            'image_generation': False,
            'image_monthly_limit': 0,
            'image_analysis': False,  # Image analysis blocked
            'image_analysis_monthly_limit': 0,

            # Economy
            'xp_multiplier': 1.0,

            # Features
            'custom_currency_name': False,
            'custom_embed_color': False,
            'custom_level_up_message': False,
        },
        'premium': {
            # Streaming (platform-specific limits)
            'twitch_streamers': 5,
            'youtube_streamers': 5,

            # Reaction Roles
            'reaction_roles': 10,

            # Custom Commands
            'custom_commands': 25,

            # Embeds
            'embeds': 100,

            # AI - SAME AS FREE (basic tier only)
            'ai_daily_limit': 20,  # Same as free
            'ai_models': ['gpt-3.5-turbo'],  # Same as free
            'image_generation': False,  # Same as free
            'image_monthly_limit': 0,  # Same as free
            'image_analysis': False,  # Same as free
            'image_analysis_monthly_limit': 0,  # Same as free

            # Economy
            'xp_multiplier': 1.2,  # 20% bonus

            # Features
            'custom_currency_name': True,
            'custom_embed_color': True,
            'custom_level_up_message': True,
        },
        'premium_plus_ai': {
            # Streaming (platform-specific limits) - Same as premium
            'twitch_streamers': 5,
            'youtube_streamers': 5,

            # Reaction Roles - Same as premium
            'reaction_roles': 10,

            # Custom Commands - Same as premium
            'custom_commands': 25,

            # Embeds - Same as premium
            'embeds': 100,

            # AI - ENHANCED (all features unlocked)
            'ai_daily_limit': 100,  # 5x increase from free/premium
            'ai_models': ['gpt-3.5-turbo', 'gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo'],  # All models
            'image_generation': True,  # Enabled
            'image_monthly_limit': 50,
            'image_analysis': True,  # Enabled
            'image_analysis_monthly_limit': 100,

            # Economy - Same as premium
            'xp_multiplier': 1.2,  # 20% bonus

            # Features - Same as premium
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
            Tier string ('free', 'premium', or 'premium_plus_ai')
        """
        try:
            with GuildDao() as dao:
                # Query the subscription_tier column directly from Guilds table
                query = "SELECT subscription_tier FROM Guilds WHERE id = %s"
                results = dao.execute_query(query, (int(guild_id),))

                # execute_query returns a list of dicts OR tuples, handle both
                if results and len(results) > 0:
                    result = results[0]
                    # Handle dict result
                    if isinstance(result, dict):
                        if result.get('subscription_tier'):
                            return result['subscription_tier']
                    # Handle tuple result
                    elif isinstance(result, tuple):
                        if result[0]:
                            return result[0]
                return 'free'
        except Exception as e:
            logger.error(f"Error getting guild tier for {guild_id}: {e}", exc_info=True)
            return 'free'  # Default to free on error

    @staticmethod
    def has_premium(guild_id: int) -> bool:
        """
        Check if guild has premium subscription (premium OR premium_plus_ai)

        Args:
            guild_id: Discord guild ID

        Returns:
            True if premium or premium_plus_ai, False otherwise
        """
        tier = PremiumChecker.get_guild_tier(guild_id)
        return tier in ['premium', 'premium_plus_ai']

    @staticmethod
    def has_tier_or_higher(guild_id: int, required_tier: str) -> bool:
        """
        Check if guild's tier meets or exceeds the required tier

        Tier hierarchy: free < premium < premium_plus_ai

        Args:
            guild_id: Discord guild ID
            required_tier: Required tier ('free', 'premium', or 'premium_plus_ai')

        Returns:
            True if guild's tier >= required tier, False otherwise
        """
        tier_hierarchy = {'free': 0, 'premium': 1, 'premium_plus_ai': 2}
        current_tier = PremiumChecker.get_guild_tier(guild_id)
        current_level = tier_hierarchy.get(current_tier, 0)
        required_level = tier_hierarchy.get(required_tier, 0)
        return current_level >= required_level

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
        if tier in ['free', 'premium']:
            return False, (
                f"❌ Model **{model}** requires **Premium + AI** subscription!\n"
                f"Your tier supports: {', '.join(allowed_models)}\n"
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
    def check_streaming_limit(guild_id: int, platform: str, current_count: int) -> Tuple[bool, str]:
        """
        Check if guild can add more streamers for specific platform

        NOTE: Limits are SEPARATE per platform (1 Twitch + 1 YouTube = valid on free tier)

        Args:
            guild_id: Discord guild ID
            platform: 'twitch' or 'youtube'
            current_count: Current number of tracked streamers for this platform

        Returns:
            Tuple of (can_add: bool, message: str)
        """
        tier = PremiumChecker.get_guild_tier(guild_id)
        limit_key = f'{platform}_streamers'
        max_streamers = PremiumChecker.TIER_LIMITS[tier].get(limit_key, 0)

        if max_streamers == 0:
            return False, (
                f"❌ **{platform.capitalize()} streaming** is not available in your tier.\n"
                f"https://acosmibot.com/premium"
            )

        if current_count <= max_streamers:
            return True, ""

        platform_display = platform.capitalize()
        if tier == 'free':
            return False, (
                f"❌ Free tier allows **{max_streamers} {platform_display} streamer** only.\n"
                f"Upgrade to **Premium** for **5 {platform_display} streamers**!\n"
                f"https://acosmibot.com/premium"
            )
        else:
            return False, (
                f"❌ Premium tier allows up to {max_streamers} {platform_display} streamers. "
                f"Remove one to add another."
            )

    @staticmethod
    def count_streamers_by_platform(guild_settings: dict, platform: str) -> int:
        """
        Count tracked streamers for specific platform from guild settings

        Args:
            guild_settings: Full guild settings dict
            platform: 'twitch' or 'youtube'

        Returns:
            Number of tracked streamers for the platform
        """
        from utils.settings_migrator import get_streaming_settings

        streaming_settings = get_streaming_settings(guild_settings)
        tracked_streamers = streaming_settings.get('tracked_streamers', [])

        return sum(1 for s in tracked_streamers if s.get('platform') == platform)

    @staticmethod
    def check_twitch_limit(guild_id: int, current_count: int) -> Tuple[bool, str]:
        """
        DEPRECATED: Use check_streaming_limit(guild_id, 'twitch', current_count) instead

        Check if guild can add more Twitch streamers

        Args:
            guild_id: Discord guild ID
            current_count: Current number of tracked Twitch streamers

        Returns:
            Tuple of (can_add: bool, message: str)
        """
        return PremiumChecker.check_streaming_limit(guild_id, 'twitch', current_count)

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

        if current_count <= max_roles:
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

        if current_count <= max_commands:
            return True, ""

        return False, f"❌ Premium tier allows up to {max_commands} custom commands. Delete one to create another."

    @staticmethod
    def check_embed_limit(guild_id: int, current_count: int) -> Tuple[bool, str]:
        """
        Check if guild can create more embeds

        Args:
            guild_id: Discord guild ID
            current_count: Current number of embeds

        Returns:
            Tuple of (can_create: bool, message: str)
        """
        tier = PremiumChecker.get_guild_tier(guild_id)
        max_embeds = PremiumChecker.TIER_LIMITS[tier]['embeds']

        if max_embeds == 0:
            return False, (
                f"❌ **Embeds** are not available in your tier.\n"
                f"Upgrade at https://acosmibot.com/premium"
            )

        if current_count < max_embeds:
            return True, ""

        if tier == 'free':
            return False, (
                f"❌ Free tier allows **{max_embeds} embeds** only.\n"
                f"Upgrade to **Premium** for **100 embeds**!\n"
                f"https://acosmibot.com/premium"
            )
        else:
            return False, f"❌ Your tier allows up to {max_embeds} embeds. Delete one to create another."

    @staticmethod
    def get_embed_limit(guild_id: int) -> int:
        """
        Get embed limit for guild

        Args:
            guild_id: Discord guild ID

        Returns:
            Maximum number of embeds allowed
        """
        return PremiumChecker.get_limit(guild_id, 'embeds')

    @staticmethod
    def get_tier_info(guild_id: int) -> dict:
        """
        Get tier information for guild

        Args:
            guild_id: Discord guild ID

        Returns:
            Dictionary with tier and limits
        """
        tier = PremiumChecker.get_guild_tier(guild_id)
        return {
            'tier': tier,
            'limits': PremiumChecker.TIER_LIMITS.get(tier, PremiumChecker.TIER_LIMITS['free'])
        }

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
                f"❌ **Image Generation** requires **Premium + AI** subscription!\n"
                f"Upgrade at https://acosmibot.com/premium"
            )
        return True, ""

    @staticmethod
    def can_analyze_images(guild_id: int) -> Tuple[bool, str]:
        """
        Check if guild can analyze images

        Args:
            guild_id: Discord guild ID

        Returns:
            Tuple of (can_analyze: bool, message: str)
        """
        if not PremiumChecker.has_feature(guild_id, 'image_analysis'):
            return False, (
                f"❌ **Image Analysis** requires **Premium + AI** subscription!\n"
                f"Upgrade at https://acosmibot.com/premium"
            )
        return True, ""

    @staticmethod
    def check_image_generation_limit(guild_id: int, current_month_count: int) -> Tuple[bool, str]:
        """
        Check if guild can generate more images this month

        Args:
            guild_id: Discord guild ID
            current_month_count: Number of images generated this month

        Returns:
            Tuple of (can_generate: bool, message: str)
        """
        tier = PremiumChecker.get_guild_tier(guild_id)
        monthly_limit = PremiumChecker.TIER_LIMITS[tier]['image_monthly_limit']

        if monthly_limit == 0:
            return False, (
                f"❌ **Image Generation** requires **Premium + AI** subscription!\n"
                f"Upgrade at https://acosmibot.com/premium"
            )

        if current_month_count >= monthly_limit:
            return False, (
                f"❌ Monthly image generation limit reached ({current_month_count}/{monthly_limit}).\n"
                f"Limit resets at the beginning of next month."
            )

        return True, ""

    @staticmethod
    def check_image_analysis_limit(guild_id: int, current_month_count: int) -> Tuple[bool, str]:
        """
        Check if guild can analyze more images this month

        Args:
            guild_id: Discord guild ID
            current_month_count: Number of images analyzed this month

        Returns:
            Tuple of (can_analyze: bool, message: str)
        """
        tier = PremiumChecker.get_guild_tier(guild_id)

        # Check if feature is enabled for this tier
        if not PremiumChecker.TIER_LIMITS[tier]['image_analysis']:
            return False, (
                f"❌ **Image Analysis** requires **Premium + AI** subscription!\n"
                f"Upgrade at https://acosmibot.com/premium"
            )

        # Check monthly limit
        monthly_limit = PremiumChecker.TIER_LIMITS[tier]['image_analysis_monthly_limit']

        if current_month_count >= monthly_limit:
            return False, (
                f"❌ Monthly image analysis limit reached ({current_month_count}/{monthly_limit}).\n"
                f"Limit resets at the beginning of next month."
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
