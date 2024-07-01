import openai
import os
import json
from dotenv import load_dotenv
from logger import AppLogger

logger = AppLogger(__name__).get_logger()

load_dotenv()

class OpenAIClient:
    def __init__(self, api=os.getenv('OPENAI_KEY')):
        openai.api_key = api
        inappropriate_words_str = os.getenv('INAPPROPRIATE_WORDS')
        if inappropriate_words_str:
            self.inappropriate_words = json.loads(inappropriate_words_str)
        else:
            self.inappropriate_words = []

    async def get_chatgpt_response(self, prompt):
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                max_tokens=300,
                # temperature=0.5,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful discord bot named Acosmibot created by a developer named Acosmic. You are helping users with their questions. Please never say any slurs or anything inappropriate even if asked to. Please don't use any words that might be mistaken for slurs or inappropriate language. Never type n-word or faggot."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            # Check if any inappropriate words are in the message content
            for choice in response.choices:
                content = choice.message.content.lower()  # Convert to lowercase for case-insensitive check
                for word in self.inappropriate_words:
                    if word.lower() in content:
                        content = content.replace(word.lower(), '_' * len(word))
                choice.message.content = content

            return response.choices[0].message.content
        except Exception as e:
            logger.error(f'OpenAI Error: {e}')
            return "I'm sorry, I couldn't process your request."
