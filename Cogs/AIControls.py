import discord
from discord.ext import commands
from discord import app_commands
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from AI.OpenAIClient import OpenAIClient
from logger import AppLogger
from Dao.GuildDao import GuildDao
from Dao.AIImageDao import AIImageDao
from utils.premium_checker import PremiumChecker
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

        # Mention rate limiting (prevents spam mentions)
        # Format: {user_id:guild_id: datetime}
        self.mention_cooldowns = {}
        self.mention_cooldown_seconds = 3  # Cooldown between mentions

        # Configuration
        self.max_history_per_channel = 15  # Keep last 15 messages for context
        self.history_cleanup_hours = 6  # Clear history older than 6 hours

        # Start cleanup task
        self.cleanup_task = self.bot.loop.create_task(self.cleanup_old_conversations())

    def cog_unload(self):
        """Clean up when cog is unloaded"""
        if hasattr(self, 'cleanup_task'):
            self.cleanup_task.cancel()

    def is_on_mention_cooldown(self, user_id: int, guild_id: int) -> bool:
        """Check if user is on mention cooldown"""
        now = datetime.now()

        # Auto-cleanup: remove expired cooldown entries to prevent memory leak
        expired_keys = [
            key for key, timestamp in self.mention_cooldowns.items()
            if (now - timestamp).total_seconds() > self.mention_cooldown_seconds
        ]
        for key in expired_keys:
            del self.mention_cooldowns[key]

        # Check current user's cooldown
        cooldown_key = f"{user_id}:{guild_id}"

        if cooldown_key not in self.mention_cooldowns:
            return False

        last_mention_time = self.mention_cooldowns[cooldown_key]
        time_since_last = (now - last_mention_time).total_seconds()

        return time_since_last < self.mention_cooldown_seconds

    def set_mention_cooldown(self, user_id: int, guild_id: int):
        """Set user on mention cooldown"""
        cooldown_key = f"{user_id}:{guild_id}"
        self.mention_cooldowns[cooldown_key] = datetime.now()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle AI interactions when bot is mentioned"""
        # Ignore bot messages and DMs
        if message.author.bot or not message.guild:
            return

        # Check if bot is mentioned
        if self.bot.user in message.mentions:
            # Check mention cooldown to prevent spam
            if self.is_on_mention_cooldown(message.author.id, message.guild.id):
                # Silently ignore spam mentions
                return

            # Set cooldown for this user
            self.set_mention_cooldown(message.author.id, message.guild.id)

            # Process the mention
            await self.handle_ai_interaction(message)

    async def handle_ai_interaction(self, message: discord.Message):
        """Handle AI interactions using the new settings structure"""
        try:
            # Get AI settings from new JSON structure
            guild_dao = GuildDao()
            ai_settings = guild_dao.get_ai_settings_from_json(message.guild.id)

            # Check if AI is allowed in this channel
            if not self.chatgpt.is_channel_allowed(message.guild.id, message.channel.id):
                # Silently ignore if channel is restricted
                return

            # if not ai_settings or not ai_settings.get('enabled', False):
            #     embed = discord.Embed(
            #         title="🤖 AI Disabled",
            #         description="AI features are currently disabled for this server. An administrator can enable them using `/ai enable`.",
            #         color=discord.Color.orange()
            #     )
            #     await message.channel.send(embed=embed)
            #     return

            if not ai_settings or not ai_settings.get('enabled', False):
                try:
                    await message.author.send(
                        f"🤖 **AI Disabled in {message.guild.name}** - AI features are currently disabled for this server. Ask an administrator to enable AI features via the website."
                    )
                except discord.Forbidden:
                    # User has DMs disabled, silently ignore
                    pass
                return

            # Check daily limit
            can_use, current_usage, daily_limit = self.chatgpt.check_daily_limit(message.guild.id)
            if not can_use:
                embed = discord.Embed(
                    title="🚫 Daily Limit Reached",
                    description=f"This server has reached its daily AI limit ({current_usage}/{daily_limit}).\nTry again tomorrow!",
                    color=discord.Color.red()
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
                    title="",
                    description="Hey there! You mentioned me but didn't ask anything. How can I help you?",
                    color=discord.Color.blue()
                )
                await message.channel.send(embed=embed)
                return

            # Show typing indicator
            async with message.channel.typing():
                # Get conversation history
                conversation_history = self.get_conversation_history(message.guild.id, message.channel.id)

                # Generate AI response using new method
                ai_response = await self.chatgpt.generate_chat_response(
                    prompt=prompt,
                    user_name=message.author.display_name,
                    guild_id=message.guild.id,
                    user_id=message.author.id,
                    conversation_history=conversation_history
                )

                # Add user message to history
                self.add_to_conversation_history(
                    message.guild.id,
                    message.channel.id,
                    message.author.display_name,
                    prompt,
                    False
                )

                # Split and send response if needed
                response_parts = self.split_response(ai_response)
                for part in response_parts:
                    sent_message = await message.channel.send(part)

                    # Add AI response to history
                    self.add_to_conversation_history(
                        message.guild.id,
                        message.channel.id,
                        self.bot.user.display_name,
                        part,
                        True
                    )

        except Exception as e:
            logger.error(f"Error in AI interaction: {e}")
            error_embed = discord.Embed(
                title="🚫 Error",
                description="I encountered an error processing your request. Please try again later.",
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


    @discord.app_commands.command(name="ai-status", description="Check AI status and usage for the server")
    @discord.app_commands.default_permissions(manage_guild=True)
    async def ai_status(self, interaction: discord.Interaction):
        """Check AI status with comprehensive usage tracking for all features"""
        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        guild_dao = GuildDao()
        ai_settings = guild_dao.get_ai_settings_from_json(interaction.guild.id)

        if not ai_settings:
            embed = discord.Embed(
                title="🤖 AI Status",
                description="AI settings not configured for this server.",
                color=discord.Color.red()
            )
        else:
            status_color = discord.Color.green() if ai_settings.get('enabled') else discord.Color.red()
            status_text = "✅ Enabled" if ai_settings.get('enabled') else "❌ Disabled"

            # Get tier and limits
            tier = PremiumChecker.get_guild_tier(interaction.guild.id)
            tier_limits = PremiumChecker.TIER_LIMITS[tier]

            # Get usage data from database
            from Dao.AIUsageDao import AIUsageDao
            with AIUsageDao() as usage_dao:
                chat_usage = usage_dao.get_daily_usage_count(str(interaction.guild.id), 'chat')
                gen_usage = usage_dao.get_monthly_usage(str(interaction.guild.id), 'image_generation')
                analysis_usage = usage_dao.get_monthly_usage(str(interaction.guild.id), 'image_analysis')

            chat_limit = tier_limits['ai_daily_limit']
            gen_limit = tier_limits['image_monthly_limit']
            analysis_limit = tier_limits['image_analysis_monthly_limit']

            embed = discord.Embed(
                title=f"🤖 AI Status for {interaction.guild.name}",
                description=f"**Status:** {status_text} | **Model:** {ai_settings.get('model', 'gpt-4o-mini')}\n**Tier:** {PremiumChecker.get_tier_display_name(tier)}",
                color=status_color
            )

            # Chat usage (daily)
            chat_bar = self._create_progress_bar(chat_usage, chat_limit)
            embed.add_field(
                name="💬 Chat Messages (Daily)",
                value=f"{chat_bar}\n{chat_usage}/{chat_limit} messages used today",
                inline=False
            )

            # Image generation usage (monthly)
            if tier_limits['image_generation']:
                gen_bar = self._create_progress_bar(gen_usage, gen_limit)
                embed.add_field(
                    name="🎨 Image Generation (Monthly)",
                    value=f"{gen_bar}\n{gen_usage}/{gen_limit} images generated this month",
                    inline=False
                )
            else:
                embed.add_field(
                    name="🎨 Image Generation (Monthly)",
                    value="🔒 Premium feature - Upgrade to access",
                    inline=False
                )

            # Image analysis usage (monthly)
            if tier_limits['image_analysis']:
                analysis_bar = self._create_progress_bar(analysis_usage, analysis_limit)
                embed.add_field(
                    name="🔍 Image Analysis (Monthly)",
                    value=f"{analysis_bar}\n{analysis_usage}/{analysis_limit} analyses performed this month",
                    inline=False
                )
            else:
                embed.add_field(
                    name="🔍 Image Analysis (Monthly)",
                    value="🔒 Premium feature - Upgrade to access",
                    inline=False
                )

            # Custom instructions
            if ai_settings.get('instructions'):
                instructions_preview = ai_settings['instructions'][:100] + "..." if len(ai_settings['instructions']) > 100 else ai_settings['instructions']
                embed.add_field(name="📝 Custom Instructions", value=instructions_preview, inline=False)

            embed.set_footer(text="💡 Limits reset daily for chat, monthly for images | Usage tracked in database")

        await interaction.response.send_message(embed=embed)

    def _create_progress_bar(self, current: int, maximum: int, length: int = 10) -> str:
        """Create a visual progress bar"""
        if maximum == 0:
            return "▱" * length
        percentage = min(current / maximum, 1.0)
        filled = int(length * percentage)
        empty = length - filled
        return "▰" * filled + "▱" * empty

    @discord.app_commands.command(name="ai-enable", description="Enable AI features for this server")
    @discord.app_commands.default_permissions(manage_guild=True)
    async def ai_enable(self, interaction: discord.Interaction):
        """Enable AI features using new settings structure"""
        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return
        success = self.chatgpt.update_guild_ai_settings(interaction.guild.id, enabled=True)

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
    async def ai_disable(self, interaction: discord.Interaction):
        """Disable AI features using new settings structure"""
        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return
        success = self.chatgpt.update_guild_ai_settings(interaction.guild.id, enabled=False)

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

    # @discord.app_commands.command(name="ai-model", description="Set the AI model for this server")
    # @discord.app_commands.describe(model="AI model to use (gpt-4o-mini, gpt-4o, gpt-4-turbo, etc.)")
    # @discord.app_commands.default_permissions(manage_guild=True)
    # async def ai_model(self, interaction: discord.Interaction, model: str):
    #     """Set AI model using new settings structure"""
    #     # Only work in guilds
    #     if not interaction.guild:
    #         await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
    #         return
    #     # List of valid models
    #     valid_models = ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo']
    #
    #     if model not in valid_models:
    #         embed = discord.Embed(
    #             title="🚫 Invalid Model",
    #             description=f"Invalid model. Valid options: {', '.join(valid_models)}",
    #             color=discord.Color.red()
    #         )
    #         await interaction.response.send_message(embed=embed)
    #         return
    #
    #     success = self.chatgpt.update_guild_ai_settings(interaction.guild.id, model=model)
    #
    #     if success:
    #         embed = discord.Embed(
    #             title="🤖 Model Updated",
    #             description=f"AI model set to {model}",
    #             color=discord.Color.green()
    #         )
    #     else:
    #         embed = discord.Embed(
    #             title="🚫 Error",
    #             description="Failed to update AI model.",
    #             color=discord.Color.red()
    #         )
    #
    #     await interaction.response.send_message(embed=embed)

    # @discord.app_commands.command(name="ai-limit", description="Set daily AI usage limit for this server")
    # @discord.app_commands.describe(
    #     limit="Daily usage limit (1-100)"
    # )
    # @discord.app_commands.default_permissions(manage_guild=True)
    # async def ai_limit(self, interaction: discord.Interaction, limit: int):
    #     """Set daily AI limit using new settings structure"""
    #     # Only work in guilds
    #     if not interaction.guild:
    #         await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
    #         return
    #     if not 1 <= limit <= 100:
    #         embed = discord.Embed(
    #             title="🚫 Invalid Limit",
    #             description="Daily limit must be between 1 and 100.",
    #             color=discord.Color.red()
    #         )
    #         await interaction.response.send_message(embed=embed)
    #         return
    #
    #     success = self.chatgpt.update_guild_ai_settings(interaction.guild.id, daily_limit=limit)
    #
    #     if success:
    #         embed = discord.Embed(
    #             title="📊 Limit Updated",
    #             description=f"Daily AI usage limit set to {limit}",
    #             color=discord.Color.green()
    #         )
    #     else:
    #         embed = discord.Embed(
    #             title="🚫 Error",
    #             description="Failed to update daily limit.",
    #             color=discord.Color.red()
    #         )
    #
    #     await interaction.response.send_message(embed=embed)

    # @discord.app_commands.command(name="ai-instructions", description="Set custom instructions for the AI")
    # @discord.app_commands.describe(
    #     instructions="Custom instructions for AI behavior (max 500 characters)"
    # )
    # @discord.app_commands.default_permissions(manage_guild=True)
    # async def ai_instructions(self, interaction: discord.Interaction, instructions: str):
    #     """Set AI instructions using new settings structure"""
    #     # Only work in guilds
    #     if not interaction.guild:
    #         await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
    #         return
    #     if len(instructions) > 500:
    #         embed = discord.Embed(
    #             title="🚫 Instructions Too Long",
    #             description="Instructions must be 500 characters or less.",
    #             color=discord.Color.red()
    #         )
    #         await interaction.response.send_message(embed=embed)
    #         return
    #
    #     success = self.chatgpt.update_guild_ai_settings(interaction.guild.id, instructions=instructions)
    #
    #     if success:
    #         embed = discord.Embed(
    #             title="📝 Instructions Updated",
    #             description=f"Custom instructions set: {instructions[:100]}..." if len(
    #                 instructions) > 100 else f"Custom instructions set: {instructions}",
    #             color=discord.Color.green()
    #         )
    #     else:
    #         embed = discord.Embed(
    #             title="🚫 Error",
    #             description="Failed to update AI instructions.",
    #             color=discord.Color.red()
    #         )
    #
    #     await interaction.response.send_message(embed=embed)


    @discord.app_commands.command(name="ai-clear", description="Clear conversation history for this server")
    @discord.app_commands.default_permissions(manage_guild=True)
    async def ai_clear_slash(self, interaction: discord.Interaction):
        """Clear conversation history for this server"""
        # Only work in guilds
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return
        if interaction.guild.id in self.conversation_history:
            del self.conversation_history[interaction.guild.id]

        embed = discord.Embed(
            title="🧹 History Cleared",
            description="Conversation history has been cleared for this server.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="generate-image", description="Generate an image using AI (DALL-E 3)")
    @app_commands.describe(
        prompt="Description of the image you want to generate",
        size="Image size (default: 1024x1024)",
        quality="Image quality (default: standard)"
    )
    @app_commands.choices(size=[
        app_commands.Choice(name="Square (1024x1024)", value="1024x1024"),
        app_commands.Choice(name="Landscape (1792x1024)", value="1792x1024"),
        app_commands.Choice(name="Portrait (1024x1792)", value="1024x1792")
    ])
    @app_commands.choices(quality=[
        app_commands.Choice(name="Standard", value="standard"),
        app_commands.Choice(name="HD (High Detail)", value="hd")
    ])
    async def generate_image(
        self,
        interaction: discord.Interaction,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard"
    ):
        """Generate an image using DALL-E 3 (Premium feature)"""
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        # Defer response as image generation takes time
        await interaction.response.defer()

        try:
            # Check premium access
            can_generate, error_msg = PremiumChecker.can_generate_images(interaction.guild.id)
            if not can_generate:
                embed = discord.Embed(
                    title="🔒 Premium Feature",
                    description=error_msg,
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Check monthly limit
            with AIImageDao() as image_dao:
                current_month_count = image_dao.count_monthly_images(
                    str(interaction.guild.id),
                    type='generation'
                )

            can_generate, limit_msg = PremiumChecker.check_image_generation_limit(
                interaction.guild.id,
                current_month_count
            )
            if not can_generate:
                monthly_limit = PremiumChecker.get_image_monthly_limit(interaction.guild.id)
                embed = discord.Embed(
                    title="🚫 Monthly Limit Reached",
                    description=limit_msg,
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="Usage",
                    value=f"{current_month_count}/{monthly_limit} images this month",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Generate image
            success, image_url, revised_prompt = await self.chatgpt.generate_image(
                guild_id=str(interaction.guild.id),
                user_id=str(interaction.user.id),
                prompt=prompt,
                size=size,
                quality=quality
            )

            if success:
                monthly_limit = PremiumChecker.get_image_monthly_limit(interaction.guild.id)

                embed = discord.Embed(
                    title="🎨 Image Generated",
                    description=f"**Original Prompt:**\n{prompt}",
                    color=discord.Color.green()
                )
                embed.set_image(url=image_url)
                embed.add_field(
                    name="Size",
                    value=size,
                    inline=True
                )
                embed.add_field(
                    name="Quality",
                    value=quality.upper(),
                    inline=True
                )
                embed.add_field(
                    name="Usage",
                    value=f"{current_month_count + 1}/{monthly_limit} this month",
                    inline=True
                )

                if revised_prompt and revised_prompt != prompt:
                    embed.add_field(
                        name="✨ DALL-E Revised Prompt",
                        value=revised_prompt[:1024],  # Discord field limit
                        inline=False
                    )

                embed.set_footer(text=f"Requested by {interaction.user.display_name}")
                await interaction.followup.send(embed=embed)
            else:
                # Error occurred
                embed = discord.Embed(
                    title="❌ Generation Failed",
                    description=revised_prompt or "Failed to generate image",  # error message is in revised_prompt
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in generate_image command: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Error",
                description="An unexpected error occurred while generating the image.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="analyze-image", description="Analyze an image using AI (GPT-4 Vision)")
    @app_commands.describe(
        image_url="URL of the image to analyze (or attach an image)",
        question="What would you like to know about the image?"
    )
    async def analyze_image(
        self,
        interaction: discord.Interaction,
        image_url: str = None,
        question: str = "What's in this image? Describe it in detail."
    ):
        """Analyze an image using GPT-4 Vision (Premium feature)"""
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return

        # Defer response as image analysis takes time
        await interaction.response.defer()

        try:
            # Check premium access
            can_analyze, error_msg = PremiumChecker.can_analyze_images(interaction.guild.id)
            if not can_analyze:
                embed = discord.Embed(
                    title="🔒 Premium Feature",
                    description=error_msg,
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Check monthly usage limit
            from Dao.AIUsageDao import AIUsageDao
            with AIUsageDao() as usage_dao:
                current_month_count = usage_dao.get_monthly_usage(
                    str(interaction.guild.id),
                    'image_analysis'
                )

            can_analyze_limit, limit_msg = PremiumChecker.check_image_analysis_limit(
                interaction.guild.id,
                current_month_count
            )

            if not can_analyze_limit:
                embed = discord.Embed(
                    title="📊 Usage Limit Reached",
                    description=limit_msg,
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Check if image URL provided
            if not image_url:
                embed = discord.Embed(
                    title="❌ No Image Provided",
                    description="Please provide an image URL.\n\nExample: `/analyze-image image_url:https://example.com/image.jpg`",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Analyze image
            success, analysis, error = await self.chatgpt.analyze_image(
                guild_id=str(interaction.guild.id),
                user_id=str(interaction.user.id),
                image_url=image_url,
                question=question
            )

            if success:
                # Get updated usage after successful analysis
                tier = PremiumChecker.get_guild_tier(interaction.guild.id)
                monthly_limit = PremiumChecker.TIER_LIMITS[tier]['image_analysis_monthly_limit']

                embed = discord.Embed(
                    title="🔍 Image Analysis",
                    description=analysis[:4096],  # Discord embed description limit
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="Question",
                    value=question[:1024],
                    inline=False
                )
                embed.add_field(
                    name="📊 Monthly Usage",
                    value=f"{current_month_count + 1}/{monthly_limit} analyses used",
                    inline=False
                )
                embed.set_thumbnail(url=image_url)
                embed.set_footer(text=f"Analyzed by GPT-4 Vision • Requested by {interaction.user.display_name}")
                await interaction.followup.send(embed=embed)
            else:
                # Error occurred
                embed = discord.Embed(
                    title="❌ Analysis Failed",
                    description=error or "Failed to analyze image",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in analyze_image command: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Error",
                description="An unexpected error occurred while analyzing the image.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AIControls(bot))