import discord
from discord.ext import commands
from discord import app_commands
import logging
import requests
from dotenv import load_dotenv
import os
from datetime import datetime

logging.basicConfig(filename='/root/dev/acosmicord-bot/logs.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Nasa(commands.Cog):
    def __init__(self, bot:commands.Bot):
        super().__init__()
        self.bot = bot
        load_dotenv()
        # self.NASA_KEY = os.getenv('NASA_KEY')
        # self.URL = f"https://api.nasa.gov/planetary/apod?api_key={self.NASA_KEY}"
        self.URL = f"https://apod.nasa.gov/apod/"
        

    @app_commands.command(name = "apod", description = "Returns the Astronomy Picture of the Day.")
    async def apod(self, interaction: discord.Interaction):
        
        logging.info(f"{interaction.user.name} used /nasa - before try block.")
        try:

            # Get today's date
            today = datetime.today()

            # Format the date as YY MM DD
            date_formatted = today.strftime("%y%m%d")

            response = requests.get(self.URL)
            data = response.text
            # logging.info(data)

            # Find the start index of the image source
            start_index = data.find('IMG SRC="') + len('IMG SRC="')
            logging.info(start_index)

            # Find the end index of the image source
            end_index = data.find('"', start_index)
            logging.info(end_index)

            # Extract the image link
            image_link = data[start_index:end_index]
            logging.info(image_link)
            apod_image = f"{self.URL}{image_link}"
            logging.info(apod_image)


            title = data.split('<b>')[1].split('</b>')[0]
            # explanation = data.split('<p>')[1].split('</p>')[0]
            embed = discord.Embed(title="Astronomy Picture of the Day", color=interaction.user.color)
            embed.add_field(name=title, value="", inline=False)
            # embed.add_field(name="Explanation", value=explanation, inline=False)
            embed.set_image(url=apod_image)
            embed.add_field(name="", value=f"[Source: NASA APOD](https://apod.nasa.gov/apod/ap{date_formatted}.html)", inline=False)
            
            await interaction.response.send_message(embed=embed)
            logging.info(f"{interaction.user.name} used /nasa")
        except Exception as e:
            logging.error(f"An error occurred while fetching the Astronomy Picture of the Day: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Nasa(bot))