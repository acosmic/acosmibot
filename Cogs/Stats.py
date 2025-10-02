import discord
from discord.ext import commands
from discord import app_commands
from Dao.GuildUserDao import GuildUserDao
from Dao.UserDao import UserDao
from Dao.CoinflipDao import CoinflipDao
from Entities.GuildUser import GuildUser
from Entities.User import User
from logger import AppLogger

logging = AppLogger(__name__).get_logger()


class Stats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="stats",
                          description="Leave blank to see your own stats, or mention another user to see their stats.")
    async def stats(self, interaction: discord.Interaction, user: discord.User = None):
        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return
        guild_user_dao = GuildUserDao()
        user_dao = UserDao()
        cfdao = CoinflipDao()

        if user is not None:
            target_user = user
        else:
            target_user = interaction.user

        # Get guild-specific data
        user_rank = guild_user_dao.get_guild_user_rank(target_user.id, interaction.guild.id)
        current_guild_user = guild_user_dao.get_guild_user(target_user.id, interaction.guild.id)

        # Get global data
        current_global_user = user_dao.get_user(target_user.id)

        if current_guild_user is None:
            if target_user == interaction.user:
                await interaction.response.send_message(
                    "You don't have stats in this server yet. Send a message to get started!", ephemeral=True)
            else:
                await interaction.response.send_message(f"{target_user.name} doesn't have stats in this server yet.",
                                                        ephemeral=True)
            return

        # Get coinflip stats
        flips = cfdao.get_total_flips(current_guild_user.user_id) if cfdao.get_total_flips(
            current_guild_user.user_id) is not None else 0
        flip_wins = cfdao.get_flip_wins(current_guild_user.user_id) if cfdao.get_flip_wins(
            current_guild_user.user_id) is not None else 0
        flip_losses = cfdao.get_flip_losses(current_guild_user.user_id) if cfdao.get_flip_losses(
            current_guild_user.user_id) is not None else 0

        flip_amount_won = cfdao.get_total_won(current_guild_user.user_id) if cfdao.get_total_won(
            current_guild_user.user_id) is not None else 0
        flip_amount_lost = cfdao.get_total_lost(current_guild_user.user_id) if cfdao.get_total_lost(
            current_guild_user.user_id) is not None else 0

        flip_win_rate = flip_wins / flips * 100 if flips > 0 else 0

        streak = current_guild_user.streak
        streak_emoji = f"🔥 x{streak}" if streak > 0 else "Chat again tomorrow to increase your streak! <:NicolasCagePOG:1203568248885346334>"

        if user_rank is not None:
            name_from_db = user_rank[2]  # nickname from guild_user_rank query
            display_name = target_user.name if target_user.name is not None else name_from_db

            # Level emoji based on global level
            level_emoji = "<a:NODDERS:1312038419517673566>"
            if current_global_user and current_global_user.global_level >= 5:
                level_emoji = "<:antivax:1258070199945531402>"
            if current_global_user and current_global_user.global_level >= 10:
                level_emoji = "<:moonlandinghoax:1258075177934131200>"
            if current_global_user and current_global_user.global_level >= 15:
                level_emoji = "<:aliens:1258067124623114351>"
            if current_global_user and current_global_user.global_level >= 20:
                level_emoji = "<:flatearth:1258058656465817691>"
            if current_global_user and current_global_user.global_level >= 25:
                level_emoji = "<a:shungite:1258061858586365963>"
            if current_global_user and current_global_user.global_level >= 30:
                level_emoji = "<:illuminati:1258059529510195200>"

            embed = discord.Embed(
                description=(
                    f"# {display_name} {level_emoji}\n\n"
                    f"### Guild Ranked #{user_rank[-1]} in {interaction.guild.name}\n"
                    f"Guild Level: {current_guild_user.level}\n"
                    f"Guild EXP: {current_guild_user.exp:,.0f}\n"
                    f"Messages: {current_guild_user.messages_sent:,.0f}\n"
                    f"Reactions: {current_guild_user.reactions_sent:,.0f}\n\n"
                    f"### 🤖 Acosmibot Global Stats\n"
                    f"Global Level: {current_global_user.global_level if current_global_user else 0}\n"
                    f"Global EXP: {current_global_user.global_exp if current_global_user else 0:,.0f}\n\n"
                    f"### 🎰 Gambling Stats\n"
                    f"Coinflips: {flips}\n"
                    f"Coinflip Wins: {flip_wins}\n"
                    f"Coinflip Losses: {flip_losses}\n"
                    f"Coinflip Credits Won: {flip_amount_won:,.0f}\n"
                    f"Coinflip Credits Lost: {flip_amount_lost:,.0f}\n"
                    f"Coinflip Win Rate: {flip_win_rate:.2f}%\n\n"
                    f"### Streak: {streak_emoji}\n"
                    f"Highest: {current_guild_user.highest_streak}\n"
                ),
                color=target_user.color)
            embed.set_thumbnail(url=target_user.avatar)

            await interaction.response.send_message(embed=embed)
            logging.info(
                f"{interaction.user.name} used /stats command for {target_user.name} in {interaction.guild.name}")

        else:
            await interaction.response.send_message("User data not found.", ephemeral=True)
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(Stats(bot))