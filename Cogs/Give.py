import discord
from discord.ext import commands
from discord import app_commands
from Dao.GuildUserDao import GuildUserDao
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class Give(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="give", description="Give Credits to your target user.")
    async def give(self, interaction: discord.Interaction, target: discord.Member, amount: int):

        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        # Validate amount
        if amount <= 0:
            await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
            return

        # Check if user is trying to give to themselves
        if interaction.user.id == target.id:
            await interaction.response.send_message(
                f"{interaction.user.name}, you can't give yourself Credits. <:FeelsNaughty:1199732493792858214>",
                ephemeral=True
            )
            logger.info(f"{interaction.user.name} tried to give themselves Credits.")
            return

        # Check if target is a bot
        if target.bot:
            await interaction.response.send_message("You can't give credits to bots!", ephemeral=True)
            return

        try:
            guild_user_dao = GuildUserDao()

            try:
                # Get or create guild users (currency is guild-specific)
                giving_user = guild_user_dao.get_or_create_guild_user_from_discord(interaction.user, interaction.guild.id)
                target_user = guild_user_dao.get_or_create_guild_user_from_discord(target, interaction.guild.id)

                if not giving_user or not target_user:
                    await interaction.response.send_message("Failed to get user data.", ephemeral=True)
                    return

                # Check if giver has enough credits
                if amount > giving_user.currency:
                    await interaction.response.send_message(
                        f"{interaction.user.name}, your heart is bigger than your wallet. "
                        f"You don't have {amount:,.0f} Credits to give. "
                        f"(You have {giving_user.currency:,.0f}) "
                        f"<:FeelsBigSad:1199734765230768139>"
                    )
                    logger.info(
                        f"{interaction.user.name} tried to give {amount:,.0f} Credits to {target.name} but didn't have enough Credits.")
                    return

                # Perform the transfer with global sync
                guild_user_dao.update_currency_with_global_sync(interaction.user.id, interaction.guild.id, -amount)
                guild_user_dao.update_currency_with_global_sync(target.id, interaction.guild.id, amount)

                # Update local objects for display
                giving_user.currency -= amount
                target_user.currency += amount

                await interaction.response.send_message(
                    f'### {interaction.user.name} has given {target.mention} {amount:,.0f} credits! <:PepePimp:1200268145693302854>\n'
                    f'*{interaction.user.name} now has {giving_user.currency:,.0f} credits.*'
                )

                logger.info(
                    f"{interaction.user.name} gave {target.name} {amount:,.0f} Credits in {interaction.guild.name}.")
            finally:
                guild_user_dao.close()

        except Exception as e:
            logger.error(f'/give command error - giver: {interaction.user.name}, target: {target.name} - {e}')
            await interaction.response.send_message("An error occurred while processing the transfer.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Give(bot))