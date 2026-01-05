import asyncio
import aiohttp
import discord
import pytz
from datetime import datetime, timedelta
from typing import Dict, Any, List

from database import get_db_session
from Dao.YoutubeDao import YoutubeDao
from Dao.GuildDao import GuildDao
from Dao.StreamingAnnouncementDao import StreamingAnnouncementDao
from Services.youtube_service import YouTubeService
import logging
logger = logging.getLogger(__name__)

async def start_task(bot):
    """
    Background task to process YouTube webhook events.
    It fetches unprocessed events, gets video details, and creates/updates
    StreamingAnnouncements for live streams.
    """
    # Create an aiohttp session for API calls
    async with aiohttp.ClientSession() as session:
        youtube_service = YouTubeService()

        while True:
            try:
                await asyncio.sleep(10) # Process every 10 seconds

                async with get_db_session() as db_session:
                    youtube_dao = YoutubeDao(db_session)

                    events = await youtube_dao.get_unprocessed_webhook_events()
                    if not events:
                        # logger.debug("No unprocessed YouTube webhook events found.")
                        continue

                    logger.info(f"Processing {len(events)} unprocessed YouTube webhook events.")

                    for event_id, _, channel_id, video_id, event_type, payload in events:
                        try:
                            # Fetch full video details using the YouTube Data API
                            video_details = await youtube_service.get_video_details(session, video_id)

                            if not video_details:
                                logger.warning(f"Could not retrieve video details for video ID {video_id} (channel {channel_id}). Marking as processed.")
                                await youtube_dao.mark_webhook_event_as_processed(event_id)
                                continue

                            if video_details['is_live']:
                                logger.info(f"YouTube channel {channel_id} (video {video_id}) is LIVE: {video_details['title']}")
                                # Post to all subscribed guilds
                                await _post_youtube_live_announcements(bot, channel_id, video_id, video_details)
                            elif event_type == 'video_published':
                                logger.info(f"YouTube channel {channel_id} published a new video: {video_details['title']} ({video_id})")
                                # Post to all subscribed guilds
                                await _post_youtube_video_announcements(bot, channel_id, video_id, video_details)
                            elif video_details['is_upcoming']:
                                logger.info(f"YouTube channel {channel_id} (video {video_id}) is UPCOMING. Not creating announcement yet.")
                                # We might want to store upcoming events differently or ignore them for now
                                # Depending on requirements, we could create a 'scheduled' announcement
                                pass # For now, just mark as processed if we don't announce upcoming
                            else:
                                logger.info(f"YouTube channel {channel_id} (video {video_id}) is a regular upload or ended live stream. Not announcing.")
                                # For ended live streams, the VOD checker will handle the update.
                                pass

                            # Mark event as processed regardless of whether an announcement was made
                            await youtube_dao.mark_webhook_event_as_processed(event_id)

                        except Exception as e:
                            logger.error(f"Error processing YouTube event {event_id} (video {video_id}, channel {channel_id}): {e}", exc_info=True)
                            # Do not mark as processed if an error occurred, so it can be retried

            except Exception as e:
                logger.error(f"Unhandled error in YouTube event processing task: {e}", exc_info=True)


async def _get_subscribed_guilds_for_channel(bot, channel_id: str) -> List[tuple]:
    """
    Get all guilds subscribed to a YouTube channel with their settings.
    Returns list of (guild, channel, streamer_config, settings) tuples.

    Optimized: Only queries guilds subscribed to this specific channel (like Twitch implementation).
    """
    subscribed_guilds = []

    # Get only subscriptions for this specific channel (efficient SQL query)
    async with get_db_session() as db_session:
        youtube_dao = YoutubeDao(db_session)
        channel_subscriptions = await youtube_dao.get_guilds_subscribed_to_channel(channel_id)

    if not channel_subscriptions:
        logger.debug(f"No guilds subscribed to YouTube channel {channel_id}")
        return []

    logger.debug(f"Found {len(channel_subscriptions)} guild(s) subscribed to YouTube channel {channel_id}")

    # For each subscribed guild, get the guild object and settings
    guild_dao = GuildDao()
    try:
        for guild_id, channel_name in channel_subscriptions:
            guild = bot.get_guild(guild_id)
            if not guild:
                logger.debug(f"Guild {guild_id} not found (bot not in guild)")
                continue

            # Get guild settings
            settings = guild_dao.get_guild_settings(guild_id)
            if not settings:
                logger.debug(f"No settings found for guild {guild_id}")
                continue

            streaming_settings = settings.get('youtube', {})
            if not streaming_settings.get('enabled'):
                logger.debug(f"Streaming disabled for guild {guild.name}")
                continue

            # Get announcement channel
            announcement_channel_id = streaming_settings.get('announcement_channel_id')
            if not announcement_channel_id:
                logger.debug(f"No announcement channel configured for guild {guild.name}")
                continue

            channel = guild.get_channel(int(announcement_channel_id))
            if not channel:
                logger.warning(f"Announcement channel {announcement_channel_id} not found in guild {guild.name}")
                continue

            # Find the streamer config for this YouTube channel
            streamer_config = None
            for streamer in streaming_settings.get('tracked_streamers', []):
                if streamer.get('platform') == 'youtube':
                    # Match by username (which should be the channel_id or handle)
                    # For now, we'll just pass the first YouTube streamer config
                    # In the future, might need to match by channel_id specifically
                    streamer_config = streamer
                    break

            if not streamer_config:
                # Create a default config if none exists
                streamer_config = {'platform': 'youtube', 'username': channel_name or channel_id}

            subscribed_guilds.append((guild, channel, streamer_config, streaming_settings))

    finally:
        guild_dao.close()

    return subscribed_guilds


