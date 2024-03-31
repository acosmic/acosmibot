import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
import random
import logging



class Polymorph(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name = "polymorph", description = "Change your target's display name for 1000 Credits... please be nice") 
    async def polymorph_command(self, interaction: discord.Interaction, target: discord.Member, rename: str):
        
        dao = UserDao()
        cost = 5000
        user = dao.get_user(interaction.user.id)
        targetUser = target.name


        if user.currency >= cost:
            try:
                await target.edit(nick=rename)
                await interaction.response.send_message(f"# 🐑 {interaction.user.name} polymorphed {targetUser} into {target.mention} for {cost:,.0f} Credits. 🐑")
                user.currency -= cost
                dao.update_user(user)
                logging.info(f'{user.discord_username} used /polymorph on {target.name}')
            except Exception as e:
                logging.error(f'{user.discord_username} tried to use /polymorph on {target.name} - {e}')
        else:
            await interaction.response.send_message(f"You're much too broke to polymorph anyone. <:PepePathetic:1200268253021360128>")

async def setup(bot: commands.Bot):
    await bot.add_cog(Polymorph(bot))