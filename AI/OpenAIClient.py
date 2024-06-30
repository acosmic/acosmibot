
import openai
import os
from dotenv import load_dotenv
from logger import AppLogger

logger = AppLogger(__name__).get_logger()

load_dotenv()

class OpenAIClient:
    def __init__(self, api=os.getenv('OPENAI_KEY')):
        openai.api_key = api

    async def get_chatgpt_response(self, prompt):
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                max_tokens=300,
                # temperature=0.5,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful discord bot named Acosmibot created by a developer named Acosmic. You are helping users with their questions."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ] 
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f'OpenAI Error: {e}')
            return "I'm sorry, I couldn't process your request."
