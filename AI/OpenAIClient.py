import openai
import os
import json
from dotenv import load_dotenv
from logger import AppLogger
from Dao.GuildDao import GuildDao
from datetime import datetime, time
from typing import List, Dict, Optional

logger = AppLogger(__name__).get_logger()

load_dotenv()


class OpenAIClient:
    def __init__(self, api_key=None):
        # Initialize OpenAI client
        self.client = openai.OpenAI(
            api_key=api_key or os.getenv('OPENAI_KEY')
        )

        inappropriate_words_str = os.getenv('INAPPROPRIATE_WORDS')

        if inappropriate_words_str:
            self.inappropriate_words = json.loads(inappropriate_words_str)
        else:
            self.inappropriate_words = []

        # Configuration
        self.max_conversation_length = 20  # Keep last 20 messages for context
        self.max_response_length = 1500

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
            # Get guild and its AI settings
            guild = guild_dao.get_guild(guild_id)

            if not guild:
                logger.error(f"Guild {guild_id} not found")
                return "Sorry, I couldn't access the server settings."

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

    def _build_conversation_messages(self, prompt: str, user_name: str, guild, conversation_history: List[Dict]) -> \
    List[Dict]:
        """
        Build the conversation messages array for the API call.

        Args:
            prompt (str): Current user message
            user_name (str): Discord username
            guild: Guild object with AI settings
            conversation_history (List[Dict]): Previous messages

        Returns:
            List[Dict]: Formatted messages for API
        """
        messages = []

        # System message with personality
        system_message = self._build_system_message(guild.ai_personality_traits or {}, user_name)
        messages.append({"role": "system", "content": system_message})

        # Add conversation history (keep it manageable)
        if conversation_history:
            # Keep only recent messages to stay within token limits
            recent_history = conversation_history[-self.max_conversation_length:]
            for msg in recent_history:
                messages.append(msg)

        # Add current user message
        messages.append({"role": "user", "content": f"{user_name}: {prompt}"})

        return messages

    def _build_system_message(self, personality_traits: Dict, user_name: str) -> str:
        """
        Build the system message based on guild's AI personality traits.

        Args:
            personality_traits (Dict): Guild's personality settings
            user_name (str): Discord username

        Returns:
            str: System message
        """
        base_instruction = f"You are Acosmibot, an AI assistant in a Discord server. You're currently talking with {user_name}. "

        # Build personality based on traits
        personality_parts = []

        humor_level = personality_traits.get("humor_level", "medium")
        if humor_level == "high":
            personality_parts.append("very humorous and witty")
        elif humor_level == "medium":
            personality_parts.append("moderately humorous")
        elif humor_level == "low":
            personality_parts.append("occasionally humorous")

        sarcasm_level = personality_traits.get("sarcasm_level", "medium")
        if sarcasm_level == "high":
            personality_parts.append("quite sarcastic")
        elif sarcasm_level == "medium":
            personality_parts.append("moderately sarcastic")
        elif sarcasm_level == "low":
            personality_parts.append("mildly sarcastic")

        friendliness = personality_traits.get("friendliness", "high")
        if friendliness == "high":
            personality_parts.append("very friendly and welcoming")
        elif friendliness == "medium":
            personality_parts.append("friendly")
        elif friendliness == "low":
            personality_parts.append("cordial but reserved")

        nerd_level = personality_traits.get("nerd_level", "high")
        if nerd_level == "high":
            personality_parts.append("a huge nerd who loves talking about science, technology, and geeky topics")
        elif nerd_level == "medium":
            personality_parts.append("knowledgeable about science and technology")
        elif nerd_level == "low":
            personality_parts.append("occasionally discusses technical topics")

        personality_description = ", ".join(personality_parts)

        instructions = f"""{base_instruction}You are {personality_description}.

Important guidelines:
- Keep responses under {self.max_response_length} characters
- Be conversational and engaging
- Stay in character based on your personality traits
- Don't mention that you're an AI unless directly asked
- If someone asks about commands or bot features, be helpful but stay in character"""

        return instructions

    def format_conversation_history(self, messages: List[tuple]) -> List[Dict]:
        """
        Format raw message history into the format expected by the API.

        Args:
            messages (List[tuple]): List of (user_name, message, is_bot) tuples

        Returns:
            List[Dict]: Formatted message history
        """
        formatted_messages = []

        for user_name, message, is_bot in messages:
            if is_bot:
                formatted_messages.append({"role": "assistant", "content": message})
            else:
                formatted_messages.append({"role": "user", "content": f"{user_name}: {message}"})

        return formatted_messages

    def update_guild_ai_settings(self, guild_id: int, **kwargs) -> bool:
        """
        Update AI settings for a guild.

        Args:
            guild_id (int): Guild ID
            **kwargs: AI settings to update

        Returns:
            bool: Success status
        """
        guild_dao = GuildDao()
        try:
            return guild_dao.update_ai_settings(guild_id, **kwargs)
        except Exception as e:
            logger.error(f"Error updating AI settings for guild {guild_id}: {e}")
            return False

    def get_guild_ai_settings(self, guild_id: int) -> Optional[Dict]:
        """
        Get AI settings for a guild.

        Args:
            guild_id (int): Guild ID

        Returns:
            dict: AI settings or None
        """
        guild_dao = GuildDao()
        try:
            return guild_dao.get_ai_settings(guild_id)
        except Exception as e:
            logger.error(f"Error getting AI settings for guild {guild_id}: {e}")
            return None

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

    @classmethod
    def OpenAIClient(cls):
        pass