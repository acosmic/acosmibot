from operator import le
from discord.ext import commands
from Dao.UserDao import UserDao
from Dao.LotteryParticipantDao import LotteryParticipantDao
from Dao.LotteryEventDao import LotteryEventDao
import logging

from Entities.LotteryParticipant import LotteryParticipant


logging.basicConfig(filename='/root/dev/acosmicord-bot/logs.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class On_Reaction(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not payload.member.bot:
            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            user = await self.bot.fetch_user(payload.user_id)
            emoji = payload.emoji
            dao = UserDao()

            discord_username = user.name
            current_user=dao.get_user(user.id)

            # Increment user total reactions 
            current_user.reactions_sent += 1

            try:
                dao.update_user(current_user)
                logging.info(f"{discord_username} added {emoji} to {message.author}'s message .")
                logging.info(f"incremented and updated db reactions_sent for {discord_username}")
            except Exception as e:
                logging.error(f'on_raw_reaction_add() - Error updating user to the database: {e}')
            

            le_dao = LotteryEventDao()
            current_lottery = le_dao.get_current_event()
            if current_lottery is not None:
                logging.info(f'current_lottery: {current_lottery.message_id}')
                logging.info(f'message.id: {message.id}')
                if message.id == current_lottery.message_id:
                    lpd = LotteryParticipantDao()
                    participants = lpd.get_all_participants(current_lottery.message_id)
                    if user.id not in participants:
                        if str(emoji) == '🎟️':
                            try:
                                
                                lpd.add_new_participant(LotteryParticipant(current_lottery.message_id, user.id))
                                logging.info(f'{user.name} has entered the lottery!')
                                await channel.send(f'{user.display_name} has entered the lottery! Good Luck! <a:pepesith:1165101386921418792> Enter here -> {message.jump_url}')
                            except Exception as e:
                                logging.error(f'on_raw_reaction_add() - Error adding participant to the database: {e}')
                    else:
                        logging.info(f'{user.name} has already entered the lottery!')
            else:
                logging.info('There is no current lottery event')            


async def setup(bot: commands.Bot):
    await bot.add_cog(On_Reaction(bot))