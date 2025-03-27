import discord
from discord.ext import commands
from discord import app_commands
from Dao.LotteryEventDao import LotteryEventDao
from Dao.VaultDao import VaultDao
from Entities.LotteryEvent import LotteryEvent
from datetime import datetime, timedelta
from logger import AppLogger

logger = AppLogger(__name__).get_logger()

class Admin_Start_Lotto(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot


    @app_commands.command(name = "admin-start-lotto", description = "Start a lottery.")
    async def admin_start_lotto(self, interaction: discord.Interaction, duration: int):
        acosmic = discord.utils.get(interaction.guild.roles, name="Acosmic")
        ashbo = discord.utils.get(interaction.guild.roles, name='Ashbo')
        general_channel = self.bot.get_channel(1155577095787917384) # Acosmicord general channel id 1155577095787917384
        if (acosmic in interaction.user.roles) or (ashbo in interaction.user.roles):
            try:
                le_dao = LotteryEventDao()
                # current_lottery = le_dao.get_current_event()
                vdao = VaultDao()
                vault_credits = vdao.get_currency()
                
                await general_channel.send(f'# React with 🎟️ to enter the lottery! There is currently {vault_credits:,.0f} Credits in the Vault.\nThe winner will be announced in {duration} hour(s)! <a:pepesith:1165101386921418792>')

                message = await general_channel.send("https://cdn.discordapp.com/attachments/1207159417980588052/1283246286442725376/ac_lottery-halloween.png?ex=66fca9bc&is=66fb583c&hm=12a56c05fb30078a2f0ddcfa345b1c264985bda3554550681a0e61424b68f0d8&")
                
                await message.add_reaction('🎟️')
                end_time = datetime.now() + timedelta(hours=duration, minutes=0)
                new_le = LotteryEvent(0, message.id, datetime.now(), end_time, 0, 0)
                
                await message.pin()
                
                le_dao.add_new_event(new_le)

                await interaction.response.send_message(f'Lottery started! The winner will be announced in {duration} hours at {end_time.strftime("%I:%M %p")}.', ephemeral=True)
                
            except Exception as e:
                logger.info(f'/start-lotto command - {e}.')
        else:
            await interaction.response.send_message(f'only {role} can run this command. <:FeelsNaughty:1199732493792858214>')

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin_Start_Lotto(bot))