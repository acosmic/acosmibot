import math
import typing
import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime, timedelta
from Dao.VaultDao import VaultDao
from logger import AppLogger
from Dao.UserDao import UserDao
from Dao.SlotsDao import SlotsDao
from Entities.SlotEvent import SlotEvent
import os
from dotenv import load_dotenv

logger = AppLogger(__name__).get_logger()

# Load environment variables
load_dotenv()

# Track losing streaks per user
user_losing_streaks = {}

class Slots(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        
        # Easter-themed slots
        self.slots = ["🐰", "🥚", "🧺", "🐣", "🌷", "🐇", "🌸", "🍫", "🐥", "🌱", "🦋", "🌈", "🎀", "🦢", "🐑", "🌻"]
        
        # Create a weighted distribution of symbols
        self.slots_pool = (
            ["🐰", "🥚"] * 3 +        # Super jackpot symbols (higher frequency)
            ["🌸", "🌷"] * 3 +         # Mega jackpot symbols (higher frequency)
            ["🧺", "🍫", "🐣"] * 2 +   # Special combo jackpot (medium frequency)
            ["🌱", "🦋", "🌈", "🎀", "🦢", "🐇", "🐥", "🌻"] * 2 +  # Regular symbols (medium frequency)
            ["🐑"] * 1                # Jail symbol (lowest frequency)
        )
        
        # Define special slot configurations for jackpots
        self.super_jackpot_emojis = ["🐰", "🥚"]  # Top jackpot symbols (Easter bunny and Easter egg)
        self.mega_jackpot_emojis = ["🌸", "🌷"]   # Mega jackpot symbols (Spring flowers)
        self.special_combo_jackpot = ["🧺", "🍫", "🐣"]  # Special jackpot for basket, chocolate and chick
        self.jail_jackpot_emoji = "🐑"  # Sheep (sent to jail)
        
        # Pattern wins
        self.easter_pattern = ["🐰", "🥚", "🧺"]  # Bunny, egg, basket pattern
        self.spring_pattern = ["🌷", "🌱", "🦋"]  # Flower, sprout, butterfly pattern
        
        # Bonus spin triggers
        self.bonus_spin_trigger = ["🌈", "🌈"]  # Two rainbows trigger a free spin
        
        # Jackpot multipliers and rewards
        self.super_jackpot_multiplier = 100
        self.mega_jackpot_multiplier = 50
        self.regular_jackpot_multiplier = 30  # Increased from 25
        self.special_combo_multiplier = 40
        self.match_two_multiplier = 8  # Increased from 5
        self.pattern_win_multiplier = 15
        
        # EXP rewards as percentage of bet
        self.super_jackpot_exp_rate = 0.05  # 5%
        self.mega_jackpot_exp_rate = 0.025  # 2.5%
        self.regular_jackpot_exp_rate = 0.0125  # 1.25%
        self.special_combo_exp_rate = 0.03  # 3%
        self.match_two_exp_rate = 0.01  # Increased from 0.5%
        self.pattern_win_exp_rate = 0.02  # 2%
        
        # Jail jackpot penalties
        self.jail_currency_penalty_rate = 0.10  # 10% of user's currency
        self.jail_exp_penalty_rate = 0.10  # 10% of user's XP
        
        # Vault contribution rate from losses
        self.vault_contribution_rate = 0.05  # 5% of loss goes to vault
        
        # Losing streak protection thresholds
        self.losing_streak_threshold = 3  # After 3 losses, odds improve
        self.max_losing_streak_bonus = 5  # Maximum odds improvement

    def is_easter_weekend(self, today):
        """Check if today is during Easter weekend (for holiday boost)"""
        # 2025 Easter Sunday is April 20
        easter_sunday_2025 = datetime(2025, 4, 20).date()
        
        # Check if date is from Good Friday through Easter Monday
        easter_weekend_start = easter_sunday_2025 - timedelta(days=2)  # Good Friday
        easter_weekend_end = easter_sunday_2025 + timedelta(days=1)    # Easter Monday
        
        return easter_weekend_start <= today <= easter_weekend_end

    def get_user_losing_streak(self, user_id):
        """Get current losing streak for user"""
        return user_losing_streaks.get(user_id, 0)
    
    def update_user_streak(self, user_id, win):
        """Update user's streak - reset on win, increment on loss"""
        if win:
            user_losing_streaks[user_id] = 0
        else:
            user_losing_streaks[user_id] = user_losing_streaks.get(user_id, 0) + 1
            
    def get_boosted_odds(self, interaction, cost):
        """Apply boosts based on losing streak and special events"""
        user_id = interaction.user.id
        user_losing_streak = self.get_user_losing_streak(user_id)
        today = datetime.now().date()
        
        # Check for Easter weekend
        easter_boost = self.is_easter_weekend(today)
        
        # Apply Easter weekend boost if applicable
        multiplier_boost = 1.2 if easter_boost else 1.0
        
        # Apply progressive multipliers
        super_jackpot_multiplier = math.ceil(self.super_jackpot_multiplier * multiplier_boost)
        mega_jackpot_multiplier = math.ceil(self.mega_jackpot_multiplier * multiplier_boost)
        regular_jackpot_multiplier = math.ceil(self.regular_jackpot_multiplier * multiplier_boost)
        special_combo_multiplier = math.ceil(self.special_combo_multiplier * multiplier_boost)
        match_two_multiplier = math.ceil(self.match_two_multiplier * multiplier_boost)
        
        # Return multipliers and information about boosts
        return {
            "super_jackpot_multiplier": super_jackpot_multiplier,
            "mega_jackpot_multiplier": mega_jackpot_multiplier,
            "regular_jackpot_multiplier": regular_jackpot_multiplier,
            "special_combo_multiplier": special_combo_multiplier,
            "match_two_multiplier": match_two_multiplier,
            "holiday_boost": easter_boost,
            "losing_streak": user_losing_streak
        }

    @app_commands.command(name="slots", description="Play a game of slots")
    async def slots(self, interaction: discord.Interaction, bet: typing.Literal[100, 1000, 5000, 10000, 25000] = 100):
        dao = UserDao()
        slotDao = SlotsDao()
        user = dao.get_user(interaction.user.id)
        cost = abs(bet)  # Ensure the bet is positive
        bet_amount = cost
        exp_gained = 0
        amount_won = 0
        amount_lost = 0
        exp_lost = 0
        is_winning_spin = False
        is_bonus_spin = False

        general_channel = self.bot.get_channel(1155577095787917384)
        jail_channel = self.bot.get_channel(1233867818055893062)

        # Check for a bonus spin that was earned previously
        bonus_message = ""
        if getattr(interaction.user, 'bonus_spin', False):
            is_bonus_spin = True
            interaction.user.bonus_spin = False
            cost = 0
            bonus_message = "🎯 **BONUS SPIN!** 🎯\n"

        if user.currency < cost and not is_bonus_spin:
            await interaction.response.send_message("You don't have enough credits to place this bet.", ephemeral=True)
            return

        # Apply odds boosts based on losing streak and special events
        boosts = self.get_boosted_odds(interaction, cost)
        
        # Calculate spin odds
        user_losing_streak = boosts["losing_streak"]
        boost_level = min(user_losing_streak - self.losing_streak_threshold, self.max_losing_streak_bonus)
        boost_level = max(0, boost_level)  # Ensure non-negative
        
        # Spin the slots with boosted odds if applicable
        if boost_level > 0:
            # Boosted spin
            slot1 = random.choice(self.slots_pool)
            # Increased chance of matching first reel based on streak
            slot2 = random.choice([slot1] * (1 + boost_level) + self.slots_pool)
            # Further increased chance of matching if first two match
            if slot1 == slot2:
                slot3 = random.choice([slot1] * (2 + boost_level) + self.slots_pool)
            else:
                slot3 = random.choice(self.slots_pool)
        else:
            # Normal spin with slightly improved odds
            slot1 = random.choice(self.slots_pool)
            # Second reel has slight chance of matching first
            slot2 = random.choice([slot1] * 2 + self.slots_pool) 
            # Third reel has higher chance of matching if first two match
            slot3 = random.choice([slot1] * 3 + self.slots_pool) if slot1 == slot2 else random.choice(self.slots_pool)

        result = f"| {slot1} | {slot2} | {slot3} |\n"
        embed = discord.Embed()
        
        # Super jackpot (highest tier)
        if slot1 == slot2 == slot3 and slot1 in self.super_jackpot_emojis:
            exp_gained = math.ceil(cost * self.super_jackpot_exp_rate)
            amount_won = cost * boosts["super_jackpot_multiplier"]
            is_winning_spin = True
            embed.description = f"# 🎯 EASTER SUPER JACKPOT 🎯\n\n\n # {result}\n{interaction.user.mention} hit the SUPER Jackpot and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!"
            embed.color = discord.Color.gold()
            general_embed = discord.Embed()
            general_embed.description = f"# 🎯 EASTER SUPER JACKPOT 🎯\n\n\n # {result}\n{interaction.user.mention} hit the EASTER SUPER Jackpot and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!!"
            general_embed.color = discord.Color.gold()
            general_embed.set_footer(text="Try your luck with /slots! in 🎰︱casino")
            await general_channel.send(embed=general_embed)

        # Mega jackpot (high tier)
        elif slot1 == slot2 == slot3 and slot1 in self.mega_jackpot_emojis:
            exp_gained = math.ceil(cost * self.mega_jackpot_exp_rate)
            amount_won = cost * boosts["mega_jackpot_multiplier"]
            is_winning_spin = True
            embed.description = f"# 🌺 SPRING MEGA JACKPOT 🌺\n\n\n # {result}\n{interaction.user.mention} hit the MEGA Jackpot and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!!"
            embed.color = discord.Color.gold()
            general_embed = discord.Embed()
            general_embed.description = f"# 🌺 SPRING MEGA JACKPOT 🌺\n\n\n # {result}\n{interaction.user.mention} hit the MEGA Jackpot and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!!"
            general_embed.color = discord.Color.gold()
            general_embed.set_footer(text="Try your luck with /slots! in 🎰︱casino")
            await general_channel.send(embed=general_embed)
        
        # Special combo jackpot - All three symbols from special combo list in any order
        elif set([slot1, slot2, slot3]) == set(self.special_combo_jackpot):
            exp_gained = math.ceil(cost * self.special_combo_exp_rate)
            amount_won = cost * boosts["special_combo_multiplier"]
            is_winning_spin = True
            embed.description = f"# 🧺 EASTER BASKET JACKPOT 🧺\n\n\n # {result}\n{interaction.user.mention} hit the Easter Basket Jackpot and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!"
            embed.color = discord.Color.gold()
            general_embed = discord.Embed()
            general_embed.description = f"# 🧺 EASTER BASKET JACKPOT 🧺\n\n\n # {result}\n{interaction.user.mention} hit the Easter Basket Jackpot and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!!"
            general_embed.color = discord.Color.gold()
            general_embed.set_footer(text="Try your luck with /slots! in 🎰︱casino")
            await general_channel.send(embed=general_embed)
        
        # JAIL POT
        elif slot1 == slot2 == slot3 == self.jail_jackpot_emoji:
            exp_lost = math.ceil(user.season_exp * self.jail_exp_penalty_rate)
            amount_lost = math.ceil(user.currency * self.jail_currency_penalty_rate)
            embed.description = f"# 🐑 SHEEP JAIL JACKPOT 🐑\n\n\n # {result}\n{interaction.user.mention} hit the Sheep Jail Jackpot and lost {amount_lost:,.0f} Credits and {exp_lost:,.0f} XP!! and sent to Jail!"
            embed.color = discord.Color.gold()
            general_embed = discord.Embed()
            general_embed.description = f"# 🐑 SHEEP JAIL JACKPOT 🐑\n\n\n # {result}\n{interaction.user.mention} hit the Sheep Jail Jackpot and lost {amount_lost:,.0f} Credits and {exp_lost:,.0f} XP!! and sent to Jail!"
            general_embed.color = discord.Color.gold()
            general_embed.set_footer(text="Try your luck with /slots! in 🎰︱casino")
            inmate_role = discord.utils.get(interaction.guild.roles, name="Inmate")
            if inmate_role in interaction.user.roles:
                return
            await interaction.user.add_roles(inmate_role)
            await general_channel.send(embed=general_embed)
            await jail_channel.send(embed=general_embed)
        
        # Regular jackpot (three of a kind)
        elif slot1 == slot2 == slot3:
            exp_gained = math.ceil(cost * self.regular_jackpot_exp_rate)
            amount_won = cost * boosts["regular_jackpot_multiplier"]
            is_winning_spin = True
            embed.description = f"# 🎰 Jackpot 🎰\n\n\n # {result}\n{interaction.user.mention} hit the Jackpot and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!"
            embed.color = discord.Color.gold()
            general_embed = discord.Embed()
            general_embed.description = f"# 🎰 Jackpot 🎰\n\n\n # {result}\n{interaction.user.mention} hit the Jackpot and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!"
            general_embed.color = discord.Color.gold()
            general_embed.set_footer(text="Try your luck with /slots! in 🎰︱casino")
            await general_channel.send(embed=general_embed)
        
        # Easter pattern win
        elif sorted([slot1, slot2, slot3]) == sorted(self.easter_pattern):
            exp_gained = math.ceil(cost * self.pattern_win_exp_rate)
            amount_won = cost * self.pattern_win_multiplier
            is_winning_spin = True
            embed.description = f"# 🐰 Easter Pattern Win! 🐰\n\n\n # {result}\n{interaction.user.mention} matched the Easter Pattern and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!"
            embed.color = discord.Color.teal()
        
        # Spring pattern win
        elif sorted([slot1, slot2, slot3]) == sorted(self.spring_pattern):
            exp_gained = math.ceil(cost * self.pattern_win_exp_rate)
            amount_won = cost * self.pattern_win_multiplier
            is_winning_spin = True
            embed.description = f"# 🌷 Spring Pattern Win! 🌷\n\n\n # {result}\n{interaction.user.mention} matched the Spring Pattern and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!"
            embed.color = discord.Color.teal()
            
        # Bonus spin trigger (two rainbows)
        elif slot1 == slot2 == "🌈" or slot2 == slot3 == "🌈" or slot1 == slot3 == "🌈":
            exp_gained = math.ceil(cost * 0.01)  # Small XP gain
            amount_won = cost  # Get your bet back
            is_winning_spin = True
            setattr(interaction.user, 'bonus_spin', True)  # Set bonus spin flag
            embed.description = f"# 🌈 BONUS SPIN EARNED! 🌈\n\n\n # {result}\n{interaction.user.mention} earned a free bonus spin for next time! You got your {cost:,.0f} credits back and {exp_gained:,.0f} EXP!"
            embed.color = discord.Color.purple()
        
        # Matching two (small win)
        elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
            exp_gained = math.ceil(cost * self.match_two_exp_rate)
            amount_won = cost * boosts["match_two_multiplier"]
            is_winning_spin = True
            embed.description = f"# 🎰 {interaction.user.name} 🎰\n\n\n # {result}\nYou matched two! You won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!"
            embed.color = discord.Color.green()

        # Loss
        else:
            vdao = VaultDao()
            vcredits = vdao.get_currency()
            vgain = cost * self.vault_contribution_rate
            vcredits += vgain
            vdao.update_currency(vcredits)
            amount_lost = cost
            
            # Add losing streak notification if streak is building
            streak_msg = ""
            if user_losing_streak >= self.losing_streak_threshold - 1:
                streak_msg = f"\n\n*Losing streak: {user_losing_streak + 1}*"
                
            embed.description = f"# 🎰 {interaction.user.name} 🎰\n\n\n # {result}\nYou lost {amount_lost:,.0f} credits.{streak_msg}\n\n{vgain:,.0f} Credits have been added to the vault! 🏦"
            embed.color = discord.Color.red()

        # Apply holiday boost message if active
        if boosts["holiday_boost"] and (amount_won > 0 or amount_lost > 0):
            embed.description += "\n\n🐣 **Easter Weekend Boost Active!** 🐣"
            
        # Apply losing streak protection message if active
        if boost_level > 0 and (amount_won > 0 or amount_lost > 0):
            embed.description += f"\n\n🍀 *Luck boost from losing streak activated!* 🍀"

        # Add bonus spin message if this was a bonus spin
        if is_bonus_spin:
            embed.description = bonus_message + embed.description

        # Update user losing streak
        self.update_user_streak(interaction.user.id, is_winning_spin)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_event = SlotEvent(0, interaction.user.id, slot1, slot2, slot3, bet_amount, amount_won, amount_lost, timestamp)

        user.currency += amount_won
        user.currency -= amount_lost
        user.exp += exp_gained
        user.exp_gained += exp_gained
        user.season_exp += exp_gained
        user.exp_lost -= exp_lost

        dao.update_user(user)
        slotDao.add_new_event(new_event)
        await interaction.response.send_message(embed=embed)
        logger.info(f"{interaction.user.name} used /slots command")

async def setup(bot: commands.Bot):
    await bot.add_cog(Slots(bot))