#! /usr/bin/python3.10
import typing
import discord
from discord.ext import commands
from discord import app_commands
import json

from Dao.GuildUserDao import GuildUserDao
from Dao.GuildDao import GuildDao
from Views.Blackjack_View import Blackjack_View
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class Blackjack(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

        # Default configuration
        self.default_config = {
            "enabled": True,
            "min_bet": 50,
            "max_bet": 10000,
            "bet_options": [50, 100, 500, 1000, 5000, 10000],
            "blackjack_multiplier": 1.5,
            "num_decks": 6,
            "allow_split": True,
            "allow_insurance": True,
            "allow_surrender": True,
            "allow_double_after_split": True,
            "persistent_shoe": False,
            "show_strategy_hints": False
        }

    def get_blackjack_config(self, guild_id):
        """Get blackjack configuration from guild settings"""
        try:
            guild_dao = GuildDao()
            guild = guild_dao.get_guild(guild_id)

            if not guild or not guild.settings:
                return self.default_config

            # Parse settings JSON
            settings = json.loads(guild.settings) if isinstance(guild.settings, str) else guild.settings

            # Get games.blackjack-config or return default
            games_settings = settings.get("games", {})
            blackjack_config = games_settings.get("blackjack-config", {})

            # Merge with defaults
            config = self.default_config.copy()
            config.update(blackjack_config)

            return config

        except Exception as e:
            logger.error(f"Error getting blackjack config: {e}")
            return self.default_config

    async def bet_autocomplete(self, interaction: discord.Interaction, current: str) -> typing.List[
        app_commands.Choice[int]]:
        """Provide bet options based on guild configuration"""
        try:
            config = self.get_blackjack_config(interaction.guild.id)
            bet_options = config.get("bet_options", [50, 100, 500, 1000, 5000, 10000])

            # Filter options based on current input
            if current:
                try:
                    current_int = int(current)
                    filtered_options = [opt for opt in bet_options if str(opt).startswith(str(current_int))]
                except ValueError:
                    filtered_options = bet_options
            else:
                filtered_options = bet_options

            # Return as choices, limited to 25 (Discord limit)
            choices = [
                app_commands.Choice(name=f"{option:,} credits", value=option)
                for option in filtered_options[:25]
            ]

            return choices

        except Exception as e:
            logger.error(f"Error in bet autocomplete: {e}")
            # Return default options on error
            return [
                app_commands.Choice(name="50 credits", value=50),
                app_commands.Choice(name="100 credits", value=100),
                app_commands.Choice(name="500 credits", value=500),
                app_commands.Choice(name="1,000 credits", value=1000),
                app_commands.Choice(name="5,000 credits", value=5000),
                app_commands.Choice(name="10,000 credits", value=10000)
            ]

    @app_commands.command(name="blackjack", description="Play blackjack against the dealer")
    @app_commands.describe(bet="Choose your bet amount")
    @app_commands.autocomplete(bet=bet_autocomplete)
    async def blackjack(self, interaction: discord.Interaction, bet: int):
        """Play a game of blackjack"""
        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        # Get configuration
        config = self.get_blackjack_config(interaction.guild.id)

        # Check if blackjack is enabled
        if not config["enabled"]:
            await interaction.response.send_message("Blackjack is currently disabled on this server.", ephemeral=True)
            return

        # Get DAOs and user objects
        guild_user_dao = GuildUserDao()
        current_guild_user = guild_user_dao.get_guild_user(interaction.user.id, interaction.guild.id)

        if current_guild_user is None:
            await interaction.response.send_message(
                "You need to send a message first to initialize your account!",
                ephemeral=True
            )
            return

        # Validate bet amount
        cost = abs(bet)

        # Check if bet is in allowed options
        allowed_bets = config.get("bet_options", [50, 100, 500, 1000, 5000, 10000])
        if cost not in allowed_bets:
            bet_list = ", ".join([f"{b:,}" for b in allowed_bets])
            await interaction.response.send_message(
                f"Invalid bet amount. Allowed bets: {bet_list} credits.",
                ephemeral=True
            )
            return

        if cost < config["min_bet"]:
            await interaction.response.send_message(
                f"Minimum bet is {config['min_bet']:,} credits.",
                ephemeral=True
            )
            return

        if cost > config["max_bet"]:
            await interaction.response.send_message(
                f"Maximum bet is {config['max_bet']:,} credits.",
                ephemeral=True
            )
            return

        if current_guild_user.currency < cost:
            await interaction.response.send_message(
                "You don't have enough credits to place this bet.",
                ephemeral=True
            )
            return

        # Deduct bet from user's currency
        current_guild_user.currency -= cost
        guild_user_dao.update_guild_user(current_guild_user)

        # Create and send game view
        game_view = Blackjack_View(
            player=interaction.user,
            bet=cost,
            guild_id=interaction.guild.id,
            config=config
        )

        await game_view.send(interaction)

        logger.info(f"{interaction.user.name} started a blackjack game with bet {cost}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Blackjack(bot))
