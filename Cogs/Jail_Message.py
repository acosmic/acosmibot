import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from logger import AppLogger

logger = AppLogger(__name__).get_logger()

class Jail_Message(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    @app_commands.command(name="jailmail", description="send a message to or from the jail. Costs 50,000 credits.")
    async def jail(self, interaction: discord.Interaction, mail: str):
        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return
        cost = 50000
        dao = UserDao()
        user = dao.get_user(interaction.user.id)

        general_channel = self.bot.get_channel(1155577095787917384)
        jail_channel = self.bot.get_channel(1233867818055893062)

        if user.currency < cost:
            await interaction.response.send_message("You do not have enough credits for /jailmail.", ephemeral=True)
            return
        
        # CHECK IF USER IS IN JAIL OR GENERAL  
        else:
            # SEND MESSAGE TO JAIL
            if interaction.channel == general_channel:
                message_text = f"### {interaction.user.name} spent {cost} credits to send a message to Jail: \n ## {interaction.user.name}: {mail}"
                await jail_channel.send(f"### Jail Mail: \n ## {interaction.user.name}: {mail}")

            # SEND MESSAGE TO GENERAL
            elif interaction.channel == jail_channel:
                message_text = f"### {interaction.user.name} spent {cost} credits to send a message to the General: \n ## message: {mail}"
                await general_channel.send(f"### Jail Mail: \n ## {interaction.user.name}: {mail}")

            # DEDUCT CREDITS    
            user.currency -= cost
            dao.update_user(user)

        
        await interaction.response.send_message(message_text)
        logger.info(f"{interaction.user.name} used /jail command")


async def setup(bot: commands.Bot):
    await bot.add_cog(Jail_Message(bot))


    