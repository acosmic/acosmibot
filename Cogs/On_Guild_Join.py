from operator import truediv

import discord
import json
from discord.ext import commands
from datetime import datetime
from Dao.GuildDao import GuildDao
from Dao.GuildUserDao import GuildUserDao
from Dao.UserDao import UserDao
from Entities.Guild import Guild
from Entities.GuildUser import GuildUser
from Entities.User import User
from logger import AppLogger
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()
logger = AppLogger(__name__).get_logger()

# Default settings for new guilds
DEFAULT_GUILD_SETTINGS = {
    "ai": {
        "model": "gpt-4o-mini",
        "enabled": False,
        "channel_mode": "exclude",
        "instructions": "Core vibe: Dry, minimal, deadpan monologues. Sounds unimpressed. Sarcastic and condescending. Doesn't always answer directly—often deflects, reframes, or answers the question they wish was asked. Respond in a single paragraph, 2–6 sentences. Don't overdo your answers. Don't constantly finish with a question.\n\nRecurring Moves:\n-Deflection: Answer a nearby question instead of the literal one.\n-Undercut: Provide a fact, then puncture it with a dry aside.\n-Elegantly wrong-foot: If user is fishing for compliments, pivot to mild roast.\n\n-If accused of obsession, deflect: \"That's a reach. Anyway…\".\n-Refusals: If content is disallowed or sketchy, decline in deadpan, one line, no moralizing.\nDiscord etiquette: Never ping @everyone or mass mention. No personal data requests.",
        "allowed_channels": [],
        "excluded_channels": []
    },
    "games": {
        "enabled": True,
        "slots-config": {
            "enabled": True,
            "tier_emojis": {
                "rare": ["🍑"],
                "common": ["🐒", "🐢", "🦉", "🦏", "🦖"],
                "scatter": ["💎"],
                "uncommon": ["🍾", "🍸", "🍺"],
                "legendary": ["🍆", "🫃"]
            }
        }
    },
    "roles": {
        "mode": "additive",
        "enabled": False,
        "role_cache": {},
        "role_mappings": {},
        "role_announcement": False,
        "remove_previous_roles": False,
        "announcement_channel_id": None
    },
    "twitch": {
        "enabled": False,
        "vod_settings": {
            "enabled": True,
            "edit_message_when_vod_available": True
        },
        "tracked_streamers": [],
        "announcement_settings": {
            "color": "0x6441A4",
            "include_game": True,
            "include_thumbnail": True,
            "include_start_time": True,
            "include_viewer_count": True
        },
        "announcement_channel_id": None
    },
    "youtube": {
        "enabled": False,
        "vod_settings": {
            "enabled": True,
            "vod_message_suffix": "[Watch VOD]({vod_url})",
            "edit_message_when_vod_available": True
        },
        "tracked_streamers": [],
        "announcement_settings": {
            "color": "0xFF0000",
            "include_game": True,
            "include_thumbnail": True,
            "include_start_time": True,
            "include_viewer_count": True
        },
        "announcement_channel_id": None
    },
    "leveling": {
        "enabled": False,
        "level_up_message": "{username}, you have reached level {level}! Gained {credits} Credits!",
        "level_up_announcements": False,
        "announcement_channel_id": None,
        "daily_announcement_message": "{username} claimed their daily reward. {credits} Credits!",
        "daily_announcements_enabled": False,
        "level_up_message_with_streak": "{username} reached level {level}! Gained {credits} Credits! {base_credits} + {streak_bonus} from {streak}x Streak!",
        "daily_announcement_channel_id": None,
        "daily_announcement_message_with_streak": "{username} claimed their daily reward! +{credits} Credits! ({base_credits} + {streak_bonus} from {streak}x streak!)"
    },
    "moderation": {
        "events": {
            "on_member_join": {
                "color": "#00ff00",
                "enabled": False,
                "message": "Welcome {user.mention} to the server!",
                "channel_id": None
            },
            "on_message_edit": {
                "enabled": False,
                "channel_id": None
            },
            "on_member_remove": {
                "color": "#ff0000",
                "enabled": False,
                "message": "{user.name} has left the server.",
                "channel_id": None
            },
            "on_member_update": {
                "nickname_change": {
                    "enabled": False,
                    "channel_id": None
                }
            },
            "on_message_delete": {
                "enabled": False,
                "channel_id": None
            },
            "on_audit_log_entry": {
                "ban": {
                    "enabled": False,
                    "channel_id": None
                },
                "kick": {
                    "enabled": False,
                    "channel_id": None
                },
                "mute": {
                    "enabled": False,
                    "channel_id": None
                },
                "unban": {
                    "enabled": False,
                    "channel_id": None
                },
                "role_change": {
                    "enabled": False,
                    "channel_id": None
                }
            }
        },
        "enabled": False,
        "mod_log_channel_id": None,
        "member_activity_channel_id": None
    },
    "cross_server_portal": {
        "enabled": False,
        "channel_id": None,
        "portal_cost": 1000,
        "display_name": None,
        "public_listing": False
    }
}


