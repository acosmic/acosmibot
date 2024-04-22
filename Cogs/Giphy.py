import discord
from discord.ext import commands
from discord import app_commands
from logger import AppLogger
import json
import random
from dotenv import load_dotenv
from urllib import parse, request
import os

logger = AppLogger(__name__).get_logger()

load_dotenv()
GIPHY_KEY = os.getenv('GIPHY_KEY')

class Giphy(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    @app_commands.command(name="giphy", description="Returns a random Gif from Giphy based on the search term provided. Example: /giphy cat")
    async def giphy(self, interaction: discord.Interaction, search_term: str):
        logger.info(f"{interaction.user.name} used /gify command with search_term: {search_term}")
        formatted_search_term = search_term.replace(" ", "-")
        await interaction.response.send_message(giphy_search(formatted_search_term))

def giphy_search(search_term):
    api_url = f"https://api.giphy.com/v1/gifs/search?api_key={GIPHY_KEY}&q={search_term}&limit=20&offset=0&rating=pg-13&lang=en"
    with request.urlopen(api_url) as response:
        data = json.loads(response.read())
        results_count = len(data['data'])
        if results_count == 0:
            return "No results found."
        random_number = random.randint(0, results_count - 1)  # Adjust random_number based on actual results count
        return data['data'][random_number]['url']

async def setup(bot: commands.Bot):
    await bot.add_cog(Giphy(bot))