import discord
from discord import Embed, app_commands
from discord.ext import commands
from Dao.UserDao import UserDao
from logger import AppLogger
import requests
import json

logger = AppLogger(__name__).get_logger()


class Dictionary(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    @app_commands.command(name="define", description="Look up the definition of a word.")
    async def define(self, interaction: discord.Interaction, word: str):
        # ✅ Check if input is a single word
        if " " in word.strip():
            await interaction.response.send_message(
                "❌ Please enter only **one word** (no spaces).",
                ephemeral=True,
            )
            return

        # Optional: check if word contains only alphabetic characters
        if not word.isalpha():
            await interaction.response.send_message(
                "❌ Please use letters only (no numbers or symbols).",
                ephemeral=True,
            )
            return

        url = f"https://api.dictionaryapi.dev/api/v2/entries/en_US/{word}"
        response = requests.get(url)

        if response.status_code == 200:
            data = json.loads(response.text)
            meanings = data[0]["meanings"]
            part_of_speech = meanings[0].get("partOfSpeech", "N/A")

            embed = Embed(title=f"{word} - {part_of_speech}", description="")

            for i, meaning in enumerate(meanings):
                definitions = meaning.get("definitions", [])
                if not definitions:
                    continue

                definition_text = definitions[0].get("definition", "No definition found.")
                embed.add_field(
                    name=f"Definition {i+1}" if len(meanings) > 1 else "Definition",
                    value=definition_text,
                    inline=False,
                )

            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(
                f"❌ No definition found for **{word}**.",
                ephemeral=True,
            )

        logger.info(f"{interaction.user.name} used /define command")


async def setup(bot: commands.Bot):
    await bot.add_cog(Dictionary(bot))
