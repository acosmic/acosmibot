from calendar import c
import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from Dao.CoinflipDao import CoinflipDao
from Entities.User import User
from logger import AppLogger


# role_level_1 = "Level One"
# role_level_2 = "Level Two"
# role_level_3 = "Level Three"
# role_level_4 = "Level Four"
# role_level_5 = "Level Five"
# role_level_6 = "Level Six"
# role_level_7 = "Level Seven"
# role_level_8 = "Level Eight"
# role_level_9 = "Level Nine"
# role_level_10 = "Level Ten"

logging = AppLogger(__name__).get_logger()


class Rank(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name = "rank", description = "Leave blank to see your own rank, or mention another user to see their rank.") 
    async def rank(self, interaction: discord.Interaction, user: discord.User = None):
        
        dao = UserDao()
        cfdao = CoinflipDao()
        if user is not None:
            user_rank = dao.get_user_rank(user.id)
            current_user = dao.get_user(user.id)
            discord_user = user
        else: 
            user_rank = dao.get_user_rank(interaction.user.id)
            current_user = dao.get_user(interaction.user.id)
            discord_user = interaction.user


        flips = cfdao.get_total_flips(current_user.id) if cfdao.get_total_flips(current_user.id) is not None else 0
        flip_wins = cfdao.get_flip_wins(current_user.id) if cfdao.get_flip_wins(current_user.id) is not None else 0
        flip_losses = cfdao.get_flip_losses(current_user.id) if cfdao.get_flip_losses(current_user.id) is not None else 0

        flip_amount_won = cfdao.get_total_won(current_user.id) if cfdao.get_total_won(current_user.id) is not None else 0
        flip_amount_lost = cfdao.get_total_lost(current_user.id) if cfdao.get_total_lost(current_user.id) is not None else 0

        flip_win_rate = flip_wins / flips * 100 if flips > 0 else 0

        streak = current_user.streak   
        streak_emoji = f"🔥 x{streak}"  if streak > 0 else "make sure to chat again tomorrow to increase your streak! <:NicolasCagePOG:1203568248885346334>"

        if user_rank is not None:
            name_from_db = user_rank[1]
            display_name = discord_user.name if discord_user.name is not None else name_from_db
            level_emoji = "🥚"
            if current_user.level >= 5:
                level_emoji = "🐣"
            if current_user.level >= 10:
                level_emoji = "🐔"
            if current_user.level >= 20:
                level_emoji = "🐓"
            
            embed = discord.Embed(
            # title=f"### {discord_user.name}",
            description=(
            f"# {display_name} {level_emoji}\n\n"
            f"### Ranked #{user_rank[-1]}\n"
            f"Current Level: {current_user.level}\n"
            f"Current EXP: {current_user.exp:,.0f}\n"
            f"Messages: {current_user.messages_sent:,.0f}\n"
            f"Reactions: {current_user.reactions_sent:,.0f}\n"
            f"Coinflips: {flips}\n"
            f"Coinflip Wins: {flip_wins}\n"
            f"Coinflip Losses: {flip_losses}\n"
            f"Coinflip Credits Won: {flip_amount_won:,.0f}\n"
            f"Coinflip Credits Lost: {flip_amount_lost:,.0f}\n"
            f"Coinflip Win Rate: {flip_win_rate:.2f}%\n\n"
            f"### Streak: {streak_emoji}\n"
            ),
            color=discord_user.color)
            embed.set_thumbnail(url=discord_user.avatar)

            await interaction.response.send_message(embed=embed)

        else:
        #     logging.info(f"The user with Discord username {interaction.user.name} was not found in the database.")
            
        #     role = discord.utils.get(interaction.user.guild.roles, name=role_level_1)
        #     await interaction.user.add_roles(role)
        #     join_date = interaction.user.joined_at

        #     # Convert join_date to a format suitable for database insertion (e.g., as a string)
        #     formatted_join_date = join_date.strftime("%Y-%m-%d %H:%M:%S")

        #     user_data = {
        #     'id': interaction.user.id,
        #     'discord_username': str(interaction.user.name),
        #     'level': 1,
        #     'streak': 0,
        #     'exp': 0,
        #     'exp_gained': 0,
        #     'exp_lost': 0,
        #     'currency': 0,
        #     'messages_sent': 1,
        #     'reactions_sent': 0,
        #     'created': formatted_join_date,
        #     'last_active': formatted_join_date,
        #     'daily': 0,
        #     'last_daily': None,
        #     }

        #     new_user = User(**user_data)
        #     dao.add_user(new_user)
        #     logging.info(f'{new_user.discord_username} added to the database.')
        #     await interaction.response.send_message(f'{interaction.user.name} was not found in the database. {new_user.discord_username} added to the database.')
        # # await interaction.response.send_message("Hello!") 
        # logging.info(f"{interaction.user.name} used /rank command")
            return

async def setup(bot: commands.Bot):
    await bot.add_cog(Rank(bot))