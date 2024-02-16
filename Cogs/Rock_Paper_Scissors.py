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

    @app_commands.command(name="rockpaperscissors", description="Challenge another member to a game of Rock, Paper, Scissors. Win 3 rounds!")
    async def rock_paper_scissors(self, interaction: discord.Interaction, bet: int):
        
        gamesDao = GamesDao()
        if gamesDao.check_game_inprogress(game_name="rps"):
            await interaction.response.send_message(f"There is already a match in progress. Please allow it to finish before starting another match.", ephemeral=True)

        else:
            gamesDao.set_game_inprogress(game_name="rps", inprogress=1)
            # role = discord.utils.get(interaction.guild.roles, name="Acosmic")
            dao = UserDao()
            current_user = dao.get_user(interaction.user.id)
            if bet > current_user.currency:
                await interaction.response.send_message(f"You don't have enough to make this bet!", ephemeral=True)

            else:
                # if role in interaction.user.roles:
                players = 2
                view = View_Start_RPS(timeout=120)
                view.initiator = interaction.user
                view.players = players
                view.bet = bet
                await view.send(interaction)

async def setup(bot: commands.Bot):
    await bot.add_cog(Rock_Paper_Scissors(bot))