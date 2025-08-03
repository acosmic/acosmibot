from Dao.UserDao import UserDao
from Dao.GuildUserDao import GuildUserDao
from logger import AppLogger
from discord.ext import commands
from dotenv import load_dotenv


load_dotenv()

logging = AppLogger(__name__).get_logger()


class On_Member_Join(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.processed_invites = set()
        self.invite_uses = {}

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """
        Handle member join events by:
        1. Creating/updating User record (global)
        2. Creating/updating GuildUser record (guild-specific)
        """
        if member.bot:
            return  # Skip bots

        try:
            # Initialize DAOs
            user_dao = UserDao()
            guild_user_dao = GuildUserDao()

            global_user = user_dao.get_or_create_user_from_discord(member)
            guild_user = guild_user_dao.get_or_create_guild_user_from_discord(member, member.guild.id)

            if not global_user:
                logging.error(f'Failed to create/get global user for {member.name}')
                return

            if not guild_user:
                logging.error(f'Failed to create/get guild user for {member.name} in {member.guild.name}')
                return

            logging.info(f'Successfully processed member join for {member.name} in {member.guild.name}')

        except Exception as e:
            logging.error(f'Error in on_member_join for {member.name}: {e}')


async def setup(bot: commands.Bot):
    await bot.add_cog(On_Member_Join(bot))