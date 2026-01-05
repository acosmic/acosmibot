"""
YouTube RSS Feed Polling Task

Polls YouTube RSS feeds every 5 minutes to detect new videos and live streams.
This is a reliable alternative to WebSub webhooks which are unreliable.

When a new video is detected:
1. Fetch video details from YouTube Data API (1 quota)
2. Check if it's live, upcoming, or a regular upload
3. Store event in YouTubeWebhookEvents table
4. process_youtube_events_task.py will process it and post to Discord

Benefits:
- No API quota for RSS polling (only for checking video details)
- Scales to thousands of channels
- ~5 minute detection time (half the poll interval on average)
- Works alongside WebSub (deduplication via UNIQUE constraint)
"""

import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from database import get_db_session
from Dao.YoutubeDao import YoutubeDao
from Services.youtube_service import YouTubeService

import logging
logger = logging.getLogger(__name__)


RSS_FEED_URL_TEMPLATE = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


async def start_task(bot):
    """
    Background task to poll YouTube RSS feeds for new videos.
    Runs every 5 minutes.
    """
    youtube_service = YouTubeService()

    while True:
        try:
            # Wait 5 minutes between polls
            await asyncio.sleep(300)  # 5 minutes = 300 seconds

            async with aiohttp.ClientSession() as http_session:
                async with get_db_session() as db_session:
                    youtube_dao = YoutubeDao(db_session)

                    # Get all unique channel IDs with active subscriptions
                    unique_channels = await youtube_dao.get_all_unique_subscribed_channels()

                    if not unique_channels:
                        logger.debug("No YouTube channels to poll.")
                        continue

                    logger.info(f"Polling {len(unique_channels)} YouTube channels for new videos...")

                    stats = {
                        'checked': 0,
                        'new_videos': 0,
                        'live_streams': 0,
                        'video_uploads': 0,
                        'upcoming': 0,
                        'errors': 0
                    }

                    # Poll each channel
                    for channel_id, channel_name in unique_channels:
                        try:
                            result = await poll_channel(
                                http_session,
                                youtube_dao,
                                youtube_service,
                                channel_id,
                                channel_name
                            )
                            stats['checked'] += 1

                            if result:
                                stats['new_videos'] += 1
                                if result['event_type'] == 'live_start':
                                    stats['live_streams'] += 1
                                elif result['event_type'] == 'upcoming':
                                    stats['upcoming'] += 1
                                elif result['event_type'] == 'video_published':
                                    stats['video_uploads'] += 1

                        except Exception as e:
                            logger.error(f"Error polling channel {channel_id}: {e}", exc_info=True)
                            stats['errors'] += 1
                            continue

                    if stats['new_videos'] > 0 or stats['errors'] > 0:
                        logger.info(f"RSS Poll complete: {stats}")

        except Exception as e:
            logger.error(f"Unhandled error in YouTube RSS polling task: {e}", exc_info=True)


