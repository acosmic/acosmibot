#! /usr/bin/python3.8
from hmac import new
import random
from urllib import parse, request
import json
import asyncio
import discord
from discord.ext import commands
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
import os
from Entities.LotteryParticipant import LotteryParticipant
from Entities.LotteryEvent import LotteryEvent
from Dao.LotteryParticipantDao import LotteryParticipantDao
from Dao.LotteryEventDao import LotteryEventDao
from Dao.UserDao import UserDao
from Dao.VaultDao import VaultDao

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
            "Cogs.Weather",
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
        self.bg_task_lottery = self.loop.create_task(self.bg_task_lottery())
        self.bg_task_lottery_end = self.loop.create_task(self.bg_task_lottery_end())
        for ext in self.cogslist:
            await self.load_extension(ext)

    async def on_ready(self):
        logging.info(f'Logged on as {bot.user}!')
        synced = await self.tree.sync()
        logging.info(f"slash cmd's synced: {str(len(synced))}")

    async def bg_task(self): # good morning gif
        await self.wait_until_ready()
        channel = self.get_channel(1155577095787917384) # general channel id 1155577095787917384
        while not self.is_closed():
            logging.info('bg_task running')
            if datetime.now().hour == 7 and datetime.now().minute == 50:
                pass
                logging.info('bg_task running at 7:50am')
                
                
                try:
                    gif = self.giphy_search('goodmorning')
                    logging.info(f'gif: {gif}')
                    await channel.send(gif)
                except Exception as e:
                    logging.error(f'bg_task error: {e}')
            await asyncio.sleep(60)

    async def bg_task_lottery(self):
        await self.wait_until_ready()
        channel = self.get_channel(1155577095787917384) # general channel id 1155577095787917384
        # channel = self.get_channel(1186805143296020520) # bot-testing channel id 1186805143296020520
        while not self.is_closed():
            logging.info('bg_task_lottery running')
            if datetime.now().weekday() == 0 and datetime.now().hour == 8:
                logging.info('bg_task_lottery running at 8:00am on Monday')
                try:
                
                    le_dao = LotteryEventDao()
                    vdao = VaultDao()
                    vault_credits = vdao.get_currency()
                    
                    await channel.send(f'React with 🎟️ to enter the lottery! There is currently {vault_credits} in the Vault.\nThe winner will be announced in 4 hours! <a:pepesith:1165101386921418792>')

                    ### GIF POST ###
                    # gif = self.giphy_search('join-us')
                    # logging.info(f'gif: {gif}')
                    # message = await channel.send(gif)

                    message = await channel.send("https://cdn.discordapp.com/attachments/1207159417980588052/1207159812656472104/acosmibot-lottery.png?ex=65dea22f&is=65cc2d2f&hm=3a9e07cf1b55f87a1fcd664c766f11636bf55f305b715e0269851f18d154fd23&")
                    
                    await message.add_reaction('🎟️')
                    end_time = datetime.now() + timedelta(hours=4)
                    new_le = LotteryEvent(0, message.id, datetime.now(), end_time, 0, 0)
                    
                    await message.pin()
                    
                    le_dao.add_new_event(new_le)
                except Exception as e:
                    logging.error(f'bg_task_lottery error: {e}')
            await asyncio.sleep(3600)

    async def bg_task_lottery_end(self):
        await self.wait_until_ready()
        channel = self.get_channel(1155577095787917384)
        # channel = self.get_channel(1186805143296020520) # bot-testing channel id 1186805143296020520
        
        while not self.is_closed():
            logging.info('bg_task_lottery_end running')
            if datetime.now().weekday() == 0 and datetime.now().hour == 12:
                logging.info('bg_task_lottery_end running at 12:00pm on Monday')
                try:
                    vdao = VaultDao()
                    lottery_credits = vdao.get_currency()
                    le_dao = LotteryEventDao()
                    lp_dao = LotteryParticipantDao()
                    userDao = UserDao()
                    current_lottery = le_dao.get_current_event()
                    participants = lp_dao.get_participants(current_lottery.message_id)
                    winner = random.choice(participants)
                    user = userDao.get_user(winner.participant_id)
                    discord_user = channel.guild.get_member(winner.participant_id)
                    logging.info(f'winner: {user.discord_username}')
                    await channel.send(f'Congratulations to {discord_user.mention} for winning {lottery_credits} Credits in the lottery! <a:pepesith:1165101386921418792>')
                    current_lottery.winner_id = winner.participant_id
                    current_lottery.end_time = datetime.now()
                    current_lottery.credits = lottery_credits
                    le_dao.update_event(current_lottery)
                    user.currency += lottery_credits
                    userDao.update_user(user)
                    vdao.update_currency(0)
                    message = await channel.fetch_message(current_lottery.message_id)
                    await message.unpin()
                    await message.delete()
                    logging.info(f'winner: {user.discord_username} won {lottery_credits} Credits and updated to db')
                except Exception as e:
                    logging.error(f'bg_task_lottery_end error: {e}')
            await asyncio.sleep(3600)
                

    def giphy_search(self, search_term):
        api_url = f"https://api.giphy.com/v1/gifs/search?api_key={GIPHY_KEY}&q={search_term}&limit=20&offset=0&rating=pg-13&lang=en"
        random_number = random.randint(0, 19)
        with request.urlopen(api_url) as response:
            data = json.loads(response.read())
            return data['data'][random_number]['url']

bot = Bot()

if __name__ == "__main__":
    bot.run(TOKEN)