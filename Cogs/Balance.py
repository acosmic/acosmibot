import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao


class Balance(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    @app_commands.command(name="balance", description="Check your Credit balance.")
    async def balance(self, interaction: discord.Interaction):
        dao = UserDao()
        user = dao.get_user(interaction.user.name)
        await interaction.response.send_message(f'Your balance: {user.currency} Credits. <:PepeRich:1200265584877772840> {interaction.user.mention}')

async def setup(bot: commands.Bot):
    await bot.add_cog(Balance(bot))
