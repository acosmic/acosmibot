from builtins import bool

import httpx
import openai
import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
from logger import AppLogger
from Dao.GuildDao import GuildDao
from Dao.AIImageDao import AIImageDao
from Entities.AIImage import AIImage
from datetime import datetime, time, timedelta
from typing import Dict, Any, Optional, List, Tuple

# Add utils to path for premium checker
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from utils.premium_checker import PremiumChecker

logger = AppLogger(__name__).get_logger()

load_dotenv()


class OpenAIClient:
    def __init__(self, api_key=None):
        # Initialize OpenAI client
        self.client = openai.OpenAI(
            api_key=api_key or os.getenv('OPENAI_KEY'),
            timeout=60.0,  # 60 second timeout
            max_retries=3,
            http_client=httpx.Client(
                timeout=httpx.Timeout(30.0, read=60.0),  # 30s connect, 60s read
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=2)
            )
        )

        inappropriate_words_str = os.getenv('INAPPROPRIATE_WORDS')

        if inappropriate_words_str:
            self.inappropriate_words = json.loads(inappropriate_words_str)
        else:
            self.inappropriate_words = []

        # Configuration
        self.max_conversation_length = 20  # Keep last 20 messages for context
        self.max_response_length = 1500

        # Add this to track daily usage

    def get_model_params(self, model: str) -> dict:
        """
        Get the correct parameters for different OpenAI models.

        Args:
            model (str): The model name

        Returns:
            dict: Parameters dictionary with correct token limit parameter
        """
        # Models that use max_completion_tokens (newer models)
        new_models = {
            'gpt-5-nano',
            'gpt-5-mini',
            'gpt-5',
            'gpt-4o-mini',
            'gpt-4o',
            'gpt-4o-2024-08-06',
            'gpt-4o-2024-05-13',
            'o1-preview',
            'o1-mini'
        }

        base_params = {
            'temperature': 1.0,
            'top_p': 1,
            'frequency_penalty': 0,
            'presence_penalty': 0
        }

        if model in new_models:
            base_params['max_completion_tokens'] = self.max_response_length
        else:
            base_params['max_tokens'] = self.max_response_length

        return base_params

    def get_guild_ai_settings(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """
        Get AI settings from the new JSON settings structure.

        Args:
            guild_id (int): Guild ID

        Returns:
            dict: AI settings or None
        """
        guild_dao = GuildDao()
        try:
            return guild_dao.get_ai_settings_from_json(guild_id)
        except Exception as e:
            logger.error(f"Error getting AI settings for guild {guild_id}: {e}")
            return None

    def is_channel_allowed(self, guild_id: int, channel_id: int) -> bool:
        """
        Check if AI is allowed to respond in the specified channel based on guild settings.

        Args:
            guild_id (int): Guild ID
            channel_id (int): Channel ID to check

        Returns:
            bool: True if AI can respond in this channel, False otherwise
        """
        ai_settings = self.get_guild_ai_settings(guild_id)
        if not ai_settings:
            return False

        channel_mode = ai_settings.get('channel_mode', 'all')
        channel_id_str = str(channel_id)

        if channel_mode == 'all':
            # AI works in all channels
            return True
        elif channel_mode == 'specific':
            # AI only works in specified channels
            allowed_channels = ai_settings.get('allowed_channels', [])
            return channel_id_str in allowed_channels
        elif channel_mode == 'exclude':
            # AI works in all channels except specified
            excluded_channels = ai_settings.get('excluded_channels', [])
            return channel_id_str not in excluded_channels
        else:
            # Default to all channels if mode is unknown
            return True

    def update_guild_ai_settings(self, guild_id: int, **kwargs) -> bool:
        """
        Update AI settings in the new JSON settings structure.

        Args:
            guild_id (int): Guild ID
            **kwargs: AI settings to update

        Returns:
            bool: Success status
        """
        guild_dao = GuildDao()
        try:
            return guild_dao.update_ai_settings_in_json(guild_id, kwargs)
        except Exception as e:
            logger.error(f"Error updating AI settings for guild {guild_id}: {e}")
            return False

    def check_daily_limit(self, guild_id: int) -> tuple[bool, int, int]:
        """
        Check if the guild has exceeded their daily AI usage limit.

        Args:
            guild_id (int): Guild ID

        Returns:
            tuple[bool, int, int]: (can_use, current_usage, daily_limit)
        """
        from Dao.AIUsageDao import AIUsageDao

        # Use tier-based daily limit (Free: 20, Premium: 100)
        daily_limit = PremiumChecker.get_ai_daily_limit(guild_id)

        # Get current usage from database
        with AIUsageDao() as dao:
            current_usage = dao.get_daily_usage_count(str(guild_id), 'chat')

        can_use = current_usage < daily_limit
        return can_use, current_usage, daily_limit

    async def generate_chat_response(self, prompt: str, user_name: str, guild_id: int,
                                         user_id: int, conversation_history: Optional[List[Dict]] = None) -> str:
        """
        Generate a chat response using the new settings structure with updated API parameters.

        Args:
            prompt (str): User's message
            user_name (str): Discord username
            guild_id (int): Discord guild ID
            user_id (int): Discord user ID
            conversation_history (Optional[List[Dict]]): Previous conversation messages

        Returns:
            str: AI response
        """
        try:
            # Get AI settings from new JSON structure
            ai_settings = self.get_guild_ai_settings(guild_id)
            if not ai_settings:
                return "AI settings not found for this server."

            # Check if AI is enabled
            if not ai_settings.get('enabled', False):
                return "AI features are currently disabled for this server."

            # Check daily limit
            can_use, current_usage, daily_limit = self.check_daily_limit(guild_id)
            if not can_use:
                return f"Daily AI limit reached ({current_usage}/{daily_limit}). Try again tomorrow!"

            # Build conversation messages using new settings
            messages = self._build_conversation_messages(
                prompt=prompt,
                user_name=user_name,
                ai_settings=ai_settings,
                conversation_history=conversation_history or []
            )

            # Get model from settings (default to gpt-4o-mini if not specified)
            model = ai_settings.get('model', 'gpt-4o-mini')

            # Validate model access based on subscription tier
            can_use_model, error_msg = PremiumChecker.can_use_ai_model(guild_id, model)
            if not can_use_model:
                # Fallback to free tier model
                logger.warning(f"Guild {guild_id} attempted to use {model} without premium. Falling back to gpt-3.5-turbo")
                model = 'gpt-3.5-turbo'

            # Get correct parameters for this model
            model_params = self.get_model_params(model)

            logger.info(f"Making chat completion request for guild {guild_id} with model: {model}")

            # Make API call using Chat Completions with correct parameters
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                **model_params  # Spread the correct parameters
            )

            # Extract response
            if response.choices and len(response.choices) > 0:
                ai_response = response.choices[0].message.content.strip()

                # Record usage in database
                from Dao.AIUsageDao import AIUsageDao
                tokens_used = 0
                cost_usd = 0.0

                if hasattr(response, 'usage'):
                    tokens_used = response.usage.total_tokens
                    # Estimate cost based on model (rough estimates)
                    if 'gpt-4' in model:
                        cost_usd = (response.usage.prompt_tokens * 0.00003 + response.usage.completion_tokens * 0.00006)
                    else:  # gpt-3.5-turbo
                        cost_usd = (response.usage.prompt_tokens * 0.0000015 + response.usage.completion_tokens * 0.000002)

                    logger.info(f"Token usage - Prompt: {response.usage.prompt_tokens}, "
                                f"Completion: {response.usage.completion_tokens}, "
                                f"Total: {response.usage.total_tokens}, Cost: ${cost_usd:.6f}")
                    logger.info(f"Daily usage: {current_usage + 1}/{daily_limit}")

                # Record in database
                with AIUsageDao() as dao:
                    dao.record_usage(
                        guild_id=str(guild_id),
                        user_id=str(user_id),
                        usage_type='chat',
                        model=model,
                        tokens_used=tokens_used,
                        cost_usd=cost_usd
                    )

                return ai_response
            else:
                logger.warning("No response choices returned from OpenAI")
                return "I'm sorry, I didn't generate a response."

        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            return "I'm currently experiencing high demand. Please try again in a moment."

        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return "I'm sorry, I encountered a technical issue. Please try again."

        except Exception as e:
            logger.error(f'OpenAI Error: {e}')
            return "I'm sorry, I couldn't process your request."

    def _build_conversation_messages(self, prompt: str, user_name: str, ai_settings: Dict[str, Any],
                                         conversation_history: List[Dict]) -> List[Dict]:
        """
        Build the conversation messages array using new AI settings structure.

        Args:
            prompt (str): User's current message
            user_name (str): Discord username
            ai_settings (Dict[str, Any]): AI settings from JSON
            conversation_history (List[Dict]): Previous messages

        Returns:
            List[Dict]: Messages formatted for OpenAI API
        """
        messages = []

        # Build system message with custom instructions
        system_message = self._build_system_message(ai_settings, user_name)
        messages.append({"role": "system", "content": system_message})

        # Add conversation history (keep last 10 messages for context)
        recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
        messages.extend(recent_history)

        # Add current user message
        messages.append({"role": "user", "content": f"{user_name}: {prompt}"})

        return messages

    def _build_system_message(self, ai_settings: Dict[str, Any], user_name: str) -> str:
        """
        Build system message using new AI settings structure.

        Args:
            ai_settings (Dict[str, Any]): AI settings from JSON
            user_name (str): Discord username

        Returns:
            str: System message for AI
        """
        base_instruction = f"You are Acosmibot, an AI assistant in a Discord server. You're currently talking with {user_name}. "

        # Get custom instructions from settings
        custom_instructions = ai_settings.get('instructions', '')
        if custom_instructions:
            base_instruction += f"{custom_instructions} "
        else:
            # Default personality if no custom instructions
            base_instruction += "Be helpful, friendly, and engaging. "

        # Add standard guidelines
        guidelines = f"""
    Important guidelines:
    - Keep responses under {self.max_response_length} characters
    - Be conversational and engaging
    - Stay in character based on your instructions
    - Don't mention that you're an AI unless directly asked
    - If someone asks about commands or bot features, be helpful but stay in character"""

        return base_instruction + guidelines

    async def get_chatgpt_response(self, prompt: str, user_name: str, guild_id: int,
                                   conversation_history: List[Dict] = None) -> str:
        """
        Get ChatGPT response using Chat Completions API.

        Args:
            prompt (str): User's message
            user_name (str): Discord username
            guild_id (int): Discord guild ID
            conversation_history (List[Dict], optional): Previous messages for context

        Returns:
            str: AI response or error message
        """
        guild_dao = GuildDao()

        try:
            # Get guild and its AI models
            guild = guild_dao.get_guild(guild_id)

            if not guild:
                logger.error(f"Guild {guild_id} not found")
                return "Sorry, I couldn't access the server models."

            # Check if AI is enabled for this guild
            if not guild.ai_enabled:
                return "AI features are currently disabled for this server."

            # Build conversation messages
            messages = self._build_conversation_messages(
                prompt=prompt,
                user_name=user_name,
                guild=guild,
                conversation_history=conversation_history or []
            )

            logger.info(f"Making chat completion request for guild {guild_id} with temp: {guild.ai_temperature}")

            # Make API call using Chat Completions
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",  # Latest efficient model
                messages=messages,
                temperature=guild.ai_temperature,
                max_tokens=self.max_response_length,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )

            # Extract response
            if response.choices and len(response.choices) > 0:
                ai_response = response.choices[0].message.content.strip()

                # Log usage info
                if hasattr(response, 'usage'):
                    logger.info(f"Token usage - Prompt: {response.usage.prompt_tokens}, "
                                f"Completion: {response.usage.completion_tokens}, "
                                f"Total: {response.usage.total_tokens}")

                return ai_response
            else:
                logger.warning("No response choices returned from OpenAI")
                return "I'm sorry, I didn't generate a response."

        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            return "I'm currently experiencing high demand. Please try again in a moment."

        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return "I'm sorry, I encountered a technical issue. Please try again."

        except Exception as e:
            logger.error(f'OpenAI Error: {e}')
            return "I'm sorry, I couldn't process your request."

    # def _build_conversation_messages(self, prompt: str, user_name: str, guild, conversation_history: List[Dict]) -> \
    # List[Dict]:
    #     """
    #     Build the conversation messages array for the API call.
    #
    #     Args:
    #         prompt (str): Current user message
    #         user_name (str): Discord username
    #         guild: Guild object with AI models
    #         conversation_history (List[Dict]): Previous messages
    #
    #     Returns:
    #         List[Dict]: Formatted messages for API
    #     """
    #     messages = []
    #
    #     # System message with personality
    #     system_message = self._build_system_message(guild.ai_personality_traits or {}, user_name)
    #     messages.append({"role": "system", "content": system_message})
    #
    #     # Add conversation history (keep it manageable)
    #     if conversation_history:
    #         # Keep only recent messages to stay within token limits
    #         recent_history = conversation_history[-self.max_conversation_length:]
    #         for msg in recent_history:
    #             messages.append(msg)
    #
    #     # Add current user message
    #     messages.append({"role": "user", "content": f"{user_name}: {prompt}"})
    #
    #     return messages

    # def _build_system_message(self, personality_traits: Dict, user_name: str) -> str:
    #     """
    #     Build the system message based on guild's AI personality traits.
    #
    #     Args:
    #         personality_traits (Dict): Guild's personality models
    #         user_name (str): Discord username
    #
    #     Returns:
    #         str: System message
    #     """
    #     base_instruction = f"You are Acosmibot, an AI assistant in a Discord server. You're currently talking with {user_name}. "
    #
    #     # Build personality based on traits
    #     personality_parts = []
    #
    #     humor_level = personality_traits.get("humor_level", "medium")
    #     if humor_level == "high":
    #         personality_parts.append("very humorous and witty")
    #     elif humor_level == "medium":
    #         personality_parts.append("moderately humorous")
    #     elif humor_level == "low":
    #         personality_parts.append("occasionally humorous")
    #
    #     sarcasm_level = personality_traits.get("sarcasm_level", "medium")
    #     if sarcasm_level == "high":
    #         personality_parts.append("quite sarcastic")
    #     elif sarcasm_level == "medium":
    #         personality_parts.append("moderately sarcastic")
    #     elif sarcasm_level == "low":
    #         personality_parts.append("mildly sarcastic")
    #
    #     friendliness = personality_traits.get("friendliness", "high")
    #     if friendliness == "high":
    #         personality_parts.append("very friendly and welcoming")
    #     elif friendliness == "medium":
    #         personality_parts.append("friendly")
    #     elif friendliness == "low":
    #         personality_parts.append("cordial but reserved")
    #
    #     nerd_level = personality_traits.get("nerd_level", "high")
    #     if nerd_level == "high":
    #         personality_parts.append("a huge nerd who loves talking about science, technology, and geeky topics")
    #     elif nerd_level == "medium":
    #         personality_parts.append("knowledgeable about science and technology")
    #     elif nerd_level == "low":
    #         personality_parts.append("occasionally discusses technical topics")
    #
    #     personality_description = ", ".join(personality_parts)
    #
    #     instructions = f"""{base_instruction}You are {personality_description}.

