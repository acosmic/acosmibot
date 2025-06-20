import discord
from discord.ext import commands
from discord import app_commands
from Dao.LotteryEventDao import LotteryEventDao
from Dao.VaultDao import VaultDao
from Entities.LotteryEvent import LotteryEvent
from datetime import datetime, timedelta


import os
from dotenv import load_dotenv
load_dotenv()

from logger import AppLogger

MY_GUILD = discord.Object(id=int(os.getenv('MY_GUILD')))
logger = AppLogger(__name__).get_logger()

class Admin_Start_Lotto(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot


    @app_commands.command(name = "admin-start-lotto", description = "Start a lottery.")
    async def admin_start_lotto(self, interaction: discord.Interaction, duration: int):
        role = discord.utils.get(interaction.guild.roles, name="Acosmic")
        general_channel = self.bot.get_channel(1155577095787917384) # Acosmicord general channel id 1155577095787917384
        if role in interaction.user.roles:
            try:
                le_dao = LotteryEventDao()
                # current_lottery = le_dao.get_current_event()
                vdao = VaultDao()
                vault_credits = vdao.get_currency()
                
                await general_channel.send(f'# React with 🎟️ to enter the lottery! There is currently {vault_credits:,.0f} Credits in the Vault.\nThe winner will be announced in {duration} hour(s)! <a:pepesith:1165101386921418792>')

                message = await general_channel.send("https://cdn.discordapp.com/attachments/1207159417980588052/1207159812656472104/acosmibot-lottery.png?ex=65dea22f&is=65cc2d2f&hm=3a9e07cf1b55f87a1fcd664c766f11636bf55f305b715e0269851f18d154fd23&")
                
                await message.add_reaction('🎟️')
                end_time = datetime.now() + timedelta(hours=duration, minutes=0)
                
                # Create new lottery event with guild_id
                new_le = LotteryEvent(
                    id=0, 
                    message_id=message.id, 
                    start_time=datetime.now(), 
                    end_time=end_time, 
                    credits=0, 
                    winner_id=0,
                    guild_id=interaction.guild_id  # Add guild_id from the interaction
                )
                
                await message.pin()
                
                le_dao.add_new_event(new_le)

                await interaction.response.send_message(f'Lottery started! The winner will be announced in {duration} hours at {end_time.strftime("%I:%M %p")}.', ephemeral=True)
                
            except Exception as e:
                logger.info(f'/start-lotto command - {e}.')
        else:
            await interaction.response.send_message(f'only {role} can run this command. <:FeelsNaughty:1199732493792858214>')

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin_Start_Lotto(bot))