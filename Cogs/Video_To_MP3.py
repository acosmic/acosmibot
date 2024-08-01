import discord
from discord.ext import commands
from discord import app_commands
import youtube_dl
import os
from pydub import AudioSegment
from logger import AppLogger

logging = AppLogger(__name__).get_logger()

class TwitchToMP3(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="twitch_to_mp3", description="Convert a Twitch clip to an MP3 file")
    async def twitch_to_mp3(self, interaction: discord.Interaction, url: str):
        try:
            await interaction.response.send_message("Downloading Twitch clip...")

            video_path = self.download_twitch_clip(url)
            if not video_path:
                await interaction.followup.send("Failed to download Twitch clip.")
                return

            await interaction.followup.send("Converting to MP3...")

            mp3_path = self.convert_to_mp3(video_path)
            if not mp3_path:
                await interaction.followup.send("Failed to convert video to MP3.")
                return

            await interaction.followup.send(file=discord.File(mp3_path))
            
            # Clean up files
            os.remove(video_path)
            os.remove(mp3_path)
        except Exception as e:
            logging.error(f"Error in twitch_to_mp3_command: {e}")
            await interaction.followup.send(f"An error occurred: {e}")

    def download_twitch_clip(self, url, download_path='downloads'):
        ydl_opts = {
            'outtmpl': f'{download_path}/%(title)s.%(ext)s',
            'format': 'best'
        }
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                video_filename = ydl.prepare_filename(info_dict)
            return video_filename
        except Exception as e:
            logging.error(f"Failed to download Twitch clip: {e}")
            return None

    def convert_to_mp3(self, video_path):
        try:
            mp3_path = video_path.rsplit('.', 1)[0] + '.mp3'
            AudioSegment.from_file(video_path).export(mp3_path, format='mp3')
            return mp3_path
        except Exception as e:
            logging.error(f"Failed to convert video to MP3: {e}")
            return None

async def setup(bot: commands.Bot):
    await bot.add_cog(TwitchToMP3(bot))
