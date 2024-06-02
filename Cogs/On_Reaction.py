from venv import logger
from discord.ext import commands
from Dao.UserDao import UserDao
from Dao.LotteryParticipantDao import LotteryParticipantDao
from Dao.LotteryEventDao import LotteryEventDao
from logger import AppLogger
import discord

from Dao.VaultDao import VaultDao
from Entities.LotteryParticipant import LotteryParticipant


logging = AppLogger(__name__).get_logger()

role_level_1 = "Microbe" # 🦠
role_level_2 = "Fish" # 🐟
role_level_3 = "Monkey" # 🐒
role_level_4 = "Human" # 🧍‍♂️
role_level_5 = "Unicorn" # 🦄

class On_Reaction(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not payload.member.bot:
            
            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            lottery_role = discord.utils.get(message.guild.roles, name="LotteryParticipant")
            user = await self.bot.fetch_user(payload.user_id)
            emoji = payload.emoji
            dao = UserDao()
            vdao = VaultDao()
            vault_credits = vdao.get_currency()

            discord_username = user.name
            current_user=dao.get_user(user.id)

            # Increment user total reactions 
            current_user.reactions_sent += 1

            # # EXP gain for reacting to a message
            # exp_gain = 1 + (current_user.streak * 0.05)

            try:
                dao.update_user(current_user)
                logging.info(f"{discord_username} added {emoji} to {message.author}'s message .")
                logging.info(f"incremented and updated db reactions_sent for {discord_username}")
            except Exception as e:
                logging.error(f'on_raw_reaction_add() - Error updating user to the database: {e}')
            
            # LOTTTERY EVENT
            le_dao = LotteryEventDao()
            current_lottery = le_dao.get_current_event()
            if current_lottery is not None:
                logging.info(f'current_lottery: {current_lottery.message_id}')
                logging.info(f'message.id: {message.id}')
                if message.id == current_lottery.message_id:
                    lpd = LotteryParticipantDao()
                    participants = lpd.get_participants(current_lottery.message_id)
                    participant_ids = [participant.participant_id for participant in participants]
                    logging.info(f'participants: {participants}')
                    if user.id not in participant_ids:
                        if str(emoji) == '🎟️':
                            try:
                                
                                lpd.add_new_participant(LotteryParticipant(current_lottery.message_id, user.id))
                                logging.info(f'{user.name} has entered the lottery!')
                                await payload.member.add_roles(lottery_role)
                                await channel.send(f'## {user.display_name} has entered the lottery for a chance to win {vault_credits:,.0f} Credits! \n \
                                                   ## <a:pepesith:1165101386921418792> Good Luck! Enter here -> {message.jump_url}')
                            except Exception as e:
                                logging.error(f'on_raw_reaction_add() - Error adding participant to the database: {e}')
                    else:
                        logging.info(f'{user.name} has already entered the lottery!')
            else:
                logging.info('There is no current lottery event')       

            role_names = [role_level_1, role_level_2, role_level_3, role_level_4, role_level_5]
            inmate_role = discord.utils.get(message.guild.roles, name="Inmate")
            roles = {name: discord.utils.get(message.guild.roles, name=name) for name in role_names}
            if None in roles.values():
                missing = [name for name, role in roles.items() if role is None]
                logging.error(f"Missing roles: {', '.join(missing)}")
                return

            # JAIL FEATURE - Check reactions for the 🚔 emoji
            required_votes = 5
            for emoji in message.reactions:
                if str(emoji) == '🚔':
                    if not payload.member.bot and not message.author.bot:
                        police_car_count = emoji.count
                        logging.info(f'police_car_count: {police_car_count} - message_id: {message.id}')

                    if str(payload.emoji) == '🚔':    
                        if police_car_count >= 1 and police_car_count < required_votes:
                            
                            vote_message = f"### <a:redALERT:1235639847029309450> {required_votes - police_car_count} more 🚔's to send {message.author.name} to Jail! <a:blueALERT:1235639375443001530> {message.jump_url}"
                            await channel.send(vote_message)
                                

                        if police_car_count == required_votes:
                            # Identify all removable roles that the user has
                            removable_roles = [role for role in message.author.roles if role in roles.values()]
                            
                            # Remove all identified roles at once
                            if removable_roles:
                                await message.author.remove_roles(*removable_roles)

                            for reaction in message.reactions:
                                if str(reaction) == '🚔':
                                    await reaction.clear()

                            # Add the 'Inmate' role
                            await message.author.add_roles(inmate_role)
                            await channel.send(f"🚨 {message.author.name} has been sent to Jail! Bail set at 100,000 Credits! 🚨")
                            logger.info(f"{message.author.name} has been sent to Jail!")
                        


                    

                        



async def setup(bot: commands.Bot):
    await bot.add_cog(On_Reaction(bot))