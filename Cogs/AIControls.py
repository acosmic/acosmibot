import discord
from discord.ext import commands
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from AI.OpenAIClient import OpenAIClient
from logger import AppLogger
from Dao.GuildDao import GuildDao
import asyncio

logger = AppLogger(__name__).get_logger()


class AIControls(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.chatgpt = OpenAIClient()
        self.guild_dao = GuildDao()

        # Conversation history storage (in-memory)
        # Format: {guild_id: {channel_id: [(user_name, message, is_bot, timestamp), ...]}}
        self.conversation_history = {}

        # Configuration
        self.max_history_per_channel = 15  # Keep last 15 messages for context
        self.history_cleanup_hours = 6  # Clear history older than 6 hours

        # Start cleanup task
        self.cleanup_task = self.bot.loop.create_task(self.cleanup_old_conversations())

    def cog_unload(self):
        """Clean up when cog is unloaded"""
        if hasattr(self, 'cleanup_task'):
            self.cleanup_task.cancel()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle AI interactions when bot is mentioned"""
        # Ignore bot messages and DMs
        if message.author.bot or not message.guild:
            return

        # Check if bot is mentioned
        if self.bot.user in message.mentions:
            await self.handle_ai_interaction(message)

    async def handle_ai_interaction(self, message: discord.Message):
        """Handle AI interactions when bot is mentioned"""
        try:
            # Check if AI is enabled for this guild (this is handled in the OpenAI client)
            guild_settings = self.guild_dao.get_ai_settings(message.guild.id)
            if not guild_settings or not guild_settings.get('ai_enabled', False):
                embed = discord.Embed(
                    title="🤖 AI Disabled",
                    description="AI features are currently disabled for this server. An administrator can enable them using `/ai enable`.",
                    color=discord.Color.orange()
                )
                await message.channel.send(embed=embed)
                return

            # Remove the mention and strip the message
            prompt = message.content
            for mention in message.mentions:
                prompt = prompt.replace(f'<@{mention.id}>', '').replace(f'<@!{mention.id}>', '')
            prompt = prompt.strip()

            if not prompt:
                embed = discord.Embed(
                    title="🤖 Acosmibot",
                    description="Hey there! You mentioned me but didn't ask anything. How can I help you?",
                    color=discord.Color.blue()
                )
                await message.channel.send(embed=embed)
                return

            # Get conversation history for context
            conversation_history = self.get_conversation_history(message.guild.id, message.channel.id)

            # Show typing indicator
            async with message.channel.typing():
                response = await self.chatgpt.get_chatgpt_response(
                    prompt=prompt,
                    user_name=message.author.display_name,
                    guild_id=message.guild.id,
                    conversation_history=conversation_history
                )

            # Store user message in history
            self.add_to_conversation_history(
                message.guild.id,
                message.channel.id,
                message.author.display_name,
                prompt,
                is_bot=False
            )

            # Split and send responses
            response_messages = self.split_response(response)

            for i, res in enumerate(response_messages):
                if i == 0:
                    # Reply to the original message for the first response
                    sent_message = await message.reply(res, mention_author=False)
                else:
                    # Send subsequent messages normally
                    sent_message = await message.channel.send(res)

                # Add bot response to conversation history
                if i == len(response_messages) - 1:  # Only store the last message to avoid duplicates
                    self.add_to_conversation_history(
                        message.guild.id,
                        message.channel.id,
                        self.bot.user.display_name,
                        response,
                        is_bot=True
                    )

        except Exception as e:
            logger.error(f'AI Error in {message.guild.name}: {e}')

            error_embed = discord.Embed(
                title="🚫 Error",
                description="I'm sorry, I encountered an error processing your request. Please try again later.",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)

    def split_response(self, response: str, max_length: int = 2000) -> List[str]:
        """Split long responses into multiple messages"""
        if len(response) <= max_length:
            return [response]

        response_list = []
        while len(response) > max_length:
            # Try to split at a sentence or word boundary
            split_pos = max_length

            # Look for sentence ending
            sentence_end = response.rfind('.', 0, max_length)
            if sentence_end > max_length * 0.7:  # If sentence end is reasonably close
                split_pos = sentence_end + 1
            else:
                # Look for word boundary
                word_boundary = response.rfind(' ', 0, max_length)
                if word_boundary > max_length * 0.8:  # If word boundary is reasonably close
                    split_pos = word_boundary

            response_list.append(response[:split_pos].strip())
            response = response[split_pos:].strip()

        if response:  # Add remaining text
            response_list.append(response)

        return response_list

    def get_conversation_history(self, guild_id: int, channel_id: int) -> List[Dict]:
        """Get conversation history for a specific channel"""
        if guild_id not in self.conversation_history:
            return []

        if channel_id not in self.conversation_history[guild_id]:
            return []

        history = self.conversation_history[guild_id][channel_id]

        # Convert to format expected by OpenAI client
        formatted_history = []
        for user_name, message, is_bot, timestamp in history:
            if is_bot:
                formatted_history.append({"role": "assistant", "content": message})
            else:
                formatted_history.append({"role": "user", "content": f"{user_name}: {message}"})

        return formatted_history

    def add_to_conversation_history(self, guild_id: int, channel_id: int, user_name: str, message: str, is_bot: bool):
        """Add a message to conversation history"""
        if guild_id not in self.conversation_history:
            self.conversation_history[guild_id] = {}

        if channel_id not in self.conversation_history[guild_id]:
            self.conversation_history[guild_id][channel_id] = []

        # Add message with timestamp
        self.conversation_history[guild_id][channel_id].append((
            user_name,
            message,
            is_bot,
            datetime.now()
        ))

        # Keep only recent messages
        if len(self.conversation_history[guild_id][channel_id]) > self.max_history_per_channel:
            self.conversation_history[guild_id][channel_id] = \
                self.conversation_history[guild_id][channel_id][-self.max_history_per_channel:]

    async def cleanup_old_conversations(self):
        """Periodically clean up old conversation history"""
        while not self.bot.is_closed():
            try:
                cutoff_time = datetime.now() - timedelta(hours=self.history_cleanup_hours)

                for guild_id in list(self.conversation_history.keys()):
                    for channel_id in list(self.conversation_history[guild_id].keys()):
                        # Filter out old messages
                        self.conversation_history[guild_id][channel_id] = [
                            msg for msg in self.conversation_history[guild_id][channel_id]
                            if msg[3] > cutoff_time  # msg[3] is timestamp
                        ]

                        # Remove empty channel histories
                        if not self.conversation_history[guild_id][channel_id]:
                            del self.conversation_history[guild_id][channel_id]

                    # Remove empty guild histories
                    if not self.conversation_history[guild_id]:
                        del self.conversation_history[guild_id]

                logger.info("Cleaned up old conversation history")

            except Exception as e:
                logger.error(f"Error cleaning up conversation history: {e}")

            # Wait 1 hour before next cleanup
            await asyncio.sleep(3600)

    # Slash Commands for AI Management
    @discord.app_commands.command(name="ai-status", description="Check AI status for the server")
    @discord.app_commands.default_permissions(manage_guild=True)
    async def ai_status_slash(self, interaction: discord.Interaction):
        """Check AI status for the server"""
        settings = self.guild_dao.get_ai_settings(interaction.guild.id)

        if not settings:
            embed = discord.Embed(
                title="🤖 AI Status",
                description="AI settings not found for this server.",
                color=discord.Color.red()
            )
        else:
            status_color = discord.Color.green() if settings.get('ai_enabled') else discord.Color.red()
            status_text = "Enabled" if settings.get('ai_enabled') else "Disabled"

            embed = discord.Embed(
                title="🤖 AI Status",
                color=status_color
            )
            embed.add_field(name="Status", value=status_text, inline=True)
            embed.add_field(name="Temperature", value=f"{settings.get('ai_temperature', 1.0)}", inline=True)

            personality = settings.get('ai_personality_traits', {})
            if personality:
                personality_text = "\n".join([f"{k.replace('_', ' ').title()}: {v.title()}"
                                              for k, v in personality.items()])
                embed.add_field(name="Personality", value=personality_text, inline=False)

        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="ai-enable", description="Enable AI features for this server")
    @discord.app_commands.default_permissions(manage_guild=True)
    async def ai_enable_slash(self, interaction: discord.Interaction):
        """Enable AI features"""
        success = self.chatgpt.update_guild_ai_settings(interaction.guild.id, ai_enabled=True)

        if success:
            embed = discord.Embed(
                title="🤖 AI Enabled",
                description="AI features have been enabled for this server! Mention me to start chatting.",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="🚫 Error",
                description="Failed to enable AI features. Please try again.",
                color=discord.Color.red()
            )

        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="ai-disable", description="Disable AI features for this server")
    @discord.app_commands.default_permissions(manage_guild=True)
    async def ai_disable_slash(self, interaction: discord.Interaction):
        """Disable AI features"""
        success = self.chatgpt.update_guild_ai_settings(interaction.guild.id, ai_enabled=False)

        if success:
            embed = discord.Embed(
                title="🤖 AI Disabled",
                description="AI features have been disabled for this server.",
                color=discord.Color.orange()
            )
        else:
            embed = discord.Embed(
                title="🚫 Error",
                description="Failed to disable AI features. Please try again.",
                color=discord.Color.red()
            )

        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="ai-temperature", description="Set AI creativity level (0.1-2.0)")
    @discord.app_commands.describe(temperature="AI creativity level between 0.1 (focused) and 2.0 (creative)")
    @discord.app_commands.default_permissions(manage_guild=True)
    async def ai_temperature_slash(self, interaction: discord.Interaction, temperature: float):
        """Set AI creativity level (0.1-2.0)"""
        if not 0.1 <= temperature <= 2.0:
            embed = discord.Embed(
                title="🚫 Invalid Temperature",
                description="Temperature must be between 0.1 and 2.0.\n"
                            "• Lower values (0.1-0.7): More focused and deterministic\n"
                            "• Higher values (1.3-2.0): More creative and random",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
            return

        success = self.chatgpt.update_guild_ai_settings(interaction.guild.id, ai_temperature=temperature)

        if success:
            embed = discord.Embed(
                title="🌡️ Temperature Updated",
                description=f"AI creativity level set to {temperature}",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="🚫 Error",
                description="Failed to update temperature setting.",
                color=discord.Color.red()
            )

        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="ai-clear", description="Clear conversation history for this server")
    @discord.app_commands.default_permissions(manage_guild=True)
    async def ai_clear_slash(self, interaction: discord.Interaction):
        """Clear conversation history for this server"""
        if interaction.guild.id in self.conversation_history:
            del self.conversation_history[interaction.guild.id]

        embed = discord.Embed(
            title="🧹 History Cleared",
            description="Conversation history has been cleared for this server.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(AIControls(bot))