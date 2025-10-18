import discord
from discord.ext import commands
from discord import app_commands
from Dao.GuildUserDao import GuildUserDao
from Dao.UserDao import UserDao
from logger import AppLogger

logging = AppLogger(__name__).get_logger()


class Stats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="stats",
                          description="View your leveling and activity stats. Use /stats-games for gambling stats.")
    async def stats(self, interaction: discord.Interaction, user: discord.User = None):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        guild_user_dao = GuildUserDao()
        user_dao = UserDao()

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

        streak = current_guild_user.streak
        streak_emoji = f"🔥 x{streak}" if streak > 0 else "Chat again tomorrow to increase your streak!"

        if user_rank is not None:
            name_from_db = user_rank[2]
            display_name = target_user.name if target_user.name else name_from_db

            embed = discord.Embed(
                description=(
                    f"# {display_name}\n\n"
                    f"### Guild Ranked #{user_rank[-1]} in {interaction.guild.name}\n"
                    f"Guild Level: {current_guild_user.level}\n"
                    f"Guild EXP: {current_guild_user.exp:,.0f}\n"
                    f"Messages: {current_guild_user.messages_sent:,.0f}\n"
                    f"Reactions: {current_guild_user.reactions_sent:,.0f}\n\n"
                    f"### 🤖 Global Stats\n"
                    f"Global Level: {current_global_user.global_level if current_global_user else 0}\n"
                    f"Global EXP: {current_global_user.global_exp if current_global_user else 0:,.0f}\n\n"
                    f"### Streak: {streak_emoji}\n"
                    f"Highest: {current_guild_user.highest_streak}\n"
                ),
                color=target_user.color)
            embed.set_thumbnail(url=target_user.avatar)
            embed.set_footer(text="💰 View gambling stats: /stats-games")

            await interaction.response.send_message(embed=embed)
            logging.info(f"{interaction.user.name} used /stats command for {target_user.name}")
        else:
            await interaction.response.send_message("User data not found.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Stats(bot))