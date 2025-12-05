import math
import typing
import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime

from Dao.GamesDao import GamesDao
from Dao.GuildUserDao import GuildUserDao
from Dao.UserDao import UserDao
from Dao.GuildDao import GuildDao
from logger import AppLogger
from Dao.SlotsDao import SlotsDao
from Entities.SlotEvent import SlotEvent
import json

logger = AppLogger(__name__).get_logger()


class Slots(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

        # Default symbols
        self.default_symbols = ["🍒", "🍋", "🍊", "🍇", "🍎", "🍌", "⭐", "🔔", "💎", "🎰", "🍀", "❤️"]

        # Global hardcoded configuration (for fairness in leaderboards)
        # These values are the same for all guilds and cannot be customized
        self.MATCH_TWO_MULTIPLIER = 2
        self.MATCH_THREE_MULTIPLIER = 10
        self.MIN_BET = 100
        self.MAX_BET = 25000
        self.BET_OPTIONS = [100, 1000, 5000, 10000, 25000]

    def get_slots_config(self, guild_id):
        """Get slots configuration - only enabled/symbols from DB, rest hardcoded"""
        try:
            guild_dao = GuildDao()
            guild = guild_dao.get_guild(guild_id)

            # Default values
            enabled = True
            symbols = self.default_symbols

            if guild and guild.settings:
                # Parse settings JSON
                settings = json.loads(guild.settings) if isinstance(guild.settings, str) else guild.settings

                # Get games settings
                games_settings = settings.get("games", {})

                # Check parent games toggle FIRST
                if not games_settings.get("enabled", False):
                    enabled = False
                else:
                    # Get slots-specific config
                    slots_config = games_settings.get("slots-config", {})
                    enabled = slots_config.get("enabled", True)
                    symbols = slots_config.get("symbols", self.default_symbols)

            # Return config with hardcoded bet values
            return {
                "enabled": enabled,
                "symbols": symbols,
                # Hardcoded values (cannot be customized per guild)
                "match_two_multiplier": self.MATCH_TWO_MULTIPLIER,
                "match_three_multiplier": self.MATCH_THREE_MULTIPLIER,
                "min_bet": self.MIN_BET,
                "max_bet": self.MAX_BET,
                "bet_options": self.BET_OPTIONS
            }

        except Exception as e:
            logger.error(f"Error getting slots config: {e}")
            # Return defaults on error
            return {
                "enabled": True,
                "symbols": self.default_symbols,
                "match_two_multiplier": self.MATCH_TWO_MULTIPLIER,
                "match_three_multiplier": self.MATCH_THREE_MULTIPLIER,
                "min_bet": self.MIN_BET,
                "max_bet": self.MAX_BET,
                "bet_options": self.BET_OPTIONS
            }

    @app_commands.command(name="slots", description="Play a simple slots game")
    @app_commands.describe(bet="Bet amount (100 - 25,000 credits)")
    async def slots(self, interaction: discord.Interaction, bet: int):
        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        # Get configuration
        config = self.get_slots_config(interaction.guild.id)

        # Check if slots is enabled
        if not config["enabled"]:
            await interaction.response.send_message("Slots is currently disabled on this server.", ephemeral=True)
            return

        # Get DAOs and user objects
        guild_user_dao = GuildUserDao()
        slots_dao = SlotsDao()
        games_dao = GamesDao()  # ADD THIS
        guild_dao = GuildDao()

        current_guild_user = guild_user_dao.get_guild_user(interaction.user.id, interaction.guild.id)

        if current_guild_user is None:
            await interaction.response.send_message("You need to send a message first to initialize your account!",
                                                    ephemeral=True)
            return

        # Validate bet amount
        cost = abs(bet)

        # Check min and max bet (any amount between 100 and 25,000)
        if cost < self.MIN_BET:
            await interaction.response.send_message(f"Minimum bet is {self.MIN_BET:,} credits.", ephemeral=True)
            return

        if cost > self.MAX_BET:
            await interaction.response.send_message(f"Maximum bet is {self.MAX_BET:,} credits.", ephemeral=True)
            return

        if current_guild_user.currency < cost:
            await interaction.response.send_message("You don't have enough credits to place this bet.", ephemeral=True)
            return

        # Spin the slots - completely random
        symbols = config["symbols"]
        slot1 = random.choice(symbols)
        slot2 = random.choice(symbols)
        slot3 = random.choice(symbols)

        result = f"# | {slot1} | {slot2} | {slot3} |"
        embed = discord.Embed()

        amount_won = 0
        amount_lost = 0
        game_result = ""

        # Check for wins
        if slot1 == slot2 == slot3:
            # Three of a kind - jackpot
            amount_won = cost * self.MATCH_THREE_MULTIPLIER
            game_result = "win"
            embed.description = f"# 🎰 JACKPOT! 🎰\n\n{result}\n\n{interaction.user.mention} won {amount_won:,} credits!"
            embed.color = discord.Color.gold()

        elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
            # Two matching - small win
            amount_won = cost * self.MATCH_TWO_MULTIPLIER
            game_result = "win"
            embed.description = f"# 🎰 Nice! 🎰\n\n{result}\n\n{interaction.user.mention} won {amount_won:,} credits!"
            embed.color = discord.Color.green()

        else:
            # Loss
            amount_lost = cost
            game_result = "lose"
            embed.description = f"# 🎰 {interaction.user.name} 🎰\n\n{result}\n\nYou lost {amount_lost:,} credits."
            embed.color = discord.Color.red()

        # Update user currency and global stats
        currency_delta = amount_won - amount_lost
        guild_user_dao.update_currency_with_global_sync(interaction.user.id, interaction.guild.id, currency_delta)
        current_guild_user.currency += amount_won
        current_guild_user.currency -= amount_lost  # Update local object for display

        # Update bank currency
        guild_dao.add_vault_currency(interaction.guild_id, int(amount_lost * 0.1))

        # Calculate multiplier
        multiplier = amount_won / cost if (cost > 0 and amount_won > 0) else 0.0

        games_dao = GamesDao()
        game_result = "win" if amount_won > 0 else "lose"

        game_id = games_dao.add_game(
            user_id=interaction.user.id,
            guild_id=interaction.guild.id,
            game_type="slots",
            amount_bet=cost,
            amount_won=amount_won,
            amount_lost=amount_lost,
            result=game_result,
            game_data={"symbols": [slot1, slot2, slot3], "multiplier": multiplier}  # JSON!
        )

        if not game_id:
            logger.error("Failed to log slots game")

        await interaction.response.send_message(embed=embed)
        logger.info(f"{interaction.user.name} used /slots command")


async def setup(bot: commands.Bot):
    await bot.add_cog(Slots(bot))