class On_Guild_Join(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """
        Event triggered when the bot joins a new guild.
        Creates guild record and adds all existing members to the database.
        """
        try:
            logger.info(f"Bot joined guild: {guild.name} (ID: {guild.id})")

            # Initialize DAOs
            guild_dao = GuildDao()
            guild_user_dao = GuildUserDao()
            user_dao = UserDao()

            # Create guild record
            await self._create_guild_record(guild, guild_dao)

            # Add all existing members to the database (both global and guild-specific)
            await self._add_guild_members(guild, guild_user_dao, user_dao)

            # Send welcome message to a general channel if possible
            # await self._send_welcome_message(guild)

            logger.info(f"Successfully processed guild join for {guild.name}")

        except Exception as e:
            logger.error(f"Error processing guild join for {guild.name}: {e}")

    async def _create_guild_record(self, guild: discord.Guild, guild_dao: GuildDao):
        """
        Create a database record for the new guild.
        """
        try:
            # Check if guild already exists
            existing_guild = guild_dao.get_guild(guild.id)

            if existing_guild:
                logger.info(f"Guild {guild.name} already exists in database, updating...")
                # Update existing guild info
                existing_guild.name = guild.name
                existing_guild.owner_id = guild.owner_id
                existing_guild.member_count = guild.member_count
                existing_guild.active = True
                existing_guild.last_active = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                guild_dao.update_guild(existing_guild)
            else:
                # Create new guild record
                formatted_join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                new_guild = Guild(
                    id=guild.id,
                    name=guild.name,
                    owner_id=guild.owner_id,
                    member_count=guild.member_count,
                    active=True,
                    settings=json.dumps(DEFAULT_GUILD_SETTINGS),
                    created=formatted_join_date,
                    last_active=formatted_join_date,
                    vault_currency=0  # Default vault currency
                )

                if guild_dao.add_new_guild(new_guild):
                    logger.info(f"Created guild record for {guild.name}")
                else:
                    logger.error(f"Failed to create guild record for {guild.name}")

        except Exception as e:
            logger.error(f"Error creating guild record for {guild.name}: {e}")

    async def _add_guild_members(self, guild: discord.Guild, guild_user_dao: GuildUserDao, user_dao: UserDao):
        """
        Add all current guild members to the database (both global and guild-specific).
        Uses bulk operations for performance with large member counts.
        """
        try:
            # Prepare lists for bulk operations
            global_users_to_upsert = []
            guild_users_to_upsert = []

            formatted_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Build lists of users to upsert (no database calls yet)
            for member in guild.members:
                if member.bot:
                    continue  # Skip bots

                # Prepare global user
                try:
                    account_created = member.created_at.strftime("%Y-%m-%d %H:%M:%S") if member.created_at else formatted_now
                except Exception:
                    account_created = formatted_now

                global_user = User(
                    id=member.id,
                    discord_username=member.name,
                    global_name=member.global_name if hasattr(member, 'global_name') else member.name,
                    avatar_url=str(member.avatar.url) if member.avatar else None,
                    is_bot=member.bot,
                    global_exp=0,
                    global_level=0,
                    total_currency=0,
                    total_messages=0,
                    total_reactions=0,
                    account_created=account_created,
                    first_seen=formatted_now,
                    last_seen=formatted_now,
                    privacy_settings=None,
                    global_settings=None
                )
                global_users_to_upsert.append(global_user)

                # Prepare guild user
                try:
                    joined_at = member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else formatted_now
                except Exception:
                    joined_at = formatted_now

                guild_user = GuildUser(
                    user_id=member.id,
                    guild_id=guild.id,
                    name=member.name,
                    nickname=member.display_name,
                    level=0,
                    streak=0,
                    highest_streak=0,
                    exp=0,
                    exp_gained=0,
                    exp_lost=0,
                    currency=1000,  # Starting currency for new users
                    messages_sent=0,
                    reactions_sent=0,
                    joined_at=joined_at,
                    last_active=formatted_now,
                    daily=0,
                    last_daily=None,
                    is_active=True
                )
                guild_users_to_upsert.append(guild_user)

            # Perform bulk operations in separate thread to avoid blocking event loop
            def bulk_db_operations():
                success_global = user_dao.bulk_upsert_users(global_users_to_upsert)
                success_guild = guild_user_dao.bulk_upsert_guild_users(guild_users_to_upsert)
                return success_global, success_guild

            # Run blocking database operations in thread pool
            success_global, success_guild = await asyncio.to_thread(bulk_db_operations)

            if success_global and success_guild:
                logger.info(
                    f"Member processing complete for {guild.name}: "
                    f"Processed {len(global_users_to_upsert)} global users and {len(guild_users_to_upsert)} guild users in bulk"
                )
            else:
                logger.error(f"Some bulk operations failed for {guild.name}")

        except Exception as e:
            logger.error(f"Error adding guild members for {guild.name}: {e}")

    def clean_channel_name(self, name: str) -> str:
        """Remove emojis, special characters, and separators from channel name"""
        import re

        # Remove emojis (Unicode emoji pattern)
        emoji_pattern = re.compile("["
                                   u"\U0001F600-\U0001F64F"  # emoticons
                                   u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                   u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                   u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                                   u"\U00002702-\U000027B0"  # Dingbats
                                   u"\U000024C2-\U0001F251"
                                   "]+", flags=re.UNICODE)

        cleaned = emoji_pattern.sub('', name)

        # Remove common separators and special characters
        cleaned = re.sub(r'[︱｜|‖∥]', '', cleaned)  # Various vertical bar characters
        cleaned = re.sub(r'[-_\s]+', '', cleaned)  # Hyphens, underscores, spaces
        cleaned = re.sub(r'[^\w]', '', cleaned)  # Any remaining non-word characters

        return cleaned.strip()

    async def _send_welcome_message(self, guild: discord.Guild):
        """
        Send a welcome message to the guild.
        """
        try:
            # Look for common channel names to send welcome message
            welcome_channels = ['general', 'welcome', 'botcommands', 'commands', 'chat', 'main']

            target_channel = None

            # Try to find a suitable channel using cleaned names
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    # Check both original and cleaned channel names
                    original_name = channel.name.lower()
                    cleaned_name = self.clean_channel_name(channel.name).lower()

                    if original_name in welcome_channels or cleaned_name in welcome_channels:
                        target_channel = channel
                        break

            # If no specific channel found, use the first channel the bot can send messages to
            if not target_channel:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        target_channel = channel
                        break

            if target_channel:
                embed = discord.Embed(
                    title="🎉 Thank you for adding Acosmibot!",
                    description="I'm excited to be part of your server!",
                    color=discord.Color.blue()
                )

                embed.add_field(
                    name="🚀 Getting Started",
                    value="Use `/help` to see all available commands!",
                    inline=False
                )

                embed.add_field(
                    name="🎮 Features",
                    value="• Leveling system with XP and rewards\n• Economy with Credits\n• Fun games like slots, coinflip, and more\n• AI chat capabilities\n• Leaderboards and stats",
                    inline=False
                )

                embed.add_field(
                    name="🤖 AI Features",
                    value="• AI-powered conversations\n• Customizable personality traits\n• Contextual responses\n• Use AI commands to get started!",
                    inline=False
                )

                embed.set_footer(text="Developed by Acosmic")

                await target_channel.send(embed=embed)
                logger.info(f"Sent welcome message to {guild.name} in #{target_channel.name}")
            else:
                logger.warning(f"Could not find a suitable channel to send welcome message in {guild.name}")

        except Exception as e:
            logger.error(f"Error sending welcome message to {guild.name}: {e}")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """
        Event triggered when the bot leaves a guild.
        Deactivates the guild in the database.
        """
        try:
            logger.info(f"Bot left guild: {guild.name} (ID: {guild.id})")

            guild_dao = GuildDao()
            guild_user_dao = GuildUserDao()

            # Deactivate guild
            existing_guild = guild_dao.get_guild(guild.id)
            if existing_guild:
                existing_guild.active = False
                existing_guild.last_active = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                guild_dao.update_guild(existing_guild)
                logger.info(f"Deactivated guild: {guild.name}")

            # Deactivate all guild users
            guild_users = guild_user_dao.get_guild_users(guild.id)
            for guild_user in guild_users:
                guild_user_dao.deactivate_guild_user(guild_user.user_id, guild.id)

            logger.info(f"Deactivated {len(guild_users)} users from guild: {guild.name}")

        except Exception as e:
            logger.error(f"Error processing guild leave for {guild.name}: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(On_Guild_Join(bot))