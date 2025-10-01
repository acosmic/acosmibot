#! /usr/bin/python3.10
import sys
import discord
from discord.ext import commands
from logger import AppLogger
from dotenv import load_dotenv
import os

from Dao.InviteDao import InviteDao
from Tasks.task_manager import register_tasks


load_dotenv()
# GIPHY_KEY = os.getenv('GIPHY_KEY')
TOKEN = os.getenv('TOKEN')

logger = AppLogger(__name__).get_logger()


class Bot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix =commands.when_mentioned_or('!'),intents=discord.Intents().all())
        self.cogslist = [
            "Cogs.Admin_Start_Lotto",
            "Cogs.RipAudio",
            "Cogs.ReminderCommand",
            # "Cogs.RPG",
            # "Cogs.Admin_Jail",
            # "Cogs.Admin_Jail_Release",
            "Cogs.Admin_Stats",
            # "Cogs.DeleteAiThread",
            "Cogs.Slots",
            # "Cogs.Reset_AI_Thread",
            # "Cogs.Reset_Season",
            # "Cogs.Reset_Daily",
            # "Cogs.Roll_Dice",
            # "Cogs.Bailout",
            # "Cogs.Jail_Message",
            "Cogs.Admin_Give",
            # "Cogs.Color", # fix this soon
            "Cogs.Giphy",
            "Cogs.Deathroll",
            "Cogs.Dictionary",
            "Cogs.Ping",
            "Cogs.Help",
            "Cogs.Nasa",
            "Cogs.Weather",
            "Cogs.Balance",
            "Cogs.Rank",
            "Cogs.Stats",
            "Cogs.Give",
            "Cogs.Check_Bank",
            "Cogs.Eightball",
            "Cogs.Polymorph",
            "Cogs.Coinflip",
            "Cogs.Rock_Paper_Scissors", # fix soon
            "Cogs.Leaderboard",
            "Cogs.Reset_RPS",
            # "Cogs.Burn",
            "Cogs.LevelingListener",
            "Cogs.On_Message",
            "Cogs.On_Reaction",
            "Cogs.On_Member_Join",
            "Cogs.On_Raw_Member_Remove",
            "Cogs.On_Guild_Join",
            "Cogs.AIControls"
        ]
        self.posted = False

    async def on_command_error(self, ctx, error):
        """Handle command errors globally"""
        # Suppress CommandNotFound errors (these happen when someone mentions the bot with non-commands)
        if isinstance(error, commands.CommandNotFound):
            # Don't log these errors since they're expected when using AI chat
            return

        # Log other errors normally
        logger.error(f"Command error in {ctx.guild.name if ctx.guild else 'DM'}: {error}")

    async def setup_hook(self):
        register_tasks(self)
        for ext in self.cogslist:
            if ext not in self.extensions:
                await self.load_extension(ext)
                logger.info(f'{ext} loaded')

    async def on_ready(self):
        logger.info(f'Logged on as {bot.user}!')
        synced = await self.tree.sync()
        logger.info(f"slash cmd's synced: {str(len(synced))}")
        logger.info(f"discord.py version: {discord.__version__}")
        logger.info(f"python version: {str(sys.version)}")
        # Create Tables - Need to add all tables here to create on bot start
        invDao = InviteDao()
        invDao.create_table()

        await self.setup_hook()
        await self.change_presence(activity=discord.CustomActivity('/help for commands!'))


    # def giphy_search(self, search_term):
    #     api_url = f"https://api.giphy.com/v1/gifs/search?api_key={GIPHY_KEY}&q={search_term}&limit=20&offset=0&rating=pg-13&lang=en"
    #     with request.urlopen(api_url) as response:
    #         data = json.loads(response.read())
    #         results_count = len(data['data'])
    #         if results_count == 0:
    #             return "No results found."
    #         random_number = random.randint(0, results_count - 1)  # Adjust random_number based on actual results count
    #         return data['data'][random_number]['url']
    

bot = Bot()

if __name__ == "__main__":
    bot.run(TOKEN)
