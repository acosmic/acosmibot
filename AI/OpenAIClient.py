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

    async def create_new_thread(user_name, prompt):
        try:
            file = openai.files.create(
                file=open("README.md", "+rb"),
                purpose="assistants"
            )

            vector_store = openai.beta.vector_stores.create(name="Acosmibot Documentation")
            file_paths = ["README.md",]
            file_streams = [open(path, "rb") for path in file_paths]

            file_batch = openai.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id, files=file_streams
            )

            assistant = openai.beta.assistants.create(
                name="Acosmibot",
                instructions="",
                model="gpt-4o-mini",
                tools = [{"type": "file_search"}],
                
            )

            assistant = openai.beta.assistants.update(
                assistant_id=assistant.id,
                tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
            )

            message_file = openai.files.create(
                file=open("README.md", "rb"), purpose="assistants"
            )
            
            thread = openai.beta.threads.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "attachments": [
                            { "file_id": message_file.id, "tools":[{"type": "file_search"}]}
                        ]
                    }
                ]
            )

            # MAKE DAO FILE AND STORE THREAD ID TO DATABASE FUNCTION HERE

            return thread.id
        except Exception as e:
            logger.error(f'OpenAI Error: {e}')
            return None
        
    

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
            file = openai.files.create(
                file=open("README.md", "rb"),
                purpose="assistants"
            )
            
            logger.info(str(file))


            vector_store = openai.beta.vector_stores.create(name="Acosmibot Documentation")

            file_paths = ["README.md",]
            file_streams = [open(path, "rb") for path in file_paths]

            # Use the upload and poll SDK helper to upload the files, add them to the vector store,
            # and poll the status of the file batch for completion.
            file_batch = openai.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id, files=file_streams
)

            assistant = openai.beta.assistants.create(
                name="Acosmibot",
                instructions="",
                model="gpt-4o-mini",
                tools = [{"type": "file_search"}],
                
            )

            assistant = openai.beta.assistants.update(
                assistant_id=assistant.id,
                tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
            )

            message_file = openai.files.create(
                file=open("README.md", "rb"), purpose="assistants"
            )
            
            thread = openai.beta.threads.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "attachments": [
                            { "file_id": message_file.id, "tools":[{"type": "file_search"}]}
                        ]
                    }
                ]
            )

            run = openai.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=assistant.id,
                instructions=f"Your name is Acosmibot. Please address the user as {user_name}. Help users with Acosmibot Documentaion how to use the listed Slash Commands and Features of Acosmibot. Keep reponses less than 2000 characters."
                )
            
            if run.status == "completed":
                messages = openai.beta.threads.messages.list(
                    thread_id=thread.id,
                )
                last_message = None
                for message in reversed(messages.data):
                    if message.role == "assistant":
                        last_message = message.content[0].text.value
            
            return last_message
        except Exception as e:
            logger.error(f'OpenAI Error: {e}')
            return "I'm sorry, I couldn't process your request."
