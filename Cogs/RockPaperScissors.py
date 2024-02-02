import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from Dao.CoinflipDao import CoinflipDao
from Entities.CoinflipEvent import CoinflipEvent
import random
import logging
import typing
from datetime import datetime
from Views import ViewStartRPS

class RockPaperScissors(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="RockPaperScissors", description="Challenge another member to a game of Rock, Paper, Scissors. Best of 3 wins!")
    async def rock_paper_scissors(self, interaction: discord.Interaction, bet: int, players: int):
        view = ViewStartRPS(timeout=None)
        view.initiatior = interaction.user
        view.players = players
        await view.send(interaction)