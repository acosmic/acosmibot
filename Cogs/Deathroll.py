import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from Dao.GamesDao import GamesDao

from datetime import datetime

from Views.Deathroll_Start_View import Deathroll_Start_View

class Deathroll(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="deathroll", description="Start a game of Deathroll. First person to roll a 1 loses!")
    async def deathroll(self, interaction: discord.Interaction, target: discord.Member, bet: int):
        gamesDao = GamesDao()
        if gamesDao.check_game_inprogress(game_name="deathroll"):
            await interaction.response.send_message(f"There is already a match in progress. Please allow it to finish before starting another match.", ephemeral=True)

        else:
            gamesDao.set_game_inprogress(game_name="deathroll", inprogress=1)
            dao = UserDao()
            current_user = dao.get_user(interaction.user.id)
            if bet > current_user.currency:
                await interaction.response.send_message(f"You don't have enough to make this bet!", ephemeral=True)

            else:
                # if role in interaction.user.roles:
                players = 2
                view = Deathroll_Start_View(timeout=120)
                view.initiator = interaction.user
                view.target = target
                view.players = players
                view.bet = bet
                await view.send(interaction)

async def setup(bot: commands.Bot):
    await bot.add_cog(Deathroll(bot))