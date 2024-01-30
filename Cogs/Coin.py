import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
import random
import logging
import typing

class Coin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="coinflip", description="Flip a coin for a chance to win credits")
    async def coin_flip(self, interaction: discord.Interaction, call: typing.Literal['Heads', 'Tails'], bet: int):
        

        if call not in ['Heads', 'Tails']:
            await interaction.response.send_message("Invalid choice. Please choose either 'Heads' or 'Tails'.", ephemeral=True)
            return

        dao = UserDao()
        user = dao.get_user(interaction.user.name)
        cost = abs(bet)  # Make sure bet is positive

        if user.currency < cost:
            await interaction.response.send_message("You don't have enough credits to place this bet.", ephemeral=True)
            return

        # Flip the coin
        result = random.choice(['Heads', 'Tails'])

        if result == call:
            user.currency += cost
            message = f"{interaction.user.name} called {call} and won {cost} credits! <:PepeDank:1200292095131406388>"
        else:
            user.currency -= cost
            message = f"{interaction.user.name} called {call} but lost {cost} credits. Better luck next time! <a:giggle:1165098258968879134>"

        dao.update_user(user)
        await interaction.response.send_message(message)
        logging.info(f"{interaction.user.name} used /coin command")

async def setup(bot: commands.Bot):
    await bot.add_cog(Coin(bot))