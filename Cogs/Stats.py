import discord
from discord.ext import commands
from discord import app_commands
from Dao.GuildUserDao import GuildUserDao
from Dao.UserDao import UserDao
from Dao.GamesDao import GamesDao
from logger import AppLogger

logging = AppLogger(__name__).get_logger()


class Stats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="stats",
                          description="Leave blank to see your own stats, or mention another user to see their stats.")
    async def stats(self, interaction: discord.Interaction, user: discord.User = None):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        guild_user_dao = GuildUserDao()
        user_dao = UserDao()
        games_dao = GamesDao()

        target_user = user if user else interaction.user

        # Get guild-specific data
        user_rank = guild_user_dao.get_guild_user_rank(target_user.id, interaction.guild.id)
        current_guild_user = guild_user_dao.get_guild_user(target_user.id, interaction.guild.id)
        current_global_user = user_dao.get_user(target_user.id)

        if current_guild_user is None:
            if target_user == interaction.user:
                await interaction.response.send_message(
                    "You don't have stats in this server yet. Send a message to get started!", ephemeral=True)
            else:
                await interaction.response.send_message(f"{target_user.name} doesn't have stats in this server yet.",
                                                        ephemeral=True)
            return

        # Get all game stats from unified table
        all_stats = games_dao.get_user_game_stats(target_user.id, interaction.guild.id)

        # Get game-specific stats
        coinflip_stats = games_dao.get_specific_game_stats(target_user.id, "coinflip", interaction.guild.id)
        slots_stats = games_dao.get_specific_game_stats(target_user.id, "slots", interaction.guild.id)
        deathroll_stats = games_dao.get_specific_game_stats(target_user.id, "deathroll", interaction.guild.id)
        rps_stats = games_dao.get_specific_game_stats(target_user.id, "rockpaperscissors", interaction.guild.id)


        # Overall stats
        total_stats = all_stats.get('total', {})
        total_games = total_stats.get('total_games', 0)
        total_net_profit = total_stats.get('net_profit', 0)
        overall_win_rate = total_stats.get('win_rate', 0)

        # Coinflip stats
        cf_games = coinflip_stats.get('total_games', 0)
        cf_wins = coinflip_stats.get('wins', 0)
        cf_losses = coinflip_stats.get('losses', 0)
        cf_won = coinflip_stats.get('total_won', 0)
        cf_lost = coinflip_stats.get('total_lost', 0)
        cf_win_rate = coinflip_stats.get('win_rate', 0)

        # Slots stats
        slots_spins = slots_stats.get('total_games', 0)
        slots_wins = slots_stats.get('wins', 0)
        slots_losses = slots_stats.get('losses', 0)
        slots_won = slots_stats.get('total_won', 0)
        slots_lost = slots_stats.get('total_lost', 0)
        slots_win_rate = slots_stats.get('win_rate', 0)
        slots_biggest = slots_stats.get('biggest_win', 0)

        # Deathroll stats
        dr_games = deathroll_stats.get('total_games', 0)
        dr_wins = deathroll_stats.get('wins', 0)
        dr_losses = deathroll_stats.get('losses', 0)
        dr_won = deathroll_stats.get('total_won', 0)
        dr_lost = deathroll_stats.get('total_lost', 0)
        dr_win_rate = deathroll_stats.get('win_rate', 0)
        dr_biggest = deathroll_stats.get('biggest_win', 0)

        # RPS stats
        rps_games = rps_stats.get('total_games', 0)
        rps_wins = rps_stats.get('wins', 0)
        rps_losses = rps_stats.get('losses', 0)
        rps_draws = rps_stats.get('draws', 0)  # Note: need to add draws to get_specific_game_stats
        rps_won = rps_stats.get('total_won', 0)
        rps_lost = rps_stats.get('total_lost', 0)
        rps_win_rate = rps_stats.get('win_rate', 0)

        streak = current_guild_user.streak
        streak_emoji = f"🔥 x{streak}" if streak > 0 else "Chat again tomorrow to increase your streak!"

        if user_rank is not None:
            name_from_db = user_rank[2]
            display_name = target_user.name if target_user.name else name_from_db

            # Build gambling stats section dynamically
            gambling_section = (
                f"### 🎰 Gambling Stats (Overall)\n"
                f"Total Games: {total_games:,}\n"
                f"Net Profit: {total_net_profit:+,.0f} credits\n"
                f"Overall Win Rate: {overall_win_rate:.1f}%\n"
            )

            # Add coinflip if user has played
            if cf_games > 0:
                gambling_section += (
                    f"### 🪙 Coinflip\n"
                    f"Games: {cf_games:,}\n"
                    f"Wins: {cf_wins:,} | Losses: {cf_losses:,}\n"
                    f"Won: {cf_won:,.0f} | Lost: {cf_lost:,.0f}\n"
                    f"Win Rate: {cf_win_rate:.1f}%\n"
                )

            # Add slots if user has played
            if slots_spins > 0:
                gambling_section += (
                    f"### 🎰 Slots\n"
                    f"Spins: {slots_spins:,}\n"
                    f"Wins: {slots_wins:,} | Losses: {slots_losses:,}\n"
                    f"Won: {slots_won:,.0f} | Lost: {slots_lost:,.0f}\n"
                    f"Win Rate: {slots_win_rate:.1f}%\n"
                    f"Biggest Win: {slots_biggest:,.0f} credits\n"
                )

            # Add deathroll if user has played
            if dr_games > 0:
                gambling_section += (
                    f"### ☠️ Deathroll\n"
                    f"Games: {dr_games:,}\n"
                    f"Wins: {dr_wins:,} | Losses: {dr_losses:,}\n"
                    f"Won: {dr_won:,.0f} | Lost: {dr_lost:,.0f}\n"
                    f"Win Rate: {dr_win_rate:.1f}%\n"
                    f"Biggest Win: {dr_biggest:,.0f} credits\n"
                )

                # Add to gambling section (after slots):
                if rps_games > 0:
                    gambling_section += (
                        f"### 🪨📄✂️ Rock Paper Scissors\n"
                        f"Games: {rps_games:,}\n"
                        f"Wins: {rps_wins:,} | Losses: {rps_losses:,} | Draws: {rps_draws:,}\n"
                        f"Won: {rps_won:,.0f} | Lost: {rps_lost:,.0f}\n"
                        f"Win Rate: {rps_win_rate:.1f}%\n"
                    )

            embed = discord.Embed(
                description=(
                    f"# {display_name}\n\n"
                    f"### Guild Ranked #{user_rank[-1]} in {interaction.guild.name}\n"
                    f"Guild Level: {current_guild_user.level}\n"
                    f"Guild EXP: {current_guild_user.exp:,.0f}\n"
                    f"Messages: {current_guild_user.messages_sent:,.0f}\n"
                    f"Reactions: {current_guild_user.reactions_sent:,.0f}\n"
                    f"### 🤖 Global Stats\n"
                    f"Global Level: {current_global_user.global_level if current_global_user else 0}\n"
                    f"Global EXP: {current_global_user.global_exp if current_global_user else 0:,.0f}\n"
                    f"{gambling_section}"
                    f"### Streak: {streak_emoji}\n"
                    f"Highest: {current_guild_user.highest_streak}\n"
                ),
                color=target_user.color)
            embed.set_thumbnail(url=target_user.avatar)

            await interaction.response.send_message(embed=embed)
            logging.info(f"{interaction.user.name} used /stats command for {target_user.name}")
        else:
            await interaction.response.send_message("User data not found.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Stats(bot))