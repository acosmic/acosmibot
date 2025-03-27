from datetime import datetime, timedelta
import os
import json
import math
import discord
from discord import Message
from discord.ext import commands
from dotenv import load_dotenv
from Dao.UserDao import UserDao
from Entities.User import User
from Leveling import Leveling
from logger import AppLogger
from AI.OpenAIClient import OpenAIClient

# Load environment variables from .env file
load_dotenv()

role_level_1 = os.getenv('ROLE_LEVEL_1')
role_level_2 = os.getenv('ROLE_LEVEL_2')
role_level_3 = os.getenv('ROLE_LEVEL_3')
role_level_4 = os.getenv('ROLE_LEVEL_4')
role_level_5 = os.getenv('ROLE_LEVEL_5')
role_level_6 = os.getenv('ROLE_LEVEL_6')
role_level_7 = os.getenv('ROLE_LEVEL_7')

  


logger = AppLogger(__name__).get_logger()


class On_Message(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.chatgpt = OpenAIClient()
        load_dotenv()  # Load environment variables from .env file
        inappropriate_words_str = os.getenv('INAPPROPRIATE_WORDS')
        if inappropriate_words_str:
            self.inappropriate_words = json.loads(inappropriate_words_str)
        else:
            self.inappropriate_words = []

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        general_channel = self.bot.get_channel(1155577095787917384)
        jail_channel = self.bot.get_channel(1233867818055893062)
        bot_testing = self.bot.get_channel(1186805143296020520)
        level_up_channel = self.bot.get_channel(1209288743912218644)
        daily_reward_channel = self.bot.get_channel(1224561092919951452)
        inmate_role = discord.utils.get(message.guild.roles, name='Inmate')
        acosmic_role = discord.utils.get(message.guild.roles, name='Acosmic')
        
        if not message.author.bot:
            if inmate_role not in message.author.roles:
                logger.info(f'Message from {message.author} - {message.channel.name} - {message.id}; {message.content}')
                dao = UserDao()
                current_user = dao.get_user(message.author.id)
                logger.info(f'{str(current_user.discord_username)} grabbed from get_user(id) in on_message()')
                if current_user is not None:
                    # SPAM PROTECTION
                    last_active = current_user.last_active
                    now = datetime.now()
                    if now - last_active > timedelta(seconds=4):
                        base_exp = 10
                    else:
                        base_exp = 0
                        logger.info(f'{str(current_user.discord_username)} - MESSAGE SENT TOO SOON - NO EXP GAINED')

                    # CHECK FOR INAPPROPRIATE WORDS
                    message_content_lower = message.content.lower()
                    for word in self.inappropriate_words:
                        if word.lower() in message_content_lower:
                            logger.info(f'{str(current_user.discord_username)} - INAPPROPRIATE WORD DETECTED: {message.content}')
                            await message.delete()
                            return

                    # CALCULATE EXP GAINED
                    bonus_exp = current_user.streak * 0.05

                    exp_gain = math.ceil((base_exp * bonus_exp) + base_exp)
                    current_user.exp += exp_gain
                    current_user.exp_gained += exp_gain
                    current_user.season_exp += exp_gain
                    current_user.messages_sent += 1
                    current_user.last_active = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    logger.info(f'{current_user.discord_username} - EXP GAINED = {exp_gain}')

                    # CHECK IF - DAILY REWARD
                    if current_user.daily == 0:
                        logger.info(f"{current_user.discord_username} - COMPLETED DAILY REWARD")

                        # Check if last_daily was yesterday
                        
                        today = datetime.now().date()
                        if current_user.last_daily is None:
                            current_user.streak = 0
                        else:
                            if current_user.last_daily.date() == today - timedelta(days=1):
                                # Increment streak
                                current_user.streak += 1
                                if current_user.streak > current_user.highest_streak:
                                    current_user.highest_streak = current_user.streak
                                    logger.info(f"{current_user.discord_username} - HIGHEST STREAK INCREMENTED TO {current_user.highest_streak}")
                                logger.info(f"{current_user.discord_username} - STREAK INCREMENTED TO {current_user.streak}")
                            elif current_user.last_daily.date() < today - timedelta(days=1):
                                # Reset streak
                                current_user.streak = 1
                                logger.info(f"{current_user.discord_username} - STREAK RESET TO {current_user.streak}")


                        # CALCULATE DAILY REWARD
                        base_daily = 100
                        streak = current_user.streak if current_user.streak < 20 else 20
                        base_bonus_multiplier = 0.05
                        streak_bonus_percentage = streak * base_bonus_multiplier
                        streak_bonus = math.floor(base_daily * streak_bonus_percentage)
                        calculated_daily_reward = base_daily + streak_bonus
                        current_user.currency += calculated_daily_reward



                        # Set daily and last_daily
                        current_user.daily = 1
                        current_user.last_daily = datetime.now().strftime("%Y-%m-%d %H:%M:%S") 


                        streak = current_user.streak if current_user.streak < 20 else 20
                        if streak > 0:
                            await daily_reward_channel.send(f'## {message.author}, You have collected your daily reward - {calculated_daily_reward} Credits! 100 + {streak_bonus} from {streak}x Streak! <:PepeCelebrate:1165105393362555021>')
                        else:
                            await daily_reward_channel.send(f'## {message.author}, You have collected your daily reward - 100 Credits! <:PepeCelebrate:1165105393362555021>')

                    else:
                        logger.info(f"{current_user.discord_username} HAS ALREADY COMPLETED THE DAILY")


                    
                    # CHECK IF - LEVELING UP
                    lvl = Leveling()
                    new_level = lvl.calc_level(current_user.exp)
                    new_season_level = lvl.calc_level(current_user.season_exp)   

                    if new_level > current_user.level:
                        
                        # CALCULATE LEVEL UP REWARD
                        base_level_up_reward = 1000
                        streak = current_user.streak if current_user.streak < 20 else 20
                        base_bonus_multiplier = 0.05
                        streak_bonus_percentage = streak * base_bonus_multiplier
                        streak_bonus = math.floor(base_level_up_reward * streak_bonus_percentage)
                        calculated_level_reward = base_level_up_reward + streak_bonus
                        current_user.currency += calculated_level_reward

                        if streak > 0:
                            await level_up_channel.send(f'## {message.author.mention} LEVEL UP! You have reached level {new_level}! Gained {calculated_level_reward} Credits! 1,000 + {streak_bonus} from max of {streak}x Streak!  <:FeelsGroovy:1199735360616407041>')
                        else:
                            await level_up_channel.send(f'## {message.author.mention} LEVEL UP! You have reached level {new_level}! Gained {calculated_level_reward} Credits! <:FeelsGroovy:1199735360616407041>')
                    
                    current_user.level = new_level
                    

                    # SEASON LEVEL UP
                    if new_season_level > current_user.season_level:

                        # CALCULATE SEASON LEVEL UP REWARD
                        base_season_level_up_reward = 5000
                        streak = current_user.streak if current_user.streak < 20 else 20
                        base_bonus_multiplier = 0.05
                        streak_bonus_percentage = streak * base_bonus_multiplier
                        streak_bonus = math.floor(base_season_level_up_reward * streak_bonus_percentage)
                        calculated_season_level_reward = base_season_level_up_reward + streak_bonus
                        current_user.currency += calculated_season_level_reward

                        if streak > 0:
                            await level_up_channel.send(f'## <a:peepoTree:1312043349305196574> {message.author.mention} HOLIDAY SEASON LEVEL UP! You have reached season level {new_season_level}! Gained {calculated_season_level_reward} Credits! 5,000 + {streak_bonus} from {streak}x Streak! <a:NODDERS:1312038419517673566>')
                        else:
                            await level_up_channel.send(f'## <a:peepoTree:1312043349305196574> {message.author.mention} HOLIDAY SEASON LEVEL UP! You have reached season level {new_season_level}! Gained {calculated_season_level_reward} Credits! <a:NODDERS:1312038419517673566>')
 
                    current_user.season_level = new_season_level
                    
                    
                    # DETECT ROLE CHANGE
                    user_roles = message.author.roles
                    roles = []
                    # if current_user.level < 5:
                    if current_user.season_level < 5:
                        role = discord.utils.get(message.guild.roles, name=role_level_1) 
                        if role not in user_roles:
                            roles.append(role)
                    # if current_user.level >= 5:
                    if current_user.season_level >= 5:
                        role = discord.utils.get(message.guild.roles, name=role_level_2) 
                        if role not in user_roles:
                            roles.append(role)
                    # if current_user.level >= 10:
                    if current_user.season_level >= 10:
                        role = discord.utils.get(message.guild.roles, name=role_level_3) 
                        if role not in user_roles:
                            roles.append(role)
                    # if current_user.level >= 15:
                    if current_user.season_level >= 15:
                        role = discord.utils.get(message.guild.roles, name=role_level_4) 
                        if role not in user_roles:
                            roles.append(role)
                    # if current_user.level >= 20:
                    if current_user.season_level >= 20:
                        role = discord.utils.get(message.guild.roles, name=role_level_5) 
                        if role not in user_roles:
                            roles.append(role)

                    # if current_user.level >= 25:
                    if current_user.season_level >= 25:
                        role = discord.utils.get(message.guild.roles, name=role_level_6) 
                        if role not in user_roles:
                            roles.append(role)

                    # if current_user.level >= 30:
                    if current_user.season_level >= 30:
                        role = discord.utils.get(message.guild.roles, name=role_level_7) 
                        if role not in user_roles:
                            roles.append(role)
                    
                    try:
                        dao.update_user(current_user)
                        logger.info(f'{str(message.author)} updated in database in on_message()')
                    except Exception as e: 
                        logger.error(f'Error updating {message.author} to the database: {e}')
                    
                    # UPDATE ROLES
                    try:
                        await message.author.add_roles(*roles)
                        logger.info(f'{str(message.author)} roles updated in on_message()')
                    except Exception as e:
                        logger.error(f'Error updating {message.author} roles: {e}')

                    # --------------------------- OPENAI CHATGPT ---------------------------    
                    try:    
                        if (self.bot.user in message.mentions):
                            # if message.author.id == 110637665128325120:
                                # Remove the mention and strip the message
                                prompt = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
                                
                                async with message.channel.typing():
                                # Get the response from OpenAI
                                # response = await self.chatgpt.get_chatgpt_response(prompt)
                                    response = await self.chatgpt.get_chatgpt_response(prompt, message.author.name, message.author.id)

                                # Send the response back to the channel
                                response_list = []
                                if len(response) <= 2000:
                                    response_list.append(response)
                                else:
                                    while len(response) > 2000:
                                        response_list.append(response[:2000])
                                        response = response[2000:]

                                
                                for res in response_list:
                                    await message.channel.send(res)
                                
                                # await message.channel.send(response)
                            # else:
                                # await message.channel.send(f'Hello {message.author.mention}! I am a bot created by <@110637665128325120>. The AI feature is currently in development. Please be patient!')
                    except Exception as e:
                        logger.error(f'OpenAI Error: {e}')

                    # Process other commands

                    if message.content.lower() == "yo":
                        await message.add_reaction("<:Wave:1203565577881526352>")

                    

                else:
                    return
                    # join_date = message.author.joined_at

                    # # Convert join_date to a format suitable for database insertion (e.g., as a string)
                    # formatted_join_date = join_date.strftime("%Y-%m-%d %H:%M:%S")

                    # new_user_data = {
                    # 'id': message.author.id,
                    # 'discord_username': str(message.author),
                    # 'level': 1,
                    # 'streak': 0,
                    # 'exp': 0,
                    # 'exp_gained': 0,
                    # 'exp_lost': 0,
                    # 'currency': 0,
                    # 'messages_sent': 1,
                    # 'reactions_sent': 0,
                    # 'created': formatted_join_date,
                    # 'last_active': formatted_join_date,
                    # 'daily': 0

                    # }
                    # new_user = User(**new_user_data)
                    # logging.info(f'{message.author} added to the database. - on_message() - DISABLED CURRENTLY nothing added to db')
                    # # try:
                    # #     # dao.add_user(new_user)
                    # #     logging.info(f'{message.author} added to the database. - on_message() - DISABLED CURRENTLY')
                    # # except Exception as e:
                    # #     logging.error(f'on_message() - Error adding user to the database: {e}')
            else:
                logger.info(f'{message.author} is an inmate - skipped level up exp rewards')
                # if message.channel.id == jail_channel.id:
                #     await bot_testing.send(f'Inmate {message.author} sends the following message from jail: {message.content}')
    
    
            

async def setup(bot: commands.Bot):
    await bot.add_cog(On_Message(bot))
        



