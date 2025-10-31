import discord
from discord.ext import commands
from discord import app_commands
import uuid
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class CommandsPaginationView(discord.ui.View):
    """View for paginated command list with navigation buttons"""

    def __init__(self, user_id: int, pages: list, timeout=180):
        """
        Initialize pagination view

        Args:
            user_id: Discord user ID who can interact with buttons
            pages: List of embed pages to display
            timeout: Timeout in seconds (default 180)
        """
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.pages = pages
        self.current_page = 0
        self.message = None
        self.view_id = str(uuid.uuid4())

        # Add initial buttons
        self.update_buttons()

    def update_buttons(self):
        """Update button states based on current page"""
        self.clear_items()

        # Previous button
        prev_button = discord.ui.Button(
            label="Previous",
            style=discord.ButtonStyle.primary,
            custom_id=f"prev_{self.view_id}",
            emoji="◀️",
            disabled=self.current_page == 0
        )
        prev_button.callback = self.previous_page
        self.add_item(prev_button)

        # Page indicator (disabled button)
        page_button = discord.ui.Button(
            label=f"Page {self.current_page + 1}/{len(self.pages)}",
            style=discord.ButtonStyle.secondary,
            custom_id=f"page_{self.view_id}",
            disabled=True
        )
        self.add_item(page_button)

        # Next button
        next_button = discord.ui.Button(
            label="Next",
            style=discord.ButtonStyle.primary,
            custom_id=f"next_{self.view_id}",
            emoji="▶️",
            disabled=self.current_page >= len(self.pages) - 1
        )
        next_button.callback = self.next_page
        self.add_item(next_button)

    async def previous_page(self, interaction: discord.Interaction):
        """Navigate to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_message(interaction)

    async def next_page(self, interaction: discord.Interaction):
        """Navigate to next page"""
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await self.update_message(interaction)

    async def update_message(self, interaction: discord.Interaction):
        """Update the message with current page"""
        await interaction.response.defer()
        self.update_buttons()
        embed = self.pages[self.current_page]
        await self.message.edit(embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the command user can interact - silently ignore others"""
        if interaction.user.id != self.user_id:
            return False
        return True

    async def on_timeout(self):
        """Disable buttons on timeout"""
        for child in self.children:
            child.disabled = True

        try:
            await self.message.edit(view=self)
        except:
            pass  # Message might be deleted


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="commands", description="Returns a list of commands.")
    async def commands(self, interaction: discord.Interaction):
        try:
            pages = []

            # PAGE 1: Games & Economy
            page1 = discord.Embed(
                title="<:acosmibot:1430085764489805824> Acosmibot - Commands",
                color=interaction.user.color,
                description="Here are all available commands organized by category:"
            )

            # 🎮 Games & Gambling
            games_commands = [
                "`/8ball` - Ask the magic 8ball",
                "`/coinflip` - Flip a coin for credits",
                "`/deathroll` - PvP Deathroll game, first to roll 1 loses",
                "`/rockpaperscissors` - PvP RPS challenge (win 3 rounds)",
                "`/slots` - Play slot machine"
            ]
            page1.add_field(
                name="🎮 Games & Gambling",
                value="\n".join(games_commands),
                inline=False
            )

            # 💰 Economy & Currency
            economy_commands = [
                "`/balance` - Check your Credits",
                "`/guildbank` - Check server bank Credits",
                "`/give` - Give Credits to another user"
            ]
            page1.add_field(
                name="💰 Economy & Currency",
                value="\n".join(economy_commands),
                inline=False
            )

            page1.set_footer(text="Page 1/4 • Use the buttons to navigate")
            pages.append(page1)

            # PAGE 2: Banking & Portals
            page2 = discord.Embed(
                title="<:acosmibot:1430085764489805824> Acosmibot - Commands",
                color=interaction.user.color,
                description="Here are all available commands organized by category:"
            )

            # 💳 Banking
            bank_commands = [
                "`/deposit` - Deposit credits to global bank",
                "`/withdraw` - Withdraw credits from bank",
                "`/bank` - View bank balance and stats",
                "`/bank-history` - View transaction history"
            ]
            page2.add_field(
                name="💳 Banking",
                value="\n".join(bank_commands),
                inline=False
            )

            # 🌀 Portals
            portal_commands = [
                "`/portal-search` - Search for servers with portals",
                "`/portal-open` - Open portal to another server (costs credits)",
                "`/portal-close` - Close active portal (admin)",
                "`/portal-send` - Send message through portal",
                "`/portal-status` - Check portal status"
            ]
            page2.add_field(
                name="🌀 Portals",
                value="\n".join(portal_commands),
                inline=False
            )

            page2.set_footer(text="Page 2/4 • Use the buttons to navigate")
            pages.append(page2)

            # PAGE 3: Lottery, Reminders & Stats
            page3 = discord.Embed(
                title="<:acosmibot:1430085764489805824> Acosmibot - Commands",
                color=interaction.user.color,
                description="Here are all available commands organized by category:"
            )

            # 🎟️ Lottery
            lottery_commands = [
                "`/admin-start-lotto` - Start a lottery (admin only)",
                "React with 🎟️ to lottery message to enter"
            ]
            page3.add_field(
                name="🎟️ Lottery",
                value="\n".join(lottery_commands),
                inline=False
            )

            # ⏰ Reminders
            reminder_commands = [
                "`/remind` - Set a reminder (e.g., /remind 30m Check oven)",
                "`/reminders` - View active reminders",
                "`/cancelreminder` - Cancel a reminder"
            ]
            page3.add_field(
                name="⏰ Reminders",
                value="\n".join(reminder_commands),
                inline=False
            )

            # 📊 Stats & Profile
            stats_commands = [
                "`/rank` - Check your rank or another user's",
                "`/stats` - View detailed user stats",
                "`/stats-games` - View detailed games stats",
                "`/leaderboard` - Top 10 users by stats"
            ]
            page3.add_field(
                name="📊 Stats & Profile",
                value="\n".join(stats_commands),
                inline=False
            )

            page3.set_footer(text="Page 3/4 • Use the buttons to navigate")
            pages.append(page3)

            # PAGE 4: Customization, AI & Utility
            page4 = discord.Embed(
                title="<:acosmibot:1430085764489805824> Acosmibot - Commands",
                color=interaction.user.color,
                description="Here are all available commands organized by category:"
            )

            # 🎨 Customization & Fun
            custom_commands = [
                "`/polymorph` - Change someone's nickname (10,000 Credits)"
            ]
            page4.add_field(
                name="🎨 Customization & Fun",
                value="\n".join(custom_commands),
                inline=False
            )

            # 🤖 AI Features
            ai_commands = [
                "`/ai-enable` - Enable AI for server",
                "`/ai-disable` - Disable AI for server",
                "`/ai-status` - Check AI status",
                "`/ai-clear` - Clear conversation history"
            ]
            page4.add_field(
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
                "`/weather` - Get weather for a city"
            ]
            page4.add_field(
                name="🛠️ Utility & Info",
                value="\n".join(utility_commands),
                inline=False
            )

            # Footer
            page4.add_field(
                name="",
                value="[Developed by Acosmic](https://acosmibot.com/) <:acosmicD:1171219346299814009>",
                inline=False
            )

            page4.set_footer(text="Page 4/4 • Use /command_name to run any command!")
            pages.append(page4)

            # Create pagination view and send
            view = CommandsPaginationView(interaction.user.id, pages)
            await interaction.response.send_message(embed=pages[0], view=view)
            view.message = await interaction.original_response()

            logger.info(f"{interaction.user.name} used /commands command")

        except Exception as e:
            logger.error(f"Error in commands command: {e}")
            await interaction.response.send_message("An error occurred while fetching commands.", ephemeral=True)

    @app_commands.command(name="help", description="Get info about Acosmibot and its features")
    async def help(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title="<:acosmibot:1430085764489805824> Welcome to Acosmibot!",
                color=interaction.user.color,
                description="A multi-featured Discord bot with leveling, economy, games, AI chat, and cross-server portals!"
            )

            # About Acosmibot
            embed.add_field(
                name="📖 About",
                value="Acosmibot is a feature-rich Discord bot designed to engage your community with:\n"
                      "• **Leveling System** - Earn XP from messages and unlock role rewards\n"
                      "• **Economy & Banking** - Server currency, global bank, and exciting games\n"
                      "• **AI Chat** - Powered by OpenAI for intelligent conversations\n"
                      "• **Cross-Server Portals** - Connect and chat with other Discord servers\n"
                      "• **Twitch Notifications** - Get notified when streamers go live\n"
                      "• **Lottery System** - Server-wide lotteries with prize pools\n"
                      "• **Reminders** - Never forget important tasks",
                inline=False
            )

            # Documentation & Dashboard
            embed.add_field(
                name="🔗 Links",
                value="[Website](https://acosmibot.com/) • [Dashboard](https://acosmibot.com/dashboard) • [Documentation](https://acosmibot.com/docs)",
                inline=False
            )

            # Important Setup Notes
            embed.add_field(
                name="⚙️ Important Setup Notes",
                value="**Role Management:**\n"
                      "For leveling role rewards and Twitch notifications to work properly, Acosmibot must be positioned **higher** in your server's role hierarchy than the roles it manages. You can adjust this in Server Settings → Roles.\n\n"
                      "**Twitch Live Now Feature:**\n"
                      "Roles for Twitch Live Now need to be created in your server and then managed through the [server dashboard](https://acosmibot.com/guild-dashboard). Give streamers a 'Streamer' role and when they go live the 'Live Now' role be applied to them.\n\n"
                      "**Portal System:**\n"
                      "Enable and configure cross-server portals via the dashboard. Both servers must have portals enabled to connect.",
                inline=False
            )

            # Commands Reference
            embed.add_field(
                name="📝 Commands",
                value="Use `/commands` to see a full list of available commands organized by category!",
                inline=False
            )

            # Footer
            embed.add_field(
                name="",
                value="[Developed by Acosmic](https://acosmibot.com/) <:acosmicD:1171219346299814009>",
                inline=False
            )

            embed.add_field(
                name="",
                value="Need support? Join the Acosmibot support server [Acosmibot Discord](https://discord.gg/qhY9XEdMc9)",
                inline=False
            )

            # embed.set_footer(text="Need support? Visit acosmibot.com for help!")

            await interaction.response.send_message(embed=embed)
            logger.info(f"{interaction.user.name} used /help command")

        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await interaction.response.send_message("An error occurred while fetching help info.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))