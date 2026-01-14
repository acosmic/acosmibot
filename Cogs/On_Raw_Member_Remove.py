from datetime import datetime, timedelta
import discord
from discord.ext import commands
from Dao.GuildUserDao import GuildUserDao
from Dao.GuildDao import GuildDao
from logger import AppLogger

logger = AppLogger(__name__).get_logger()

class On_Raw_Member_Remove(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            logger.warning(f"Could not get guild {payload.guild_id} on member remove event.")
            return

        try:
            user = payload.user
            if user.bot:
                return  # Skip bot accounts

            logger.info(f"{user.name} left the server {guild.name}.")
            mod_channel = self.bot.get_channel(1155580804269867170)  # janitorial 🚽

            guild_user_dao = GuildUserDao()
            guild_dao = GuildDao()

            # Retrieve the guild-specific user from the database
            guild_user = guild_user_dao.get_guild_user(user.id, guild.id)
            
            if guild_user and guild_user.is_active:
                currency_to_confiscate = guild_user.currency

                if currency_to_confiscate > 0:
                    # Add the confiscated currency to the GUILD'S vault
                    guild_dao.add_vault_currency(guild.id, currency_to_confiscate)

                    # Use global sync to remove the currency from the user
                    guild_user_dao.update_currency_with_global_sync(user.id, guild.id, -currency_to_confiscate)

                    # Send the message to the mod channel
                    if mod_channel:
                        await mod_channel.send(f"## {user.name} left the server. {currency_to_confiscate:,.0f} credits removed and added to the Vault.")

                # Deactivate the user for this guild
                guild_user_dao.deactivate_guild_user(user.id, guild.id)
                logger.info(f"Deactivated {user.name} in guild {guild.name}.")

            else:
                logger.warning(f"User {user.name} (ID: {user.id}) left guild {guild.name} but was not found or was already inactive in the database.")

        except Exception as e:
            logger.error(f'on_raw_member_remove Error in guild {payload.guild_id}: {e}')


async def setup(bot: commands.Bot):
    await bot.add_cog(On_Raw_Member_Remove(bot))