import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from logger import AppLogger


logger = AppLogger(__name__).get_logger()

class Admin_Stats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name = "admin-stats", description = "Get server stats.")
    @discord.app_commands.default_permissions(manage_guild=True)
    async def admin_stats(self, interaction: discord.Interaction):
        uDao = UserDao()
        try:
            total_users = uDao.get_total_active_users()
            total_messages = uDao.get_total_messages()
            total_reactions = uDao.get_total_reactions()
            total_currency = uDao.get_total_currency()
            total_exp = uDao.get_total_exp()

            await interaction.response.send_message(f'# Acosmicord Stats:\
                                                    \n## Active Users: {total_users:,.0f}\
                                                    \n## Messages: {total_messages:,.0f}\
                                                    \n## Reactions: {total_reactions:,.0f}\
                                                    \n## Currency: {total_currency:,.0f}\
                                                    \n## XP: {total_exp:,.0f}')
        except Exception as e:
            logger.info(f'/stats command - {e}.')
            await interaction.response.send_message(f'An error occurred while fetching stats. {e}.', ephemeral=True)
        uDao.close()

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin_Stats(bot))
