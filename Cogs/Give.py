import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from logger import AppLogger

logger  = AppLogger(__name__).get_logger()

class Give(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name = "give", description = "Give Credits to your target user.") 
    async def give(self, interaction: discord.Interaction, target: discord.Member, amount: int):
        
        # role = discord.utils.get(interaction.guild.roles, name="Acosmic")
        dao = UserDao()
        # if role in interaction.user.roles:
        #     target_user = dao.get_user(target.id)
        #     target_user.currency += amount
        #     try:
        #         dao.update_user(target_user)
        #         await interaction.response.send_message(f'### {interaction.user.name} has given {target.mention} {amount:,.0f} credits! <a:pepesith:1165101386921418792>')
        #     except Exception as e:
        #         logging.info(f'/give command - target = {target.name} - {e}.')
        # else:
            # await interaction.response.send_message(f'only {role} can run this command. <:FeelsNaughty:1199732493792858214>')
        giving_user = dao.get_user(interaction.user.id)
        target_user = dao.get_user(target.id)

        if amount > giving_user.currency:
            await interaction.response.send_message(f"{interaction.user.name}, your heart is bigger than your wallet. You don't have {amount:,.0f} Credits to give. <:FeelsBigSad:1199734765230768139>")
            logger.info(f"{interaction.user.name} tried to give {amount:,.0f} Credits to {target.name} but didn't have enough Credits.")

        elif interaction.user.id == target.id:
            await interaction.response.send_message(f"{interaction.user.name}, you can't give yourself Credits. <:FeelsNaughty:1199732493792858214>")
            logger.info(f"{interaction.user.name} tried to give themselves Credits.")
        else:
            giving_user.currency -= amount
            target_user.currency += amount
            dao.update_user(giving_user)
            dao2 = UserDao()
            dao2.update_user(target_user)
            await interaction.response.send_message(f'### {interaction.user.name} has given {target.mention} {amount:,.0f} credits! <:PepePimp:1200268145693302854>')
            logger.info(f"{interaction.user.name} gave {target.name} {amount:,.0f} Credits.")



async def setup(bot: commands.Bot):
    await bot.add_cog(Give(bot))
        
