import discord
from discord.ext import commands
from discord import app_commands
from Dao.GuildUserDao import GuildUserDao
import random
from logger import AppLogger

logger = AppLogger(__name__).get_logger()


class Eightball(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="8ball", description="Ask the magic 8ball your yes/no questions for 50 Credits")
    async def eightball(self, interaction: discord.Interaction, question: str):

        # Funnier and more varied 8-ball responses
        responses = [
            # Positive responses (with humor)
            "It is certain... unlike your dating life! 💯",
            "It is decidedly so, my dude! 🎯",
            "Without a doubt, unlike your last excuse! ✅",
            "Yes - definitely! Even a broken clock is right twice a day! ⏰",
            "You may rely on it... more than you rely on your alarm! 📢",
            "As I see it, yes! And I see everything from in here! 👁️",
            "Most likely... probably... maybe... definitely! 📈",
            "Outlook good! Unlike your email inbox! 📧",
            "Yes, and I'm saying that with confidence! 💪",
            "Signs point to yes... all of them! Even the stop sign! 🛑",
            "Absolutely! 100%! Well, maybe 99.9%... 🎉",

            # Neutral/uncertain responses (with humor)
            "Reply hazy, try again... I'm having signal issues! 📶",
            "Ask again later, I'm on my coffee break! ☕",
            "Better not tell you now... it's classified! 🤐",
            "Cannot predict now... Mercury is in microwave! 🌌",
            "Concentrate and ask again... I wasn't listening! 🧘‍♂️",
            "Magic 8-ball.exe has stopped working... 🔄",
            "Error 404: Answer not found! Try turning it off and on again! 💻",
            "The crystal ball is buffering... please wait! ⏳",

            # Negative responses (with humor)
            "Don't count on it... seriously, don't! 🚫",
            "My reply is no... and I'm sticking to it! ❌",
            "My sources say no... and my sources are reliable! 📰",
            "Outlook not so good... have you tried therapy? 🌧️",
            "Very doubtful... like your chances of winning the lottery! 🎰",
            "Nope! Not happening! Not in this universe! 🌍",
            "Hard no from me, chief! 👎",
            "That's a Texas-sized no from me! 🤠",

            # Sassy/sarcastic responses
            "Oh honey, no... just no! 💅",
            "Are you serious right now? The answer is NO! 🙄",
            "I'd rather not say... but it rhymes with 'go'! 🎵",
            "The universe says 'lol no'! 🌌",
            "Even my non-existent magic couldn't make that happen! ✨",
            "That's gonna be a no from me, dog! 🐕",
            "Not with that attitude! (But also just no.) 😤",

            # Weird/random responses
            "Ask your mom! 👩",
            "42... wait, wrong question! 🤖",
            "The answer lies within... your refrigerator! 🧊",
            "Have you tried turning yourself off and on again? 🔌",
            "Magic 8-ball says: 'Why are you asking me? I'm just a ball!' ⚽",
            "The spirits say... they're busy right now! 👻",
            "My psychic network is down... try again after midnight! 🌙"
        ]

        # Use GuildUserDao for multi-server architecture
        guild_user_dao = GuildUserDao()
        cost = 50

        # Get guild-specific user data
        guild_user = guild_user_dao.get_guild_user(interaction.user.id, interaction.guild.id)

        if not guild_user:
            await interaction.response.send_message(
                "You need to be registered in this server first. Send a message to get started!", ephemeral=True)
            return

        if guild_user.currency >= cost:

            eightball_response = random.choice(responses)

            # Create embed with enhanced visual appeal
            embed = discord.Embed(
                title=f"🎱 Magic 8-Ball",
                description=f"**Question:** {question}\n\n**Answer:** {eightball_response}",
                color=interaction.user.color if interaction.user.color.value != 0 else discord.Color.purple()
            )

            # Add user info with their display name or nickname
            user_display_name = interaction.user.display_name or interaction.user.name
            embed.set_author(
                name=f"{user_display_name} asks...",
                icon_url=interaction.user.display_avatar.url
            )

            embed.set_footer(text=f"-{cost} Credits • The 8-ball has spoken!")

            # Deduct currency and update guild user
            guild_user.currency -= cost
            guild_user_dao.update_guild_user(guild_user)

            await interaction.response.send_message(embed=embed)
            logger.info(
                f"{interaction.user.name} used /8ball command with question: {question} in guild {interaction.guild.name}")

        else:
            # Enhanced broke message with multiple variations
            broke_messages = [
                f"You're too broke to use the magic 8ball! <:OhGodMan:1200262332392157184>",
                f"Insufficient funds! The 8-ball requires {cost} Credits, but you only have {guild_user.currency}! 💸",
                f"The magic 8-ball says: 'Pay me first!' You need {cost - guild_user.currency} more Credits! 💰",
                f"Error: Wallet.exe has stopped working! You need {cost} Credits! 🚫",
                f"The spirits demand payment! {cost} Credits required! 👻💰"
            ]

            broke_response = random.choice(broke_messages)

            embed = discord.Embed(
                title="💸 Insufficient Credits",
                description=broke_response,
                color=discord.Color.red()
            )
            embed.set_footer(text=f"You have {guild_user.currency} Credits • Need {cost} Credits")

            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(
                f"{interaction.user.name} tried to use /8ball but had insufficient credits ({guild_user.currency}/{cost}) in guild {interaction.guild.name}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Eightball(bot))