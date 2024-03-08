from database import Database
from Entities.DeathrollEvent import DeathrollEvent
from dotenv import load_dotenv
import os

load_dotenv()
db_host = os.getenv('db_host')
db_user = os.getenv('db_user')
db_password = os.getenv('db_password')
db_name = os.getenv('db_name')

class DeathrollDao:
    def __init__(self):
        self.db = Database(db_host, db_user, db_password, db_name)
    
        def add_new_event(self, deathroll_event):
            sql = """
                INSERT INTO Deathroll (initiator, acceptor, bet, message_id, current_roll, current_player, is_finished) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                deathroll_event.initiator,
                deathroll_event.acceptor,
                deathroll_event.bet,
                deathroll_event.message_id,
                deathroll_event.current_roll,
                deathroll_event.current_player,
                deathroll_event.is_finished
            )
            self.db.mycursor.execute(sql, values)
            self.db.mydb.commit()
    
        def get_event(self, message_id):
            sql = """
                SELECT * FROM Deathroll
                WHERE message_id = %s
            """
            values = (message_id, )
            self.db.mycursor.execute(sql, values)
            event = self.db.mycursor.fetchone()
            return DeathrollEvent(*event)
    
        def update_event(self, deathroll_event):
            sql = """
                UPDATE Deathroll
                SET current_roll = %s, current_player = %s, is_finished = %s
                WHERE message_id = %s
            """
            values = (
                deathroll_event.current_roll,
                deathroll_event.current_player,
                deathroll_event.is_finished,
                deathroll_event.message_id
            )
            self.db.mycursor.execute(sql, values)
            self.db.mydb.commit()
    
        def delete_event(self, message_id):
            sql = """
                DELETE FROM Deathroll
                WHERE message_id = %s
            """
            values = (message_id, )
            self.db.mycursor.execute(sql, values)
            self.db.mydb.commit()

        def get_all_events(self):
            sql = """
                SELECT * FROM Deathroll
            """
            self.db.mycursor.execute(sql)
            events = self.db.mycursor.fetchall()
            return [DeathrollEvent(*event) for event in events]
    
        def close_connection(self):
            self.db.mycursor.close()
            self.db.mydb.close()