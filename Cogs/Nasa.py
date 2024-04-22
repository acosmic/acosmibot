# from math import log
# import discord
# from discord.ext import commands
# from discord import app_commands
# import logging
# import requests
# from dotenv import load_dotenv
# import os
# from datetime import datetime

# logging.basicConfig(filename='/home/acosmic/Dev/acosmibot/logs.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# class Nasa(commands.Cog):
#     def __init__(self, bot:commands.Bot):
#         super().__init__()
#         self.bot = bot
#         load_dotenv()
#         self.URL = f"https://apod.nasa.gov/apod/"
        

#     @app_commands.command(name = "apod", description = "Returns the Astronomy Picture of the Day.")
#     async def apod(self, interaction: discord.Interaction):
        
#         logging.info(f"{interaction.user.name} used /nasa - before try block.")
#         try:

#             # Get today's date
#             today = datetime.today()

#             # Format the date as YY MM DD
#             date_formatted = today.strftime("%y%m%d")

#             response = requests.get(self.URL)
#             data = response.text
#             # logging.info(data)

#             # Find the start index of the image source
#             start_index = data.find('IMG SRC="') + len('IMG SRC="')
#             logging.info(f"start_index: {start_index}")

#             # Find the end index of the image source
#             end_index = data.find('"', start_index)
#             logging.info(f"end_index: {end_index}")

#             # Extract the image link
#             image_link = data[start_index:end_index]
#             logging.info(f"image_link: {image_link}")
#             apod_image = f"{self.URL}{image_link}"
#             logging.info(f"apod_image: {apod_image}")

#             post_url = f"https://apod.nasa.gov/apod/ap{date_formatted}.html"
#             # Extract the title and explanation
#             title = data.split('<b>')[1].split('</b>')[0]
#             # explanation = data.split('<p>')[1].split('</p>')[0]
#             embed = discord.Embed(title="Astronomy Picture of the Day", color=interaction.user.color)
#             embed.add_field(name=title, value="", inline=False)
#             # embed.add_field(name="Explanation", value=explanation, inline=False)
#             embed.set_image(url=apod_image)
#             embed.add_field(name="", value=f"[Source: NASA APOD]({post_url}])", inline=False)
            
#             await interaction.response.send_message(embed=embed)
#             logging.info(f"{interaction.user.name} used /nasa")
#         except Exception as e:
#             logging.error(f"date_formatted: {date_formatted}")
#             logging.error(f"today: {today}")
#             logging.error(f"post_url: {post_url}")
#             logging.error(f"An error occurred while fetching the Astronomy Picture of the Day: {e}")

# async def setup(bot: commands.Bot):
#     await bot.add_cog(Nasa(bot))


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
            if media_type == "Image":
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