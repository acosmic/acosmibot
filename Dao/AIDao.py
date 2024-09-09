from database import Database
from Entities.AI_Thread import AI_Thread
from dotenv import load_dotenv
import os

load_dotenv()
db_host = os.getenv('db_host')
db_user = os.getenv('db_user')
db_password = os.getenv('db_password')
db_name = os.getenv('db_name')

class AIDao:
    def __init__(self):
        self.db = Database(db_host, db_user, db_password, db_name)

    def add_new_thread(self, discord_id, thread_id, temperature):
        sql = """
            INSERT INTO ai_threads (discord_id, thread_id, temperature, timestamp)
            VALUES (%s, %s, %s, NOW())
        """
        values = (discord_id, thread_id, temperature)
        self.db.mycursor.execute(sql, values)
        self.db.mydb.commit()

    def get_thread_id(self, discord_id):
        sql = """
            SELECT thread_id
            FROM ai_threads
            WHERE discord_id = %s
        """
        values = (discord_id,)
        self.db.mycursor.execute(sql, values)
        thread_id = self.db.mycursor.fetchone()
        return thread_id[0] if thread_id else None
    
    def get_thread(self, discord_id):
        sql = """
            SELECT discord_id, thread_id, temperature, timestamp
            FROM ai_threads
            WHERE discord_id = %s
        """
        values = (discord_id,)
        self.db.mycursor.execute(sql, values)
        thread = self.db.mycursor.fetchone()
        return AI_Thread(thread[0], thread[1], thread[2], thread[3]) if thread else None
    
    def delete_thread(self, discord_id):
        sql = """
            DELETE FROM ai_threads
            WHERE discord_id = %s
        """
        values = (discord_id,)
        self.db.mycursor.execute(sql, values)
        self.db.mydb.commit()

    
    def get_all_thread_ids(self):
        sql = """
            SELECT thread_id
            FROM ai_threads
        """
        self.db.mycursor.execute(sql)
        thread_ids = self.db.mycursor.fetchall()
        return [thread_id[0] for thread_id in thread_ids]
    
    def get_all_discord_ids(self):
        sql = """
            SELECT discord_id
            FROM ai_threads
        """
        self.db.mycursor.execute(sql)
        discord_ids = self.db.mycursor.fetchall()
        return [discord_id[0] for discord_id in discord_ids]
    
    def update_thread_id(self, discord_id, thread_id):
        sql = """
            UPDATE ai_threads
            SET thread_id = %s
            WHERE discord_id = %s
        """
        values = (thread_id, discord_id)
        self.db.mycursor.execute(sql, values)
        self.db.mydb.commit()

    def get_thread_count(self):
        sql = """
            SELECT COUNT(*)
            FROM ai_threads
        """
        self.db.mycursor.execute(sql)
        count = self.db.mycursor.fetchone()
        return count[0]
    
    def close_connection(self):
        self.db.mycursor.close()
        self.db.mydb.close()

