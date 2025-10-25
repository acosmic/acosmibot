#! /usr/bin/python3.10
import discord
from discord.ext import commands
from discord import app_commands
from Dao.GamesDao import GamesDao
from logger import AppLogger

logging = AppLogger(__name__).get_logger()


class StatsGames(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="stats-games",
                          description="View your gambling statistics. Leave blank for your stats, or mention another user.")
    async def stats_games(self, interaction: discord.Interaction, user: discord.User = None):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        games_dao = GamesDao()
        target_user = user if user else interaction.user

        # Get all game stats from unified table
        all_stats = games_dao.get_user_game_stats(target_user.id, interaction.guild.id)

        # Get game-specific stats
        coinflip_stats = games_dao.get_specific_game_stats(target_user.id, "coinflip", interaction.guild.id)
        slots_stats = games_dao.get_specific_game_stats(target_user.id, "slots", interaction.guild.id)
        deathroll_stats = games_dao.get_specific_game_stats(target_user.id, "deathroll", interaction.guild.id)
        rps_stats = games_dao.get_specific_game_stats(target_user.id, "rockpaperscissors", interaction.guild.id)
        blackjack_stats = games_dao.get_specific_game_stats(target_user.id, "blackjack", interaction.guild.id)

        # Overall stats
        total_stats = all_stats.get('total', {})
        total_games = total_stats.get('total_games', 0)
        total_bet = total_stats.get('total_bet', 0)
        total_won = total_stats.get('total_won', 0)
        total_lost = total_stats.get('total_lost', 0)
        total_net_profit = total_stats.get('net_profit', 0)
        overall_win_rate = total_stats.get('win_rate', 0)

        # Check if user has any gambling stats
        if total_games == 0:
            if target_user == interaction.user:
                await interaction.response.send_message(
                    "You haven't played any games yet! Try `/coinflip`, `/slots`, `/deathroll`, `/rockpaperscissors`, or `/blackjack`",
                    ephemeral=True)
            else:
                await interaction.response.send_message(
                    f"{target_user.name} hasn't played any games yet.",
                    ephemeral=True)
            return

        # Determine favorite game
        favorite_game = self._get_favorite_game(all_stats)

        # Build the embed
        display_name = target_user.display_name

        # Build overall section
        overall_section = self._build_overall_section(total_stats, favorite_game)

        # Build game-specific sections (only if played)
        game_sections = ""

        if blackjack_stats.get('total_games', 0) > 0:
            game_sections += self._build_blackjack_section(blackjack_stats)

        if slots_stats.get('total_games', 0) > 0:
            game_sections += self._build_slots_section(slots_stats)

        if coinflip_stats.get('total_games', 0) > 0:
            game_sections += self._build_coinflip_section(coinflip_stats)

        if deathroll_stats.get('total_games', 0) > 0:
            game_sections += self._build_deathroll_section(deathroll_stats)

        if rps_stats.get('total_games', 0) > 0:
            game_sections += self._build_rps_section(rps_stats)

        embed = discord.Embed(
            title=f"🎰 {display_name}'s Gambling Stats",
            description=f"{overall_section}{game_sections}",
            color=self._get_profit_color(total_net_profit)
        )
        embed.set_thumbnail(url=target_user.avatar)
        embed.set_footer(text="📊 View leaderboards: /leaderboard")

        await interaction.response.send_message(embed=embed)
        logging.info(f"{interaction.user.name} used /stats-games command for {target_user.name}")

    def _format_profit(self, profit: int) -> str:
        """Format profit with emoji indicator"""
        if profit > 0:
            return f"📈 +{profit:,}"
        elif profit < 0:
            return f"📉 {profit:,}"
        else:
            return f"➡️ {profit:,}"

    def _get_profit_color(self, profit: int) -> discord.Color:
        """Get embed color based on profit"""
        if profit > 0:
            return discord.Color.green()
        elif profit < 0:
            return discord.Color.red()
        else:
            return discord.Color.blue()

    def _get_favorite_game(self, all_stats: dict) -> str:
        """Determine favorite game by total games played"""
        game_counts = {}

        for game_type, stats in all_stats.items():
            if game_type != 'total' and isinstance(stats, dict):
                games_played = stats.get('total_games', 0)
                if games_played > 0:
                    game_counts[game_type] = games_played

        if not game_counts:
            return "None"

        favorite = max(game_counts, key=game_counts.get)

        # Format game names
        game_names = {
            'coinflip': 'Coinflip',
            'slots': 'Slots',
            'deathroll': 'Deathroll',
            'rockpaperscissors': 'Rock Paper Scissors',
            'blackjack': 'Blackjack'
        }

        return f"{game_names.get(favorite, favorite)} ({game_counts[favorite]:,} games)"

    def _build_overall_section(self, total_stats: dict, favorite_game: str) -> str:
        """Build overall gambling stats section"""
        total_games = total_stats.get('total_games', 0)
        total_bet = total_stats.get('total_bet', 0)
        total_won = total_stats.get('total_won', 0)
        total_lost = total_stats.get('total_lost', 0)
        net_profit = total_stats.get('net_profit', 0)
        win_rate = total_stats.get('win_rate', 0)

        return (
            f"### 🎰 Overall\n"
            f"Total Games: {total_games:,}\n"
            f"Total Wagered: {total_bet:,} credits\n"
            f"Total Won: {total_won:,} credits\n"
            f"Total Lost: {total_lost:,} credits\n"
            f"Net Profit: {self._format_profit(net_profit)} credits\n"
            f"Win Rate: {win_rate:.1f}%\n"
            f"Favorite Game: {favorite_game}\n\n"
        )

    def _build_coinflip_section(self, stats: dict) -> str:
        """Build coinflip stats section"""
        games = stats.get('total_games', 0)
        wins = stats.get('wins', 0)
        losses = stats.get('losses', 0)
        won = stats.get('total_won', 0)
        lost = stats.get('total_lost', 0)
        win_rate = stats.get('win_rate', 0)
        net_profit = won - lost

        return (
            f"### 🪙 Coinflip\n"
            f"Games: {games:,}\n"
            f"Wins: {wins:,} | Losses: {losses:,}\n"
            f"Total Won: {won:,} | Lost: {lost:,}\n"
            f"Win Rate: {win_rate:.1f}%\n"
            f"Net Profit: {self._format_profit(net_profit)} credits\n\n"
        )

    def _build_slots_section(self, stats: dict) -> str:
        """Build slots stats section"""
        spins = stats.get('total_games', 0)
        wins = stats.get('wins', 0)
        losses = stats.get('losses', 0)
        won = stats.get('total_won', 0)
        lost = stats.get('total_lost', 0)
        win_rate = stats.get('win_rate', 0)
        biggest = stats.get('biggest_win', 0)
        net_profit = won - lost

        return (
            f"### 🎰 Slots\n"
            f"Spins: {spins:,}\n"
            f"Wins: {wins:,} | Losses: {losses:,}\n"
            f"Total Won: {won:,} | Lost: {lost:,}\n"
            f"Win Rate: {win_rate:.1f}%\n"
            f"Biggest Win: {biggest:,} credits\n"
            f"Net Profit: {self._format_profit(net_profit)} credits\n\n"
        )

    def _build_deathroll_section(self, stats: dict) -> str:
        """Build deathroll stats section"""
        games = stats.get('total_games', 0)
        wins = stats.get('wins', 0)
        losses = stats.get('losses', 0)
        won = stats.get('total_won', 0)
        lost = stats.get('total_lost', 0)
        win_rate = stats.get('win_rate', 0)
        biggest = stats.get('biggest_win', 0)
        net_profit = won - lost

        return (
            f"### 💀 Deathroll\n"
            f"Games: {games:,}\n"
            f"Wins: {wins:,} | Losses: {losses:,}\n"
            f"Total Won: {won:,} | Lost: {lost:,}\n"
            f"Win Rate: {win_rate:.1f}%\n"
            f"Biggest Win: {biggest:,} credits\n"
            f"Net Profit: {self._format_profit(net_profit)} credits\n\n"
        )

    def _build_rps_section(self, stats: dict) -> str:
        """Build Rock Paper Scissors stats section"""
        games = stats.get('total_games', 0)
        wins = stats.get('wins', 0)
        losses = stats.get('losses', 0)
        draws = stats.get('draws', 0)
        won = stats.get('total_won', 0)
        lost = stats.get('total_lost', 0)
        win_rate = stats.get('win_rate', 0)
        net_profit = won - lost

        return (
            f"### 🪨📄✂️ Rock Paper Scissors\n"
            f"Games: {games:,}\n"
            f"Wins: {wins:,} | Losses: {losses:,} | Draws: {draws:,}\n"
            f"Total Won: {won:,} | Lost: {lost:,}\n"
            f"Win Rate: {win_rate:.1f}%\n"
            f"Net Profit: {self._format_profit(net_profit)} credits\n\n"
        )

    def _build_blackjack_section(self, stats: dict) -> str:
        """Build blackjack stats section with pushes and blackjacks"""
        games = stats.get('total_games', 0)
        wins = stats.get('wins', 0)
        losses = stats.get('losses', 0)
        draws = stats.get('draws', 0)  # Pushes in blackjack
        won = stats.get('total_won', 0)
        lost = stats.get('total_lost', 0)
        win_rate = stats.get('win_rate', 0)
        biggest = stats.get('biggest_win', 0)
        net_profit = won - lost

        # Calculate win rate excluding pushes
        non_push_games = wins + losses
        win_rate_excl_push = (wins / non_push_games * 100) if non_push_games > 0 else 0

        return (
            f"### ♠️ Blackjack\n"
            f"Games: {games:,}\n"
            f"Wins: {wins:,} | Losses: {losses:,} | Pushes: {draws:,}\n"
            f"Total Won: {won:,} | Lost: {lost:,}\n"
            f"Win Rate: {win_rate_excl_push:.1f}% (excl. pushes)\n"
            f"Biggest Win: {biggest:,} credits\n"
            f"Net Profit: {self._format_profit(net_profit)} credits\n\n"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(StatsGames(bot))
