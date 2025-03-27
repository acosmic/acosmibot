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
        self.slots = ["<:EZ:1312042915891253329>", 
                      "<a:EDM:1312052671762665553>", 
                      "🎄", 
                      "<a:AAAA:1312039915583963176>", 
                      "<:Kappa:1312048639660527637>", 
                      "<a:NODDERS:1312038419517673566>", 
                      "<a:POGGIES:1312041859408859148>", 
                      "<a:duckass:1312036019482132520>", 
                      "<:peepoCozy:1312042216390131794>", 
                      "<:slayyy:1312040872866480138>", 
                      "<:D_:1312033819976794142>", 
                      "<a:Kissahomie:1312041225230225408>",
                      "<a:KEKWiggle:1312045854009593876>",
                      "🎁",
                      "<a:peepoTree:1312043349305196574>", 
                      "<:acosmicD:1171219346299814009>"]
        

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


        general_channel = self.bot.get_channel(1155577095787917384)
        jail_channel = self.bot.get_channel(1233867818055893062)

        if user.currency < cost:
            await interaction.response.send_message("You don't have enough credits to place this bet.", ephemeral=True)
            return

        # Spin the slots
        slot1 = random.choice(self.slots)
        slot2 = random.choice(self.slots)
        slot3 = random.choice(self.slots)

        # if interaction.user.id == 110637665128325120:
        #     slot1 = "<a:RareGhost:1283619489124057240>"
        #     slot2 = "<a:RareGhost:1283619489124057240>"
        #     slot3 = "<a:RareGhost:1283619489124057240>"

        result = f"| {slot1} | {slot2} | {slot3} |\n"
        embed = discord.Embed()
        # if slot1 == slot2 == slot3 == "<:uriahBlinker:1219818964314755142>":
        #     # Top Right Jackpot
        #     exp_gained = math.ceil(cost * .05) # 5% of the bet
        #     amount_won = cost * 125 # Top Right Jackpot
        #     embed.description = f"# 🎰 TOP RIGHT JACKPOT 🎰\n\n\n # {result}\n{interaction.user.mention} hit the TOP RIGHT JACKPOT and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!"
        #     embed.color = discord.Color.gold()
        #     general_embed = discord.Embed()
        #     general_embed.description = f"# 🎰 TOP RIGHT JACKPOT 🎰\n\n\n # {result}\n{interaction.user.mention} hit the TOP RIGHT JACKPOT and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!!"
        #     general_embed.color = discord.Color.gold()
        #     general_embed.set_footer(text="Try your luck with /slots! in 🎰︱casino")
        #     await general_channel.send(embed=general_embed)

        if slot1 == slot2 == slot3 == "<:acosmicD:1171219346299814009>":
            # Cosmic Jackpot
            exp_gained = math.ceil(cost * .05) # 5% of the bet
            amount_won = cost * 100 # Cosmic Jackpot
            embed.description = f"# 🌌 COSMIC JACKPOT 🌌\n\n\n # {result}\n{interaction.user.mention} hit the COSMIC Jackpot and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!"
            embed.color = discord.Color.gold()
            general_embed = discord.Embed()
            general_embed.description = f"# 🌌 COSMIC JACKPOT 🌌\n\n\n # {result}\n{interaction.user.mention} hit the COSMIC Jackpot and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!!"
            general_embed.color = discord.Color.gold()
            general_embed.set_footer(text="Try your luck with /slots! in 🎰︱casino")
            await general_channel.send(embed=general_embed)
        elif (slot1 == slot2 == slot3 == "<:POGGIES:1283619829126922251>") or (slot1 == slot2 == slot3 == "<a:skeletonPls:1283625772011225139>"):
            # Mega Jackpot
            exp_gained = math.ceil(cost * .025) # 2.5% of the bet
            amount_won = cost * 50 # Mega Jackpot
            embed.description = f"# <a:peepoGamba:1247551104414257262> MEGA Jackpot <a:peepoGamba:1247551104414257262>\n\n\n # {result}\n{interaction.user.mention} hit the MEGA Jackpot and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!!"
            embed.color = discord.Color.gold()
            general_embed = discord.Embed()
            general_embed.description = f"# <a:peepoGamba:1247551104414257262> MEGA Jackpot <a:peepoGamba:1247551104414257262>\n\n\n # {result}\n{interaction.user.mention} hit the MEGA Jackpot and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!!"
            general_embed.color = discord.Color.gold()
            general_embed.set_footer(text="Try your luck with /slots! in 🎰︱casino")
            await general_channel.send(embed=general_embed)
        
        # # JAIL POT
        # elif slot1 == slot2 == slot3 == "<a:docPLSjail:1258436674250084383>":
        #     # Jail Jackpot
        #     exp_lost = math.ceil(user.season_exp * .10) # 10% of the user's exp
        #     amount_lost = math.ceil(user.currency * 0.10) # 10% of the user's credits
        #     embed.description = f"# <:kekpoint:1224792810889154760> JAIL JACKPOT <:kekpoint:1224792810889154760>\n\n\n # {result}\n{interaction.user.mention} hit the Jail Jackpot and lost {amount_lost:,.0f} Credits and {exp_lost:,.0f} XP!! and sent to Jail!"
        #     embed.color = discord.Color.gold()
        #     general_embed = discord.Embed()
        #     general_embed.description = f"# <:kekpoint:1224792810889154760> JAIL JACKPOT <:kekpoint:1224792810889154760>\n\n\n # {result}\n{interaction.user.mention} hit the Jail Jackpot and lost {amount_lost:,.0f} Credits and {exp_lost:,.0f} XP!! and sent to Jail!"
        #     general_embed.color = discord.Color.gold()
        #     general_embed.set_footer(text="Try your luck with /slots! in 🎰︱casino")
        #     inmate_role = discord.utils.get(interaction.guild.roles, name="Inmate")
        #     if inmate_role in interaction.user.roles:
        #         return
        #     await interaction.user.add_roles(inmate_role)
        #     await general_channel.send(embed=general_embed)
        #     await jail_channel.send(embed=general_embed)                    
        elif slot1 == slot2 == slot3:
            # Jackpot
            exp_gained = math.ceil(cost * .0125) # 1.25% of the bet 
            amount_won = cost * 25 # Jackpot
            embed.description = f"# <a:peepoGamba:1247551104414257262> Jackpot <a:peepoGamba:1247551104414257262>\n\n\n # {result}\n{interaction.user.mention} hit the Jackpot and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!"
            embed.color = discord.Color.gold()
            general_embed = discord.Embed()
            # general_embed.title = f"🎰 {interaction.user.name} hit the Jackpot! 🎰"
            general_embed.description = f"# <a:peepoGamba:1247551104414257262> Jackpot <a:peepoGamba:1247551104414257262>\n\n\n # {result}\n{interaction.user.mention} hit the Jackpot and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!"
            general_embed.color = discord.Color.gold()
            general_embed.set_footer(text="Try your luck with /slots! in 🎰︱casino")
            await general_channel.send(embed=general_embed)
        # elif (slot1 == "🏬" and slot2 == "✈️" and slot3 == "✈️") or \
        #         (slot1 == "✈️" and slot2 == "🏬" and slot3 == "✈️") or \
        #         (slot1 == "✈️" and slot2 == "✈️" and slot3 == "🏬"):
        #     # Inside Job Jackpot
        #     exp_gained = math.ceil(cost * .05) # 5% of the bet
        #     amount_won = cost * 50
        #     embed.description = f"# Inside Job Jackpot \n\n\n # {result}\n{interaction.user.mention} hit the Inside Job Jackpot and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!"
        #     embed.color = discord.Color.gold()
        #     general_embed = discord.Embed()
        #     general_embed.description = f"# Inside Job Jackpot \n\n\n # {result}\n{interaction.user.mention} hit the Inside Job Jackpot and won {amount_won:,.0f} credits and {exp_gained:,.0f} EXP!!"
        #     general_embed.color = discord.Color.gold()
        #     general_embed.set_footer(text="Try your luck with /slots! in 🎰︱casino")
        #     await general_channel.send(embed=general_embed)

        elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
            # Small win
            exp_gained = math.ceil(cost * .005) # 0.5% of the bet
            amount_won = cost * 5 # Small win
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
        new_event = SlotEvent(0, interaction.user.id, slot1, slot2, slot3, bet_amount,  amount_won, amount_lost, timestamp)

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