#! /usr/bin/python3.8

from curses.ascii import US
import discord
from discord.app_commands.tree import CommandTree
from discord.ext import commands
from Dao.UserDao import UserDao
from Entities.User import User
from datetime import datetime
import logging
from dotenv import load_dotenv
import os

load_dotenv()
db_host = os.getenv('db_host')
db_user = os.getenv('db_user')
db_password = os.getenv('db_password')
db_name = os.getenv('db_name')

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
            "Cogs.Eightball",
            "Cogs.Polymorph",
            "Cogs.Coinflip",
            "Cogs.Leaderboard",
            "Cogs.On_Message",
            "Cogs.On_Reaction",
            "Cogs.On_Member_Join",
            
        ]
    
    async def setup_hook(self):
        for ext in self.cogslist:
            await self.load_extension(ext)

    async def on_ready(self):
        logging.info(f'Logged on as {bot.user}!')
        synced = await self.tree.sync()
        logging.info(f"slash cmd's synced: {str(len(synced))}")

bot = Bot()
bot.setup_hook()

if __name__ == "__main__":
    bot.run(TOKEN)