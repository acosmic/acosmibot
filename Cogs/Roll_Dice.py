from email import message
import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from logger import AppLogger
import random

logger = AppLogger(__name__).get_logger()

class Roll_Dice(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    @app_commands.command(name="roll", description="Roll a double to get out of Jail.")
    
    async def roll(self, interaction: discord.Interaction):
        dao = UserDao()
        user = dao.get_user(interaction.user.id)
        cost = 500

        if user.currency < cost:
            await interaction.response.send_message("You do not have enough credits for /roll.", ephemeral=True)
            return


        die1 = random.randint(1, 6)
        die2 = random.randint(1, 6)

        embed = discord.Embed()
        

        if die1 == die2:
            result = "a double"
            embed.title = f"{interaction.user.name} rolled a DOUBLE!"
            embed.description = f"# 🎲 = {die1} 🎲 = {die2} | <:PepeDank:1200292095131406388> \n # {interaction.user.name} was released from Jail!"
            embed.color = discord.Color.green()
            # need to remove inmate role and add egg role
        
        else:
            result = "not a double"
            embed.title = f"{interaction.user.name} failed to roll a double!"
            embed.description = f"# 🎲 = {die1} 🎲 = {die2} | <a:giggle:1165098258968879134> \n # {interaction.user.name} will remain in Jail! \n\n ⛓️ Try again in 10 minutes! ⛓️"
            embed.color = discord.Color.red()



        # user.currency -= cost UNCOMMENT THIS LINE AFTER TESTING
        # dao.update_user(user) UNCOMMENT THIS LINE AFTER TESTING
        logger.info(f"{interaction.user.name} used /roll command - {result}")
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Roll_Dice(bot))

