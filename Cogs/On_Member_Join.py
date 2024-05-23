from datetime import datetime
import discord
from discord.ext import commands
from Dao.UserDao import UserDao
from Entities.User import User
from logger import AppLogger

role_level_1 = "Soy Milk"
role_level_2 = "Whole Milk"
role_level_3 = "Choccy Milk"
role_level_4 = "Poggies Milk"

# role_level_5 = "Level Five"
# role_level_6 = "Level Six"
# role_level_7 = "Level Seven"
# role_level_8 = "Level Eight"
# role_level_9 = "Level Nine"
# role_level_10 = "Level Ten"

logging = AppLogger(__name__).get_logger()

class On_Member_Join(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        role = discord.utils.get(member.guild.roles, name=role_level_1)
        join_date = member.joined_at
        dao = UserDao()

        # Convert join_date to a format suitable for database insertion (e.g., as a string)
        formatted_join_date = join_date.strftime("%Y-%m-%d %H:%M:%S")

        member_data = {
        'id': member.id,
        'discord_username': member.name,
        'nickname': "",
        'level': 0,
        'season_level': 0,
        'season_exp': 0,
        'streak': 0,
        'highest_streak': 0,
        'exp': 0,
        'exp_gained': 0,
        'exp_lost': 0,
        'currency': 0,
        'messages_sent': 0,
        'reactions_sent': 0,
        'created': formatted_join_date,
        'last_active': formatted_join_date,
        'daily': 0,
        'last_daily': None,
        }
        new_user = User(**member_data)
        existing_user = dao.get_user(new_user.id)

        if existing_user is None:
            await member.add_roles(role)
            logging.info(f'Auto assigned {role} role to {member}')

            # add new user to database
            try:
                dao.add_user(new_user)
                logging.info(f'{new_user.discord_username} added to the database. on_member_join()')
            except Exception as e:
                logging.error(f'on_member_join() - Error adding user to the database: {e}')
        else:
            level = existing_user.level
            if level < 5:
                role = discord.utils.get(member.guild.roles, name=role_level_1)
            elif level >= 5 and level < 10:
                role = discord.utils.get(member.guild.roles, name=role_level_2)
            elif level >= 10 and level < 20:
                role = discord.utils.get(member.guild.roles, name=role_level_3)
            elif level >= 20:
                role = discord.utils.get(member.guild.roles, name=role_level_4)

            await member.add_roles(role)

            logging.info(f'{new_user.discord_username} already exists, so was not added again.')

async def setup(bot: commands.Bot):
    await bot.add_cog(On_Member_Join(bot))