import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from Dao.CoinflipDao import CoinflipDao 
import logging
import typing

logging.basicConfig(filename='/root/dev/acosmicord-bot/logs.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Leaderboard(commands.Cog):
    def __init__(self, bot:commands.Bot):
        super().__init__()
        self.bot = bot

    
    @app_commands.command(name = "leaderboard", description = "Returns top 5 users by Credits based on Currency, EXP, etc.")
    async def leaderboard(self, interaction: discord.Interaction, stat: typing.Literal['Currency', 'Exp', 'Largest Single Win - CF', 'Largest Single Loss - CF']):
        
        # if stat not in options_list:
        #     await interaction.response.send_message("Invalid choice. Please choose from the list.", ephemeral=True)
        #     return
        if stat == 'Currency' or stat == 'Exp':
            dao = UserDao()
            leaders = dao.get_top_users(column=stat.lower())


            embed = discord.Embed(title=f"Top 5 Users by {stat.upper()}", color=interaction.user.color)

            for i, (user_id, username, value) in enumerate(leaders, start=1):
                formatted_value = "{:,.0f}".format(value)
                embed.add_field(name=f"{i}. {username}", value=f"{formatted_value} {stat.capitalize()}\n", inline=False)

            await interaction.response.send_message(embed=embed)
            logging.info(f"{interaction.user.name} used /leaderboard {stat.lower()}")

        if stat == 'Largest Single Win - CF':
            dao = UserDao()
            cfdao = CoinflipDao()
            leaders = cfdao.get_top_wins()

            embed = discord.Embed(title=f"Top 5 Users by {stat.upper()}", color=interaction.user.color)

            for i, (discord_username, amount_won, timestamp) in enumerate(leaders, start=1):
                formatted_amount_won = "{:,.0f}".format(amount_won)
                formatted_timestamp = timestamp.strftime('%m-%d-%Y %H:%M')
                embed.add_field(name=f"{i}. {discord_username} | {formatted_timestamp} CST", value=f"{formatted_amount_won} Credits", inline=False)

            await interaction.response.send_message(embed=embed)
            logging.info(f"{interaction.user.name} used /leaderboard {stat.lower()}")

        if stat == 'Largest Single Loss - CF':
            dao = UserDao()
            cfdao = CoinflipDao()
            leaders = cfdao.get_top_losses()

            embed = discord.Embed(title=f"Top 5 Users by {stat.upper()}", color=interaction.user.color)

            for i, (discord_username, amount_lost, timestamp) in enumerate(leaders, start=1):
                formatted_amount_lost = "{:,.0f}".format(amount_lost)
                formatted_timestamp = timestamp.strftime('%m-%d-%Y %H:%M')
                embed.add_field(name=f"{i}. {discord_username} | {formatted_timestamp} CST", value=f"{formatted_amount_lost} Credits", inline=False)

            await interaction.response.send_message(embed=embed)
            logging.info(f"{interaction.user.name} used /leaderboard {stat.lower()}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Leaderboard(bot))