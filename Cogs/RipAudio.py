import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import os
from logger import AppLogger

logging = AppLogger(__name__).get_logger()


class RipAudio(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="ripaudio", description="Convert a YouTube/Twitch video to an MP3 file")
    async def ripaudio(self, interaction: discord.Interaction, url: str):
        try:
            # Initial response that we'll edit
            await interaction.response.send_message("🔄 Starting audio extraction...")

            # Download and convert to MP3 in one step
            await interaction.edit_original_response(content="📥 Downloading and converting to MP3...")
            mp3_path = self.download_and_convert_audio(url)
            if not mp3_path:
                await interaction.edit_original_response(content="❌ Failed to download and convert audio.")
                return

            # Upload the file
            await interaction.edit_original_response(content="📤 Uploading MP3 file...")
            await interaction.followup.send(file=discord.File(mp3_path))

            # Success message
            await interaction.edit_original_response(content="✅ Audio extraction complete!")

            # Clean up files
            os.remove(mp3_path)
        except Exception as e:
            logging.error(f"Error in ripaudio command: {e}")
            await interaction.edit_original_response(content=f"❌ An error occurred: {e}")

    def download_and_convert_audio(self, url, download_path='downloads'):
        """Download video and extract audio directly to MP3 using yt-dlp"""
        ydl_opts = {
            'outtmpl': f'{download_path}/%(title)s.%(ext)s',
            'format': 'bestaudio/best',  # Get best audio quality
            'noplaylist': True,  # Only download single video, not playlist
            'extractaudio': True,  # Extract audio
            'audioformat': 'mp3',  # Convert to MP3
            'audioquality': '192',  # Set audio quality
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                # yt-dlp will create the MP3 file automatically
                base_filename = ydl.prepare_filename(info_dict)
                mp3_filename = base_filename.rsplit('.', 1)[0] + '.mp3'
            return mp3_filename
        except Exception as e:
            logging.error(f"Failed to download and convert audio: {e}")
            return None


async def setup(bot: commands.Bot):
    await bot.add_cog(RipAudio(bot))