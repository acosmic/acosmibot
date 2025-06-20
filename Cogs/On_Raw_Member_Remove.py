from datetime import datetime, timedelta
import discord
from discord.ext import commands
from Dao.UserDao import UserDao
from Dao.VaultDao import VaultDao
from logger import AppLogger

logger = AppLogger(__name__).get_logger()

class On_Raw_Member_Remove(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent):
        guild = self.bot.get_guild(payload.guild_id)
        
        try:
            member = guild.get_member(payload.user.id)  # Try to get the member from the guild
            if member is None:
                member = await self.bot.fetch_user(payload.user.id)  # If not available, fetch the user directly
            
            if member.bot:
                return  # Skip bot accounts

            logger.info(f"{member.name} left the server.")
            mod_channel = self.bot.get_channel(1155580804269867170)  # janitorial 🚽
            dao = UserDao()
            vdao = VaultDao()

            # Retrieve the user from the database
            loser = dao.get_user(member.id)
            if loser:
                # Update vault and reset user currency
                current_vault = vdao.get_currency()
                add_to_vault = current_vault + loser.currency
                vdao.update_currency(add_to_vault)

                loser.currency = 0
                dao.update_user(loser)

                # Send the message to the mod channel
                await mod_channel.send(f"## {member.name} left the server. Credits removed and added to Vault.")
            else:
                logger.warning(f"User with ID {payload.user.id} not found in the database.")

        except Exception as e:
            logger.error(f'on_member_remove Error: {e}')


async def setup(bot: commands.Bot):
    await bot.add_cog(On_Raw_Member_Remove(bot))