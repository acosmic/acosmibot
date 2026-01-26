import discord
from discord.ext import commands
from discord import app_commands
from Dao.GuildUserDao import GuildUserDao
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class Balance(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    @app_commands.command(name="balance", description="Check your Credit balance.")
    async def balance(self, interaction: discord.Interaction, user: discord.User = None):
        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        guild_user_dao = GuildUserDao()
        try:
            if user is None or not user.bot:
                target_user = user if user else interaction.user

                # Try to get currency from session cache first
                from Services.SessionManager import get_session_manager
                session_manager = get_session_manager()
                cached_currency = None

                if session_manager.redis_available:
                    try:
                        cached_currency = await session_manager.get_currency(interaction.guild.id, target_user.id)
                        if cached_currency is not None:
                            logger.debug(f"Using cached currency for {target_user.name}: {cached_currency}")
                    except Exception as e:
                        logger.warning(f"Could not load currency from session cache: {e}")

                # Get guild user data
                guild_user = guild_user_dao.get_guild_user(target_user.id, interaction.guild.id)

                if guild_user is None:
                    title_text = "Balance"
                    if target_user == interaction.user:
                        message_text = "### You don't have an account in this server yet. Send a message to get started! 💰"
                    else:
                        message_text = f"### {target_user.name} doesn't have an account in this server yet. 💰"
                else:
                    # Use cached currency if available, otherwise use DB value
                    current_currency = cached_currency if cached_currency is not None else guild_user.currency

                    if target_user == interaction.user:
                        title_text = f"Your balance:"
                        message_text = f"{current_currency:,.0f} Credits. 💰"
                    else:
                        title_text = f"{target_user.name}'s balance:"
                        message_text = f"{current_currency:,.0f} Credits. 💰"
            else:
                target_user = user
                title_text = "Balance"
                message_text = "### Bots don't have balances. 🤖"

            embed = discord.Embed(
                title= title_text,
                color= target_user.color,
                description=message_text,
            )
            embed.set_author(
                name=f"{target_user.name}",
                icon_url=target_user.avatar.url,
            )

            await interaction.response.send_message(embed=embed, ephemeral=False)
            logger.info(f"{interaction.user.name} used /balance command in {interaction.guild.name}")

        except Exception as e:
            logger.error(f"Error in /balance command for {interaction.user.name} in {interaction.guild.name}: {e}")
            await interaction.response.send_message("An error occurred while checking the balance.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Balance(bot))