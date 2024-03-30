import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
import logging
import os
from dotenv import load_dotenv

load_dotenv()
MY_GUILD = discord.Object(id=int(os.getenv('MY_GUILD')))
logging.basicConfig(filename='/home/acosmic/Dev/acosmibot/logs.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class Admin_Give(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name = "admin-give", description = "Give Credits to your target user.") 
    async def admin_give(self, interaction: discord.Interaction, target: discord.Member, amount: int):
        
        role = discord.utils.get(interaction.guild.roles, name="Acosmic")
        dao = UserDao()
        if role in interaction.user.roles:
            target_user = dao.get_user(target.id)
            target_user.currency += amount
            try:
                dao.update_user(target_user)
                await interaction.response.send_message(f'### {interaction.user.name} has given {target.mention} {amount:,.0f} credits! <a:pepesith:1165101386921418792>')
            except Exception as e:
                logging.info(f'/give command - target = {target.name} - {e}.')
        else:
            await interaction.response.send_message(f'only {role} can run this command. <:FeelsNaughty:1199732493792858214>')

                



async def setup(bot: commands.Bot):
    await bot.add_cog(Admin_Give(bot))