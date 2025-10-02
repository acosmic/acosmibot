import math
import typing
import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime
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

        # Default configuration
        self.default_config = {
            "enabled": True,
            "symbols": ["🍒", "🍋", "🍊", "🍇", "🍎", "🍌", "⭐", "🔔", "💎", "🎰", "🍀", "❤️"],
            "match_two_multiplier": 2,
            "match_three_multiplier": 5,
            "min_bet": 10,
            "max_bet": 2000,
            "bet_options": [10, 100, 200, 300, 500, 1000, 2000]
        }

    def get_slots_config(self, guild_id):
        """Get slots configuration from guild settings"""
        try:
            guild_dao = GuildDao()
            guild = guild_dao.get_guild(guild_id)

            if not guild or not guild.settings:
                return self.default_config

            # Parse settings JSON
            settings = json.loads(guild.settings) if isinstance(guild.settings, str) else guild.settings

            # Get games.slots-config or return default
            games_settings = settings.get("games", {})
            slots_config = games_settings.get("slots-config", {})

            # Merge with defaults
            config = self.default_config.copy()
            config.update(slots_config)

            return config

        except Exception as e:
            logger.error(f"Error getting slots config: {e}")
            return self.default_config

    async def bet_autocomplete(self, interaction: discord.Interaction, current: str) -> typing.List[
        app_commands.Choice[int]]:
        """Provide bet options based on guild configuration"""
        try:
            config = self.get_slots_config(interaction.guild.id)
            bet_options = config.get("bet_options", [10, 100, 200, 300, 500, 1000, 2000])

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
                app_commands.Choice(name="10 credits", value=10),
                app_commands.Choice(name="100 credits", value=100),
                app_commands.Choice(name="200 credits", value=200),
                app_commands.Choice(name="300 credits", value=300),
                app_commands.Choice(name="500 credits", value=500),
                app_commands.Choice(name="1,000 credits", value=1000),
                app_commands.Choice(name="2,000 credits", value=2000)
            ]

    @app_commands.command(name="slots", description="Play a simple slots game")
    @app_commands.describe(bet="Choose your bet amount")
    @app_commands.autocomplete(bet=bet_autocomplete)
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
        slotDao = SlotsDao()
        guildDao = GuildDao()

        current_guild_user = guild_user_dao.get_guild_user(interaction.user.id, interaction.guild.id)

        if current_guild_user is None:
            await interaction.response.send_message("You need to send a message first to initialize your account!",
                                                    ephemeral=True)
            return

        # Validate bet amount
        cost = abs(bet)

        # Check if bet is in allowed options
        allowed_bets = config.get("bet_options", [10, 100, 200, 300, 500, 1000, 2000])
        if cost not in allowed_bets:
            bet_list = ", ".join([f"{b:,}" for b in allowed_bets])
            await interaction.response.send_message(f"Invalid bet amount. Allowed bets: {bet_list} credits.",
                                                    ephemeral=True)
            return

        if cost < config["min_bet"]:
            await interaction.response.send_message(f"Minimum bet is {config['min_bet']:,} credits.", ephemeral=True)
            return

        if cost > config["max_bet"]:
            await interaction.response.send_message(f"Maximum bet is {config['max_bet']:,} credits.", ephemeral=True)
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

        # Check for wins
        if slot1 == slot2 == slot3:
            # Three of a kind - jackpot
            amount_won = cost * config["match_three_multiplier"]
            embed.description = f"# 🎰 JACKPOT! 🎰\n\n{result}\n\n{interaction.user.mention} won {amount_won:,} credits!"
            embed.color = discord.Color.gold()

        elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
            # Two matching - small win
            amount_won = cost * config["match_two_multiplier"]
            embed.description = f"# 🎰 Nice! 🎰\n\n{result}\n\n{interaction.user.mention} won {amount_won:,} credits!"
            embed.color = discord.Color.green()

        else:
            # Loss
            amount_lost = cost
            embed.description = f"# 🎰 {interaction.user.name} 🎰\n\n{result}\n\nYou lost {amount_lost:,} credits."
            embed.color = discord.Color.red()

        # Update user currency
        current_guild_user.currency += amount_won
        current_guild_user.currency -= amount_lost

        # Save to database
        guild_user_dao.update_guild_user(current_guild_user)

        #update bank currency
        guildDao.add_vault_currency(interaction.guild_id, (int(amount_lost*.1)))

        # Log the event
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_event = SlotEvent(0, interaction.user.id, slot1, slot2, slot3, cost, amount_won, amount_lost, timestamp)
        slotDao.add_new_event(new_event)

        await interaction.response.send_message(embed=embed)
        logger.info(f"{interaction.user.name} used /slots command")


async def setup(bot: commands.Bot):
    await bot.add_cog(Slots(bot))