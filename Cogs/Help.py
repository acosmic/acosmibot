import discord
from discord.ext import commands
from discord import app_commands
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="help", description="Returns a list of commands.")
    async def help(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title="🤖 Acosmibot - Commands",
                color=interaction.user.color,
                description="Here are all available commands organized by category:"
            )

            # 🎮 Games & Gambling
            games_commands = [
                "`/8ball` - Ask the magic 8ball (50 Credits)",
                "`/coinflip` - Flip a coin for credits",
                "`/deathroll` - Deathroll game, first to roll 1 loses",
                "`/rockpaperscissors` - RPS challenge (3 rounds)",
                "`/slots` - Play slot machine"
            ]
            embed.add_field(
                name="🎮 Games & Gambling",
                value="\n".join(games_commands),
                inline=False
            )

            # 💰 Economy & Currency
            economy_commands = [
                "`/balance` - Check your Credits",
                "`/checkbank` - Check server bank Credits",
                "`/give` - Give Credits to another user",
                "`/leaderboard` - Top 5 users by stats"
            ]
            embed.add_field(
                name="💰 Economy & Currency",
                value="\n".join(economy_commands),
                inline=False
            )

            # 📊 Stats & Profile
            stats_commands = [
                "`/rank` - Check your rank or another user's",
                "`/stats` - View detailed user statistics"
            ]
            embed.add_field(
                name="📊 Stats & Profile",
                value="\n".join(stats_commands),
                inline=False
            )

            # 🎨 Customization & Fun
            custom_commands = [
                "`/color` - Change your color role (5,000 Credits)",
                "`/polymorph` - Change someone's nickname (10,000 Credits)",
                "`/jailmail` - Send message to/from jail (50,000 Credits)"
            ]
            embed.add_field(
                name="🎨 Customization & Fun",
                value="\n".join(custom_commands),
                inline=False
            )

            # 🤖 AI Features
            ai_commands = [
                "`/ai-enable` - Enable AI for server",
                "`/ai-disable` - Disable AI for server",
                "`/ai-status` - Check AI status",
                "`/ai-temperature` - Set AI creativity (0.1-2.0)",
                "`/ai-clear` - Clear conversation history",
                "`/reset-ai-thread` - Reset your AI thread"
            ]
            embed.add_field(
                name="🤖 AI Features",
                value="\n".join(ai_commands),
                inline=False
            )

            # 🛠️ Utility & Info
            utility_commands = [
                "`/apod` - NASA Astronomy Picture of the Day",
                "`/define` - Look up word definitions",
                "`/giphy` - Get random GIFs",
                "`/ping` - Check bot latency",
                "`/weather` - Get weather for a city",
                "`/twitch_to_mp3` - Convert Twitch clips to MP3"
            ]
            embed.add_field(
                name="🛠️ Utility & Info",
                value="\n".join(utility_commands),
                inline=False
            )

            # Footer
            embed.add_field(
                name="",
                value="[Developed by Acosmic](https://github.com/acosmic/acosmicord-bot) <a:pepesith:1165101386921418792>",
                inline=False
            )

            embed.set_footer(text="Use /command_name to run any command!")

            await interaction.response.send_message(embed=embed)
            logger.info(f"{interaction.user.name} used /help command")

        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await interaction.response.send_message("An error occurred while fetching commands.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))