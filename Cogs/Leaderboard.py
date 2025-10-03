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

    @staticmethod
    def has_problematic_chars(text):
        """Check if text contains non-ASCII characters that break alignment"""
        return any(ord(c) >= 128 for c in text)

    @app_commands.command(name="leaderboard", description="Returns top 10 users based on Currency, EXP, etc.")
    async def leaderboard(self, interaction: discord.Interaction, stat: typing.Literal[
        'Currency', 'Exp', 'Level', 'Global Exp', 'Global Level', 'Coinflip Wins', 'Coinflip Losses', 'Slots Wins']):

        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        if stat == 'Currency' or stat == 'Exp' or stat == 'Level':
            guild_dao = GuildUserDao()
            # Map stat names to database column names
            column_map = {
                'Currency': 'currency',
                'Exp': 'exp',
                'Level': 'level'
            }
            column = column_map[stat]
            leaders = guild_dao.get_top_guild_users(interaction.guild.id, column)

            embed = discord.Embed(title=f"Top Users by {stat.upper()}", color=interaction.user.color)
            leaderboard_text = ""

            for i, (user_id, name, nickname, value) in enumerate(leaders, start=1):
                formatted_value = "{:,.0f}".format(value)

                # Use nickname if it exists and has no problematic characters, otherwise use name
                display_name = nickname or name or "Unknown User"
                if nickname and self.has_problematic_chars(nickname):
                    display_name = name or "Unknown User"

                line = f"{i:>2}. {display_name:<20} {formatted_value:>10}\n"
                leaderboard_text += line

            embed.description = f"```\n{leaderboard_text}```"
            await interaction.response.send_message(embed=embed)
            logger.info(f"{interaction.user.name} used /leaderboard {stat.lower()}")

        if stat == 'Global Exp' or stat == 'Global Level':
            dao = UserDao()
            if stat == 'Global Exp':
                leaders = dao.get_top_users_by_global_exp()
            else:
                leaders = dao.get_top_users_by_global_level()

            embed = discord.Embed(title=f"Top Users by {stat.upper()}", color=interaction.user.color)
            leaderboard_text = ""

            for i, (user_id, username, global_name, value, level) in enumerate(leaders, start=1):
                formatted_value = "{:,.0f}".format(value)

                # Use global_name if it exists and has no problematic characters, otherwise use username
                display_name = global_name or username or "Unknown User"
                if global_name and self.has_problematic_chars(global_name):
                    display_name = username or "Unknown User"

                line = f"{i:>2}. {display_name:<20} {formatted_value:>10}\n"
                leaderboard_text += line

            embed.description = f"```\n{leaderboard_text}```"
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