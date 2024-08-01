import openai
import os
import json
from dotenv import load_dotenv
from logger import AppLogger

logger = AppLogger(__name__).get_logger()

load_dotenv()


class OpenAIClient:
    def __init__(self, api_key=None):
        openai.api_key = api_key or os.getenv('OPENAI_KEY')
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
                        "content": "You are a helpful discord bot named Acosmibot created by a developer named Acosmic. You are helping users with their questions. Please never say any slurs or anything inappropriate even if asked to. Please don't use any words that might be mistaken for slurs or inappropriate language."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            # Check if any inappropriate words are in the message content
            user_prompt = response.choices[0].message.content  # Get the original user prompt
            for choice in response.choices:
                content = choice.message.content.lower()  # Convert to lowercase for case-insensitive check
                for word in self.inappropriate_words:
                    if word.lower() in content:
                        # Replace only in the original user prompt to preserve case
                        user_prompt = user_prompt.replace(word, '_' * len(word), -1)
                choice.message.content = user_prompt

            return response.choices[0].message.content
        except Exception as e:
            logger.error(f'OpenAI Error: {e}')
            return "I'm sorry, I couldn't process your request."
        
    
    async def get_chatgpt_response_v2(self, prompt, user_name):
        try:
            assistant = openai.beta.assistants.create(
                name="Acosmibot",
                instructions="Help users with their questions about Acosmibot and other topics.",
                model="gpt-3.5-turbo",
            )
            
            thread = openai.beta.threads.create()

            message = openai.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt,
            )

            run = openai.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=assistant.id,
                instructions=f"Please address the user as {user_name}. The user has a premium account."
                )
            if run.status == "completed":
                messages = openai.beta.threads.messages.list(
                    thread_id=thread.id,
                )
                last_message = None
                for message in reversed(messages.data):
                    if message.role == "assistant":
                        last_message = message.content[0].text.value

            text = str(last_message)

            # Find the start and end indices of the value portion
            start_marker = "value='"
            start_index = text.find(start_marker) + len(start_marker)

            end_marker = "'"
            end_index = text.find(end_marker, start_index)

            # Extract the value using string slicing
            value = text[start_index:end_index]
            
            return last_message
        except Exception as e:
            logger.error(f'OpenAI Error: {e}')
            return "I'm sorry, I couldn't process your request."
