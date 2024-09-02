import openai
import os
import json
from dotenv import load_dotenv
from logger import AppLogger
from Dao.AIDao import AIDao

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

        self.assistant = openai.beta.assistants.create(
                name="Acosmibot",
                instructions="",
                model="gpt-4o-mini",
                tools = [{"type": "file_search"}],
            )

    async def create_new_thread(self, discord_id):
        aidao = AIDao()
        try:
            thread = openai.beta.threads.create()
            aidao.add_new_thread(discord_id, thread.id)
            
            logger.info(f"NEW THREAD ID: {thread.id}")
            return thread.id
        
        except Exception as e:
            logger.error(f'OpenAI create_new_thread() Error: {e}')
            return None
        
        
    
    async def get_chatgpt_response(self, prompt, user_name, discord_id):
        aidao = AIDao()
        try:
            user_thread_id = aidao.get_thread_id(discord_id)
            if user_thread_id is None:
                user_thread_id = await self.create_new_thread(discord_id)
            
        except Exception as e:
            logger.error(f'OpenAI get_chatgpt_response() Error: {e}')
                
        try:
            # Step 1: Upload the file (README.md)
            file = openai.files.create(
                file=open("README.md", "rb"),
                purpose="assistants"
            )
            logger.info(str(file))

            # Step 2: Create a vector store for documentation
            vector_store = openai.beta.vector_stores.create(name="Acosmibot Documentation")
            file_paths = ["README.md"]
            file_streams = [open(path, "rb") for path in file_paths]

            # Upload and poll SDK helper to upload files to the vector store
            file_batch = openai.beta.vector_stores.file_batches.upload_and_poll(
                vector_store_id=vector_store.id, files=file_streams
            )

            # Step 3: Update the assistant to use the vector store for file search
            self.assistant = openai.beta.assistants.update(
                assistant_id=self.assistant.id,
                tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
            )

            # # Step 4: Attach the file to a new message in the existing thread
            # test_thread = "thread_BxDkOPLTUPGCfLiG7dAKM9WD"

            # Correct way to create a message in the existing thread
            openai.beta.threads.messages.create(
                thread_id=user_thread_id,
                role="user",
                content=prompt,
                attachments=[
                    {"file_id": file.id, "tools": [{"type": "file_search"}]}
                ]
            )

            # Step 5: Run the assistant on the updated thread
            run = openai.beta.threads.runs.create_and_poll(
                thread_id=user_thread_id,
                assistant_id=self.assistant.id,
                instructions=f"Your name is Acosmibot. Please address the user as {user_name}. Help users with Acosmibot Documentation on how to use the listed Slash Commands and Features of Acosmibot. Keep responses less than 2000 characters."
            )

            if run.status == "completed":
                # List messages from the thread to get the response
                messages = openai.beta.threads.messages.list(
                    thread_id=user_thread_id,
                )
                last_message = None

                # Find the last assistant message
                for message in reversed(messages.data):
                    if message.role == "assistant":
                        last_message = message.content[0].text.value

                # DEBUGGING 
                message_count = 0
                for message in reversed(messages.data):
                    logger.info(f"{user_name} - {user_thread_id} - {message_count} | {message.role} | {message.content[0].text.value}\n")
                    message_count += 1 
                logger.info(f"FULL THREAD DATA: {messages.data}")

                dev_string = f"\n\n-# user: {user_name} - thread_id: {user_thread_id} count: {message_count}"    
            
            return last_message+dev_string

        except Exception as e:
            logger.error(f'OpenAI Error: {e}')
            return "I'm sorry, I couldn't process your request."
        

