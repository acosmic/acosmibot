from json import load
import discord
from datetime import datetime
from Dao.InviteDao import InviteDao
from Dao.UserDao import UserDao
from Entities.User import User
from Entities.Invite import Invite
from logger import AppLogger
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()
role_level_1 = os.getenv('ROLE_LEVEL_1')
role_level_2 = os.getenv('ROLE_LEVEL_2')
role_level_3 = os.getenv('ROLE_LEVEL_3')
role_level_4 = os.getenv('ROLE_LEVEL_4')
role_level_5 = os.getenv('ROLE_LEVEL_5')
role_level_6 = os.getenv('ROLE_LEVEL_6')
role_level_7 = os.getenv('ROLE_LEVEL_7')


logging = AppLogger(__name__).get_logger()

class On_Member_Join(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.processed_invites = set()
        self.invite_uses = {}

    @commands.Cog.listener()
    async def on_member_join(self, member):
        role = discord.utils.get(member.guild.roles, name=role_level_1)
        join_date = member.joined_at

        
        channel = discord.utils.get(member.guild.channels, id=1155577095787917384) # General channel
        dao = UserDao()

        # Convert join_date to a format suitable for database insertion (e.g., as a string)
        formatted_join_date = join_date.strftime("%Y-%m-%d %H:%M:%S")

        member_data = {
        'id': member.id,
        'discord_username': member.name,
        'nickname': "",
        'level': 0,
        'season_level': 0,
        'season_exp': 0,
        'streak': 0,
        'highest_streak': 0,
        'exp': 0,
        'exp_gained': 0,
        'exp_lost': 0,
        'currency': 0,
        'messages_sent': 0,
        'reactions_sent': 0,
        'created': formatted_join_date,
        'last_active': formatted_join_date,
        'daily': 0,
        'last_daily': None,
        }
        new_user = User(**member_data)
        existing_user = dao.get_user(new_user.id)

        if existing_user is None:
            await member.add_roles(role)
            logging.info(f'Auto assigned {role} role to {member}')

            # add new user to database
            try:
                dao.add_user(new_user)
                logging.info(f'{new_user.discord_username} added to the database. on_member_join()')
            except Exception as e:
                logging.error(f'on_member_join() - Error adding user to the database: {e}')
        else:
            # level = existing_user.level
            # if level < 5:
            #     role = discord.utils.get(member.guild.roles, name=role_level_1)
            # elif level >= 5 and level < 10:
            #     role = discord.utils.get(member.guild.roles, name=role_level_2)
            # elif level >= 10 and level < 20:
            #     role = discord.utils.get(member.guild.roles, name=role_level_3)
            # elif level >= 15:
            #     role = discord.utils.get(member.guild.roles, name=role_level_4)
            # elif level >= 20:
            #     role = discord.utils.get(member.guild.roles, name=role_level_5)
            # elif level >= 25:
            #     role = discord.utils.get(member.guild.roles, name=role_level_6)
            # elif level >= 30:
            #     role = discord.utils.get(member.guild.roles, name=role_level_7)

            # await member.add_roles(role)

            logging.info(f'{new_user.discord_username} already exists, so was not added again.')


    #     # PROCESS INVITES
    #     invDao = InviteDao()
        

    #     # Track invites before the member joins
    #     invites_before = await member.guild.invites()
    #     self.invite_uses = {invite.code: invite.uses for invite in invites_before}


    #     await asyncio.sleep(1)

    #      # Track invites after the member joins
    #     invites_after = await member.guild.invites()
    #     inviter, code, guildid, inviterid, inviteeid, uses = None, None, None, None, None, None
    #     for invite in invites_after:
    #         if invite.code in self.invite_uses and invite.uses > self.invite_uses[invite.code]:
    #             inviter = invite.inviter
    #             guildid = invite.guild.id
    #             inviterid = inviter.id
    #             inviteeid = member.id
    #             code = invite.code
    #             uses = invite.uses # Number of uses of the invite after the member joins
    #             break

    #     # Check if invite has already been processed
    #     if (guildid, inviterid, inviteeid) in self.processed_invites:
    #         logging.info(f'Invite from {inviter} to {member} has already been processed.')
    #         return
        
    #     # Mark invite as processed
    #     self.processed_invites.add((guildid, inviterid, inviteeid))

    #     logging.info(f'TESTING - Inviter: {inviter}\n'
    #                 f'Guild ID: {guildid}\n'
    #                 f'Inviter ID: {inviterid}\n'
    #                 f'Invitee ID: {inviteeid}\n'
    #                 f'Code: {code}\n'
    #                 f'Uses: {uses}\n')
        
    #     dbinvites = invDao.get_invites(guildid)
    #     if dbinvites:
    #         for dbinvite in dbinvites:
    #             if dbinvite.inviter_id == inviterid and dbinvite.invitee_id == inviteeid:
    #                 logging.info(f'Inviter has already invited this user before.')
    #                 break
    #         else:
    #             try:
    #                 newinvite = Invite(0, guildid, inviterid, inviteeid, code, datetime.now())
    #                 invDao.add_new_invite(newinvite)
    #                 inviterUser = dao.get_user(inviterid)
    #                 inviterUser.currency += 50000
    #                 inviterUser.exp += 500
    #                 inviterUser.exp_gained += 500
    #                 inviterUser.season_exp += 500
    #                 dao.update_user(inviterUser)
    #                 inviterDiscord = self.bot.get_user(inviterid)
    #                 logging.info(f'{inviterDiscord.name} has been rewarded 50,000 Credits for inviting {member.name} to the server.')
    #                 await channel.send(f'# {inviterDiscord.mention} has been rewarded 50,000 Credits and 500 EXP for inviting {member.name} to the server.')
    #                 logging.info(f'Rewards have been given to the inviter: 50,000 Credits and 500 EXP to {inviterDiscord.name}')

    #             except Exception as e:
    #                 logging.error(f'DBinvites exists, but Error adding invite to the database: {e}')

    #     else:
    #         try:
    #             newinvite = Invite(0, guildid, inviterid, inviteeid, code, datetime.now())
    #             invDao.add_new_invite(newinvite)
    #             inviterUser = dao.get_user(inviterid)
    #             inviterUser.currency += 50000
    #             inviterUser.exp += 500
    #             inviterUser.exp_gained += 500
    #             inviterUser.season_exp += 500
    #             dao.update_user(inviterUser)
    #             inviterDiscord = self.bot.get_user(inviterid)
    #             logging.info(f'{inviterDiscord.name} has been rewarded 50,000 Credits for inviting {member.name} to the server.')
    #             await channel.send(f'# {inviterDiscord.mention} has been rewarded 50,000 Credits and 500 EXP for inviting {member.name} to the server.')
    #         except Exception as e:
    #             logging.error(f'No DBinvites, Error adding invite to the database: {e}')

    #     # Clear processed_invites after invite processing
    #     await self.clear_processed_invites()

    # async def clear_processed_invites(self):
    #     await asyncio.sleep(5)
    #     self.processed_invites.clear()
    #     logging.info('Processed invites have been cleared.')


async def setup(bot: commands.Bot):
    await bot.add_cog(On_Member_Join(bot))