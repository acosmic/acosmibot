from pickle import FALSE
import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from Entities.User import User
import logging
import typing

logging.basicConfig(filename='/root/dev/acosmicord-bot/logs.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Leaderboard(commands.Cog):
    def __init__(self, bot:commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name = "leaderboard", description = "Returns top 5 users by Credits based on Currency, EXP, etc.")
    async def leaderboard(self, interaction: discord.Interaction, stat: typing.Literal['currency', 'exp']):

        if stat not in ['currency', 'exp']:
            await interaction.response.send_message("Invalid choice. Please choose from the list.", ephemeral=True)
            return
         
        dao = UserDao()
        leaders = dao.get_top_users(column=stat.lower())


        embed = discord.Embed(title=f"Top 5 Users by {stat.upper()}", color=interaction.user.color)

        for i, (user_id, username, value) in enumerate(leaders, start=1):
            embed.add_field(name=f"{i}. {username}", value=f"{value} {stat.capitalize()}\n", inline=False)

        await interaction.response.send_message(embed=embed)

        logging.info(f"{interaction.user.name} used /leaderboard {stat.lower()}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Leaderboard(bot))