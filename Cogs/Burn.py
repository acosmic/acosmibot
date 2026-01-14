import typing
import discord
from discord.ext import commands
from discord import app_commands
from Dao.GuildUserDao import GuildUserDao
from logger import AppLogger


logger = AppLogger(__name__).get_logger()
class Burn(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name = "admin-burn", description = "set attribute to 0 for target")
    @discord.app_commands.default_permissions(manage_guild=True)
    async def burn(self, interaction: discord.Interaction, target: discord.Member, column: typing.Literal['currency', 'exp', 'daily', 'streak', "level"]):
        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return
        role = discord.utils.get(interaction.guild.roles, name="Acosmic")
        guild_user_dao = GuildUserDao()
        if role in interaction.user.roles:
            target_user = guild_user_dao.get_guild_user(target.id, interaction.guild.id)

            if not target_user:
                await interaction.response.send_message("Failed to get user data.", ephemeral=True)
                return

            if column == "currency":
                # Calculate how much we're burning to sync global stats
                currency_delta = -target_user.currency
                guild_user_dao.update_currency_with_global_sync(target.id, interaction.guild.id, currency_delta)

            if column == "exp":
                target_user.exp = 0

            if column == "daily":
                target_user.daily = 0

            if column == "streak":
                target_user.streak = 0

            if column == "level":
                target_user.level = 0

            try:
                # Only update if not currency (currency already updated via update_currency_with_global_sync)
                if column != "currency":
                    guild_user_dao.update_guild_user(target_user)
                await interaction.response.send_message(f"{interaction.user.name} has burned {target.mention}'s {column} to 0! <a:pepesith:1165101386921418792>")
            except Exception as e:
                logger.error(f'/admin-burn command - target = {target.name} - {e}.')
        else:
            await interaction.response.send_message(f'only {role} can run this command. <:FeelsNaughty:1199732493792858214>', ephemeral=True)
   
                
async def setup(bot: commands.Bot):
    await bot.add_cog(Burn(bot))