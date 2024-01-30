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
    async def leaderboard(self, interaction: discord.Interaction, stat: typing.Literal['CURRENCY', 'EXP']):

        if stat not in ['CURRENCY', 'EXP']:
            await interaction.response.send_message("Invalid choice. Please choose from the list.", ephemeral=True)
            return
         
        dao = UserDao()
        leaders = dao.get_top_users(column=stat.upper())


        embed = discord.Embed(title=f"Top 5 Users by {stat.capitalize()}", color=discord.Color.blue())

        for i, (user_id, username, value) in enumerate(leaders, start=1):
            embed.add_field(name=f"{i}. {username}", value=f"{value} {stat.capitalize()}", inline=False)

        await interaction.response.send_message(embed=embed)

        logging.info(f"{interaction.user.name} used /leaderboard {stat.upper()}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Leaderboard(bot))