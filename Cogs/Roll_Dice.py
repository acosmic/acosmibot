from email import message
import discord
from discord.ext import commands
from discord import app_commands
from more_itertools import first
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
        general_channel = self.bot.get_channel(1155577095787917384)
        jail_channel = self.bot.get_channel(1233867818055893062)
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
            inmate_role = discord.utils.get(interaction.guild.roles, name="Inmate")
            first_role = discord.utils.get(interaction.guild.roles, name="Soy Milk")
            await interaction.user.remove_roles(inmate_role)
            await interaction.user.add_roles(first_role)
            await general_channel.send(embed=embed)
        
        else:
            result = "not a double"
            embed.title = f"{interaction.user.name} failed to roll a double!"
            embed.description = f"# 🎲 = {die1} 🎲 = {die2} | <a:giggle:1165098258968879134> \n # {interaction.user.name} will remain in Jail! \n\n ⛓️ Testing - no cooldown ⛓️"
            embed.color = discord.Color.red()



        # user.currency -= cost 
        # dao.update_user(user) 
        logger.info(f"{interaction.user.name} used /roll command - {result}")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Roll_Dice(bot))

