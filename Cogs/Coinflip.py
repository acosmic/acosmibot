import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from Dao.GuildUserDao import GuildUserDao
from Dao.GamesDao import GamesDao, CoinflipDao
from Dao.GuildDao import GuildDao

import random
from logger import AppLogger
import typing
from datetime import datetime

logger = AppLogger(__name__).get_logger()


class Coinflip(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="coinflip", description="Flip a coin for a chance to win credits")
    async def coinflip(self, interaction: discord.Interaction, call: typing.Literal['Heads', 'Tails'], bet: int):
        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return
        if call not in ['Heads', 'Tails']:
            await interaction.response.send_message("Invalid choice. Please choose either 'Heads' or 'Tails'.",
                                                    ephemeral=True)
            return

        # Use GuildUserDao for server-specific currency
        guild_user_dao = GuildUserDao()
        # cfdao = CoinflipDao()

        # Get guild user (server-specific data)
        guild_user = guild_user_dao.get_guild_user(interaction.user.id, interaction.guild.id)

        if not guild_user:
            await interaction.response.send_message(
                "You need to send at least one message in this server before using games.", ephemeral=True)
            return

        cost = abs(bet)  # Make sure bet is positive

        # Minimum bet validation
        if cost < 1:
            await interaction.response.send_message("Minimum bet is 1 credit.", ephemeral=True)
            return

        # Check if user has enough currency
        if guild_user.currency < cost:
            await interaction.response.send_message(
                f"You don't have enough credits. You have {guild_user.currency:,} credits but need {cost:,}.",
                ephemeral=True)
            return

        # Flip the coin
        result = random.choice(['Heads', 'Tails'])

        embed = discord.Embed()

        if result == call:
            # User wins
            guild_user.currency += cost
            amount_won = cost
            amount_lost = 0

            embed.title = f":white_check_mark: {interaction.user.display_name} called {call}! :white_check_mark:"
            embed.description = f"# {result.upper()}! | {interaction.user.display_name} won {cost:,.0f} credits! <:PepeDank:1200292095131406388>"
            embed.colour = discord.Color.green()
            embed.add_field(name="New Balance", value=f"{guild_user.currency:,} credits", inline=True)

        else:
            # User loses
            guild_user.currency -= cost
            amount_won = 0
            amount_lost = cost

            # Add to vault (10% of lost credits)
            try:

                guild_dao = GuildDao()
                vgain = int(cost * 0.1)  # 10% of the lost credits
                guild_dao.add_vault_currency(interaction.guild.id, vgain)

                embed.title = f":x: {interaction.user.display_name} called {call}! :x:"
                embed.description = f"# {result.upper()}! | {interaction.user.display_name} lost {cost:,.0f} credits. <a:giggle:1165098258968879134>\n\n{vgain:,.0f} Credits have been added to the vault! 🏦"
                embed.colour = discord.Color.red()
                embed.add_field(name="New Balance", value=f"{guild_user.currency:,} credits", inline=True)
                embed.add_field(name="Vault Gained", value=f"{vgain:,} credits", inline=True)

            except Exception as e:
                logger.error(f"Error updating vault: {e}")
                # Still proceed with the game even if vault update fails
                embed.title = f"🪙 {interaction.user.display_name} called {call}! 🪙"
                embed.description = f"# {result.upper()}! | {interaction.user.display_name} lost {cost:,.0f} credits."
                embed.colour = discord.Color.red()
                embed.add_field(name="New Balance", value=f"{guild_user.currency:,} credits", inline=True)

        # Log the event to both tables
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Add to main Games table first
        games_dao = GamesDao()
        game_result = "win" if amount_won > 0 else "lose"
        game_id = games_dao.add_game(
            user_id=interaction.user.id,
            guild_id=interaction.guild.id,
            game_type="coinflip",
            amount_bet=cost,
            amount_won=amount_won,
            amount_lost=amount_lost,
            result=game_result
        )

        # Add to specific Coinflip table
        if game_id:
            coinflip_dao = CoinflipDao()
            coinflip_dao.add_coinflip_game(
                game_id=game_id,
                user_id=interaction.user.id,
                guild_id=interaction.guild.id,
                user_call=call,
                actual_result=result,
                amount_bet=cost,
                amount_won=amount_won,
                amount_lost=amount_lost
            )

        # Update database
        try:
            guild_user_dao.update_guild_user(guild_user)

            # Also update global user stats if needed
            user_dao = UserDao()
            global_user = user_dao.get_user(interaction.user.id)
            if global_user:
                if hasattr(global_user, 'total_currency'):
                    if amount_won > 0:
                        global_user.total_currency += amount_won
                    elif amount_lost > 0:
                        global_user.total_currency = max(0, global_user.total_currency - amount_lost)
                    user_dao.update_user(global_user)

        except Exception as e:
            logger.error(f"Error updating database for coinflip: {e}")

            # # Check if we've already responded
            # if interaction.response.is_done():
            #     await interaction.followup.send("An error occurred while processing your bet. Please try again.",
            #                                     ephemeral=True)
            # else:
            #     await interaction.response.send_message("An error occurred while processing your bet. Please try again.", ephemeral=True)
            # return
        await interaction.response.send_message(embed=embed)
        logger.info(f"{interaction.user.name} used /coinflip command - {call} vs {result} - {cost} credits")


async def setup(bot: commands.Bot):
    await bot.add_cog(Coinflip(bot))