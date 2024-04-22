from datetime import datetime, timedelta

import math
import discord
from discord.ext import commands
from Dao.UserDao import UserDao
from Entities.User import User
from Leveling import Leveling
from logger import AppLogger

role_level_1 = "Egg"
role_level_2 = "Biddy"
role_level_3 = "Chicken"
role_level_4 = "Cock"

logger = AppLogger(__name__).get_logger()


class On_Message(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        level_up_channel = self.bot.get_channel(1209288743912218644)
        daily_reward_channel = self.bot.get_channel(1224561092919951452)
        
        if not message.author.bot:
            logger.info(f'Message from {message.author}: {message.channel.name} - {message.content}')
            dao = UserDao()

            current_user = dao.get_user(message.author.id)
            logger.info(f'{str(current_user.discord_username)} grabbed from get_user(id) in on_message()')
            if current_user is not None:
                # SPAM PROTECTION
                last_active = current_user.last_active
                now = datetime.now()
                if now - last_active > timedelta(seconds=2):
                    base_exp = 10
                else:
                    base_exp = 0
                    logger.info(f'{str(current_user.discord_username)} - MESSAGE SENT TOO SOON - NO EXP GAINED')

                # CALCULATE EXP GAINED
                bonus_exp = current_user.streak * 0.05

                exp_gain = math.ceil((base_exp * bonus_exp) + base_exp)
                current_user.exp += exp_gain
                current_user.exp_gained += exp_gain
                current_user.messages_sent += 1
                current_user.last_active = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f'CURRENT TIME = {current_user.last_active} - {current_user.discord_username} - EXP GAINED = {exp_gain}')

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
                        await daily_reward_channel.send(f'## {message.author.mention} You have collected your daily reward - {calculated_daily_reward} Credits! 100 + {streak_bonus} from {streak}x Streak! <:PepeCelebrate:1165105393362555021>')
                    else:
                        await daily_reward_channel.send(f'## {message.author.mention} You have collected your daily reward - 100 Credits! <:PepeCelebrate:1165105393362555021>')

                else:
                    logger.info(f"{current_user.discord_username} HAS ALREADY COMPLETED THE DAILY")


                
                # CHECK IF - LEVELING UP
                lvl = Leveling()
                new_level = lvl.calc_level(current_user.exp)
                if new_level > current_user.level:
                    
                    # CALCULATE LEVEL UP REWARD
                    base_level_up_reward = 1000
                    streak = current_user.streak if current_user.streak < 20 else 20
                    base_bonus_multiplier = 0.05
                    streak_bonus_percentage = streak * base_bonus_multiplier
                    streak_bonus = math.floor(base_level_up_reward * streak_bonus_percentage)
                    calculated_level_reward = base_level_up_reward + streak_bonus

                    if streak > 0:
                        await level_up_channel.send(f'## {message.author.mention} LEVEL UP! You have reached level {new_level}! Gained {calculated_level_reward} Credits! 1,000 + {streak_bonus} from {streak}x Streak! <:FeelsGroovy:1199735360616407041>')
                    else:
                        await level_up_channel.send(f'## {message.author.mention} LEVEL UP! You have reached level {new_level}! Gained {calculated_level_reward} Credits! <:FeelsGroovy:1199735360616407041>')
                
                current_user.level = new_level

                # DETECT ROLE CHANGE
                user_roles = message.author.roles
                roles = []
                if current_user.level < 5:
                    role = discord.utils.get(message.guild.roles, name=role_level_1) # 🥚 EGG 
                    if role not in user_roles:
                        roles.append(role)
                if current_user.level >= 5:
                    role = discord.utils.get(message.guild.roles, name=role_level_2) # 🐣 BIDDY
                    if role not in user_roles:
                        roles.append(role)
                if current_user.level >= 10:
                    role = discord.utils.get(message.guild.roles, name=role_level_3) # 🐔 CHICKEN
                    if role not in user_roles:
                        roles.append(role)
                if current_user.level >= 20:
                    role = discord.utils.get(message.guild.roles, name=role_level_4) # 🐓 COCK
                    if role not in user_roles:
                        roles.append(role)
                
                try:
                    dao.update_user(current_user)
                    logger.info(f'{str(message.author)} updated in database in on_message()')
                except Exception as e: 
                    logger.error(f'Error updating {message.author} to the database: {e}')
                try:
                    await message.author.add_roles(*roles)
                    logger.info(f'{str(message.author)} roles updated in on_message()')
                except Exception as e:
                    logger.error(f'Error updating {message.author} roles: {e}')

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


async def setup(bot: commands.Bot):
    await bot.add_cog(On_Message(bot))
        



