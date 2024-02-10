import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from Dao.CoinflipDao import CoinflipDao
from Dao.VaultDao import VaultDao
from Entities.CoinflipEvent import CoinflipEvent
import random
import logging
import typing
from datetime import datetime

class Coinflip(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="coinflip", description="Flip a coin for a chance to win credits")
    async def coin_flip(self, interaction: discord.Interaction, call: typing.Literal['Heads', 'Tails'], bet: int):
        

        if call not in ['Heads', 'Tails']:
            await interaction.response.send_message("Invalid choice. Please choose either 'Heads' or 'Tails'.", ephemeral=True)
            return

        dao = UserDao()
        cfdao = CoinflipDao()
        user = dao.get_user(interaction.user.id)
        cost = abs(bet)  # Make sure bet is positive

        if user.currency < cost:
            await interaction.response.send_message("You don't have enough credits to place this bet.", ephemeral=True)
            return

        # Flip the coin
        result = random.choice(['Heads', 'Tails'])
        

        if result == call:
            user.currency += cost
            amount_won = cost
            amount_lost = 0
            message = f"{interaction.user.name} called {call} and won {cost} credits! <:PepeDank:1200292095131406388>"
        else:
            vdao = VaultDao()
            vcredits = vdao.get_currency()
            vcredits += cost
            vdao.update_currency(vcredits)
            user.currency -= cost
            amount_won = 0
            amount_lost = cost
            message = f"{interaction.user.name} called {call} but lost {cost} credits. Better luck next time! <a:giggle:1165098258968879134>\n\n{cost} Credits have been added to the vault! 🏦"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_event = CoinflipEvent(0, interaction.user.id, call, result, amount_won, amount_lost, timestamp)

        dao.update_user(user)
        cfdao.add_new_event(new_event)
        await interaction.response.send_message(message)
        logging.info(f"{interaction.user.name} used /coinflip command")

async def setup(bot: commands.Bot):
    await bot.add_cog(Coinflip(bot))