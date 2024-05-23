#! /usr/bin/python3.10
import random
import json
import asyncio
from urllib import request
import discord
from discord.ext import commands
from datetime import datetime, timedelta
from logger import AppLogger
from dotenv import load_dotenv
import os
import pytz

from Twitch import Twitch
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
TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')

logger = AppLogger(__name__).get_logger()




class Bot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix =commands.when_mentioned_or('!'),intents=discord.Intents().all())
        self.cogslist = [
            "Cogs.Reset_Daily",
            "Cogs.Roll_Dice",
            "Cogs.Bailout",
            "Cogs.Jail_Message",
            "Cogs.Admin_Give",
            "Cogs.Color",
            "Cogs.Giphy",
            "Cogs.Deathroll",
            "Cogs.Dictionary",
            "Cogs.Ping",
            "Cogs.Help",
            "Cogs.Nasa",
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
            "Cogs.Reset_RPS",
            "Cogs.Burn",
            "Cogs.On_Message",
            "Cogs.On_Reaction",
            "Cogs.On_Member_Join",
        ]
        self.setup_hook()

        self.posted = False
        
    
    async def setup_hook(self):
        self.gm_na_task = self.loop.create_task(self.gm_na_task())
        self.gm_eu_task = self.loop.create_task(self.gm_eu_task())
        self.bg_task_lottery = self.loop.create_task(self.bg_task_lottery())
        self.bg_task_lottery_end = self.loop.create_task(self.bg_task_lottery_end())
        self.check_if_live_task = self.loop.create_task(self.check_if_live_task())
        for ext in self.cogslist:
            await self.load_extension(ext)
        
    async def on_ready(self):
        logger.info(f'Logged on as {bot.user}!')
        synced = await self.tree.sync()
        logger.info(f"slash cmd's synced: {str(len(synced))}")
        await self.change_presence(activity=discord.CustomActivity('/help for commands!'))

    async def gm_na_task(self): # good morning gif
        await self.wait_until_ready()
        channel = self.get_channel(1155577095787917384) # general channel id 1155577095787917384
        search_term = 'goodmorning-' + datetime.now().strftime('%A').lower()   
        logger.info(f'goodmorning gif search_term: {search_term}')
        while not self.is_closed():
            
            logger.info('gm_na_task running')
            if datetime.now().hour == 7 and datetime.now().minute == 50:
                search_term = 'goodmorning-' + datetime.now().strftime('%A').lower()
                logger.info('gm_na_task running at 7:50am')
                
                try:
                    gif = self.giphy_search(search_term)
                    logger.info(f'search_term:')
                    await channel.send(gif)
                except Exception as e:
                    logger.error(f'gm_na_task error: {e}')
            await asyncio.sleep(60)

    async def gm_eu_task(self): # good morning gif
        await self.wait_until_ready()
        channel = self.get_channel(1155577095787917384)
        # search_term = 'goodmorning-' + datetime.now().strftime('%A').lower()
        search_term = 'milk-morning'
        logger.info(f'goodmorning gif search_term: {search_term}')
        while not self.is_closed():
            logger.info('gm_eu_task running')
            if datetime.now().hour == 2 and datetime.now().minute == 50:
                logger.info('gm_eu_task running at 2:50am which is 7:50am in EU')
                try:
                    gif = self.giphy_search(search_term)
                    logger.info(f'search_term: {search_term} gif: {gif}')
                    await channel.send(gif)
                    dao = UserDao()
                    dao.reset_daily()
                                        
                    today = datetime.now().date()
                    for member in channel.guild.members:
                        current_user = dao.get_user(member.id)
                        if current_user.last_daily is not None:
                            last_daily_date = datetime.strptime(str(current_user.last_daily), "%Y-%m-%d %H:%M:%S").date()
                            if last_daily_date < today - timedelta(days=1):
                                if current_user.streak > 0:
                                    dao.reset_streak(current_user.id)
                                    logger.info(f'{current_user.discord_username} streak reset')
                    
                except Exception as e:
                    logger.error(f'gm_eu_task error: {e}')
                logger.info("DAILY RESET FOR ALL USERS")
            await asyncio.sleep(60)

    async def bg_task_lottery(self):
        await self.wait_until_ready()
        channel = self.get_channel(1155577095787917384) # general channel id 1155577095787917384
        # channel = self.get_channel(1186805143296020520) # bot-testing channel id 1186805143296020520
        while not self.is_closed():
            logger.info('bg_task_lottery running')
            if datetime.now().weekday() == 0 and datetime.now().hour == 8 and datetime.now().minute == 0:
                logger.info('bg_task_lottery running at 8:00am on Monday')
                try:
                
                    le_dao = LotteryEventDao()
                    # current_lottery = le_dao.get_current_event()
                    vdao = VaultDao()
                    vault_credits = vdao.get_currency()
                    
                    await channel.send(f'# React with 🎟️ to enter the lottery! There is currently {vault_credits:,.0f} Credits in the Vault.\nThe winner will be announced in 4 hours! <a:pepesith:1165101386921418792>')

                    message = await channel.send("https://cdn.discordapp.com/attachments/1207159417980588052/1207159812656472104/acosmibot-lottery.png?ex=65dea22f&is=65cc2d2f&hm=3a9e07cf1b55f87a1fcd664c766f11636bf55f305b715e0269851f18d154fd23&")
                    
                    await message.add_reaction('🎟️')
                    end_time = datetime.now() + timedelta(hours=4, minutes=5)
                    new_le = LotteryEvent(0, message.id, datetime.now(), end_time, 0, 0)
                    
                    await message.pin()
                    
                    le_dao.add_new_event(new_le)
                except Exception as e:
                    logger.error(f'bg_task_lottery error: {e}')
            
            elif datetime.now().weekday() == 0 and datetime.now().hour == 11 and datetime.now().minute == 45:
                await channel.send(f"## <a:pepesith:1165101386921418792> The lottery ends in 15 minutes! Enter here -> {message.jump_url}")
            await asyncio.sleep(60)

    async def bg_task_lottery_end(self):
        await self.wait_until_ready()
        channel = self.get_channel(1155577095787917384)
        # channel = self.get_channel(1186805143296020520) # bot-testing channel id 1186805143296020520
        
        while not self.is_closed():
            logger.info('bg_task_lottery_end running')
            if datetime.now().weekday() == 0 and datetime.now().hour == 12 and datetime.now().minute == 0:
                logger.info('bg_task_lottery_end running at 12:00pm on Monday')
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
                    lottery_role = discord.utils.get(channel.guild.roles, name="LotteryParticipant")
                    logger.info(f'winner: {user.discord_username}')
                    await channel.send(f'# {lottery_role.mention} Congratulations to {discord_user.mention} for winning {lottery_credits:,.0f} Credits in the lottery! <a:pepesith:1165101386921418792>')
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
                    for member in channel.guild.members:
                        await member.remove_roles(lottery_role)
                    logger.info(f'winner: {user.discord_username} won {lottery_credits} Credits and updated to db')
                except Exception as e:
                    logger.error(f'bg_task_lottery_end error: {e}')
            await asyncio.sleep(60)

    async def check_if_live_task(self):
        await self.wait_until_ready()
        # channel = self.get_channel(1224417564684456146) # TWITCH ANNOUCEMENTS CHANNEL
        channel = self.get_channel(1186805143296020520) # Bot Testing Channel
        while not self.is_closed():
            logger.info('check_if_live_task running')
            tw = Twitch()
            try:
                user_name = 'acosmic'
                if tw.check_if_live(user_name):
                    if not self.posted:
                        data = tw.get_stream_info(user_name)
                        profile_picture = tw.get_profile_picture(user_name) # profile picture
                        user_name = data['data'][0]['user_name'] # user name
                        game_name = data['data'][0]['game_name'] # game name
                        stream_title = data['data'][0]['title'] # stream title
                        viewer_count = data['data'][0]['viewer_count'] # viewer count
                        stream_start_time = data['data'][0]['started_at'] # stream start time
                        thumbnail_url = data['data'][0]['thumbnail_url'].format(width=1920, height=1080) # stream thumbnail url
                        
                        stream_link = f"<https://www.twitch.tv/{user_name}>"
                        markdown_link = f"[{stream_title}]({stream_link})"

                        # TIMEZONE SHIT
                        # Convert the string to a datetime object (assuming it's in UTC)
                        dt = datetime.strptime(stream_start_time, "%Y-%m-%dT%H:%M:%SZ")
                        # Convert the datetime object to UTC
                        dt_utc = dt.replace(tzinfo=pytz.utc)
                        # Define Central Daylight Time (CDT) timezone
                        cdt_timezone = pytz.timezone('America/Chicago')
                        # Convert the UTC datetime object to CDT
                        dt_cdt = dt_utc.astimezone(cdt_timezone)
                        # Convert the CDT datetime object to a Unix timestamp
                        unix_timestamp = int(dt_cdt.timestamp())
                        # Discord timestamp string (full date/time format)
                        discord_timestamp = f"<t:{unix_timestamp}:F>"

                        embed = discord.Embed(title=f"🔴 {user_name} is live on Twitch!", description=f"## {markdown_link}", color=0x6441A4)
                        embed.set_image(url=thumbnail_url)
                        embed.set_thumbnail(url=profile_picture)
                        
                        embed.add_field(name="Category", value=game_name, inline=False)
                        embed.add_field(name="Viewers", value=viewer_count, inline=False)
                        embed.add_field(name="Started", value=discord_timestamp, inline=False)
                        # embed.set_footer(text=discord_timestamp)
                        await channel.send(f"@test is live on Twitch! {stream_link}")
                        await channel.send(embed=embed)
                        self.posted = True
                        logger.info(f"POSTED TWITCH ANNOUNCEMENT - posted bool: {self.posted}")
                    else:
                        logger.info(f"TWITCH ANNOUNCEMENT TASK - LIVE BUT ALREADY POSTED | THIS SHOULD BE TRUE - posted bool: {self.posted}")
                        
                else:
                    logger.info(f"TWITCH ANNOUNCEMENT TASK | THIS SHOULD BE FALSE - posted bool: {self.posted}")
                    self.posted = False
                    
            except Exception as e:
                logger.error(f'check_if_live_task error: {e}')
            
            try:
                await self.check_streaming_members() 

                # streamers = tw.streamerDict
                # for discord_id in streamers:
                #     twitch_username = streamers[discord_id]
                #     if tw.check_if_live(twitch_username):

                        # if not self.posted:
                        #     data = tw.get_stream_info(streamer)
                        #     profile_picture = tw.get_profile_picture(streamer) # profile picture
                        #     user_name = data['data'][0]['user_name'] # user name
                        #     game_name = data['data'][0]['game_name'] # game name
                        #     stream_title = data['data'][0]['title'] # stream title
                        #     viewer_count = data['data'][0]['viewer_count'] # viewer count
                        #     stream_start_time = data['data'][0]['started_at'] # stream start time
                        #     thumbnail_url = data['data'][0]['thumbnail_url'].format(width=1920, height=1080) # stream thumbnail url
                            
                        #     stream_link = f"<https://www.twitch.tv/{user_name}>"
                        #     markdown_link = f"[{stream_title}]({stream_link})"
        
            except Exception as e:
                logger.error(f'check_if_live_task error: {e}')
            await asyncio.sleep(60)
            
    async def check_streaming_members(self):
        live_now_role_name = "Live Now"
        streamer_role_name = "Streamer"
        live_now_role = discord.utils.get(bot.guilds[0].roles, name=live_now_role_name)
        streamer_role = discord.utils.get(bot.guilds[0].roles, name=streamer_role_name)
        for guild in bot.guilds:
            for member in guild.members:
                if streamer_role in member.roles:
                    streaming_activities = [activity for activity in member.activities if isinstance(activity, discord.Streaming)]
                    
                    if streaming_activities:
                        if live_now_role not in member.roles:
                            logger.info(f'{member.display_name} is streaming')
                            await member.add_roles(live_now_role)
                        else:
                            logger.info(f'{member.display_name} is streaming and already has the role')
                    else:
                        if live_now_role in member.roles:
                            logger.info(f'{member.display_name} is not streaming')
                            await member.remove_roles(live_now_role)

    def giphy_search(self, search_term):
        api_url = f"https://api.giphy.com/v1/gifs/search?api_key={GIPHY_KEY}&q={search_term}&limit=20&offset=0&rating=pg-13&lang=en"
        with request.urlopen(api_url) as response:
            data = json.loads(response.read())
            results_count = len(data['data'])
            if results_count == 0:
                return "No results found."
            random_number = random.randint(0, results_count - 1)  # Adjust random_number based on actual results count
            return data['data'][random_number]['url']
    

bot = Bot()

if __name__ == "__main__":
    bot.run(TOKEN)
