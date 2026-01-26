import discord
from discord.ext import commands
from discord import app_commands
from Dao.GuildUserDao import GuildUserDao
from Dao.UserDao import UserDao
from Views.Deathroll_View import Deathroll_View
from Services.SessionManager import get_session_manager
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class Deathroll(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="deathroll", description="Start a game of Deathroll. First person to roll a 1 loses!")
    async def deathroll(self, interaction: discord.Interaction, target: discord.Member, bet: int):
        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return
        if bet < 100:
            await interaction.response.send_message(f"Please enter a bet of at least 100.", ephemeral=True)
            return

        if bet < 0:
            await interaction.response.send_message(f"Bet amount must be positive!", ephemeral=True)
            return

        if target.id == interaction.user.id:
            await interaction.response.send_message(f"You cannot challenge yourself!", ephemeral=True)
            return

        # Use GuildUserDao for multi-guild support
        guild_user_dao = GuildUserDao()
        current_user = guild_user_dao.get_guild_user(interaction.user.id, interaction.guild.id)

        if not current_user:
            await interaction.response.send_message(
                f"You need to be registered in this server first. Send a message to get started!", ephemeral=True)
            return

        target_user = guild_user_dao.get_guild_user(target.id, interaction.guild.id)

        if not target_user:
            await interaction.response.send_message(
                f"{target.display_name} needs to be registered in this server first. They should send a message to get started!",
                ephemeral=True)
            return

        # Get or create sessions for both players
        user_dao = UserDao()
        session_manager = get_session_manager()

        # Get/create initiator session
        initiator_session = await session_manager.get_or_create_session(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            guild_user_dao=guild_user_dao,
            user_dao=user_dao
        )

        # Get/create target session
        target_session = await session_manager.get_or_create_session(
            guild_id=interaction.guild.id,
            user_id=target.id,
            guild_user_dao=guild_user_dao,
            user_dao=user_dao
        )

        # Get currency from sessions if available
        if initiator_session:
            initiator_currency = initiator_session.get("currency", current_user.currency)
        else:
            initiator_currency = current_user.currency

        if target_session:
            target_currency = target_session.get("currency", target_user.currency)
        else:
            target_currency = target_user.currency

        # Check if both players have enough
        if bet > initiator_currency:
            await interaction.response.send_message(
                f"You don't have enough to make this bet! You have {initiator_currency:,.0f} Credits.",
                ephemeral=True)
            return

        if bet > target_currency:
            await interaction.response.send_message(
                f"{target.display_name} doesn't have enough to accept this bet! They have {target_currency:,.0f} Credits",
                ephemeral=True)
            return

        # Create the Deathroll view (pass session_manager)
        view = Deathroll_View(timeout=120, is_matchmaking=True, session_manager=session_manager)
        view.initiator = interaction.user
        view.target = target
        view.guild_id = interaction.guild.id
        view.bet = bet
        await view.send(interaction)
        logger.info(
            f"{interaction.user.name} has challenged {target.name} to Deathroll in guild {interaction.guild.name}.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Deathroll(bot))