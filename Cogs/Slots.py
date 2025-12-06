import math
import typing
import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime
import json

from Dao.GamesDao import GamesDao
from Dao.GuildUserDao import GuildUserDao
from Dao.UserDao import UserDao
from Dao.GuildDao import GuildDao
from logger import AppLogger
from Dao.SlotsDao import SlotsDao
from Entities.SlotEvent import SlotEvent

logger = AppLogger(__name__).get_logger()


class Slots(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

        # Default symbol tiers with weights and payout multipliers
        # These are fallback defaults if guild hasn't configured custom emojis
        self.default_symbols_config = [
            # Common (flattened distribution for fairer gameplay)
            {"emoji": "🍒", "name": "Cherry",   "weight": 30, "tier": "common"},
            {"emoji": "🍋", "name": "Lemon",    "weight": 28, "tier": "common"},
            {"emoji": "🍊", "name": "Orange",   "weight": 26, "tier": "common"},
            {"emoji": "🍇", "name": "Grapes",   "weight": 24, "tier": "common"},
            {"emoji": "🍌", "name": "Banana",   "weight": 22, "tier": "common"},
            # Uncommon (slightly increased)
            {"emoji": "⭐", "name": "Star",     "weight": 12, "tier": "uncommon"},
            {"emoji": "🔔", "name": "Bell",     "weight": 10, "tier": "uncommon"},
            {"emoji": "❤️", "name": "Heart",    "weight": 8,  "tier": "uncommon"},
            # Rare
            {"emoji": "🍀", "name": "Clover",   "weight": 5,  "tier": "rare"},
            # Legendary (increased Diamond for better feel)
            {"emoji": "💎", "name": "Diamond",  "weight": 3,  "tier": "legendary"},
            {"emoji": "🎰", "name": "Jackpot",  "weight": 1,  "tier": "legendary"},
        ]
        # Total weight: 169 (was 159)

        # Tier weights (used when building config from guild settings)
        self.tier_weights = {
            "common": [30, 28, 26, 24, 22],
            "uncommon": [12, 10, 8],
            "rare": [5],
            "legendary": [3, 1]
        }

        # Hardcoded global rules (same for all servers)
        self.MIN_BET = 100
        self.MAX_BET = 25000
        self.BET_OPTIONS = [100, 1000, 5000, 10000, 25000]

        # Base multipliers (conservative with 2-match payouts)
        self.BASE_MULTIPLIERS = {
            2: 0.5,   # Half bet back for single pair
            3: 3,     # Reduced from 5 (compensates for 2-match)
            4: 15,    # Reduced from 30
            5: 100    # Reduced from 150
        }
        self.LEGENDARY_BONUS = 10  # ×10 extra on 5 legendary symbols → ×1000 total
        self.DOUBLE_PAIR_MULTIPLIER = 1  # Break even for two pairs

    def build_symbols_config_from_tiers(self, tier_emojis):
        """Build symbols config from guild's tier-based emoji configuration"""
        symbols_config = []

        for tier in ["common", "uncommon", "rare", "legendary"]:
            tier_emoji_list = tier_emojis.get(tier, [])
            tier_weight_list = self.tier_weights.get(tier, [])

            # Assign weights to emojis in this tier
            for idx, emoji in enumerate(tier_emoji_list):
                # Use tier-specific weight, or default to last weight if we run out
                weight = tier_weight_list[idx] if idx < len(tier_weight_list) else tier_weight_list[-1]
                symbols_config.append({
                    "emoji": emoji,
                    "name": f"{tier.capitalize()}-{idx+1}",
                    "weight": weight,
                    "tier": tier
                })

        return symbols_config if symbols_config else self.default_symbols_config

    def get_slots_config(self, guild_id):
        """Get slots configuration including emoji tiers from guild settings"""
        try:
            guild_dao = GuildDao()
            guild = guild_dao.get_guild(guild_id)
            enabled = True
            symbols_config = self.default_symbols_config

            if guild and guild.settings:
                settings = json.loads(guild.settings) if isinstance(guild.settings, str) else guild.settings
                games_settings = settings.get("games", {})
                if not games_settings.get("enabled", False):
                    enabled = False
                else:
                    slots_config = games_settings.get("slots-config", {})
                    enabled = slots_config.get("enabled", True)

                    # Check if guild has configured tier-based emojis
                    tier_emojis = slots_config.get("tier_emojis", {})
                    if tier_emojis:
                        symbols_config = self.build_symbols_config_from_tiers(tier_emojis)

            return {
                "enabled": enabled,
                "symbols_config": symbols_config,
                "min_bet": self.MIN_BET,
                "max_bet": self.MAX_BET,
                "bet_options": self.BET_OPTIONS
            }
        except Exception as e:
            logger.error(f"Error getting slots config: {e}")
            return {
                "enabled": True,
                "symbols_config": self.default_symbols_config,
                "min_bet": self.MIN_BET,
                "max_bet": self.MAX_BET,
                "bet_options": self.BET_OPTIONS
            }

    def spin_reel(self, symbols_config):
        """Spin the reels using provided symbols configuration"""
        emojis = [s["emoji"] for s in symbols_config]
        weights = [s["weight"] for s in symbols_config]
        return random.choices(emojis, weights=weights, k=5)

    def render_slots(self, reels):
        """Render slots in simple pipe format like 3-reel slots"""
        return f"# | {' | '.join(reels)} |"

    def find_all_matches(self, reels, symbols_config):
        """Find all consecutive matching sequences in reels (left to right)"""
        matches = []
        i = 0
        while i < len(reels):
            symbol = reels[i]
            count = 1
            j = i + 1
            while j < len(reels) and reels[j] == symbol:
                count += 1
                j += 1
            if count >= 2:
                symbol_config = next((s for s in symbols_config if s["emoji"] == symbol), None)
                tier = symbol_config["tier"] if symbol_config else "common"
                matches.append({
                    "symbol": symbol,
                    "count": count,
                    "start": i,
                    "tier": tier
                })
            i = j
        return matches

    @app_commands.command(name="slots", description="Play slots! Match symbols to win credits!")
    @app_commands.describe(bet="Bet amount (100 - 25,000 credits)")
    async def slots(self, interaction: discord.Interaction, bet: int):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        config = self.get_slots_config(interaction.guild.id)
        if not config["enabled"]:
            await interaction.response.send_message("Slots is currently disabled on this server.", ephemeral=True)
            return

        # Get the symbols configuration for this guild
        symbols_config = config["symbols_config"]

        cost = abs(bet)
        if cost < self.MIN_BET:
            await interaction.response.send_message(f"Minimum bet is {self.MIN_BET:,} credits.", ephemeral=True)
            return
        if cost > self.MAX_BET:
            await interaction.response.send_message(f"Maximum bet is {self.MAX_BET:,} credits.", ephemeral=True)
            return

        guild_user_dao = GuildUserDao()
        user = guild_user_dao.get_guild_user(interaction.user.id, interaction.guild.id)
        if not user or user.currency < cost:
            await interaction.response.send_message("You don't have enough credits!", ephemeral=True)
            return

        # SPIN!
        reels = self.spin_reel(symbols_config)
        display = self.render_slots(reels)

        # Find all consecutive matches from left to right
        all_matches = self.find_all_matches(reels, symbols_config)

        # Use nickname if available, otherwise username
        user_display_name = interaction.user.display_name

        embed = discord.Embed(color=discord.Color.gold())
        # Description will be updated after calculating results

        amount_won = 0
        amount_lost = cost
        result_text = ""

        # Determine payout based on matches
        if not all_matches:
            # No matches - full loss
            result_text = "**No win this time...**"
            embed.color = discord.Color.red()

        elif len(all_matches) >= 2 and all_matches[0]["count"] == 2 and all_matches[1]["count"] == 2:
            # Two separate 2-matches = break even (1x)
            amount_won = cost
            amount_lost = 0
            result_text = f"**DOUBLE PAIR!** {all_matches[0]['symbol']} {all_matches[1]['symbol']} Break even! 🎲"
            embed.color = discord.Color.blue()

        elif all_matches[0]["count"] >= 3:
            # 3+ matches - use base multipliers
            primary = all_matches[0]
            base_mult = self.BASE_MULTIPLIERS[primary["count"]]
            multiplier = base_mult

            # Legendary bonus for 5 matching legendary symbols
            if primary["count"] == 5 and primary["tier"] == "legendary":
                multiplier = base_mult * self.LEGENDARY_BONUS  # 100 × 10 = 1000x

            amount_won = cost * multiplier
            amount_lost = 0

            win_phrases = {
                3: f"**THREE OF A KIND!** {primary['symbol']} ×{multiplier}",
                4: f"**FOUR IN A ROW!** {primary['symbol']} ×{multiplier} 🔥",
                5: f"**JACKPOT! FIVE IN A ROW!!** {primary['symbol']} ×{multiplier} 💰"
            }
            result_text = win_phrases.get(primary["count"], f"×{multiplier} WIN!")

            embed.color = discord.Color.gold() if primary["count"] == 5 else discord.Color.green()

        elif all_matches[0]["count"] == 2:
            # Single 2-match - half bet back (0.5x)
            # Player gets half their bet back, loses the other half
            amount_won = cost // 2
            amount_lost = cost  # They still lost the full bet initially
            result_text = f"**PAIR!** {all_matches[0]['symbol']} Half back ↩️"
            embed.color = discord.Color.light_grey()

        net = amount_won - amount_lost
        guild_user_dao.update_currency_with_global_sync(interaction.user.id, interaction.guild.id, net)
        GuildDao().add_vault_currency(interaction.guild_id, int(amount_lost * 0.1))

        # Build description with all info (for proper markdown rendering)
        description_parts = [
            f"# 🎰 {user_display_name} 🎰",
            "",
            display,
            "",
            result_text or "No win this time...",
            ""
        ]

        # Add bet/win/loss info
        bet_info = f"Bet: **{cost:,}** credits"
        if amount_won > cost:
            bet_info += f" → Won **{amount_won:,}** credits (+{amount_won - cost:,})"
        elif amount_won > 0:
            bet_info += f" → Won **{amount_won:,}** credits (±{amount_won - cost:,})"
        else:
            bet_info += f" → Lost **{cost:,}** credits"

        description_parts.append(bet_info)

        # Add tier info if there were matches
        if all_matches:
            primary_tier = all_matches[0]["tier"].capitalize()
            description_parts.append(f"{all_matches[0]['symbol']} = {primary_tier} tier")

        embed.description = "\n".join(description_parts)

        # Log game
        try:
            # Calculate match count from all_matches
            match_count = all_matches[0]["count"] if all_matches else 0

            GamesDao().add_game(
                user_id=interaction.user.id,
                guild_id=interaction.guild.id,
                game_type="slots",
                amount_bet=cost,
                amount_won=amount_won,
                amount_lost=amount_lost,
                result="win" if amount_won > 0 else "lose",
                game_data={"reels": reels, "matches": match_count, "multiplier": amount_won / cost if amount_won else 0}
            )
        except Exception as e:
            logger.error(f"Failed to log slots game: {e}")

        await interaction.response.send_message(embed=embed)
        logger.info(f"{interaction.user} played 5-reel slots | Bet: {cost} | Won: {amount_won}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Slots(bot))



# import math
# import typing
# import discord
# from discord.ext import commands
# from discord import app_commands
# import random
# from datetime import datetime
#
# from Dao.GamesDao import GamesDao
# from Dao.GuildUserDao import GuildUserDao
# from Dao.UserDao import UserDao
# from Dao.GuildDao import GuildDao
# from logger import AppLogger
# from Dao.SlotsDao import SlotsDao
# from Entities.SlotEvent import SlotEvent
# import json
#
# logger = AppLogger(__name__).get_logger()
#
#
# class Slots(commands.Cog):
#     def __init__(self, bot: commands.Bot):
#         super().__init__()
#         self.bot = bot
#
#         # Default symbols
#         self.default_symbols = ["🍒", "🍋", "🍊", "🍇", "🍎", "🍌", "⭐", "🔔", "💎", "🎰", "🍀", "❤️"]
#
#         # Global hardcoded configuration (for fairness in leaderboards)
#         # These values are the same for all guilds and cannot be customized
#         self.MATCH_TWO_MULTIPLIER = 2
#         self.MATCH_THREE_MULTIPLIER = 10
#         self.MIN_BET = 100
#         self.MAX_BET = 25000
#         self.BET_OPTIONS = [100, 1000, 5000, 10000, 25000]
#
#     def get_slots_config(self, guild_id):
#         """Get slots configuration - only enabled/symbols from DB, rest hardcoded"""
#         try:
#             guild_dao = GuildDao()
#             guild = guild_dao.get_guild(guild_id)
#
#             # Default values
#             enabled = True
#             symbols = self.default_symbols
#
#             if guild and guild.settings:
#                 # Parse settings JSON
#                 settings = json.loads(guild.settings) if isinstance(guild.settings, str) else guild.settings
#
#                 # Get games settings
#                 games_settings = settings.get("games", {})
#
#                 # Check parent games toggle FIRST
#                 if not games_settings.get("enabled", False):
#                     enabled = False
#                 else:
#                     # Get slots-specific config
#                     slots_config = games_settings.get("slots-config", {})
#                     enabled = slots_config.get("enabled", True)
#                     symbols = slots_config.get("symbols", self.default_symbols)
#
#             # Return config with hardcoded bet values
#             return {
#                 "enabled": enabled,
#                 "symbols": symbols,
#                 # Hardcoded values (cannot be customized per guild)
#                 "match_two_multiplier": self.MATCH_TWO_MULTIPLIER,
#                 "match_three_multiplier": self.MATCH_THREE_MULTIPLIER,
#                 "min_bet": self.MIN_BET,
#                 "max_bet": self.MAX_BET,
#                 "bet_options": self.BET_OPTIONS
#             }
#
#         except Exception as e:
#             logger.error(f"Error getting slots config: {e}")
#             # Return defaults on error
#             return {
#                 "enabled": True,
#                 "symbols": self.default_symbols,
#                 "match_two_multiplier": self.MATCH_TWO_MULTIPLIER,
#                 "match_three_multiplier": self.MATCH_THREE_MULTIPLIER,
#                 "min_bet": self.MIN_BET,
#                 "max_bet": self.MAX_BET,
#                 "bet_options": self.BET_OPTIONS
#             }
#
#     @app_commands.command(name="slots", description="Play a simple slots game")
#     @app_commands.describe(bet="Bet amount (100 - 25,000 credits)")
#     async def slots(self, interaction: discord.Interaction, bet: int):
#         # Only work in guilds
#         if not interaction.guild:
#             await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
#             return
#
#         # Get configuration
#         config = self.get_slots_config(interaction.guild.id)
#
#         # Check if slots is enabled
#         if not config["enabled"]:
#             await interaction.response.send_message("Slots is currently disabled on this server.", ephemeral=True)
#             return
#
#         # Get DAOs and user objects
#         guild_user_dao = GuildUserDao()
#         slots_dao = SlotsDao()
#         games_dao = GamesDao()  # ADD THIS
#         guild_dao = GuildDao()
#
#         current_guild_user = guild_user_dao.get_guild_user(interaction.user.id, interaction.guild.id)
#
#         if current_guild_user is None:
#             await interaction.response.send_message("You need to send a message first to initialize your account!",
#                                                     ephemeral=True)
#             return
#
#         # Validate bet amount
#         cost = abs(bet)
#
#         # Check min and max bet (any amount between 100 and 25,000)
#         if cost < self.MIN_BET:
#             await interaction.response.send_message(f"Minimum bet is {self.MIN_BET:,} credits.", ephemeral=True)
#             return
#
#         if cost > self.MAX_BET:
#             await interaction.response.send_message(f"Maximum bet is {self.MAX_BET:,} credits.", ephemeral=True)
#             return
#
#         if current_guild_user.currency < cost:
#             await interaction.response.send_message("You don't have enough credits to place this bet.", ephemeral=True)
#             return
#
#         # Spin the slots - completely random
#         symbols = config["symbols"]
#         slot1 = random.choice(symbols)
#         slot2 = random.choice(symbols)
#         slot3 = random.choice(symbols)
#
#         result = f"# | {slot1} | {slot2} | {slot3} |"
#         embed = discord.Embed()
#
#         amount_won = 0
#         amount_lost = 0
#         game_result = ""
#
#         # Check for wins
#         if slot1 == slot2 == slot3:
#             # Three of a kind - jackpot
#             amount_won = cost * self.MATCH_THREE_MULTIPLIER
#             game_result = "win"
#             embed.description = f"# 🎰 JACKPOT! 🎰\n\n{result}\n\n{interaction.user.mention} won {amount_won:,} credits!"
#             embed.color = discord.Color.gold()
#
#         elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
#             # Two matching - small win
#             amount_won = cost * self.MATCH_TWO_MULTIPLIER
#             game_result = "win"
#             embed.description = f"# 🎰 Nice! 🎰\n\n{result}\n\n{interaction.user.mention} won {amount_won:,} credits!"
#             embed.color = discord.Color.green()
#
#         else:
#             # Loss
#             amount_lost = cost
#             game_result = "lose"
#             embed.description = f"# 🎰 {interaction.user.name} 🎰\n\n{result}\n\nYou lost {amount_lost:,} credits."
#             embed.color = discord.Color.red()
#
#         # Update user currency and global stats
#         currency_delta = amount_won - amount_lost
#         guild_user_dao.update_currency_with_global_sync(interaction.user.id, interaction.guild.id, currency_delta)
#         current_guild_user.currency += amount_won
#         current_guild_user.currency -= amount_lost  # Update local object for display
#
#         # Update bank currency
#         guild_dao.add_vault_currency(interaction.guild_id, int(amount_lost * 0.1))
#
#         # Calculate multiplier
#         multiplier = amount_won / cost if (cost > 0 and amount_won > 0) else 0.0
#
#         games_dao = GamesDao()
#         game_result = "win" if amount_won > 0 else "lose"
#
#         game_id = games_dao.add_game(
#             user_id=interaction.user.id,
#             guild_id=interaction.guild.id,
#             game_type="slots",
#             amount_bet=cost,
#             amount_won=amount_won,
#             amount_lost=amount_lost,
#             result=game_result,
#             game_data={"symbols": [slot1, slot2, slot3], "multiplier": multiplier}  # JSON!
#         )
#
#         if not game_id:
#             logger.error("Failed to log slots game")
#
#         await interaction.response.send_message(embed=embed)
#         logger.info(f"{interaction.user.name} used /slots command")
#
#
# async def setup(bot: commands.Bot):
#     await bot.add_cog(Slots(bot))