async def _post_youtube_live_announcements(bot, channel_id: str, video_id: str, video_details: Dict[str, Any]):
    """Post YouTube live stream announcement to all subscribed guilds."""
    subscribed_guilds = await _get_subscribed_guilds_for_channel(bot, channel_id)

    if not subscribed_guilds:
        logger.info(f"No guilds subscribed to YouTube channel {channel_id}")
        return

    for guild, discord_channel, streamer_config, settings in subscribed_guilds:
        try:
            await _post_youtube_live_announcement_to_guild(
                guild, discord_channel, streamer_config, settings, video_details
            )
        except Exception as e:
            logger.error(f"Error posting YouTube live announcement to guild {guild.name}: {e}", exc_info=True)


async def _post_youtube_video_announcements(bot, channel_id: str, video_id: str, video_details: Dict[str, Any]):
    """Post YouTube video published announcement to all subscribed guilds."""
    subscribed_guilds = await _get_subscribed_guilds_for_channel(bot, channel_id)

    if not subscribed_guilds:
        logger.info(f"No guilds subscribed to YouTube channel {channel_id}")
        return

    for guild, discord_channel, streamer_config, settings in subscribed_guilds:
        try:
            await _post_youtube_video_announcement_to_guild(
                guild, discord_channel, streamer_config, settings, video_details
            )
        except Exception as e:
            logger.error(f"Error posting YouTube video announcement to guild {guild.name}: {e}", exc_info=True)


async def _post_youtube_live_announcement_to_guild(
    guild, channel, streamer_config, settings, video_details
):
    """Post a YouTube live stream announcement to a specific guild."""
    try:
        # Extract video data
        channel_title = video_details.get('channel_title', 'Unknown Channel')
        video_title = video_details.get('title', 'Untitled Stream')
        video_id = video_details.get('video_id')
        video_url = video_details.get('url')
        thumbnail_url = video_details.get('thumbnail_url')
        viewer_count = video_details.get('viewer_count', 0)
        started_at = video_details.get('started_at')
        channel_id = video_details.get('channel_id')

        # Get announcement settings
        ann_settings = settings.get('announcement_settings', {})
        color_hex = ann_settings.get('youtube_color', '0xFF0000')
        color = int(color_hex.replace('0x', ''), 16) if isinstance(color_hex, str) else color_hex

        # Build embed
        embed_title = f"🔴 {channel_title} is live on YouTube!"
        markdown_link = f"[{video_title}]({video_url})"

        embed = discord.Embed(
            title=embed_title,
            description=f"### {markdown_link}",
            color=color
        )

        if ann_settings.get('include_thumbnail', True) and thumbnail_url:
            embed.set_image(url=thumbnail_url)

        if ann_settings.get('include_viewer_count', True):
            embed.add_field(name="Viewers", value=f"{viewer_count:,}", inline=False)

        if ann_settings.get('include_start_time', True) and started_at:
            discord_timestamp = _convert_to_discord_timestamp(started_at)
            embed.add_field(name="Started", value=discord_timestamp, inline=False)

        # Build content with pings and custom message
        content = _build_announcement_content_youtube(
            streamer_config, channel_title, video_title, viewer_count
        )

        # Send message
        message = await channel.send(content=content, embed=embed)

        # Store in database
        dao = StreamingAnnouncementDao()
        try:
            # Parse started_at timestamp
            if isinstance(started_at, str):
                try:
                    stream_started_dt = datetime.fromisoformat(started_at.replace('Z', '+00:00')).replace(tzinfo=None)
                except:
                    stream_started_dt = datetime.utcnow()
            else:
                stream_started_dt = started_at or datetime.utcnow()

            dao.create_announcement(
                platform='youtube',
                guild_id=guild.id,
                channel_id=channel.id,
                message_id=message.id,
                streamer_username=streamer_config.get('username', channel_title),
                streamer_id=channel_id,
                stream_id=video_id,
                stream_title=video_title,
                game_name=None,  # YouTube doesn't have game categories in the same way
                stream_started_at=stream_started_dt,
                initial_viewer_count=viewer_count
            )

            logger.info(f'Guild {guild.name}: Posted YouTube live announcement for {channel_title} (message {message.id})')
        finally:
            dao.close()

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error posting YouTube live announcement: {e}', exc_info=True)


