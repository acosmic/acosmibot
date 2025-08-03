from discord.ext import commands
from Dao.UserDao import UserDao
from Dao.GuildUserDao import GuildUserDao
# from Dao.LotteryParticipantDao import LotteryParticipantDao
# from Dao.LotteryEventDao import LotteryEventDao
# from Dao.VaultDao import VaultDao
# from Entities.User import User
# from Entities.GuildUser import GuildUser
# from Entities.LotteryParticipant import LotteryParticipant
from logger import AppLogger
# import discord
# from datetime import datetime

logging = AppLogger(__name__).get_logger()



class On_Reaction(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """
        Handle reaction additions with new dual user system.
        """
        if payload.member and payload.member.bot:
            return  # Skip bot reactions

        try:
            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            user = await self.bot.fetch_user(payload.user_id)
            emoji = payload.emoji

            # Initialize DAOs
            user_dao = UserDao()
            guild_user_dao = GuildUserDao()

            # Get or create users
            # Get or create users (much cleaner!)
            global_user = user_dao.get_or_create_user_from_discord(user)
            guild_user = guild_user_dao.get_or_create_guild_user_from_discord(payload.member, message.guild.id)

            if not global_user or not guild_user:
                logging.error(f"Failed to get/create user records for {user.name}")
                return

            # Update reaction counts
            # Guild-specific reaction count
            guild_user.reactions_sent += 1
            guild_user_dao.update_guild_user(guild_user)

            # Global reaction count
            global_user._total_reactions += 1
            user_dao.update_user(global_user)

            logging.info(f"{user.name} added {emoji} to {message.author}'s message.")
            logging.info(
                f"Updated reaction counts for {user.name} - Guild: {guild_user.reactions_sent}, Global: {global_user.total_reactions}")

            # # LOTTERY EVENT HANDLING
            # await self.handle_lottery_reaction(payload, message, user, emoji, channel, vdao)
            #
            # # JAIL FEATURE HANDLING
            # await self.handle_jail_reaction(payload, message, channel)

        except Exception as e:
            logging.error(f'on_raw_reaction_add() - Error processing reaction: {e}')


    # async def handle_lottery_reaction(self, payload, message, user, emoji, channel, vdao):
    #     """
    #     Handle lottery-related reactions.
    #     """
    #     try:
    #         le_dao = LotteryEventDao()
    #         current_lottery = le_dao.get_current_event()
    #
    #         if current_lottery is None:
    #             logging.info('There is no current lottery event')
    #             return
    #
    #         logging.info(f'current_lottery: {current_lottery.message_id}')
    #         logging.info(f'message.id: {message.id}')
    #
    #         if message.id != current_lottery.message_id:
    #             return
    #
    #         lpd = LotteryParticipantDao()
    #         participants = lpd.get_participants(current_lottery.message_id)
    #         participant_ids = [participant.participant_id for participant in participants]
    #
    #         if user.id in participant_ids:
    #             logging.info(f'{user.name} has already entered the lottery!')
    #             return
    #
    #         if str(emoji) == '🎟️':
    #             try:
    #                 lottery_role = discord.utils.get(message.guild.roles, name="LotteryParticipant")
    #                 vault_credits = vdao.get_currency()
    #
    #                 lpd.add_new_participant(LotteryParticipant(current_lottery.message_id, user.id))
    #                 logging.info(f'{user.name} has entered the lottery!')
    #
    #                 if lottery_role:
    #                     await payload.member.add_roles(lottery_role)
    #
    #                 await channel.send(
    #                     f'## {user.display_name} has entered the lottery for a chance to win {vault_credits:,.0f} Credits! \n'
    #                     f'## <a:pepesith:1165101386921418792> Good Luck! Enter here -> {message.jump_url}')
    #
    #             except Exception as e:
    #                 logging.error(f'Error adding lottery participant: {e}')
    #
    #     except Exception as e:
    #         logging.error(f'Error handling lottery reaction: {e}')

    # async def handle_jail_reaction(self, payload, message, channel):
    #     """
    #     Handle jail-related reactions (🚔 emoji).
    #     """
    #     try:
    #         inmate_role = discord.utils.get(message.guild.roles, name="Inmate")
    #         if not inmate_role:
    #             logging.warning("Inmate role not found in guild")
    #             return
    #
    #         required_votes = 5
    #
    #         # Check for police car reactions
    #         for reaction in message.reactions:
    #             if str(reaction) == '🚔':
    #                 if payload.member.bot or message.author.bot:
    #                     return
    #
    #                 police_car_count = reaction.count
    #                 logging.info(f'police_car_count: {police_car_count} - message_id: {message.id}')
    #
    #                 if str(payload.emoji) == '🚔':
    #                     if police_car_count >= 1 and police_car_count < required_votes:
    #                         vote_message = (
    #                             f"### <a:redALERT:1235639847029309450> {required_votes - police_car_count} more 🚔's to send "
    #                             f"{message.author.name} to Jail! <a:blueALERT:1235639375443001530> {message.jump_url}")
    #                         await channel.send(vote_message)
    #
    #                     elif police_car_count == required_votes:
    #                         # Check if user is already in jail
    #                         if inmate_role in message.author.roles:
    #                             logging.info(f"{message.author.name} is already in Jail!")
    #                             return
    #
    #                         # Clear the police reactions
    #                         for msg_reaction in message.reactions:
    #                             if str(msg_reaction) == '🚔':
    #                                 await msg_reaction.clear()
    #
    #                         # Add the 'Inmate' role
    #                         await message.author.add_roles(inmate_role)
    #                         await channel.send(
    #                             f"🚨 {message.author.name} has been sent to Jail! Bail set at 100,000 Credits! 🚨")
    #                         logging.info(f"{message.author.name} has been sent to Jail!")

        except Exception as e:
            logging.error(f'Error handling jail reaction: {e}')


async def setup(bot: commands.Bot):
    await bot.add_cog(On_Reaction(bot))