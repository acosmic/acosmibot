import discord
from discord import Embed
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
import logging
import requests
import json



class Dictionary(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    @app_commands.command(name="define", description="Look up the definition of a word.")
    async def balance(self, interaction: discord.Interaction, word: str):

        

        url = f"https://api.dictionaryapi.dev/api/v2/entries/en_US/{word}"
        response = requests.get(url)
        if response.status_code == 200:
            data = json.loads(response.text)
            length = len(data[0]["meanings"])
            speech = data[0]["meanings"][0]["partOfSpeech"]
            embed = Embed(title=f"{word} - {speech}", description="Definition:")
            if length > 1:
                for i in range(length):
                    definition = data[0]["meanings"][i]["definitions"][0]["definition"]
                    embed.add_field(name=f"Definition {i+1}", value=definition, inline=False)
                    # print(f"## Definition of {word}: {definition}")
            else:
                definition = data[0]["meanings"][0]["definitions"][0]["definition"]
                embed.add_field(name="Definition", value=definition, inline=False)
                # print(f"## Definition of {word}: {definition}")
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"## Definition of {word}: Not found.")
        logging.info(f"{interaction.user.name} used /define command")



async def setup(bot: commands.Bot):
    await bot.add_cog(Dictionary(bot))