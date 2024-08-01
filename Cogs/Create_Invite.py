import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from logger import AppLogger

logger = AppLogger(__name__).get_logger()

class Create_Invite(commands.Cog):
    def __init__(self, bot:commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name = "create_invite", description = "Creates a new invite link.")
    async def create_invite(self, interaction: discord.Interaction):
        guild = interaction.guild
        invite = await guild.text_channels[0].create_invite(max_age=0, max_uses=1, unique=True)
        await interaction.response.send_message(f"Invite link: {invite.url}")
        logger.info(f"{interaction.user.name} used /create_invite")