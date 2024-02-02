import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
import random
import logging

class Eightball(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name = "8ball", description = "Ask the magic 8ball your yes/no questions for 10 Credits") 
    async def eightball(self, interaction: discord.Interaction, question: str):
        # List of 8-ball responses
        responses = [
            "It is certain.",
            "It is decidedly so.",
            "Without a doubt.",
            "Yes - definitely.",
            "You may rely on it.",
            "As I see it, yes.",
            "Most likely.",
            "Outlook good.",
            "Yes.",
            "Signs point to yes.",
            "Reply hazy, try again.",
            "Ask again later.",
            "Better not tell you now.",
            "Cannot predict now.",
            "Concentrate and ask again.",
            "Don't count on it.",
            "My reply is no.",
            "My sources say no.",
            "Outlook not so good.",
            "Very doubtful."
        ]
        dao = UserDao()
        cost = 10
        user = dao.get_user(interaction.user.id)

        if user.currency >= cost:
            
            eightball = random.choice(responses) 
            await interaction.response.send_message(f"{interaction.user.name} asks: {question}\n\n <:PepeWizard:1200288529138327662> {eightball} 🎱  \n\n*{cost} Credits have been withdrawn from your balance*")
            user.currency -= cost
            dao.update_user(user)
            logging.info(f"{interaction.user.name} used /8ball command")
        else:
            await interaction.response.send_message(f"You're too broke to use the magic 8ball. <:OhGodMan:1200262332392157184>")

async def setup(bot: commands.Bot):
    await bot.add_cog(Eightball(bot))