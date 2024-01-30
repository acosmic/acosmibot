import discord
from discord.ext import commands
from discord import app_commands
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


class Rank(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name = "rank", description = "Returns your rank based on current EXP and general stats.") 
    async def rank(self, interaction: discord.Interaction):
        dao = UserDao()
        user_rank = dao.get_user_rank(interaction.user.name)
        
        current_user = dao.get_user(interaction.user.name)

        if user_rank is not None:
            embed = discord.Embed(
            title=f"{interaction.user.name}'s stats",
            description=(
            f"Ranked #{user_rank[-1]}\n"
            f"Current Level: {current_user.level}\n"
            f"Current EXP: {current_user.exp}\n"
            f"Total Messages: {current_user.messages_sent}\n"
            f"Total Reactions: {current_user.reactions_sent}\n"
            ),
            color=interaction.user.color)
            embed.set_thumbnail(url=interaction.user.avatar)

            await interaction.response.send_message(embed=embed)

        else:
            logging.info(f"The user with Discord username {interaction.user.name} was not found in the database.")
            
            role = discord.utils.get(interaction.user.guild.roles, name=role_level_1)
            await interaction.user.add_roles(role)
            join_date = interaction.user.joined_at

            # Convert join_date to a format suitable for database insertion (e.g., as a string)
            formatted_join_date = join_date.strftime("%Y-%m-%d %H:%M:%S")

            user_data = {
            'id': 0,
            'discord_username': str(interaction.user.name),
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

            new_user = User(**user_data)
            dao.add_user(new_user)
            logging.info(f'{new_user.discord_username} added to the database.')
            await interaction.response.send_message(f'{interaction.user.name} was not found in the database. {new_user.discord_username} added to the database.')
        # await interaction.response.send_message("Hello!") 
        logging.info(f"{interaction.user.name} used /rank command")

async def setup(bot: commands.Bot):
    await bot.add_cog(Rank(bot))