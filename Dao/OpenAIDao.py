from database import Database
from Entities.AI_Thread import AI_Thread
from dotenv import load_dotenv
import os

load_dotenv()
db_host = os.getenv('db_host')
db_user = os.getenv('db_user')
db_password = os.getenv('db_password')
db_name = os.getenv('db_name')

class OpenAIDao:
    def __init__(self):
        self.db = Database(db_host, db_user, db_password, db_name)

    # def add_new_thread(self, ai_thread):
    #     sql = """
    #     INSERT INTO ai_threads 
    #     """