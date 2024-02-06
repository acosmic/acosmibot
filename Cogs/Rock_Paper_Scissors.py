import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from Dao.GamesDao import GamesDao

from datetime import datetime
from Views.View_Start_RPS import View_Start_RPS

class Rock_Paper_Scissors(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="rockpaperscissors", description="NOT WORKING YET - Challenge another member to a game of Rock, Paper, Scissors. Best of 3 wins!")
    async def rock_paper_scissors(self, interaction: discord.Interaction, bet: int):
        gamesDao = GamesDao()
        if gamesDao.check_game_inprogress(game_name="rps"):
            await interaction.response.send_message(f"This is already a match in progress. Please allow it to finish before starting another match.", ephemeral=True)

        else:
            gamesDao.set_game_inprogress(game_name="rps", int=1)
            role = discord.utils.get(interaction.guild.roles, name="Acosmic")
            dao = UserDao()
            if role in interaction.user.roles:
                players = 2
                view = View_Start_RPS(timeout=300)
                view.initiator = interaction.user
                view.players = players
                await view.send(interaction)

async def setup(bot: commands.Bot):
    await bot.add_cog(Rock_Paper_Scissors(bot))