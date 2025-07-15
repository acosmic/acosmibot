import os
from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
from io import BytesIO
import discord
from discord.ext import commands
from discord import app_commands
from Dao.GuildUserDao import GuildUserDao
from Dao.UserDao import UserDao
from Entities.GuildUser import GuildUser
from Entities.User import User
from logger import AppLogger
from Leveling import Leveling

logger = AppLogger(__name__).get_logger()


class Rank(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.leveling = Leveling()

    @app_commands.command(name="rank",
                          description="Leave blank to see your own rank, or mention another user to see their rank.")
    async def rank(self, interaction: discord.Interaction, user: discord.User = None):
        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        guild_user_dao = GuildUserDao()
        user_dao = UserDao()
        target_user = user if user else interaction.user

        try:
            # Get guild user rank and data
            user_rank = guild_user_dao.get_guild_user_rank(target_user.id, interaction.guild.id)
            current_guild_user = guild_user_dao.get_guild_user(target_user.id, interaction.guild.id)
            current_global_user = user_dao.get_user(target_user.id)

            if user_rank is not None and current_guild_user is not None:
                # Create the rank card image
                img_path = self.create_rank_card(target_user, current_guild_user, current_global_user, user_rank[-1],
                                                 interaction.guild)
                await interaction.response.send_message(file=discord.File(img_path))

                # Clean up the image file
                try:
                    os.remove(img_path)
                except:
                    pass  # If file deletion fails, just continue

                logger.info(
                    f"{interaction.user.name} used /rank command for {target_user.name} in {interaction.guild.name}")
                return
            else:
                if target_user == interaction.user:
                    message = "You don't have a rank in this server yet. Send a message to get started!"
                else:
                    message = f"{target_user.name} doesn't have a rank in this server yet."

                await interaction.response.send_message(message, ephemeral=True)
                logger.info(f"User {target_user.name} not found in database for guild {interaction.guild.name}")

        except Exception as e:
            logger.error(f"Error in /rank command for {target_user.name} in {interaction.guild.name}: {e}")
            await interaction.response.send_message("An error occurred while generating the rank card.", ephemeral=True)

    def create_rank_card(self, user, current_guild_user, current_global_user, rank, guild):
        try:
            # Create RankCards directory if it doesn't exist
            rank_cards_dir = "RankCards"
            if not os.path.exists(rank_cards_dir):
                os.makedirs(rank_cards_dir)

            # Use original dimensions
            img_width = 800
            img_height = 250
            img = Image.new('RGB', (img_width, img_height), color=(24, 25, 28))

            # Set font paths (try multiple common paths)
            font_paths = [
                '/usr/share/fonts/truetype/msttcorefonts/arialbd.ttf',
                '/System/Library/Fonts/Arial.ttf',  # macOS
                'C:/Windows/Fonts/arialbd.ttf',  # Windows
                '/usr/share/fonts/TTF/arial.ttf',  # Some Linux distros
                '/Users/acosmic/Library/Fonts/MartianMonoNerdFont-Regular.ttf',  # Keep the macOS path
            ]

            font_bold = None

            for path in font_paths:
                if os.path.exists(path):
                    try:
                        font_bold = path
                        break
                    except:
                        continue

            # Load fonts with original sizes
            try:
                font_username = ImageFont.truetype(font_bold, 48) if font_bold else ImageFont.load_default()  # Username
                font_rank_level = ImageFont.truetype(font_bold,
                                                     32) if font_bold else ImageFont.load_default()  # Rank/Level
                font_xp = ImageFont.truetype(font_bold, 24) if font_bold else ImageFont.load_default()  # XP text
                font_guild = ImageFont.truetype(font_bold, 18) if font_bold else ImageFont.load_default()  # Guild name
                font_global = ImageFont.truetype(font_bold,
                                                 16) if font_bold else ImageFont.load_default()  # Global level (smaller)
            except:
                font_username = ImageFont.load_default()
                font_rank_level = ImageFont.load_default()
                font_xp = ImageFont.load_default()
                font_guild = ImageFont.load_default()
                font_global = ImageFont.load_default()

            # Create a drawing context
            d = ImageDraw.Draw(img)

            # Fetch and create profile picture (original size)
            try:
                if user.avatar:
                    avatar_url = str(user.avatar.url)
                    response = requests.get(avatar_url, timeout=10)
                    avatar = Image.open(BytesIO(response.content)).convert("RGBA")
                    avatar = avatar.resize((140, 140), Image.LANCZOS)  # Original size

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

                    # Paste the combined avatar on the rank card (original position)
                    img.paste(combined_avatar, (20, avatar_y_position), combined_avatar)
            except Exception as e:
                logger.warning(f"Could not load avatar for {user.name}: {e}")

            # Adjust text positions for original layout
            text_start_x = 180  # Original position

            # Guild name (small, at top)
            guild_text = f"in {guild.name}"
            d.text((text_start_x, 20), guild_text, font=font_guild, fill=(150, 150, 150))

            # Global level in top right corner (small and subtle)
            global_level = current_global_user.global_level if current_global_user else 0
            global_text = f"Global Lvl {global_level}"
            global_bbox = d.textbbox((0, 0), global_text, font=font_global)
            global_width = global_bbox[2] - global_bbox[0]
            global_x = img_width - global_width - 20  # 20px padding from right edge
            d.text((global_x, 20), global_text, font=font_global,
                   fill=(255, 165, 0, 180))  # Slightly transparent orange

            # User name (big)
            display_name = current_guild_user.nickname or user.display_name or user.name
            username_text = f"{display_name}"
            d.text((text_start_x, 50), username_text, font=font_username, fill=(255, 255, 255))

            # Rank and Level on same line (original style)
            rank_text = f"RANK  #{rank}"
            level_text = f"LVL  {current_guild_user.level}"

            # Use guild exp for XP display (updated from season_exp)
            current_exp = current_guild_user.exp
            current_level_exp = self.leveling.calc_exp_required(current_guild_user.level)
            next_level_exp = self.leveling.calc_exp_required(current_guild_user.level + 1)
            exp_progress = current_exp - current_level_exp
            exp_needed = next_level_exp - current_level_exp

            xp_text = f"{current_exp:,} XP ({exp_progress:,} / {exp_needed:,})"

            # Calculate XP bar fill
            if exp_needed > 0:
                xp_bar_fill = exp_progress / exp_needed
            else:
                xp_bar_fill = 1.0
            xp_bar_fill = max(0, min(1, xp_bar_fill))  # Clamp between 0 and 1

            # Position text with dynamic spacing based on text width
            # Draw rank text
            d.text((text_start_x, 110), rank_text, font=font_rank_level, fill=(255, 255, 255))

            # Get text width for dynamic positioning
            rank_text_bbox = d.textbbox((0, 0), rank_text, font=font_rank_level)
            rank_text_width = rank_text_bbox[2] - rank_text_bbox[0]

            # Draw level text with padding after rank
            level_x = text_start_x + rank_text_width + 25  # 25px padding
            d.text((level_x, 110), level_text, font=font_rank_level, fill=(73, 23, 214))  # purple level text

            # XP text remains at original position
            d.text((text_start_x, 150), xp_text, font=font_xp, fill=(200, 200, 200))

            # XP bar with original dimensions
            bar_x = text_start_x
            bar_y = 180
            bar_width = 530  # Original width
            bar_height = 30  # Original height

            # Create XP bar background
            xp_bar_bg = Image.new("RGBA", (bar_width, bar_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(xp_bar_bg)
            draw.rounded_rectangle([0, 0, bar_width, bar_height], radius=bar_height // 2, fill=(50, 50, 50))

            # Calculate the minimum fill width
            min_fill_width = int(bar_width * 0.08)

            # Calculate the actual fill width
            fill_width = max(min_fill_width, int(bar_width * xp_bar_fill))

            # Draw XP bar fill
            xp_bar_fill_img = Image.new("RGBA", (bar_width, bar_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(xp_bar_fill_img)
            draw.rounded_rectangle([0, 0, fill_width, bar_height], radius=bar_height // 2, fill=(73, 23, 214))

            # Create outline
            outline = Image.new("RGBA", (bar_width + 6, bar_height + 6), (0, 0, 0, 0))
            draw = ImageDraw.Draw(outline)
            draw.rounded_rectangle([0, 0, bar_width + 6, bar_height + 6], radius=(bar_height + 6) // 2, outline="black",
                                   width=3)

            # Combine the XP bar components
            combined_xp_bar = Image.new("RGBA", (bar_width + 6, bar_height + 6), (0, 0, 0, 0))
            combined_xp_bar.paste(outline, (0, 0))
            combined_xp_bar.paste(xp_bar_bg, (3, 3), xp_bar_bg)
            combined_xp_bar.paste(xp_bar_fill_img, (3, 3), xp_bar_fill_img)

            # Paste the combined XP bar on the rank card
            img.paste(combined_xp_bar, (bar_x, bar_y), combined_xp_bar)

            # Save the image with guild-specific filename
            img_path = f"{rank_cards_dir}/rank_{user.id}_{guild.id}.png"
            img.save(img_path)

            return img_path

        except Exception as e:
            logger.error(f"Error creating rank card for {user.name}: {e}")
            raise e


async def setup(bot: commands.Bot):
    await bot.add_cog(Rank(bot))