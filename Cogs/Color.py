import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from logger import AppLogger

logger = AppLogger(__name__).get_logger()

class Color(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    @app_commands.command(name="color", description="Change your color role. Cost = 5,000 credits.")
    async def color(self, interaction: discord.Interaction, r: int, g: int, b: int):
            
        if r < 0 or r > 255 or g < 0 or g > 255 or b < 0 or b > 255:
            await interaction.response.send_message(f"## Please enter valid RGB values (0-255).", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        roles = interaction.guild.roles
        dao = UserDao()
        user = dao.get_user(interaction.user.id)
        role_name = f"color_{str(r)}_{str(g)}_{str(b)}"
        cost = 5000

        if len(roles) < 200:
            if user.currency >= cost:
                await interaction.user.remove_roles(*[role for role in roles if role.name.startswith("color_")])
                
                
                if role_name in [role.name for role in roles]:
                        role = discord.utils.get(roles, name=role_name)
                        await interaction.user.add_roles(role)
                        await interaction.followup.send(f"## {interaction.user.mention} You have successfully changed your color to {role_name}. -{cost:,.0f} credits.")
                        user.currency -= cost
                        logger.info(f"Color role existed already. {interaction.user.name} changed their color to {role_name}.")

                elif "Ashbo" in [interaction.user.roles[i].name for i in range(len(interaction.user.roles))]:
                    role = discord.utils.get(roles, name="Ashbo")
                    await role.edit(color=discord.Color.from_rgb(r, g, b))
                    await interaction.followup.send(f"## {interaction.user.mention} You have successfully changed your role color {r}_{g}_{b}. -{cost:,.0f} credits.")

                elif "Acosmic" in [interaction.user.roles[i].name for i in range(len(interaction.user.roles))]:
                    role = discord.utils.get(roles, name="Acosmic")
                    await role.edit(color=discord.Color.from_rgb(r, g, b))
                    await interaction.followup.send(f"## {interaction.user.mention} You have successfully changed your role color to {r}_{g}_{b}. -{cost:,.0f} credits.")

                else:
                    color = discord.Color.from_rgb(r, g, b)
                    new_role = await interaction.guild.create_role(name=role_name, color=color)
                    await new_role.edit(position=len(roles) - 5)
                    await interaction.user.add_roles(new_role)
                    await interaction.followup.send(f"## {interaction.user.mention} You created a new role and successfully changed your color to {role_name}. -{cost:,.0f} credits")
                    user.currency -= cost
                    logger.info(f"{interaction.user.name} created a new role and changed their color to {role_name}.")
            else:
                await interaction.followup.send(f"## You do not have enough credits to change your color. You need {cost:,.0f} credits.", ephemeral=True)
                logger.info(f"{interaction.user.name} tried to change their color but did not have enough credits.")
        else:
            await interaction.followup.send(f"## The server has reached the maximum number of roles. Please contact a server administrator to remove some roles.", ephemeral=True)
            logger.info(f"{interaction.user.name} tried to change their color but the server has reached the maximum number of roles.")
        dao.update_user(user)
async def setup(bot: commands.Bot):
    await bot.add_cog(Color(bot))

                    
