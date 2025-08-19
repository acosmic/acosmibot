import discord
from discord.ext import commands
from discord import app_commands
from Dao.GuildUserDao import GuildUserDao
from Views.Deathroll_View import Deathroll_View
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class Deathroll(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="deathroll", description="Start a game of Deathroll. First person to roll a 1 loses!")
    async def deathroll(self, interaction: discord.Interaction, target: discord.Member, bet: int):

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

        if bet > current_user.currency:
            await interaction.response.send_message(
                f"You don't have enough to make this bet! You have {current_user.currency:,.0f} Credits.",
                ephemeral=True)
            return

        target_user = guild_user_dao.get_guild_user(target.id, interaction.guild.id)

        if not target_user:
            await interaction.response.send_message(
                f"{target.display_name} needs to be registered in this server first. They should send a message to get started!",
                ephemeral=True)
            return

        if bet > target_user.currency:
            await interaction.response.send_message(
                f"{target.display_name} doesn't have enough to accept this bet! They have {target_user.currency:,.0f} Credits",
                ephemeral=True)
            return

        # Create the Deathroll view - no need to check for existing games
        view = Deathroll_View(timeout=120, is_matchmaking=True)
        view.initiator = interaction.user
        view.target = target
        view.guild_id = interaction.guild.id
        view.bet = bet
        await view.send(interaction)
        logger.info(
            f"{interaction.user.name} has challenged {target.name} to Deathroll in guild {interaction.guild.name}.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Deathroll(bot))