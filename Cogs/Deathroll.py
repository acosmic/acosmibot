import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from Dao.GamesDao import GamesDao
from Dao.DeathrollDao import DeathrollDao
from Entities import DeathrollEvent

from datetime import datetime

from Views.Deathroll_View import Deathroll_View

class Deathroll(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="deathroll", description="Start a game of Deathroll. First person to roll a 1 loses!")
    async def deathroll(self, interaction: discord.Interaction, target: discord.Member, bet: int):

        drDao = DeathrollDao()
        current_events = drDao.check_if_user_ingame(interaction.user.id, target.id)
        if current_events:
            await interaction.response.send_message(f"Either you or your target is currently in a match. Please wait for that game to finish before starting another one.", ephemeral=True)

        elif bet < 100:
            await interaction.response.send_message(f"Please enter a bet of at least 100.", ephemeral=True)

        else:

            dao = UserDao()
            current_user = dao.get_user(interaction.user.id)
            if bet > current_user.currency:
                await interaction.response.send_message(f"You don't have enough to make this bet!", ephemeral=True)

            target_user = dao.get_user(target.id)
            if bet > target_user.currency:
                await interaction.response.send_message(f"{target.display_name} doesn't have enough to accept this bet! They have {target_user.currency:,.0f} Credits", ephemeral=True)

            else:
                # if role in interaction.user.roles:
                players = 2
                view = Deathroll_View(timeout=120)
                view.initiator = interaction.user
                view.target = target
                view.players = players
                view.bet = bet
                await view.send(interaction)
                

async def setup(bot: commands.Bot):
    await bot.add_cog(Deathroll(bot))