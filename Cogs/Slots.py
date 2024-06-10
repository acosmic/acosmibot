from math import exp
import math
import typing
import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime
from Dao.VaultDao import VaultDao
from logger import AppLogger
from Dao.UserDao import UserDao
from Dao.SlotsDao import SlotsDao
from Entities.SlotEvent import SlotEvent

logger = AppLogger(__name__).get_logger()

class Slots(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.slots = ["🐶", "🐱", "🦠", "🐟", "🦏", "🦉", "🦄", "🦈", "🦐", "🦧", "🐐", "🐸", "<:acosmicD:1171219346299814009>"]

    @app_commands.command(name="slots", description="Play a game of slots")
    async def slots(self, interaction: discord.Interaction, bet: typing.Literal[100, 1000, 5000, 10000, 25000] = 100):
        dao = UserDao()
        slotDao = SlotsDao()
        user = dao.get_user(interaction.user.id)
        cost = abs(bet)  # Ensure the bet is positive
        exp_gained = 0
        amount_won = 0
        amount_lost = 0


        general_channel = self.bot.get_channel(1155577095787917384)

        if user.currency < cost:
            await interaction.response.send_message("You don't have enough credits to place this bet.", ephemeral=True)
            return

        # Spin the slots
        slot1 = random.choice(self.slots)
        slot2 = random.choice(self.slots)
        slot3 = random.choice(self.slots)

        # if interaction.user.id == 110637665128325120:
        #     slot1 = "<:acosmicD:1171219346299814009>"
        #     slot2 = "<:acosmicD:1171219346299814009>"
        #     slot3 = "<:acosmicD:1171219346299814009>"

        result = f"| {slot1} | {slot2} | {slot3} |\n"
        embed = discord.Embed()
        if slot1 == slot2 == slot3 == "<:acosmicD:1171219346299814009>":
            # Super Jackpot
            exp_gained = math.ceil(cost * .1) # 10% of the bet  
            amount_won = cost * 100
            embed.description = f"# <a:OOOOM:1236019284904509621> SUPER JACKPOT <a:OOOOM:1236019284904509621>\n\n\n # {result}\n{interaction.user.mention} hit the SUPER Jackpot and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!"
            embed.color = discord.Color.gold()
            general_embed = discord.Embed()
            general_embed.description = f"# <a:OOOOM:1236019284904509621> SUPER JACKPOT <a:OOOOM:1236019284904509621>\n\n\n # {result}\n{interaction.user.mention} hit the SUPER Jackpot and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!!"
            general_embed.color = discord.Color.gold()
            general_embed.set_footer(text="Try your luck with /slots! in 🎰︱casino")
            await general_channel.send(embed=general_embed)
        elif slot1 == slot2 == slot3 == "🦄":
            # Mega Jackpot
            exp_gained = math.ceil(cost * .05) # 5% of the bet
            amount_won = cost * 50
            # EMBED
            embed.description = f"# <a:OOOOM:1236019284904509621> {interaction.user.name} <a:OOOOM:1236019284904509621>\n\n\n # {result}\nMEGA JACKPOT! You won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!!"
            embed.color = discord.Color.gold()
            general_embed = discord.Embed()
            general_embed.description = f"# <a:OOOOM:1236019284904509621> {interaction.user.name} <a:OOOOM:1236019284904509621>\n\n\n # {result}\n{interaction.user.mention} hit the MEGA Jackpot and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!!"
            general_embed.color = discord.Color.gold()
            general_embed.set_footer(text="Try your luck with /slots! in 🎰︱casino")
            await general_channel.send(embed=general_embed)
        elif slot1 == slot2 == slot3:
            # Jackpot
            exp_gained = math.ceil(cost * .025) # 2.5% of the bet 
            amount_won = cost * 25
            #EMBED
            embed.description = f"# <a:OOOOM:1236019284904509621> {interaction.user.name} <a:OOOOM:1236019284904509621>\n\n\n # {result}\nJackpot! You won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!"
            embed.color = discord.Color.gold()
            general_embed = discord.Embed()
            # general_embed.title = f"🎰 {interaction.user.name} hit the Jackpot! 🎰"
            general_embed.description = f"# <a:peepoGamba:1247551104414257262> {interaction.user.name} <a:peepoGamba:1247551104414257262>\n\n\n # {result}\n{interaction.user.mention} hit the Jackpot and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!"
            general_embed.color = discord.Color.gold()
            general_embed.set_footer(text="Try your luck with /slots! in 🎰︱casino")
            await general_channel.send(embed=general_embed)
        elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
            # Small win
            exp_gained = math.ceil(cost * .005) # 0.5% of the bet
            amount_won = cost * 5 
            embed.description = f"# <a:peepoGamba:1247551104414257262> {interaction.user.name} <a:peepoGamba:1247551104414257262>\n\n\n # {result}\nYou matched two! You won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!"
            embed.color = discord.Color.green()
        else:
            vdao = VaultDao()
            vcredits = vdao.get_currency()
            vgain = cost * 0.05 # 5% of the bet
            vcredits += vgain
            vdao.update_currency(vcredits)
            # Loss
            amount_lost = cost
            embed.description = f"# <a:peepoGamba:1247551104414257262> {interaction.user.name} <a:peepoGamba:1247551104414257262>\n\n\n # {result}\nYou lost {amount_lost:,.0f} credits.\n\n{vgain:,.0f} Credits have been added to the vault! 🏦"
            embed.color = discord.Color.red()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_event = SlotEvent(0, interaction.user.id, slot1, slot2, slot3, amount_won, amount_lost, timestamp)

        user.currency += amount_won
        user.currency -= amount_lost
        user.exp += exp_gained
        user.exp_gained += exp_gained
        user.season_exp += exp_gained

        dao.update_user(user)
        slotDao.add_new_event(new_event)
        await interaction.response.send_message(embed=embed)
        logger.info(f"{interaction.user.name} used /slots command")

async def setup(bot: commands.Bot):
    await bot.add_cog(Slots(bot))