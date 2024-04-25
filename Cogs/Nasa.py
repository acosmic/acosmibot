import discord
from discord.ext import commands
from discord import app_commands
from logger import AppLogger
import requests
from bs4 import BeautifulSoup
from datetime import datetime

logger = AppLogger(__name__).get_logger()

class Nasa(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.URL = "https://apod.nasa.gov/apod/astropix.html"

    @app_commands.command(name="apod", description="Returns the Astronomy Picture of the Day.")
    async def apod(self, interaction: discord.Interaction):
        logger.info(f"{interaction.user.name} used /apod - before try block.")
        try:
            response = requests.get(self.URL)
            if response.status_code != 200:
                logger.error(f"Failed to fetch APOD: HTTP {response.status_code}")
                await interaction.response.send_message("Failed to fetch APOD, please try again later.", ephemeral=True)
                return

            soup = BeautifulSoup(response.text, 'html.parser')
            # Check for image or video content
            media_tag = soup.find('iframe') or soup.find('img')
            if not media_tag:
                logger.error("No media found on APOD page.")
                await interaction.response.send_message("No APOD media found today.")
                return

            if media_tag.name == 'iframe':  # It's a video
                media_link = media_tag['src']
                media_type = "a Video"
            else:  # It's an image
                media_link = f"https://apod.nasa.gov/apod/{media_tag['src']}"
                media_type = "an Image"

            embed = discord.Embed(title="Astronomy Picture of the Day", description=f"Today's APOD is {media_type}.", color=interaction.user.color)
            if media_type == "an Image":
                
                embed.set_image(url=media_link)
            else:
                embed.add_field(name="Watch Video", value=f"[Click here to watch the video]({media_link})")
                # embed.set_image(url=media_link)
            embed.set_footer(text="Source: NASA APOD")

            await interaction.response.send_message(embed=embed)
            logger.info(f"{interaction.user.name} successfully received APOD data.")
        except Exception as e:
            logger.error(f"An error occurred while fetching the Astronomy Picture of the Day: {e}")
            await interaction.response.send_message("An error occurred while fetching the APOD. Please try again later.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Nasa(bot))