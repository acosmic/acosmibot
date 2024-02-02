from types import NoneType
import discord
from discord.ext import commands
from discord import app_commands

class ViewStartRPS(discord.ui.View):

    initiator: discord.User = None
    players: int = 0
    
    async def send(self, interaction: discord.Interaction):
        embed = self.create_embed()
        await interaction.response.send_message(view=self, embed=embed)
        self.message = await interaction.original_response()


    def create_embed(self):
        desc = f"{self.initiator.display_name} is looking for another {self.players - 1} player"
        embed = discord.Embed(title="Accept Rock Paper Scissors Match!?", description=desc)

        embed.add_field(inline=True, name="✅ Joined", value="")
        embed.add_field(inline=True, name="❌ Declined", value="")
        embed.add_field(inline=True, name="🔄 Tentative", value="")

        return embed
    
    def convert_user_list_to_str(self, user_list, defualt_str="No one")
