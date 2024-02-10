#! /usr/bin/python3.8

import random
from urllib import parse, request
import json
import asyncio
import discord
from discord.app_commands.tree import CommandTree
from discord.ext import commands
from datetime import datetime
import logging
from dotenv import load_dotenv
import os



from Cogs.Give import Give

load_dotenv()
db_host = os.getenv('db_host')
db_user = os.getenv('db_user')
db_password = os.getenv('db_password')
db_name = os.getenv('db_name')
GIPHY_KEY = os.getenv('GIPHY_KEY')

client_id = os.getenv('client_id')
client_secret =  os.getenv('client_secret')

MY_GUILD = discord.Object(id=int(os.getenv('MY_GUILD')))
TOKEN = os.getenv('TOKEN')

logging.basicConfig(filename='/root/dev/acosmicord-bot/logs.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Bot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix =commands.when_mentioned_or('!'),intents=discord.Intents().all())
        self.cogslist = [
            "Cogs.Balance",
            "Cogs.Rank",
            "Cogs.Give",
            "Cogs.Check_Vault",
            "Cogs.Eightball",
            "Cogs.Polymorph",
            "Cogs.Coinflip",
            "Cogs.Rock_Paper_Scissors",
            "Cogs.Leaderboard",
            "Cogs.On_Message",
            "Cogs.On_Reaction",
            "Cogs.On_Member_Join",
            "Cogs.Reset_RPS",
            "Cogs.Burn",
        ]
        self.setup_hook()
    
    async def setup_hook(self):
        self.bg_task = self.loop.create_task(self.bg_task())
        for ext in self.cogslist:
            await self.load_extension(ext)

    async def on_ready(self):
        logging.info(f'Logged on as {bot.user}!')
        synced = await self.tree.sync()
        logging.info(f"slash cmd's synced: {str(len(synced))}")

    async def bg_task(self):
        await self.wait_until_ready()
        channel = self.get_channel(1155577095787917384) # channel ID goes here
        while not self.is_closed():
            logging.info('bg_task running')
            if datetime.now().hour == 8 and datetime.now().minute == 0:
                pass
                logging.info('bg_task running at 8:00am')
                
                
                try:
                    gif = self.giphy_search('goodmorning')
                    logging.info(f'gif: {gif}')
                    await channel.send(gif)
                except Exception as e:
                    logging.error(f'bg_task error: {e}')
            await asyncio.sleep(60)

    def giphy_search(self, search_term):
        api_url = f"https://api.giphy.com/v1/gifs/search?api_key={GIPHY_KEY}&q={search_term}&limit=20&offset=0&rating=pg-13&lang=en"
        random_number = random.randint(0, 19)
        with request.urlopen(api_url) as response:
            data = json.loads(response.read())
            return data['data'][random_number]['url']

bot = Bot()

if __name__ == "__main__":
    bot.run(TOKEN)