async def _post_youtube_video_announcement_to_guild(
    guild, channel, streamer_config, settings, video_details
):
    """Post a YouTube video published announcement to a specific guild."""
    try:
        # Extract video data
        channel_title = video_details.get('channel_title', 'Unknown Channel')
        video_title = video_details.get('title', 'Untitled Video')
        video_id = video_details.get('video_id')
        video_url = video_details.get('url')
        thumbnail_url = video_details.get('thumbnail_url')
        published_at = video_details.get('published_at')
        view_count = video_details.get('view_count', 0)

        # Get announcement settings
        ann_settings = settings.get('announcement_settings', {})
        color_hex = ann_settings.get('youtube_color', '0xFF0000')
        color = int(color_hex.replace('0x', ''), 16) if isinstance(color_hex, str) else color_hex

        # Build embed
        embed_title = f"📹 {channel_title} uploaded a new video!"
        markdown_link = f"[{video_title}]({video_url})"

        embed = discord.Embed(
            title=embed_title,
            description=f"### {markdown_link}",
            color=color
        )

        if ann_settings.get('include_thumbnail', True) and thumbnail_url:
            embed.set_image(url=thumbnail_url)

        if published_at:
            discord_timestamp = _convert_to_discord_timestamp(published_at)
            embed.add_field(name="Published", value=discord_timestamp, inline=False)

        # Build content with pings and custom message
        content = _build_announcement_content_youtube(
            streamer_config, channel_title, video_title, view_count
        )

        # Send message
        await channel.send(content=content, embed=embed)

        logger.info(f'Guild {guild.name}: Posted YouTube video announcement for {channel_title}')

    except Exception as e:
        logger.error(f'Guild {guild.name}: Error posting YouTube video announcement: {e}', exc_info=True)


def _build_announcement_content_youtube(streamer_config, channel_title, video_title, viewer_count):
    """Builds the raw message content for YouTube announcements, handling pings and custom messages."""
    mention_parts = []

    # Check for the unified 'mention' field
    mention = streamer_config.get('mention', '').lower()
    if mention == 'everyone':
        mention_parts.append("@everyone")
    elif mention == 'here':
        mention_parts.append("@here")
    elif mention.startswith('<@&'):
        mention_parts.append(mention)
    # Support for the old role list field, if still used
    if streamer_config.get('mention_role_ids'):
        role_ids = streamer_config['mention_role_ids']
        if isinstance(role_ids, list):
            for role_id in role_ids:
                mention_parts.append(f"<@&{role_id}>")

    content_parts = []

    if mention_parts:
        content_parts.append(" ".join(mention_parts))

    # Add custom message if configured
    custom_message = streamer_config.get('custom_message')
    if custom_message:
        # Replace placeholders
        custom_message = custom_message.replace('{username}', channel_title)
        custom_message = custom_message.replace('{channel}', channel_title)
        custom_message = custom_message.replace('{title}', video_title)
        custom_message = custom_message.replace('{viewer_count}', str(viewer_count))
        content_parts.append(custom_message)

    return " ".join(content_parts) if content_parts else None


def _convert_to_discord_timestamp(dt_input: Any) -> str:
    """Convert timestamp to Discord Unix Timestamp format."""
    try:
        if isinstance(dt_input, str):
            # Handle ISO 8601 string input
            try:
                dt_obj = datetime.fromisoformat(dt_input.replace('Z', '+00:00'))
            except ValueError:
                dt_obj = datetime.strptime(dt_input.split('.')[0], "%Y-%m-%dT%H:%M:%S")
        elif isinstance(dt_input, datetime):
            dt_obj = dt_input
        else:
            return str(dt_input)

        dt_utc = dt_obj.replace(tzinfo=pytz.utc)
        unix_timestamp = int(dt_utc.timestamp())
        return f"<t:{unix_timestamp}:R>"
    except Exception:
        return str(dt_input)
