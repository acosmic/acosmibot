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
            # Common (higher weights for better match probability)
            {"emoji": "🍒", "name": "Cherry",   "weight": 35, "tier": "common"},
            {"emoji": "🍋", "name": "Lemon",    "weight": 33, "tier": "common"},
            {"emoji": "🍊", "name": "Orange",   "weight": 31, "tier": "common"},
            {"emoji": "🍇", "name": "Grapes",   "weight": 29, "tier": "common"},
            {"emoji": "🍎", "name": "Apple",    "weight": 27, "tier": "common"},
            {"emoji": "🍌", "name": "Banana",   "weight": 25, "tier": "common"},
            # Uncommon (increased for more matches)
            {"emoji": "⭐", "name": "Star",     "weight": 16, "tier": "uncommon"},
            {"emoji": "🔔", "name": "Bell",     "weight": 14, "tier": "uncommon"},
            {"emoji": "❤️", "name": "Heart",    "weight": 12, "tier": "uncommon"},
            # Rare
            {"emoji": "🍀", "name": "Clover",   "weight": 8,  "tier": "rare"},
            # Legendary (increased for better feel)
            {"emoji": "💎", "name": "Diamond",  "weight": 5,  "tier": "legendary"},
            {"emoji": "🎰", "name": "Jackpot",  "weight": 2,  "tier": "legendary"},
        ]
        # Total weight: 237 (higher weights on common symbols)

        # Tier weights (used when building config from guild settings)
        self.tier_weights = {
            "common": [35, 33, 31, 29, 27, 25],
            "uncommon": [16, 14, 12],
            "rare": [8],
            "legendary": [5, 2]
        }

        # Hardcoded global rules (same for all servers)
        self.MIN_BET = 100
        self.MAX_BET = 25000
        self.BET_OPTIONS = [100, 1000, 5000, 10000, 25000]

        # Base multipliers (whole numbers only)
        self.BASE_MULTIPLIERS = {
            2: 0.5,   # Single pair = half back (0.5x)
            3: 3,     # Base for 3-match
            4: 15,    # Base for 4-match
            5: 100    # Base for 5-match
        }

        # Tier multiplier bonuses (applied on top of base multipliers)
        self.TIER_BONUSES = {
            "common": 1,        # No bonus (×1)
            "uncommon": 2,      # ×2 bonus (e.g., 3-match becomes 3 × 2 = 6x)
            "rare": 3,          # ×3 bonus (e.g., 3-match becomes 3 × 3 = 9x)
            "legendary": 5,     # ×5 bonus (e.g., 3-match becomes 3 × 5 = 15x)
            "scatter": 1        # Scatter acts as wild, uses matched symbol's tier
        }

        self.LEGENDARY_5_MATCH_BONUS = 10  # Additional ×10 for 5 legendary symbols → ×1000 total
        self.DOUBLE_PAIR_MULTIPLIER = 1  # Break even for two pairs (0.5x + 0.5x = 1x)

        # Scatter symbol configuration for bonus rounds
        self.default_scatter_config = {
            "emoji": "⚡",
            "name": "Scatter",
            "weight": 17,  # Fairly common (between uncommon tier)
            "tier": "scatter"
        }

        # Bonus round weight multipliers
        self.BONUS_WEIGHT_MULTIPLIERS = {
            "common": 0.75,      # 25% reduction
            "uncommon": 1.15,    # 15% increase
            "rare": 1.25,        # 25% increase
            "legendary": 1.35,   # 35% increase
            "scatter": 1.0       # No change
        }

        # Scatter trigger thresholds
        self.SCATTER_FREE_SPINS = {
            2: 5,    # 2 scatters = 5 free spins
            3: 10,   # 3 scatters = 10 free spins
            4: 15,   # 4 scatters = 15 free spins
            5: 20    # 5 scatters = 20 free spins
        }

        # Bonus round limits
        self.MAX_FREE_SPINS_WARNING = 100  # Soft cap
        self.MAX_FREE_SPINS_HARD_CAP = 200  # Hard cap

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

    def get_scatter_config(self, guild_id: int) -> dict:
        """Get scatter symbol configuration for a guild."""
        try:
            guild_dao = GuildDao()
            guild = guild_dao.get_guild(guild_id)

            if guild and guild.settings:
                settings = json.loads(guild.settings) if isinstance(guild.settings, str) else guild.settings
                slots_config = settings.get("games", {}).get("slots-config", {})
                tier_emojis = slots_config.get("tier_emojis", {})

                scatter_emojis = tier_emojis.get("scatter", [])
                if scatter_emojis and len(scatter_emojis) > 0:
                    return {
                        "emoji": scatter_emojis[0],
                        "name": "Scatter",
                        "weight": 17,
                        "tier": "scatter"
                    }
            return self.default_scatter_config
        except Exception as e:
            logger.error(f"Error getting scatter config: {e}")
            return self.default_scatter_config

    def get_bonus_symbols_config(self, base_symbols_config: list, scatter_config: dict) -> list:
        """Generate modified symbols configuration for bonus rounds with adjusted weights."""
        bonus_config = []

        for symbol in base_symbols_config:
            tier = symbol["tier"]
            multiplier = self.BONUS_WEIGHT_MULTIPLIERS.get(tier, 1.0)

            bonus_symbol = symbol.copy()
            bonus_symbol["weight"] = int(symbol["weight"] * multiplier)
            bonus_config.append(bonus_symbol)

        # Add scatter symbol to bonus config
        bonus_config.append(scatter_config)
        return bonus_config

    def check_scatter_trigger(self, reels: list, scatter_emoji: str) -> int:
        """
        Check if consecutive scatter symbols trigger bonus round and return free spins awarded.
        Scatters must be adjacent (consecutive) to trigger the bonus.
        """
        max_consecutive = 0
        current_consecutive = 0

        for symbol in reels:
            if symbol == scatter_emoji:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return self.SCATTER_FREE_SPINS.get(max_consecutive, 0) if max_consecutive >= 2 else 0

    def trigger_bonus_round(self, user, guild_user_dao: GuildUserDao,
                           free_spins: int, bet_amount: int) -> bool:
        """Initialize bonus round state for a user."""
        free_spins = min(free_spins, self.MAX_FREE_SPINS_HARD_CAP)

        return guild_user_dao.update_slots_bonus_state(
            user.user_id,
            user.guild_id,
            free_spins,
            bet_amount,
            0  # Reset total won
        )

    def add_retrigger_spins(self, user, guild_user_dao: GuildUserDao,
                           additional_spins: int) -> tuple:
        """Add re-triggered free spins to existing bonus and return (new_total, warning_msg)."""
        new_total = user.slots_free_spins_remaining + additional_spins
        warning_msg = None

        if new_total > self.MAX_FREE_SPINS_WARNING:
            warning_msg = f"⚠️ **Extended Bonus!** You've accumulated **{new_total}** free spins!"

        if new_total > self.MAX_FREE_SPINS_HARD_CAP:
            new_total = self.MAX_FREE_SPINS_HARD_CAP
            warning_msg = f"⚠️ **Maximum Reached!** Capped at **{self.MAX_FREE_SPINS_HARD_CAP}** spins!"

        success = guild_user_dao.update_slots_bonus_state(
            user.user_id, user.guild_id, new_total,
            user.slots_locked_bet_amount, user.slots_bonus_total_won
        )

        return (new_total if success else user.slots_free_spins_remaining, warning_msg)

    def end_bonus_round(self, user, guild_user_dao: GuildUserDao) -> dict:
        """End bonus round, clear bonus state, and return summary."""
        summary = {
            "total_won": user.slots_bonus_total_won,
            "locked_bet": user.slots_locked_bet_amount,
            "net_profit": user.slots_bonus_total_won
        }

        guild_user_dao.clear_slots_bonus_state(user.user_id, user.guild_id)
        return summary

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
                "scatter_config": self.get_scatter_config(guild_id),
                "min_bet": self.MIN_BET,
                "max_bet": self.MAX_BET,
                "bet_options": self.BET_OPTIONS
            }
        except Exception as e:
            logger.error(f"Error getting slots config: {e}")
            return {
                "enabled": True,
                "symbols_config": self.default_symbols_config,
                "scatter_config": self.default_scatter_config,
                "min_bet": self.MIN_BET,
                "max_bet": self.MAX_BET,
                "bet_options": self.BET_OPTIONS
            }

    def spin_reel(self, symbols_config: list, scatter_config: dict = None, is_bonus_round: bool = False):
        """Spin the reels using provided symbols configuration."""
        if is_bonus_round and scatter_config:
            # Use bonus weights (reduced commons, increased rare/legendary)
            config = self.get_bonus_symbols_config(symbols_config, scatter_config)
        else:
            # Regular weights with scatter added
            config = symbols_config.copy()
            if scatter_config:
                config.append(scatter_config)

        emojis = [s["emoji"] for s in config]
        weights = [s["weight"] for s in config]

        return random.choices(emojis, weights=weights, k=5)

    def render_slots(self, reels):
        """Render slots in simple pipe format like 3-reel slots"""
        return f"# | {' | '.join(reels)} |"

    def find_all_matches(self, reels, symbols_config, scatter_emoji=None):
        """
        Find all consecutive matching sequences in reels (left to right).
        Scatter symbols act as wildcards and can substitute for any symbol.
        """
        matches = []
        i = 0

        while i < len(reels):
            # If current position is scatter, look for next non-scatter to start the match
            if scatter_emoji and reels[i] == scatter_emoji:
                # Count leading scatters
                wild_count = 0
                j = i
                while j < len(reels) and reels[j] == scatter_emoji:
                    wild_count += 1
                    j += 1

                # If we found a non-scatter symbol after wilds, use it as the match symbol
                if j < len(reels):
                    symbol = reels[j]
                    count = wild_count + 1  # wilds + the symbol itself
                    j += 1

                    # Continue matching
                    while j < len(reels):
                        if reels[j] == symbol:
                            count += 1
                            j += 1
                        elif reels[j] == scatter_emoji:
                            # More wilds extend the match
                            count += 1
                            j += 1
                        else:
                            break

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
                else:
                    # All remaining symbols are scatters, we're done
                    break
            else:
                # Regular symbol starts the match
                symbol = reels[i]
                count = 1
                j = i + 1

                # Count consecutive matches including wildcards (scatter)
                while j < len(reels):
                    if reels[j] == symbol:
                        count += 1
                        j += 1
                    elif scatter_emoji and reels[j] == scatter_emoji:
                        # Scatter acts as wild, extends the match
                        count += 1
                        j += 1
                    else:
                        # Different symbol, stop counting
                        break

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

        # Get the symbols and scatter configuration for this guild
        symbols_config = config["symbols_config"]
        scatter_config = config["scatter_config"]
        scatter_emoji = scatter_config["emoji"]

        guild_user_dao = GuildUserDao()
        user = guild_user_dao.get_guild_user(interaction.user.id, interaction.guild.id)
        if not user:
            await interaction.response.send_message("You need to send a message first to initialize your account!", ephemeral=True)
            return

        # Check if user is in bonus round
        is_bonus_round = user.slots_free_spins_remaining > 0

        if is_bonus_round:
            # Use locked bet amount
            cost = user.slots_locked_bet_amount

            # Validate locked bet sanity
            if cost < self.MIN_BET or cost > self.MAX_BET:
                guild_user_dao.clear_slots_bonus_state(user.user_id, user.guild_id)
                await interaction.response.send_message("Bonus round error cleared. Please try again.", ephemeral=True)
                return
        else:
            # Regular spin - validate bet
            cost = abs(bet)
            if cost < self.MIN_BET:
                await interaction.response.send_message(f"Minimum bet is {self.MIN_BET:,} credits.", ephemeral=True)
                return
            if cost > self.MAX_BET:
                await interaction.response.send_message(f"Maximum bet is {self.MAX_BET:,} credits.", ephemeral=True)
                return

            # Check currency only for regular spins
            if user.currency < cost:
                await interaction.response.send_message("You don't have enough credits!", ephemeral=True)
                return

        # SPIN with bonus flag!
        reels = self.spin_reel(symbols_config, scatter_config, is_bonus_round)
        display = self.render_slots(reels)

        # Check for scatter trigger
        scatter_free_spins = self.check_scatter_trigger(reels, scatter_emoji)

        # Find all consecutive matches (scatter acts as wild card)
        all_matches = self.find_all_matches(reels, symbols_config, scatter_emoji)

        # Use nickname if available, otherwise username
        user_display_name = interaction.user.display_name

        embed = discord.Embed(color=discord.Color.gold())

        amount_won = 0
        amount_lost = cost if not is_bonus_round else 0  # No loss during bonus
        result_text = ""

        # Determine payout based on matches
        if not all_matches:
            # No matches - full loss (or no win for bonus)
            result_text = "**No win this time...**"
            embed.color = discord.Color.red()

        elif all_matches[0]["count"] >= 3:
            # 3+ matches - use base multipliers (check this FIRST, before double pair)
            primary = all_matches[0]
            base_mult = self.BASE_MULTIPLIERS[primary["count"]]

            # Apply tier bonus
            tier_bonus = self.TIER_BONUSES.get(primary["tier"], 1)
            multiplier = base_mult * tier_bonus

            # Special legendary 5-match bonus (on top of tier bonus)
            if primary["count"] == 5 and primary["tier"] == "legendary":
                multiplier = base_mult * tier_bonus * self.LEGENDARY_5_MATCH_BONUS  # 100 × 5 × 10 = 5000x

            amount_won = int(cost * multiplier)
            amount_lost = 0

            # Check if there's also a pair in the remaining matches - bonus payout!
            if len(all_matches) >= 2 and all_matches[1]["count"] == 2:
                pair_bonus = int(cost * 0.5)  # Pair is 0.5x (half back)
                amount_won += pair_bonus
                win_phrases = {
                    3: f"**THREE OF A KIND!** {primary['symbol']} ×{multiplier} + **PAIR BONUS!** {all_matches[1]['symbol']} +{pair_bonus:,}",
                    4: f"**FOUR IN A ROW!** {primary['symbol']} ×{multiplier} 🔥 + **PAIR BONUS!** {all_matches[1]['symbol']} +{pair_bonus:,}",
                    5: f"**JACKPOT! FIVE IN A ROW!!** {primary['symbol']} ×{multiplier} 💰 + **PAIR BONUS!** {all_matches[1]['symbol']} +{pair_bonus:,}"
                }
            else:
                win_phrases = {
                    3: f"**THREE OF A KIND!** {primary['symbol']} ×{multiplier}",
                    4: f"**FOUR IN A ROW!** {primary['symbol']} ×{multiplier} 🔥",
                    5: f"**JACKPOT! FIVE IN A ROW!!** {primary['symbol']} ×{multiplier} 💰"
                }

            result_text = win_phrases.get(primary["count"], f"×{multiplier} WIN!")
            embed.color = discord.Color.gold() if primary["count"] == 5 else discord.Color.green()

        elif len(all_matches) >= 2 and all_matches[0]["count"] == 2 and all_matches[1]["count"] == 2:
            # Two separate 2-matches = 1x break even (both pairs pay 0.5x each)
            amount_won = cost
            amount_lost = 0
            result_text = f"**DOUBLE PAIR!** {all_matches[0]['symbol']} {all_matches[1]['symbol']} Break even 🎲"
            embed.color = discord.Color.blue()

        elif all_matches[0]["count"] == 2:
            # Single 2-match - half back (0.5x)
            amount_won = int(cost * 0.5)
            amount_lost = cost - amount_won
            result_text = f"**PAIR!** {all_matches[0]['symbol']} Half back ↩️"
            embed.color = discord.Color.light_grey()

        # Handle currency and bonus state updates
        if is_bonus_round:
            # BONUS ROUND: Track winnings, update bonus state
            new_spins = user.slots_free_spins_remaining - 1
            new_total_won = user.slots_bonus_total_won + amount_won
            warning_msg = None

            # Check for scatter re-trigger
            if scatter_free_spins > 0:
                new_spins, warning_msg = self.add_retrigger_spins(user, guild_user_dao, scatter_free_spins)

            if new_spins > 0:
                # Continue bonus - save updated state
                guild_user_dao.update_slots_bonus_state(
                    user.user_id, user.guild_id, new_spins, cost, new_total_won
                )
            else:
                # End bonus - pay out ALL winnings
                summary = self.end_bonus_round(user, guild_user_dao)

                # Pay out all accumulated winnings at once
                guild_user_dao.update_currency_with_global_sync(
                    user.user_id, user.guild_id, summary['total_won']
                )
        else:
            # REGULAR SPIN: Update currency normally
            net = amount_won - amount_lost
            guild_user_dao.update_currency_with_global_sync(interaction.user.id, interaction.guild.id, net)
            GuildDao().add_vault_currency(interaction.guild_id, int(amount_lost * 0.1))

            # Check if scatter triggered bonus
            if scatter_free_spins > 0:
                self.trigger_bonus_round(user, guild_user_dao, scatter_free_spins, cost)

        # Build description with all info (for proper markdown rendering)
        if is_bonus_round:
            # Bonus round header
            original_spins = user.slots_free_spins_remaining
            current_spin_num = original_spins - new_spins if 'new_spins' in locals() else 1
            description_parts = [
                f"# 🎰 BONUS ROUND - Free Spin 🎰",
                "",
                display,
                "",
                result_text or "No win this time...",
                ""
            ]
        else:
            description_parts = [
                f"# 🎰 {user_display_name} 🎰",
                "",
                display,
                "",
                result_text or "No win this time...",
                ""
            ]

        # Add bet/win/loss info
        if is_bonus_round:
            bet_info = f"Locked Bet: **{cost:,}** credits (FREE)"
            if amount_won > 0:
                bet_info += f" → Won **{amount_won:,}** credits"
            description_parts.append(bet_info)
            description_parts.append(f"Bonus Total: **{new_total_won:,}** credits" if 'new_total_won' in locals() else f"Bonus Total: **{amount_won:,}** credits")

            if 'new_spins' in locals():
                description_parts.append(f"Remaining: **{new_spins}** free spins")

                if new_spins == 0:
                    description_parts.append("")
                    description_parts.append("✨ **BONUS COMPLETE!** ✨")
                    if 'summary' in locals():
                        description_parts.append(f"Final Payout: **+{summary['total_won']:,}** credits")
        else:
            bet_info = f"Bet: **{cost:,}** credits"
            if amount_won > cost:
                bet_info += f" → Won **{amount_won:,}** credits (+{amount_won - cost:,})"
            elif amount_won > 0:
                bet_info += f" → Won **{amount_won:,}** credits (±{amount_won - cost:,})"
            else:
                bet_info += f" → Lost **{cost:,}** credits"
            description_parts.append(bet_info)

        # Add scatter trigger info
        if scatter_free_spins > 0:
            description_parts.append("")
            if is_bonus_round:
                description_parts.append(f"⚡ **RE-TRIGGER!** +{scatter_free_spins} Free Spins!")
                if 'warning_msg' in locals() and warning_msg:
                    description_parts.append(warning_msg)
            else:
                description_parts.append(f"⚡ **BONUS TRIGGERED!** {scatter_free_spins} Free Spins!")

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
                game_data={
                    "reels": reels,
                    "matches": match_count,
                    "multiplier": amount_won / cost if amount_won else 0,
                    "bonus_round": is_bonus_round,
                    "scatter_count": reels.count(scatter_emoji),
                    "scatter_triggered": scatter_free_spins > 0,
                    "free_spins_awarded": scatter_free_spins
                }
            )
        except Exception as e:
            logger.error(f"Failed to log slots game: {e}")

        await interaction.response.send_message(embed=embed)

        if is_bonus_round:
            logger.info(f"{interaction.user} played BONUS slots | Bet: {cost} | Won: {amount_won} | Spins remaining: {new_spins if 'new_spins' in locals() else 0}")
        else:
            logger.info(f"{interaction.user} played slots | Bet: {cost} | Won: {amount_won} | Scatter: {scatter_free_spins}")


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