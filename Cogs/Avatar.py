import discord
from discord.ext import commands
from discord import app_commands
from logger import AppLogger

logger = AppLogger(__name__).get_logger()

class Avatar(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    @app_commands.command(name="avatar", description="Get your target's Avatar")
    async def avatar(self, interaction: discord.Interaction, user: discord.User = None):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        try:
            target_user = user or interaction.user

            embed = discord.Embed(
                title=f"",
                color=target_user.color,
            )
            # Set the author (this adds the small avatar + name at the top)
            embed.set_author(
                name=f"{target_user.display_name}'s Avatar",
                icon_url=target_user.avatar.url if target_user.avatar else target_user.default_avatar.url
            )

            # Set the main large image
            embed.set_image(
                url=target_user.avatar if target_user.avatar else target_user.default_avatar.url
            )

            embed.set_footer(text="/avatar [@target]")

            await interaction.response.send_message(embed=embed)
            logger.info(f"{interaction.user.name} used /avatar command in {interaction.guild.name}")

        except Exception as e:
            logger.error(f"Error in /avatar command for {interaction.user.name} in {interaction.guild.name}: {e}")
            await interaction.response.send_message("An error occurred while fetching the avatar.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Avatar(bot))
