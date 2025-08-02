import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from Dao.GuildUserDao import GuildUserDao
from Dao.SlotsDao import SlotsDao
from Dao.CoinflipDao import CoinflipDao
from logger import AppLogger
import typing

logger = AppLogger(__name__).get_logger()


class Leaderboard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="leaderboard", description="Returns top 5 users based on Currency, EXP, etc.")
    async def leaderboard(self, interaction: discord.Interaction, stat: typing.Literal[
        'Currency', 'Exp', 'Season Level', 'Global Exp', 'Global Level', 'Coinflip Wins', 'Coinflip Losses', 'Slots Wins']):

        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        if stat == 'Currency' or stat == 'Exp' or stat == 'Season Level':
            guild_dao = GuildUserDao()

            # Map stat names to database column names
            column_map = {
                'Currency': 'currency',
                'Exp': 'exp',
                'Season Level': 'season_level'
            }

            column = column_map[stat]
            leaders = guild_dao.get_top_guild_users(interaction.guild.id, column)

            embed = discord.Embed(title=f"Top 5 Users by {stat.upper()}", color=interaction.user.color)

            for i, (user_id, nickname, value) in enumerate(leaders, start=1):
                formatted_value = "{:,.0f}".format(value)
                display_name = nickname or "Unknown User"
                embed.add_field(name=f"{i}. {display_name}", value=f"{formatted_value} {stat.capitalize()}\n",
                                inline=False)

            await interaction.response.send_message(embed=embed)
            logger.info(f"{interaction.user.name} used /leaderboard {stat.lower()}")

        if stat == 'Global Exp' or stat == 'Global Level':
            dao = UserDao()

            if stat == 'Global Exp':
                leaders = dao.get_top_users_by_global_exp()
            else:  # Global Level
                # You'll need to add this method to UserDao
                leaders = dao.get_top_users_by_global_level()

            embed = discord.Embed(title=f"Top 5 Users by {stat.upper()}", color=interaction.user.color)

            for i, (user_id, username, global_name, value, level) in enumerate(leaders, start=1):
                formatted_value = "{:,.0f}".format(value)
                display_name = global_name or username
                embed.add_field(name=f"{i}. {display_name}",
                                value=f"{formatted_value} {stat.replace('Global ', '').capitalize()}\n", inline=False)

            await interaction.response.send_message(embed=embed)
            logger.info(f"{interaction.user.name} used /leaderboard {stat.lower()}")

        if stat == 'Coinflip Wins':
            dao = UserDao()
            cfdao = CoinflipDao()
            leaders = cfdao.get_top_wins()

            embed = discord.Embed(title=f"Top 5 Users by {stat.upper()}", color=interaction.user.color)

            for i, (discord_username, amount_won, timestamp) in enumerate(leaders, start=1):
                formatted_amount_won = "{:,.0f}".format(amount_won)
                formatted_timestamp = timestamp.strftime('%m-%d-%Y %H:%M')
                embed.add_field(name=f"{i}. {discord_username} | {formatted_timestamp} CST",
                                value=f"{formatted_amount_won} Credits", inline=False)

            await interaction.response.send_message(embed=embed)
            logger.info(f"{interaction.user.name} used /leaderboard {stat.lower()}")

        if stat == 'Coinflip Losses':
            dao = UserDao()
            cfdao = CoinflipDao()
            leaders = cfdao.get_top_losses()

            embed = discord.Embed(title=f"Top 5 Users by {stat.upper()}", color=interaction.user.color)

            for i, (discord_username, amount_lost, timestamp) in enumerate(leaders, start=1):
                formatted_amount_lost = "{:,.0f}".format(amount_lost)
                formatted_timestamp = timestamp.strftime('%m-%d-%Y %H:%M')
                embed.add_field(name=f"{i}. {discord_username} | {formatted_timestamp} CST",
                                value=f"{formatted_amount_lost} Credits", inline=False)

            await interaction.response.send_message(embed=embed)
            logger.info(f"{interaction.user.name} used /leaderboard {stat.lower()}")

        if stat == 'Slots Wins':
            dao = UserDao()
            slotsDao = SlotsDao()
            leaders = slotsDao.get_top_wins()

            embed = discord.Embed(title=f"Top 5 Users by {stat.upper()}", color=interaction.user.color)

            for i, (discord_username, amount_won, timestamp) in enumerate(leaders, start=1):
                formatted_amount_won = "{:,.0f}".format(amount_won)
                formatted_timestamp = timestamp.strftime('%m-%d-%Y %H:%M')
                embed.add_field(name=f"{i}. {discord_username} | {formatted_timestamp} CST",
                                value=f"{formatted_amount_won} Credits", inline=False)

            await interaction.response.send_message(embed=embed)
            logger.info(f"{interaction.user.name} used /leaderboard {stat.lower()}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Leaderboard(bot))