import discord
from discord.ext import commands
from discord import app_commands
from Dao.GuildUserDao import GuildUserDao
from Dao.UserDao import UserDao
from Views.View_Rock_Paper_Scissors import View_Rock_Paper_Scissors
from Services.SessionManager import get_session_manager
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class Rock_Paper_Scissors(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="rockpaperscissors",
                          description="Challenge another member to a game of Rock, Paper, Scissors. Win 3 rounds!")
    async def rock_paper_scissors(self, interaction: discord.Interaction, bet: int):

        # Use GuildUserDao for multi-guild support
        guild_user_dao = GuildUserDao()
        user_dao = UserDao()
        current_user = guild_user_dao.get_guild_user(interaction.user.id, interaction.guild.id)

        if not current_user:
            await interaction.response.send_message(
                f"You need to be registered in this server first. Send a message to get started!", ephemeral=True)
            return

        # Get or create session for currency tracking
        session_manager = get_session_manager()
        session = await session_manager.get_or_create_session(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            guild_user_dao=guild_user_dao,
            user_dao=user_dao
        )

        # Get current currency from session if available
        if session:
            current_currency = session.get("currency", current_user.currency)
        else:
            current_currency = current_user.currency

        if bet > current_currency:
            await interaction.response.send_message(
                f"You don't have enough credits to make this bet! You have {current_currency} credits.",
                ephemeral=True)
            return

        if bet < 0:
            await interaction.response.send_message(f"Bet amount must be positive!", ephemeral=True)
            return

        # Create the RPS view (pass session_manager)
        view = View_Rock_Paper_Scissors(timeout=120, is_matchmaking=True, session_manager=session_manager)
        view.initiator = interaction.user
        view.guild_id = interaction.guild.id
        view.bet = bet
        await view.send(interaction)
        logger.info(
            f"{interaction.user.name} has started a game of Rock, Paper, Scissors in guild {interaction.guild.name}.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Rock_Paper_Scissors(bot))