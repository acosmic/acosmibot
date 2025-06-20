import typing
import discord
import openai
from discord.ext import commands
from discord import app_commands
from Entities.AI_Thread import AI_Thread
from Dao.AIDao import AIDao
from logger import AppLogger

logger = AppLogger(__name__).get_logger()

class Reset_AI_Thread(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="reset-ai-thread", description="Reset your AI Thread.")
    async def reset_ai_thread(
        self,
        interaction: discord.Interaction,
        temp: typing.Literal["0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9", "1.0", "1.1", "1.2", "1.3", "1.4", "1.5"]
    ):
        dao = AIDao()

        try:
            dao.delete_thread(interaction.user.id)
        except Exception as e:
            logger.error(f"Error in /reset_ai_thread command: {e}")
            message_text = "## Error deleting your AI Thread. ❌"

        try:
            if temp is None:
                temp = "1.0"
            temp_float = float(temp)  # Convert string to float for further operations
            new_thread = openai.beta.threads.create()
            dao.add_new_thread(interaction.user.id, new_thread.id, temp_float)
            logger.info(f"NEW THREAD ID: {new_thread.id}")
            if new_thread:
                message_text = f"## Your AI Thread has been reset. 🔄 \n\n ### New Thread: {new_thread.id} - Temp: {temp if temp else 1.0}"

            else:
                message_text = "## Error creating a new AI Thread. ❌"
        except Exception as e:
            logger.error(f"Error creating a new AI Thread: {e}")
            message_text = "## Error creating a new AI Thread. ❌"

        await interaction.response.send_message(message_text)

        
async def setup(bot: commands.Bot):
    await bot.add_cog(Reset_AI_Thread(bot))
        

