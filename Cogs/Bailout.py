from email import message
from lib2to3.fixes import fix_standarderror
import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from logger import AppLogger

class Bailout(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    @app_commands.command(name="bailout", description="Pay bail to get out of jail or pay someone else's bail.")
    async def bail(self, interaction: discord.Interaction, target: discord.User = None):
        general_channel = self.bot.get_channel(1155577095787917384)
        jail_channel = self.bot.get_channel(1233867818055893062)
        first_role = discord.utils.get(interaction.guild.roles, name="Soy Milk")
        inmate_role = discord.utils.get(interaction.guild.roles, name="Inmate")
        
        bail = 100000

        dao = UserDao()
        current_user = dao.get_user(interaction.user.id)

        

        if current_user.currency < bail:
            await interaction.response.send_message("You do not have enough credits for /bail.", ephemeral=True)
            return
        
        if current_user.currency >= bail:
            if target is None:
                for role in interaction.user.roles:
                    if role.name == "Inmate":
                        await interaction.user.remove_roles(role)
                        await interaction.user.add_roles(first_role)
                        current_user.currency -= bail
                        dao.update_user(current_user)
                        await interaction.response.send_message(f"{interaction.user.name} paid {bail:,.0f} credits to get out of jail.")
                        await general_channel.send(f"## {interaction.user.name} paid {bail:,.0f} credits to get out of jail.")
                        return
                    else:
                        await interaction.response.send_message("You are not in jail.", ephemeral=True)
                        return
            
            else:
                
                if inmate_role in target.roles:
                    await target.remove_roles(inmate_role)
                    if first_role not in target.roles:
                        await target.add_roles(first_role)    

                    current_user.currency -= bail
                    dao.update_user(current_user)
                    await interaction.response.send_message(f"{interaction.user.name} paid {bail:,.0f} credits to get {target.name} out of jail.")
                    await general_channel.send(f"## {interaction.user.name} paid {bail:,.0f} credits to get {target.name} out of jail.")
                    return
                else:
                    await interaction.response.send_message(f"{target.name} is not in jail.", ephemeral=True)
                    return
        dao.update_user(current_user)
                

async def setup(bot: commands.Bot):
    await bot.add_cog(Bailout(bot))