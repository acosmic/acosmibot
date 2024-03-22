import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao 
import logging

## used this to update ids to discord ids rather than auto incremented integers upon joing the server
## REMOVED FROM COMMANDS LIST


logging.basicConfig(filename='/home/acosmic/Dev/acosmibot/logs.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Update_ids(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="update_ids", description="Updates IDs in the database based on Discord IDs.")
    async def update_ids(self, interaction: discord.Interaction):
        dao = UserDao()  
        role = discord.utils.get(interaction.guild.roles, name="Acosmic")
        if role in interaction.user.roles:

           
            guild = interaction.guild
            members = guild.members

            
            try: 
                for member in members:
                    discord_id = member.id
                    logging.info(f'{member.name} : {discord_id}')

                    dao.update_user_id(member.name, discord_id)
                
                await interaction.response.send_message("IDs updated in the database.")
                logging.info(f'{str(interaction.user.name)} used /update_ids')
            except Exception as e:
                logging.error(f' /update_ids - ERROR: {e}')
        else:
            await interaction.response.send_message("You can not use this command")

async def setup(bot: commands.Bot):
    await bot.add_cog(Update_ids(bot))