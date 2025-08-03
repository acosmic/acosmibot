from json import load
import discord
from datetime import datetime
from Dao.InviteDao import InviteDao
from Dao.UserDao import UserDao
from Dao.GuildUserDao import GuildUserDao
from Dao.GuildDao import GuildDao
from Entities.User import User
from Entities.GuildUser import GuildUser
from Entities.Invite import Invite
from logger import AppLogger
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()
# role_level_1 = os.getenv('ROLE_LEVEL_1')
# role_level_2 = os.getenv('ROLE_LEVEL_2')
# role_level_3 = os.getenv('ROLE_LEVEL_3')
# role_level_4 = os.getenv('ROLE_LEVEL_4')
# role_level_5 = os.getenv('ROLE_LEVEL_5')
# role_level_6 = os.getenv('ROLE_LEVEL_6')
# role_level_7 = os.getenv('ROLE_LEVEL_7')

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

            join_date = member.joined_at or datetime.now()
            formatted_join_date = join_date.strftime("%Y-%m-%d %H:%M:%S")

            # Get or create global User record
            existing_user = user_dao.get_user(member.id)

            if existing_user is None:
                # Create new global user
                new_user = User(
                    id=member.id,
                    discord_username=member.name,
                    global_name=member.global_name if hasattr(member, 'global_name') else None,
                    avatar_url=str(member.avatar.url) if member.avatar else None,
                    is_bot=member.bot,
                    global_exp=0,
                    global_level=0,
                    total_currency=0,
                    total_messages=0,
                    total_reactions=0,
                    account_created=member.created_at.strftime("%Y-%m-%d %H:%M:%S") if member.created_at else None,
                    first_seen=formatted_join_date,
                    last_seen=formatted_join_date,
                    privacy_settings=None,
                    global_settings=None
                )

                try:
                    user_dao.add_user(new_user)
                    logging.info(f'{new_user.discord_username} added to global Users database.')
                    current_user = new_user
                except Exception as e:
                    logging.error(f'Error adding user to global database: {e}')
                    return
            else:
                # Update existing user info
                existing_user._discord_username = member.name
                existing_user._global_name = member.global_name if hasattr(member,
                                                                           'global_name') else existing_user.global_name
                existing_user._avatar_url = str(member.avatar.url) if member.avatar else existing_user.avatar_url
                existing_user._last_seen = formatted_join_date
                user_dao.update_user(existing_user)
                current_user = existing_user
                logging.info(f'{member.name} updated in global Users database.')

            # Get or create GuildUser record
            existing_guild_user = guild_user_dao.get_guild_user(member.id, member.guild.id)

            if existing_guild_user is None:
                # Create new guild user
                new_guild_user = GuildUser(
                    user_id=member.id,
                    guild_id=member.guild.id,
                    name=member.name,
                    nickname=member.display_name,
                    level=0,
                    streak=0,
                    highest_streak=0,
                    exp=0,
                    exp_gained=0,
                    exp_lost=0,
                    currency=1000,  # Starting currency for new guild users
                    messages_sent=0,
                    reactions_sent=0,
                    joined_at=formatted_join_date,
                    last_active=formatted_join_date,
                    daily=0,
                    last_daily=None,
                    is_active=True
                )

                try:
                    guild_user_dao.add_guild_user(new_guild_user)
                    logging.info(f'{member.name} added to GuildUsers database for guild {member.guild.name}.')
                except Exception as e:
                    logging.error(f'Error adding guild user to database: {e}')
                    return
            else:
                # Reactivate and update existing guild user
                existing_guild_user.name = member.name
                existing_guild_user.nickname = member.display_name
                existing_guild_user.is_active = True
                existing_guild_user.last_active = formatted_join_date
                guild_user_dao.update_guild_user(existing_guild_user)
                logging.info(f'{member.name} reactivated in guild {member.guild.name}.')

            # Role assignment removed for now
            # await self.assign_user_roles(current_user, member)

            # Process invite tracking (if enabled)
            # await self.process_invite_tracking(member)

        except Exception as e:
            logging.error(f'Error in on_member_join for {member.name}: {e}')

    # Role assignment functionality removed for now
    # async def assign_user_roles(self, user: User, member: discord.Member):
    #     """
    #     Assign roles to the member based on their global level.
    #     """
    #     try:
    #         # Use the global_level property from the new User structure
    #         global_level = user.global_level
    #
    #         # Define role thresholds (highest to lowest)
    #         role_thresholds = [
    #             (30, role_level_7),
    #             (25, role_level_6),
    #             (20, role_level_5),
    #             (15, role_level_4),
    #             (10, role_level_3),
    #             (5, role_level_2),
    #             (0, role_level_1)
    #         ]
    #
    #         # Find the appropriate role
    #         target_role = None
    #         for threshold, role_name in role_thresholds:
    #             if global_level >= threshold and role_name:
    #                 target_role = discord.utils.get(member.guild.roles, name=role_name)
    #                 if target_role:
    #                     break
    #
    #         # Assign the role if found and not already assigned
    #         if target_role and target_role not in member.roles:
    #             await member.add_roles(target_role)
    #             logging.info(f'Assigned {target_role.name} role to {member.name} (global level: {global_level})')
    #         elif not target_role:
    #             # Fallback to level 1 role if no role found
    #             fallback_role = discord.utils.get(member.guild.roles, name=role_level_1)
    #             if fallback_role and fallback_role not in member.roles:
    #                 await member.add_roles(fallback_role)
    #                 logging.info(f'Assigned fallback {fallback_role.name} role to {member.name}')

    #     except Exception as e:
    #         logging.error(f'Error assigning roles to {member.name}: {e}')

    # async def process_invite_tracking(self, member):
    #     """
    #     Process invite tracking and rewards.
    #     Currently disabled but framework ready for re-enablement.
    #     """
    #     try:
    #         channel = discord.utils.get(member.guild.channels, id=1155577095787917384)  # General channel
    #         inv_dao = InviteDao()
    #         user_dao = UserDao()
    #
    #         # Track invites before and after
    #         invites_before = await member.guild.invites()
    #         self.invite_uses = {invite.code: invite.uses for invite in invites_before}
    #
    #         await asyncio.sleep(1)  # Small delay to ensure invite count updates
    #
    #         invites_after = await member.guild.invites()
    #         inviter, code, guild_id, inviter_id, invitee_id, uses = None, None, None, None, None, None
    #
    #         for invite in invites_after:
    #             if invite.code in self.invite_uses and invite.uses > self.invite_uses[invite.code]:
    #                 inviter = invite.inviter
    #                 guild_id = invite.guild.id
    #                 inviter_id = inviter.id
    #                 invitee_id = member.id
    #                 code = invite.code
    #                 uses = invite.uses
    #                 break
    #
    #         if not inviter:
    #             logging.info(f'Could not determine inviter for {member.name}')
    #             return
    #
    #         # Check if invite has already been processed
    #         if (guild_id, inviter_id, invitee_id) in self.processed_invites:
    #             logging.info(f'Invite from {inviter} to {member} has already been processed.')
    #             return
    #
    #         # Mark invite as processed
    #         self.processed_invites.add((guild_id, inviter_id, invitee_id))
    #
    #         # Check if this invite combination already exists in database
    #         db_invites = inv_dao.get_invites(guild_id)
    #         invite_exists = False
    #
    #         if db_invites:
    #             for db_invite in db_invites:
    #                 if db_invite.inviter_id == inviter_id and db_invite.invitee_id == invitee_id:
    #                     invite_exists = True
    #                     logging.info(f'Inviter {inviter.name} has already invited {member.name} before.')
    #                     break
    #
    #         if not invite_exists:
    #             try:
    #                 # Create new invite record
    #                 new_invite = Invite(0, guild_id, inviter_id, invitee_id, code, datetime.now())
    #                 inv_dao.add_new_invite(new_invite)
    #
    #                 # Reward the inviter using the new User structure
    #                 inviter_user = user_dao.get_user(inviter_id)
    #                 if inviter_user:
    #                     # Update global stats using the new structure
    #                     inviter_user._total_currency += 50000
    #                     inviter_user._global_exp += 500
    #
    #                     # Update last seen
    #                     inviter_user._last_seen = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #
    #                     user_dao.update_user(inviter_user)
    #
    #                     inviter_discord = self.bot.get_user(inviter_id)
    #                     if inviter_discord and channel:
    #                         await channel.send(
    #                             f'# {inviter_discord.mention} has been rewarded 50,000 Credits and 500 Global EXP for inviting {member.name} to the server!'
    #                         )
    #
    #                     logging.info(
    #                         f'{inviter.name} rewarded for inviting {member.name}: 50,000 Credits and 500 Global EXP')
    #
    #             except Exception as e:
    #                 logging.error(f'Error processing invite reward: {e}')
    #
    #         # Clear processed invites after delay
    #         await self.clear_processed_invites()
    #
    #     except Exception as e:
    #         logging.error(f'Error in invite tracking for {member.name}: {e}')
    #
    # async def clear_processed_invites(self):
    #     """Clear processed invites after a delay to prevent duplicates."""
    #     await asyncio.sleep(5)
    #     self.processed_invites.clear()
    #     logging.info('Processed invites have been cleared.')


async def setup(bot: commands.Bot):
    await bot.add_cog(On_Member_Join(bot))