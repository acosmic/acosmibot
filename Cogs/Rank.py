import os
from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
from io import BytesIO
import discord
from discord.ext import commands
from discord import app_commands
from Dao.UserDao import UserDao
from Entities.User import User
from logger import AppLogger
from Leveling import Leveling

logging = AppLogger(__name__).get_logger()

class Rank(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.leveling = Leveling()

    @app_commands.command(name="rank", description="Leave blank to see your own rank, or mention another user to see their rank.")
    async def rank(self, interaction: discord.Interaction, user: discord.User = None):
        dao = UserDao()
        if user is not None:
            user_rank = dao.get_user_rank(user.id)
            current_user = dao.get_user(user.id)
            discord_user = user
        else:
            user_rank = dao.get_user_rank(interaction.user.id)
            current_user = dao.get_user(interaction.user.id)
            discord_user = interaction.user

        if user_rank is not None:
            name_from_db = user_rank[1]
            display_name = discord_user.name if discord_user.name is not None else name_from_db
            
            # Create the rank card image
            img_path = self.create_rank_card(discord_user, current_user, user_rank[-1])
            await interaction.response.send_message(file=discord.File(img_path))
            os.remove(img_path) # Delete the image file after sending it
            return

        logging.info(f"The user with Discord username {interaction.user.name} was not found in the database.")
        return

    def create_rank_card(self, user, current_user, rank):
        # Create a blank image with a dark background
        img_width = 800
        img_height = 250
        img = Image.new('RGB', (img_width, img_height), color=(24, 25, 28))

        # Set font paths
        font_path_bold = '/usr/share/fonts/truetype/msttcorefonts/arialbd.ttf'
        font_path_regular = '/usr/share/fonts/truetype/msttcorefonts/arial.ttf'

        # Load fonts
        font_large_bold = ImageFont.truetype(font_path_bold, 42) if os.path.exists(font_path_bold) else ImageFont.load_default()
        font_medium_bold = ImageFont.truetype(font_path_bold, 28) if os.path.exists(font_path_bold) else ImageFont.load_default()
        font_regular = ImageFont.truetype(font_path_regular, 22) if os.path.exists(font_path_regular) else ImageFont.load_default()

        # Create a drawing context
        d = ImageDraw.Draw(img)

        # Fetch and create the profile picture if available
        if user.avatar:
            avatar_url = str(user.avatar.url)
            response = requests.get(avatar_url)
            avatar = Image.open(BytesIO(response.content)).convert("RGBA")
            avatar = avatar.resize((140, 140), Image.LANCZOS)

            # Create a circular mask for the avatar
            mask = Image.new("L", (140, 140), 0)
            draw = ImageDraw.Draw(mask) 
            draw.ellipse((0, 0, 140, 140), fill=255)

            # Create the black circular outline
            outline = Image.new("RGBA", (150, 150), (0, 0, 0, 0))
            draw = ImageDraw.Draw(outline)
            draw.ellipse((2, 2, 148, 148), outline="black", width=2)

            # Apply the mask to the avatar
            avatar.putalpha(mask)

            # Combine the avatar with the outline
            combined_avatar = Image.new("RGBA", (150, 150), (0, 0, 0, 0))
            combined_avatar.paste(avatar, (5, 5), avatar)
            combined_avatar.paste(outline, (0, 0), outline)

            # Calculate the vertical position to center the avatar
            avatar_y_position = (img_height - 150) // 2

            # Paste the combined avatar on the rank card
            img.paste(combined_avatar, (20, avatar_y_position), combined_avatar)

        # User name
        username_text = f"{user.name}"
        d.text((180, 40), username_text, font=font_large_bold, fill=(255, 255, 255))

        # Rank, Level, and XP
        rank_text = f"RANK  #{rank}"
        level_text = f"LVL  {current_user.level}"
        xp_text = f"{current_user.exp:,} / {self.leveling.calc_exp_required(current_user.level + 1):,} XP"
        xp_bar_fill = (current_user.exp - self.leveling.calc_exp_required(current_user.level)) / (self.leveling.calc_exp_required(current_user.level + 1) - self.leveling.calc_exp_required(current_user.level))

        d.text((180, 90), rank_text, font=font_medium_bold, fill=(255, 255, 255))
        d.text((340, 90), level_text, font=font_medium_bold, fill=(73, 23, 214)) # purple level text
        d.text((180, 130), xp_text, font=font_regular, fill=(200, 200, 200))

        # Draw XP bar background and light gray fill
        bar_x = 180
        bar_y = 180
        bar_width = 530
        bar_height = 30
        outline = Image.new("RGBA", (bar_width + 4, bar_height + 4), (0, 0, 0, 0))
        draw = ImageDraw.Draw(outline)
        draw.rounded_rectangle([0, 0, bar_width + 4, bar_height + 4], radius=(bar_height + 4) // 2, outline="black", width=2)
        
        xp_bar_bg = Image.new("RGBA", (bar_width, bar_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(xp_bar_bg)
        draw.rounded_rectangle([0, 0, bar_width, bar_height], radius=bar_height // 2, fill=(50, 50, 50)) # inner fill

        # Calculate the minimum fill width
        min_fill_width = int(bar_width * 0.08)
        
        # Calculate the actual fill width
        fill_width = max(min_fill_width, int(bar_width * xp_bar_fill))

        # Draw XP bar
        xp_bar_fill = Image.new("RGBA", (bar_width, bar_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(xp_bar_fill)
        draw.rounded_rectangle([0, 0, fill_width, bar_height], radius=bar_height // 2, fill=(73, 23, 214)) # fill color

        # Combine the XP bar with the outline and background
        combined_xp_bar = Image.new("RGBA", (bar_width + 4, bar_height + 4), (0, 0, 0, 0))
        combined_xp_bar.paste(outline, (0, 0))
        combined_xp_bar.paste(xp_bar_bg, (2, 2), xp_bar_bg)
        combined_xp_bar.paste(xp_bar_fill, (2, 2), xp_bar_fill)

        # Paste the combined XP bar on the rank card
        img.paste(combined_xp_bar, (bar_x, bar_y), combined_xp_bar)

        # Save the image
        img_path = f"RankCards/rank_{user.id}.png"
        img.save(img_path)

        return img_path
        

async def setup(bot: commands.Bot):
    await bot.add_cog(Rank(bot))
