from datetime import datetime
import discord
from discord.ext import commands
from Dao.UserDao import UserDao
from Entities.User import User
import logging

role_level_1 = "Level One"
role_level_2 = "Level Two"
role_level_3 = "Level Three"
role_level_4 = "Level Four"
role_level_5 = "Level Five"
role_level_6 = "Level Six"
role_level_7 = "Level Seven"
role_level_8 = "Level Eight"
role_level_9 = "Level Nine"
role_level_10 = "Level Ten"

logging.basicConfig(filename='/root/dev/acosmicord-bot/logs.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class On_Message(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        
        if not message.author.bot:
            logging.info(f'Message from {message.author}: {message.content}')
            role1 = discord.utils.get(message.guild.roles, name=role_level_1)
            role2 = discord.utils.get(message.guild.roles, name=role_level_2)
            role3 = discord.utils.get(message.guild.roles, name=role_level_3)
            role4 = discord.utils.get(message.guild.roles, name=role_level_4)
            role5 = discord.utils.get(message.guild.roles, name=role_level_5)
            role6 = discord.utils.get(message.guild.roles, name=role_level_6)
            role7 = discord.utils.get(message.guild.roles, name=role_level_7)
            role8 = discord.utils.get(message.guild.roles, name=role_level_8)
            role9 = discord.utils.get(message.guild.roles, name=role_level_9)
            role10 = discord.utils.get(message.guild.roles, name=role_level_10)

            dao = UserDao()

            current_user = dao.get_user(message.author.id)
            logging.info(f'{str(current_user.discord_username)} grabbed from get_user(id) in on_message()')
            if current_user is not None:
                current_user.exp += 2
                current_user.exp_gained += 2
                current_user.messages_sent += 1
                current_user.last_active = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logging.info(f'CURRENT TIME = {current_user.last_active}')
                current_level = current_user.level

                if current_user.exp < 100:
                    role = role1
                    current_user.level = 1
                elif current_user.exp >= 100 and current_user.exp < 200:
                    role = role2
                    current_user.level = 2
                elif current_user.exp >= 200 and current_user.exp < 300:
                    role = role3
                    current_user.level = 3
                elif current_user.exp >= 300 and current_user.exp < 400:
                    role = role4
                    current_user.level = 4
                elif current_user.exp >= 400 and current_user.exp < 500:
                    role = role5
                    current_user.level = 5
                elif current_user.exp >= 500 and current_user.exp < 600:
                    role = role6
                    current_user.level = 6
                elif current_user.exp >= 600 and current_user.exp < 700:
                    role = role7
                    current_user.level = 7
                elif current_user.exp >= 700 and current_user.exp < 800:
                    role = role8
                    current_user.level = 8
                elif current_user.exp >= 800 and current_user.exp < 900:
                    role = role9
                    current_user.level = 9
                elif current_user.exp >= 900:
                    role = role10
                    current_user.level = 10

                # CHECK IF - DAILY REWARD
                if current_user.daily == 0:
                    logging.info(f"{current_user.discord_username} - COMPLETED DAILY REWARD")

                    current_user.currency += 100
                    current_user.daily = 1
                    await message.reply(f'<:PepeCelebrate:1165105393362555021> {message.author.mention} You have collected your daily reward - 100 Credits! <:PepeCelebrate:1165105393362555021>')
                else:
                    logging.info(f"{current_user.discord_username} HAS ALREADY COMPLETED THE DAILY")
                
                # CHECK IF _ LEVELING UP
                if current_user.level > current_level:
                    current_user.currency += 500
                    await message.reply(f'<:FeelsGroovy:1199735360616407041> LEVEL UP! You have reached {str(role)}! You have been awarded 500 Credits!')
                    
                try:
                    dao.update_user(current_user)
                    logging.info(f'{str(message.author)} updated in database in on_message()')
                except Exception as e: 
                    logging.error(f'Error updating {message.author} to the database: {e}')
                await message.author.add_roles(role)

            else:
                join_date = message.author.joined_at

                # Convert join_date to a format suitable for database insertion (e.g., as a string)
                formatted_join_date = join_date.strftime("%Y-%m-%d %H:%M:%S")

                new_user_data = {
                'id': message.author.id,
                'discord_username': str(message.author),
                'level': 1,
                'streak': 0,
                'exp': 0,
                'exp_gained': 0,
                'exp_lost': 0,
                'currency': 0,
                'messages_sent': 1,
                'reactions_sent': 0,
                'created': formatted_join_date,
                'last_active': formatted_join_date,
                'daily': 0

                }
                new_user = User(**new_user_data)
                logging.info(f'{message.author} added to the database. - on_message() - DISABLED CURRENTLY nothing added to db')
                # try:
                #     # dao.add_user(new_user)
                #     logging.info(f'{message.author} added to the database. - on_message() - DISABLED CURRENTLY')
                # except Exception as e:
                #     logging.error(f'on_message() - Error adding user to the database: {e}')


async def setup(bot: commands.Bot):
    await bot.add_cog(On_Message(bot))
        



