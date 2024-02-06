import typing
import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
import logging
import os
from dotenv import load_dotenv

load_dotenv()
MY_GUILD = discord.Object(id=int(os.getenv('MY_GUILD')))
logging.basicConfig(filename='/root/dev/acosmicord-bot/logs.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class Burn(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name = "burn", description = "set attribute to 0 for target") 
    async def burn(self, interaction: discord.Interaction, target: discord.Member, column: typing.Literal['currency', 'exp', 'daily', 'streak', "level"]):
        role = discord.utils.get(interaction.guild.roles, name="Acosmic")
        dao = UserDao()
        if role in interaction.user.roles:
            target_user = dao.get_user(target.id)

            if column == "currency":
                target_user.currency = 0

            if column == "exp":
                target_user.exp = 0

            if column == "daily":
                target_user.daily = 0

            if column == "streak":
                target_user.daily = 0

            if column == "level":
                target_user.level = 0            

            try:
                dao.update_user(target_user)
                await interaction.response.send_message(f"{interaction.user.name} has burned {target.mention}'s {column} to 0! <a:pepesith:1165101386921418792>")
            except Exception as e:
                logging.info(f'/give command - target = {target.name} - {e}.')
        else:
            await interaction.response.send_message(f'only {role} can run this command. <:FeelsNaughty:1199732493792858214>', ephemeral=True)
   
                
async def setup(bot: commands.Bot):
    await bot.add_cog(Burn(bot))