# Important guidelines:
# - Keep responses under {self.max_response_length} characters
# - Be conversational and engaging
# - Stay in character based on your personality traits
# - Don't mention that you're an AI unless directly asked
# - If someone asks about commands or bot features, be helpful but stay in character"""
#
#         return instructions
#
#     def format_conversation_history(self, messages: List[tuple]) -> List[Dict]:
#         """
#         Format raw message history into the format expected by the API.
#
#         Args:
#             messages (List[tuple]): List of (user_name, message, is_bot) tuples
#
#         Returns:
#             List[Dict]: Formatted message history
#         """
#         formatted_messages = []
#
#         for user_name, message, is_bot in messages:
#             if is_bot:
#                 formatted_messages.append({"role": "assistant", "content": message})
#             else:
#                 formatted_messages.append({"role": "user", "content": f"{user_name}: {message}"})
#
#         return formatted_messages

    # def update_guild_ai_settings(self, guild_id: int, **kwargs) -> bool:
    #     """
    #     Update AI models for a guild.
    #
    #     Args:
    #         guild_id (int): Guild ID
    #         **kwargs: AI models to update
    #
    #     Returns:
    #         bool: Success status
    #     """
    #     guild_dao = GuildDao()
    #     try:
    #         return guild_dao.update_ai_settings(guild_id, **kwargs)
    #     except Exception as e:
    #         logger.error(f"Error updating AI models for guild {guild_id}: {e}")
    #         return False

    # def get_guild_ai_settings(self, guild_id: int) -> Optional[Dict]:
    #     """
    #     Get AI models for a guild.
    #
    #     Args:
    #         guild_id (int): Guild ID
    #
    #     Returns:
    #         dict: AI models or None
    #     """
    #     guild_dao = GuildDao()
    #     try:
    #         return guild_dao.get_ai_settings(guild_id)
    #     except Exception as e:
    #         logger.error(f"Error getting AI models for guild {guild_id}: {e}")
    #         return None

    def validate_message(self, message: str) -> bool:
        """
        Validate message against inappropriate words list.

        Args:
            message (str): Message to validate

        Returns:
            bool: True if message is appropriate
        """
        if not self.inappropriate_words:
            return True

        message_lower = message.lower()
        for word in self.inappropriate_words:
            if word.lower() in message_lower:
                logger.warning(f"Inappropriate word detected: {word}")
                return False

        return True

    async def moderate_content(self, text: str) -> bool:
        """
        Use OpenAI's moderation API to check content.

        Args:
            text (str): Text to moderate

        Returns:
            bool: True if content is appropriate
        """
        try:
            response = self.client.moderations.create(input=text)

            if response.results and len(response.results) > 0:
                result = response.results[0]
                if result.flagged:
                    logger.warning(f"Content flagged by moderation: {result.categories}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error in content moderation: {e}")
            # If moderation fails, allow the content (fail-safe)
            return True

    async def generate_image(
        self,
        guild_id: str,
        user_id: str,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard"
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Generate an image using DALL-E 3.

        Args:
            guild_id: Discord guild ID
            user_id: Discord user ID
            prompt: Image generation prompt
            size: Image size (1024x1024, 1792x1024, 1024x1792)
            quality: Image quality (standard or hd)

        Returns:
            Tuple of (success, image_url, error_message)
        """
        try:
            logger.info(f"Generating image for guild {guild_id}, user {user_id}: {prompt[:50]}...")

            # Validate size
            valid_sizes = ["1024x1024", "1792x1024", "1024x1792"]
            if size not in valid_sizes:
                return False, None, f"Invalid size. Must be one of: {', '.join(valid_sizes)}"

            # Validate quality
            if quality not in ["standard", "hd"]:
                return False, None, "Invalid quality. Must be 'standard' or 'hd'"

            # Generate image in thread to avoid blocking Discord heartbeat
            import asyncio
            response = await asyncio.to_thread(
                self.client.images.generate,
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality=quality,
                n=1
            )

            if response.data and len(response.data) > 0:
                image_data = response.data[0]
                image_url = image_data.url
                revised_prompt = getattr(image_data, 'revised_prompt', None)

                # Save to database
                ai_image = AIImage(
                    guild_id=guild_id,
                    user_id=user_id,
                    type='generation',
                    prompt=prompt,
                    image_url=image_url,
                    revised_prompt=revised_prompt,
                    model='dall-e-3',
                    size=size,
                    quality=quality,
                    created_at=datetime.now()
                )

                with AIImageDao() as image_dao:
                    image_dao.add_image(ai_image)

                # Record usage in AIUsage table for tracking/limits
                from Dao.AIUsageDao import AIUsageDao
                cost_usd = 0.04 if quality == 'standard' else 0.08  # DALL-E 3 pricing
                with AIUsageDao() as usage_dao:
                    usage_dao.record_usage(
                        guild_id=guild_id,
                        user_id=user_id,
                        usage_type='image_generation',
                        model='dall-e-3',
                        tokens_used=0,  # DALL-E doesn't use tokens
                        cost_usd=cost_usd
                    )

                logger.info(f"Image generated successfully for guild {guild_id}, Cost: ${cost_usd}")
                return True, image_url, revised_prompt

            else:
                logger.warning("No image data returned from DALL-E")
                return False, None, "No image was generated"

        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit for image generation: {e}")
            return False, None, "Image generation is experiencing high demand. Please try again later."

        except openai.BadRequestError as e:
            logger.error(f"Bad request for image generation: {e}")
            error_msg = str(e)
            if "content_policy_violation" in error_msg.lower():
                return False, None, "Your prompt was rejected by our content policy. Please try a different prompt."
            return False, None, "Your request could not be processed. Please rephrase your prompt."

        except openai.APIError as e:
            logger.error(f"OpenAI API error for image generation: {e}")
            return False, None, "Technical issue with image generation. Please try again."

        except Exception as e:
            logger.error(f"Error generating image: {e}", exc_info=True)
            return False, None, "An unexpected error occurred while generating the image."

    async def analyze_image(
        self,
        guild_id: str,
        user_id: str,
        image_url: str,
        question: str = "What's in this image?"
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Analyze an image using GPT-4 Vision.

        Args:
            guild_id: Discord guild ID
            user_id: Discord user ID
            image_url: URL of the image to analyze
            question: Question to ask about the image

        Returns:
            Tuple of (success, analysis_result, error_message)
        """
        try:
            logger.info(f"Analyzing image for guild {guild_id}, user {user_id}: {question[:50]}...")

            # Use GPT-4 Vision model in thread to avoid blocking Discord heartbeat
            import asyncio
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4o",  # gpt-4o has vision capabilities
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": question
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )

            if response.choices and len(response.choices) > 0:
                analysis_result = response.choices[0].message.content.strip()

                # Save to database
                ai_image = AIImage(
                    guild_id=guild_id,
                    user_id=user_id,
                    type='analysis',
                    prompt=question,
                    image_url=image_url,
                    analysis_result=analysis_result,
                    model='gpt-4o',
                    created_at=datetime.now()
                )

                with AIImageDao() as image_dao:
                    image_dao.add_image(ai_image)

                # Record usage in AIUsage table for tracking/limits
                from Dao.AIUsageDao import AIUsageDao
                tokens_used = 0
                cost_usd = 0.0

                if hasattr(response, 'usage'):
                    tokens_used = response.usage.total_tokens
                    # GPT-4o pricing (approximate)
                    cost_usd = (response.usage.prompt_tokens * 0.000005 + response.usage.completion_tokens * 0.000015)

                with AIUsageDao() as usage_dao:
                    usage_dao.record_usage(
                        guild_id=guild_id,
                        user_id=user_id,
                        usage_type='image_analysis',
                        model='gpt-4o',
                        tokens_used=tokens_used,
                        cost_usd=cost_usd
                    )

                logger.info(f"Image analyzed successfully for guild {guild_id}, Tokens: {tokens_used}, Cost: ${cost_usd:.6f}")
                return True, analysis_result, None

            else:
                logger.warning("No analysis returned from GPT-4 Vision")
                return False, None, "No analysis was generated"

        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit for image analysis: {e}")
            return False, None, "Image analysis is experiencing high demand. Please try again later."

        except openai.BadRequestError as e:
            logger.error(f"Bad request for image analysis: {e}")
            return False, None, "Could not analyze this image. Please ensure the URL is valid and accessible."

        except openai.APIError as e:
            logger.error(f"OpenAI API error for image analysis: {e}")
            return False, None, "Technical issue with image analysis. Please try again."

        except Exception as e:
            logger.error(f"Error analyzing image: {e}", exc_info=True)
            return False, None, "An unexpected error occurred while analyzing the image."

    @classmethod
    def OpenAIClient(cls):
        pass