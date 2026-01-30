import discord
from discord.ext import commands
from discord import app_commands
from Dao.GuildDao import GuildDao
from logger import AppLogger
from datetime import datetime

logger = AppLogger(__name__).get_logger()


class CheckBank(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="guildbank", description="Check the amount of Credits in this server's bank!")
    async def checkbank(self, interaction: discord.Interaction):
        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=False)

        try:
            dao = GuildDao()
            currency = dao.get_vault_currency(interaction.guild.id)

            # Create embed
            embed = discord.Embed(
                title=f"🏦 {interaction.guild.name} Bank Vault",
                color=discord.Color.gold(),
                timestamp=datetime.utcnow()
            )

            # Set guild icon if available
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)

            # Bank balance
            embed.add_field(
                name="💰 Total Credits in Vault",
                value=f"**{currency:,}** credits",
                inline=False
            )

            embed.add_field(
                name="ℹ️ About the Vault",
                value="The guild vault collects a percentage of losses from games, and bank transaction fees from deposits and withdrawals.",
                inline=False
            )

            embed.set_footer(text=f"Requested by {interaction.user.display_name}")

            await interaction.followup.send(embed=embed, ephemeral=False)
            logger.info(f"{interaction.user.name} used /guildbank command in {interaction.guild.name}")

        except Exception as e:
            logger.error(f"Error in guildbank command: {e}")
            await interaction.followup.send("❌ An error occurred while fetching guild bank information.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(CheckBank(bot))