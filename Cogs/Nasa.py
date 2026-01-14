import discord
from discord.ext import commands
from discord import app_commands
from logger import AppLogger
import aiohttp
from bs4 import BeautifulSoup
import io
from datetime import datetime
import hashlib

logger = AppLogger(__name__).get_logger()


class Nasa(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.URL = "https://apod.nasa.gov/apod/astropix.html"

        # Cache for APOD data
        self.apod_cache = {
            'date': None,  # Date when cached
            'title': None,  # APOD title
            'media_link': None,  # Image/video URL
            'is_video': False,  # Whether it's a video
            'image_data': None,  # Downloaded image bytes
            'filename': None  # Image filename
        }

    def get_today_date(self):
        """Get today's date as a string for cache comparison"""
        return datetime.now().strftime("%Y-%m-%d")

    def is_cache_valid(self):
        """Check if the current cache is still valid for today"""
        return self.apod_cache['date'] == self.get_today_date()

    def clear_cache(self):
        """Clear the cache data"""
        self.apod_cache = {
            'date': None,
            'title': None,
            'media_link': None,
            'is_video': False,
            'image_data': None,
            'filename': None
        }

    @app_commands.command(name="apod", description="Returns the Astronomy Picture of the Day.")
    async def apod(self, interaction: discord.Interaction):
        logger.info(f"{interaction.user.name} used /apod - before try block.")

        # DEFER THE INTERACTION IMMEDIATELY
        await interaction.response.defer()

        # Debug logging
        logger.info(f"Cache date: {self.apod_cache['date']}, Today: {self.get_today_date()}")
        logger.info(f"Cache valid: {self.is_cache_valid()}")

        # Check if we have valid cached data
        if self.is_cache_valid():
            logger.info("Using cached APOD data")
            await self.send_cached_apod(interaction)
            return

        # Cache is invalid, fetch new data
        logger.info("Cache invalid or empty, fetching new APOD data")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.URL) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch APOD: HTTP {response.status}")
                        await interaction.followup.send("Failed to fetch APOD, please try again later.", ephemeral=True)
                        return

                    html_content = await response.text()

            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract the title
            title_tag = soup.find('b')
            if title_tag:
                title = title_tag.get_text().strip()
            else:
                title = "Astronomy Picture of the Day"

            # Check for image or video content
            media_tag = soup.find('iframe') or soup.find('img')
            if not media_tag:
                logger.error("No media found on APOD page.")
                await interaction.followup.send("No APOD media found today.")
                return

            # Update cache with basic info
            self.apod_cache['date'] = self.get_today_date()
            self.apod_cache['title'] = title

            if media_tag.name == 'iframe':  # It's a video
                media_link = media_tag['src']
                # Handle relative URLs for videos
                if not media_link.startswith('http'):
                    media_link = f"https:{media_link}" if media_link.startswith(
                        '//') else f"https://apod.nasa.gov/apod/{media_link}"

                self.apod_cache['media_link'] = media_link
                self.apod_cache['is_video'] = True

                description = f"Click [here]({self.URL}) to view today's APOD."
                embed = discord.Embed(title=title, description=description, color=interaction.user.color)
                embed.add_field(name="🎥 Watch Video", value=f"[Click here to watch the video]({media_link})",
                                inline=False)
                embed.set_footer(text="Source: NASA APOD")

                await interaction.followup.send(embed=embed)
                logger.info(f"{interaction.user.name} successfully received APOD video data.")

            else:  # It's an image
                await self.handle_image_apod(interaction, media_tag, title)

        except Exception as e:
            logger.error(f"An error occurred while fetching the Astronomy Picture of the Day: {e}")
            await interaction.followup.send(
                "An error occurred while fetching the APOD. Please try again later.", ephemeral=True)

    async def handle_image_apod(self, interaction, media_tag, title):
        """Handle image APOD with caching"""
        img_src = media_tag.get('src')
        if not img_src:
            logger.error("Image source not found")
            await interaction.followup.send("Image source not found for today's APOD.")
            return

        # Handle relative URLs
        if img_src.startswith('http'):
            media_link = img_src
        else:
            media_link = f"https://apod.nasa.gov/apod/{img_src}"

        logger.info(f"Image URL: {media_link}")
        self.apod_cache['media_link'] = media_link
        self.apod_cache['is_video'] = False

        # Download and cache the image
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(media_link, timeout=aiohttp.ClientTimeout(total=30)) as img_response:
                    if img_response.status != 200:
                        logger.error(f"Failed to download image: HTTP {img_response.status}")
                        raise Exception(f"Image download failed: {img_response.status}")

                    image_content = await img_response.read()

            # Check file size (Discord limit is 25MB for files)
            file_size_mb = len(image_content) / (1024 * 1024)
            logger.info(f"Downloaded image size: {file_size_mb:.2f} MB")

            if len(image_content) > 25 * 1024 * 1024:  # 25MB limit
                logger.error(f"Image too large: {file_size_mb:.2f} MB")
                raise Exception(f"Image too large: {file_size_mb:.2f} MB")

            # Get filename from URL or create one
            filename = media_link.split('/')[-1]
            if '?' in filename:
                filename = filename.split('?')[0]
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                filename += '.jpg'

            # Cache the image data
            self.apod_cache['image_data'] = image_content
            self.apod_cache['filename'] = filename

            # Create and send the embed with image
            await self.send_image_embed(interaction, title, filename, image_content)
            logger.info(
                f"{interaction.user.name} successfully received APOD with downloaded image (cached for future use).")

        except aiohttp.ClientError as e:
            logger.error(f"Failed to download image: {e}")
            await self.send_fallback_embed(interaction, title, media_link)

        except Exception as e:
            logger.error(f"Error processing downloaded image: {e}")
            await self.send_fallback_embed(interaction, title, media_link)

    async def send_cached_apod(self, interaction):
        """Send APOD using cached data"""
        title = self.apod_cache['title']

        if self.apod_cache['is_video']:
            # Send cached video
            media_link = self.apod_cache['media_link']
            description = f"Click [here]({self.URL}) to view today's APOD."
            embed = discord.Embed(title=title, description=description, color=interaction.user.color)
            embed.add_field(name="🎥 Watch Video", value=f"[Click here to watch the video]({media_link})", inline=False)
            embed.set_footer(text="Source: NASA APOD")
            await interaction.followup.send(embed=embed)
        else:
            # Send cached image
            filename = self.apod_cache['filename']
            image_data = self.apod_cache['image_data']

            if image_data and filename:
                await self.send_image_embed(interaction, title, filename, image_data)
            else:
                # Fallback if cached image data is missing
                media_link = self.apod_cache['media_link']
                await self.send_fallback_embed(interaction, title, media_link)

        logger.info(f"{interaction.user.name} successfully received cached APOD data.")

    async def send_image_embed(self, interaction, title, filename, image_data):
        """Send embed with image attachment"""
        file = discord.File(
            fp=io.BytesIO(image_data),
            filename=filename
        )

        description = f"Click [here]({self.URL}) to view today's APOD page."
        embed = discord.Embed(title=title, description=description, color=interaction.user.color)
        embed.set_image(url=f"attachment://{filename}")
        embed.set_footer(text="Source: NASA APOD")

        await interaction.followup.send(embed=embed, file=file)

    async def send_fallback_embed(self, interaction, title, media_link):
        """Send fallback embed with links only"""
        description = f"Click [here]({self.URL}) to view today's APOD.\n\n[Direct Image Link]({media_link})"
        embed = discord.Embed(title=title, description=description, color=interaction.user.color)
        embed.add_field(name="🖼️ Today's Image", value=f"[View Image]({media_link})", inline=False)
        embed.set_footer(text="Source: NASA APOD")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Nasa(bot))