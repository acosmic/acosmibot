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

                # Get guild user data
                guild_user = guild_user_dao.get_guild_user(target_user.id, interaction.guild.id)

                if guild_user is None:
                    if target_user == interaction.user:
                        message_text = "## You don't have an account in this server yet. Send a message to get started! 💰"
                    else:
                        message_text = f"## {target_user.name} doesn't have an account in this server yet. 💰"
                else:
                    if target_user == interaction.user:
                        message_text = f"## Your balance: {guild_user.currency:,.0f} Credits. 💰 {interaction.user.mention}"
                    else:
                        message_text = f"## {target_user.name}'s balance: {guild_user.currency:,.0f} Credits. 💰 {interaction.user.mention}"
            else:
                message_text = "## Bots don't have balances. 🤖"

            await interaction.response.send_message(message_text)
            logger.info(f"{interaction.user.name} used /balance command in {interaction.guild.name}")

        except Exception as e:
            logger.error(f"Error in /balance command for {interaction.user.name} in {interaction.guild.name}: {e}")
            await interaction.response.send_message("An error occurred while checking the balance.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Balance(bot))