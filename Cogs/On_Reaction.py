from discord.ext import commands
from Dao.UserDao import UserDao
import logging


logging.basicConfig(filename='/root/dev/acosmicord-bot/logs.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class On_Reaction(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        user = await self.bot.fetch_user(payload.user_id)
        emoji = payload.emoji
        dao = UserDao()

        discord_username = user.name
        current_user=dao.get_user(discord_username)

        # Increment user total reactions 
        current_user.reactions_sent += 1

        try:
            dao.update_user(current_user)
            logging.info(f"{discord_username} added {emoji} to {message.author}'s message .")
            logging.info(f"incremented and updated db reactions_sent for {discord_username}")
        except Exception as e:
            logging.error(f'on_raw_reaction_add() - Error updating user to the database: {e}')

async def setup(bot: commands.Bot):
    await bot.add_cog(On_Reaction(bot))