async def poll_channel(
    http_session: aiohttp.ClientSession,
    youtube_dao: YoutubeDao,
    youtube_service: YouTubeService,
    channel_id: str,
    channel_name: str
) -> dict:
    """
    Poll a single channel's RSS feed.
    Returns dict with event info if new video found, None otherwise.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    }
    feed_url = RSS_FEED_URL_TEMPLATE.format(channel_id=channel_id)

    try:
        async with http_session.get(feed_url, timeout=10, headers=headers) as response:
            if response.status != 200:
                logger.warning(f"RSS feed returned {response.status} for channel {channel_id} ({channel_name})")
                return None

            feed_xml = await response.text()

    except asyncio.TimeoutError:
        logger.warning(f"RSS feed fetch timeout for channel {channel_id} ({channel_name})")
        return None
    except Exception as e:
        logger.error(f"Failed to fetch RSS feed for {channel_id} ({channel_name}): {e}")
        return None

    # Parse RSS feed
    try:
        root = ET.fromstring(feed_xml)
        atom_ns = '{http://www.w3.org/2005/Atom}'
        yt_ns = '{http://www.youtube.com/xml/schemas/2015}'

        # Get most recent entry (first entry in feed)
        entries = root.findall(f'.//{atom_ns}entry')
        if not entries:
            logger.debug(f"No entries in RSS feed for channel {channel_id} ({channel_name})")
            await youtube_dao.update_youtube_poll_tracking(channel_id, None, None)
            return None

        latest_entry = entries[0]

        # Extract video info
        video_id_el = latest_entry.find(f'.//{yt_ns}videoId')
        published_el = latest_entry.find(f'.//{atom_ns}published')

        if video_id_el is None or published_el is None:
            logger.warning(f"Missing video_id or published in RSS entry for {channel_id} ({channel_name})")
            return None

        video_id = video_id_el.text
        published_str = published_el.text
        published_at = datetime.fromisoformat(published_str.replace('Z', '+00:00'))

        # Check if this is a new video
        last_state = await youtube_dao.get_youtube_poll_tracking(channel_id)

        if last_state and last_state['last_video_id'] == video_id:
            # Not a new video, just update poll time
            await youtube_dao.update_youtube_poll_tracking(channel_id, video_id, published_at)
            return None

        # NEW VIDEO DETECTED!
        logger.info(f"🆕 New video detected for channel {channel_id} ({channel_name}): {video_id}")

        # Check if video is live using YouTube Data API (costs 1 quota)
        video_details = await youtube_service.get_video_details(http_session, video_id)

        if not video_details:
            logger.warning(f"Could not fetch details for new video {video_id}")
            await youtube_dao.update_youtube_poll_tracking(channel_id, video_id, published_at)
            return None

        is_live = video_details.get('is_live', False)
        is_upcoming = video_details.get('is_upcoming', False)

        # Determine event type
        if is_live:
            event_type = 'live_start'
            logger.info(f"🔴 LIVE stream detected: {video_details.get('title')} ({video_id})")
        elif is_upcoming:
            event_type = 'upcoming'
            logger.info(f"⏰ Upcoming stream detected: {video_details.get('title')} ({video_id})")
        else:
            event_type = 'video_published'
            logger.info(f"📹 Video upload detected: {video_details.get('title')} ({video_id})")

        # Create event in database
        event_id = f"{channel_id}-{video_id}-rss-{datetime.now(timezone.utc).isoformat()}"

        payload_data = {
            "title": video_details.get('title', 'N/A'),
            "url": video_details.get('url', f"https://www.youtube.com/watch?v={video_id}"),
            "thumbnail_url": video_details.get('thumbnail_url'),
            "published_at": video_details.get('published_at'),
            "started_at": video_details.get('started_at'),
            "scheduled_start": video_details.get('scheduled_start'),
            "viewer_count": video_details.get('viewer_count', 0),
            "view_count": video_details.get('view_count', 0),
            "channel_title": video_details.get('channel_title'),
            "description": video_details.get('description', ''),
            "source": "rss_poll"  # Mark source as RSS polling
        }

        try:
            await youtube_dao.add_youtube_webhook_event(
                event_id=event_id,
                channel_id=channel_id,
                video_id=video_id,
                event_type=event_type,
                payload=payload_data
            )
            logger.info(f"✅ Stored {event_type} event for {video_id}")

        except IntegrityError:
            logger.debug(f"Duplicate event for {video_id} (already processed by WebSub?)")

        # Update poll tracking
        await youtube_dao.update_youtube_poll_tracking(channel_id, video_id, published_at)

        return {
            'video_id': video_id,
            'event_type': event_type,
            'is_live': is_live,
            'is_upcoming': is_upcoming
        }

    except ET.ParseError as e:
        logger.error(f"Failed to parse RSS XML for {channel_id} ({channel_name}): {e}")
        return None
