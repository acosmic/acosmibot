from discord.ext import commands
from Dao.UserDao import UserDao
from Dao.GuildUserDao import GuildUserDao
from Dao.LotteryParticipantDao import LotteryParticipantDao
from Dao.LotteryEventDao import LotteryEventDao
from Dao.GuildDao import GuildDao  # Use GuildDao instead of VaultDao for per-guild vaults
from Entities.LotteryParticipant import LotteryParticipant
from logger import AppLogger
import discord

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
            global_user = user_dao.get_or_create_user_from_discord(user)
            guild_user = guild_user_dao.get_or_create_guild_user_from_discord(payload.member, message.guild.id)

            if not global_user or not guild_user:
                logging.error(f"Failed to get/create user records for {user.name}")
                return

            # Update reaction counts
            guild_user.reactions_sent += 1
            guild_user_dao.update_guild_user(guild_user)

            global_user.total_reactions += 1
            user_dao.update_user(global_user)

            logging.info(f"{user.name} added {emoji} to {message.author}'s message.")
            logging.info(
                f"Updated reaction counts for {user.name} - Guild: {guild_user.reactions_sent}, Global: {global_user.total_reactions}")

            # LOTTERY EVENT HANDLING
            await self.handle_lottery_reaction(payload, message, user, emoji, channel)

        except Exception as e:
            logging.error(f'on_raw_reaction_add() - Error processing reaction: {e}')

    async def handle_lottery_reaction(self, payload, message, user, emoji, channel):
        """
        Handle lottery-related reactions.
        """
        try:
            # Only handle ticket emoji
            if str(emoji) != '🎟️':
                return

            le_dao = LotteryEventDao()
            guild_dao = GuildDao()

            # Get current lottery for this specific guild
            current_lottery = le_dao.get_current_event(message.guild.id)

            if current_lottery is None:
                logging.debug('There is no current lottery event in this guild')
                return

            logging.info(f'current_lottery: {current_lottery.message_id}')
            logging.info(f'message.id: {message.id}')

            # Check if this reaction is on the lottery message
            if message.id != current_lottery.message_id:
                return

            # Check if user is already a participant
            lpd = LotteryParticipantDao()
            participants = lpd.get_participants(current_lottery.id)  # ✅ Use event_id, not message_id
            participant_ids = [participant.participant_id for participant in participants]

            if user.id in participant_ids:
                logging.info(f'{user.name} has already entered the lottery!')
                return

            # Add user to lottery
            try:
                # Get guild vault credits
                vault_credits = guild_dao.get_vault_currency(message.guild.id)

                # Add participant to database
                new_participant = LotteryParticipant(current_lottery.id, user.id)  # ✅ Use event_id, not message_id
                lpd.add_new_participant(new_participant)
                logging.info(f'{user.name} has entered the lottery!')

                # Add lottery role if it exists
                lottery_role = discord.utils.get(message.guild.roles, name="LotteryParticipant")
                if lottery_role:
                    await payload.member.add_roles(lottery_role)

                # Send confirmation message
                await channel.send(
                    f'## {user.display_name} has entered the lottery for a chance to win {vault_credits:,.0f} Credits! \n'
                    f'## 🎰 Good Luck! Enter here -> {message.jump_url}'
                )

            except Exception as e:
                logging.error(f'Error adding lottery participant: {e}')

        except Exception as e:
            logging.error(f'Error handling lottery reaction: {e}')


async def setup(bot: commands.Bot):
    await bot.add_cog(On_Reaction(bot))